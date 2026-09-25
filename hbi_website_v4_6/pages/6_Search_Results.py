"""Global Search Results — cross-section search across all HBI directory sections."""

import html as _html
from urllib.parse import quote

import pandas as pd
import streamlit as st
from st_keyup import st_keyup
from utils.page_config import BLANK_PAGE_ICON

from utils.components import (
    COMMUNITY_TEAL,
    INSTITUTION_COLOR,
    UCALGARY_RED,
    format_research_label,
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_grid,
    render_card_html,
    render_community_card_html,
)
from utils.data_loader import (
    build_directory_data,
    load_hybrid_research_taxonomy,
    load_member_institution_tags,
    load_source_research_phrases,
)
from utils.linkedin_data_loader import (
    build_community_directory_data,
    load_li_institution_tags,
)
from utils.profile_search import search_community_profiles, search_member_profiles

st.set_page_config(
    page_title="Search – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_custom_css()
render_public_sidebar_navigation()

_esc = lambda s: _html.escape(str(s)) if s else ""

# ── Read query ────────────────────────────────────────────────────────────────
incoming_query = st.session_state.pop("global_search_query", "").strip()
if incoming_query:
    st.session_state["global_search_generation"] = (
        st.session_state.get("global_search_generation", 0) + 1
    )
initial_query = incoming_query or st.query_params.get("q", "").strip()
query = st_keyup(
    "Search all profiles",
    value=initial_query,
    placeholder="Name, keyword, expertise, publication…",
    key=f"global_search_{st.session_state.get('global_search_generation', 0)}",
    debounce=250,
)

if not query:
    st.warning("No search query provided.")
    if st.button("← Back to Home"):
        st.switch_page("Home.py")
    st.stop()

q_lower = query.lower()

st.markdown(
    f'<div class="hbi-banner">'
    f'<h1>Search Results</h1>'
    f'<p>Results for &ldquo;<strong>{_esc(query)}</strong>&rdquo;</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Load all data (cached) ────────────────────────────────────────────────────
_members_dir = build_directory_data()
_community_dir = build_community_directory_data()
_hybrid = load_hybrid_research_taxonomy()
_source_phrases = load_source_research_phrases()
_source_member_ids = set(_source_phrases["member_id"])
_hybrid_source_fallback = _hybrid.loc[
    _hybrid["candidate_origin"].str.contains(
        r"structured_source|legacy_research_narrative|biography_",
        case=False,
        na=False,
        regex=True,
    )
    & ~_hybrid["member_id"].isin(_source_member_ids),
    ["member_id", "input_phrase"],
].rename(columns={"input_phrase": "area"})
_source_areas = _source_phrases[["member_id", "phrase"]].rename(
    columns={"phrase": "area"}
)
_hybrid_standardized = _hybrid.loc[
    _hybrid["disposition"].eq("accepted"),
    ["member_id", "preferred_display_label"],
].rename(columns={"preferred_display_label": "area"})
_research_tags = (
    pd.concat(
        [_source_areas, _hybrid_source_fallback, _hybrid_standardized],
        ignore_index=True,
    )
    .dropna(subset=["area"])
    .drop_duplicates(["member_id", "area"])
)
_member_inst = load_member_institution_tags()        # member_id, institution_tag
_community_inst = load_li_institution_tags()         # profile_id, institution_tag

# ── Search helpers ────────────────────────────────────────────────────────────

def _col_contains(val, q: str) -> bool:
    if val is None:
        return False
    if isinstance(val, list):
        return any(q in str(v).lower() for v in val)
    return q in str(val).lower()


# ── HBI Members ───────────────────────────────────────────────────────────────
_member_results = search_member_profiles(query)
_mem_match = _member_results.merge(_members_dir, on="member_id", how="inner")

# ── Community Profiles ────────────────────────────────────────────────────────
_community_results = search_community_profiles(query)
_comm_match = _community_results.merge(_community_dir, on="profile_id", how="inner")

# ── Research Areas ────────────────────────────────────────────────────────────
_ra_match = _research_tags[
    _research_tags["area"].str.lower().str.contains(q_lower, na=False)
]
_ra_summary = (
    _ra_match.groupby("area")["member_id"]
    .nunique()
    .reset_index()
    .rename(columns={"member_id": "member_count"})
    .sort_values("member_count", ascending=False)
    .reset_index(drop=True)
)

# ── Organizations ─────────────────────────────────────────────────────────────
_org_mem = _member_inst[
    _member_inst["institution_tag"].str.lower().str.contains(q_lower, na=False)
]
_org_comm = _community_inst[
    _community_inst["institution_tag"].str.lower().str.contains(q_lower, na=False)
]
_org_all = pd.concat(
    [
        _org_mem[["institution_tag"]].assign(src="member"),
        _org_comm[["institution_tag"]].assign(src="community"),
    ],
    ignore_index=True,
)
_org_summary = (
    _org_all.groupby("institution_tag")
    .agg(
        member_count=("src", lambda x: (x == "member").sum()),
        community_count=("src", lambda x: (x == "community").sum()),
    )
    .reset_index()
    .sort_values(["member_count", "community_count"], ascending=False)
    .reset_index(drop=True)
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
_MAX_CARDS = 30

_tab_labels = [
    f"HBI Members ({len(_mem_match)})",
    f"Community ({len(_comm_match)})",
    f"Research Areas ({len(_ra_summary)})",
    f"Organizations ({len(_org_summary)})",
]

tab_mem, tab_comm, tab_ra, tab_org = st.tabs(_tab_labels)

# ── HBI Members tab ───────────────────────────────────────────────────────────
with tab_mem:
    if _mem_match.empty:
        st.info("No HBI members matched your search.")
    else:
        _cards = []
        for _, row in _mem_match.head(_MAX_CARDS).iterrows():
            _pp = row.get("photo_path", "")
            _photo = f"/app/static/images/member/{_pp}" if _pp and pd.notna(_pp) else None
            _cards.append(
                render_card_html(
                    name=str(row.get("name") or ""),
                    title=str(row.get("title") or ""),
                    department=str(row.get("department") or ""),
                    areas=row.get("research_areas_list") or [],
                    member_id=str(row.get("member_id") or ""),
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list") or [],
                )
            )
        st.markdown(render_card_grid(_cards), unsafe_allow_html=True)
        if len(_mem_match) > _MAX_CARDS:
            st.caption(
                f"Showing first {_MAX_CARDS} of {len(_mem_match)} results. "
                "Try a more specific search term to narrow results."
            )

# ── Community tab ─────────────────────────────────────────────────────────────
with tab_comm:
    if _comm_match.empty:
        st.info("No community profiles matched your search.")
    else:
        _cards = []
        for _, row in _comm_match.head(_MAX_CARDS).iterrows():
            _pp = row.get("photo_path", "")
            _photo = f"/app/static/images/community/{_pp}" if _pp and pd.notna(_pp) else None
            _cards.append(
                render_community_card_html(
                    name=str(row.get("full_name") or ""),
                    current_title=str(row.get("current_title") or ""),
                    current_company=str(row.get("current_company") or ""),
                    location=str(row.get("location") or ""),
                    tags=row.get("research_tags_list") or [],
                    profile_id=str(row.get("profile_id") or ""),
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list") or [],
                )
            )
        st.markdown(render_card_grid(_cards), unsafe_allow_html=True)
        if len(_comm_match) > _MAX_CARDS:
            st.caption(
                f"Showing first {_MAX_CARDS} of {len(_comm_match)} results. "
                "Try a more specific search term to narrow results."
            )

# ── Research Areas tab ────────────────────────────────────────────────────────
with tab_ra:
    if _ra_summary.empty:
        st.info("No areas of research matched your search.")
    else:
        for _, row in _ra_summary.head(_MAX_CARDS).iterrows():
            area = str(row["area"])
            display_area = format_research_label(area)
            count = int(row["member_count"])
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:10px 14px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:6px;">'
                f'<span style="font-weight:600;font-size:0.95rem;'
                f'color:{UCALGARY_RED};">{_esc(display_area)}</span>'
                f'<span style="font-size:0.82rem;color:#888;">'
                f'{count} member{"s" if count != 1 else ""}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Organizations tab ─────────────────────────────────────────────────────────
with tab_org:
    if _org_summary.empty:
        st.info("No organizations matched your search.")
    else:
        for _, row in _org_summary.head(_MAX_CARDS).iterrows():
            org = str(row["institution_tag"])
            mem_cnt = int(row["member_count"])
            comm_cnt = int(row["community_count"])
            href = f"/Organizations?org={quote(org)}"
            parts = []
            if mem_cnt:
                parts.append(f"{mem_cnt} HBI member{'s' if mem_cnt != 1 else ''}")
            if comm_cnt:
                parts.append(f"{comm_cnt} community profile{'s' if comm_cnt != 1 else ''}")
            subtitle = " · ".join(parts) if parts else "Organization"
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:10px 14px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:6px;">'
                f'<a href="{href}" style="font-weight:600;font-size:0.95rem;'
                f'color:{INSTITUTION_COLOR};text-decoration:none;">{_esc(org)}</a>'
                f'<span style="font-size:0.82rem;color:#888;">{subtitle}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
