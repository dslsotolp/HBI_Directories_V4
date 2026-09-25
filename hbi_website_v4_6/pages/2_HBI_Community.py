"""HBI Community — LinkedIn profiles directory."""

from datetime import datetime

import pandas as pd
import streamlit as st
from st_keyup import st_keyup
from utils.page_config import BLANK_PAGE_ICON

from utils.components import (
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_grid,
    render_community_card_html,
    render_community_list_row_html,
    render_list_view,
    COMMUNITY_TEAL,
    INSTITUTION_COLOR,
)
from utils.linkedin_data_loader import build_community_directory_data, load_li_institution_tags, get_all_profiles_recent_tags, load_community_location_audit
from utils.linkedin_expertise import get_all_profiles_linkedin_expertise
from utils.profile_search import search_community_profiles

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Community Directory – LinkedIn Profiles",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_custom_css()
render_public_sidebar_navigation("community")

# ── Data ──────────────────────────────────────────────────────────────────────
directory = build_community_directory_data()

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="li-banner">
        <h1>Community Directory</h1>
        <p>Current &amp; Past Trainees, Alumni and Staff · Hotchkiss Brain Institute</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar filters ───────────────────────────────────────────────────────────
_FILTER_KEYS = ["comm_search", "comm_area", "comm_employer", "comm_location", "comm_edu", "comm_institution", "comm_lookback"]
_FILTER_KEYS.append("community_map_location_id")

# Apply pending reset BEFORE widgets are instantiated (Streamlit forbids
# modifying a widget's session-state key after it has been rendered).
if st.session_state.pop("_comm_reset", False):
    for _k in _FILTER_KEYS:
        if _k == "comm_institution":
            st.session_state[_k] = []
        elif _k == "comm_lookback":
            st.session_state[_k] = 10
        elif _k == "comm_search":
            st.session_state["comm_search_generation"] = (
                st.session_state.get("comm_search_generation", 0) + 1
            )
        else:
            st.session_state[_k] = ""
    st.session_state["comm_page"] = 0

with st.sidebar:
    st.markdown('<div style="height:70px"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:0.4rem;">Search</p>', unsafe_allow_html=True)
    search_query = st_keyup(
        "Search",
        placeholder="Name, keyword, title…",
        label_visibility="collapsed",
        key=f"comm_search_{st.session_state.get('comm_search_generation', 0)}",
        debounce=250,
    )

    st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:0.4rem;">Filters</p>', unsafe_allow_html=True)

    filter_area = st.text_input("Expertise", placeholder="e.g. neuroscience", key="comm_area")
    filter_employer = st.text_input("Employer / Company", placeholder="e.g. University", key="comm_employer")
    _default_location = st.session_state.pop("community_city_filter", "")
    if _default_location:
        st.session_state["comm_location"] = _default_location
    filter_location = st.text_input("Location", placeholder="e.g. Calgary", key="comm_location")
    _map_location = st.session_state.get("community_map_location_id", "")
    if _map_location:
        _map_rows = load_community_location_audit()
        _map_rows = _map_rows[_map_rows["location_id"].eq(_map_location)]
        if not _map_rows.empty:
            st.caption(f"Map selection: {_map_rows.iloc[0]['city']}, {_map_rows.iloc[0]['country']}")
        if st.button("Clear map selection"):
            st.session_state["community_map_location_id"] = ""
            st.rerun()
    filter_edu = st.text_input("Education Institution", placeholder="e.g. Toronto", key="comm_edu")

    # Institution tags multiselect (top 50 by frequency)
    _inst_all = load_li_institution_tags()
    _inst_counts = (
        _inst_all["institution_tag"]
        .value_counts()
        .head(50)
        .index.tolist()
    )
    _inst_options = sorted(_inst_counts)
    filter_institution = st.multiselect(
        "Organization / Institution",
        options=_inst_options,
        placeholder="Select institutions…",
        key="comm_institution",
    )
    lookback = st.slider(
        "Areas of Expertise lookback (years)",
        min_value=1,
        max_value=20,
        value=10,
        step=1,
        key="comm_lookback",
        help="Show Areas of Expertise only from experience positions within this many years.",
    )
    st.markdown("---")
    if st.button("🔄 Reset All Filters", use_container_width=True):
        st.session_state["_comm_reset"] = True
        st.rerun()
# ── Apply experience-year tag filter ───────────────────────────────────────────
_min_year = datetime.now().year - lookback
_recent_tags = get_all_profiles_recent_tags(_min_year)
_recent_expertise = get_all_profiles_linkedin_expertise(
    _min_year,
    datetime.now().year,
)
directory = directory.copy()
directory["research_tags_list"] = directory["profile_id"].map(
    lambda pid: _recent_tags.get(pid, [])
)
directory["researcher_declared_areas_list"] = directory["profile_id"].map(
    lambda pid: _recent_expertise.get(str(pid), {}).get("declared_terms", [])
)
# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = directory.copy()
search_scores = {}

if search_query:
    search_results = search_community_profiles(search_query)
    search_scores = search_results.set_index("profile_id")["search_score"].to_dict()
    filtered = filtered[filtered["profile_id"].isin(search_results["profile_id"])]

if filter_area:
    fa = filter_area.lower()
    filtered = filtered[
        filtered["research_tags_list"].apply(
            lambda tags: any(fa in t.lower() for t in tags)
        )
    ]

if filter_employer:
    fe = filter_employer.lower()
    filtered = filtered[
        filtered["current_company"].str.lower().str.contains(fe, na=False)
        | filtered["institution_tags_list"].apply(
            lambda tags: any(fe in t.lower() for t in tags)
        )
    ]

if filter_location:
    fl = filter_location.lower()
    filtered = filtered[
        filtered["location"].str.lower().str.contains(fl, na=False)
    ]

if st.session_state.get("community_map_location_id"):
    _map_audit = load_community_location_audit()
    _map_ids = _map_audit.loc[
        _map_audit["location_id"].eq(st.session_state["community_map_location_id"]), "profile_id"
    ]
    filtered = filtered[filtered["profile_id"].isin(_map_ids)]

if filter_edu:
    fdu = filter_edu.lower()
    filtered = filtered[
        filtered["education_list"].apply(
            lambda schools: any(fdu in s.lower() for s in schools)
        )
    ]

if filter_institution:
    filtered = filtered[
        filtered["institution_tags_list"].apply(
            lambda itags: any(inst in itags for inst in filter_institution)
        )
    ]

if search_query:
    filtered = filtered.copy()
    filtered["search_score"] = filtered["profile_id"].map(search_scores).fillna(0)
    filtered = filtered.sort_values(["search_score", "full_name"], ascending=[False, True])
else:
    filtered = filtered.sort_values("full_name")
filtered = filtered.reset_index(drop=True)

# ── Results count + view toggle + per-page selector ──────────────────────────
rcount_col, toggle_col, perpage_col = st.columns([3, 1, 1])
with rcount_col:
    st.markdown(f"Showing **{len(filtered)}** of **{len(directory)}** profiles")
with toggle_col:
    st.markdown("**View mode**")
    view_mode = st.selectbox(
        "View mode", ["Grid", "List"], index=0, label_visibility="collapsed"
    )
with perpage_col:
    st.markdown("**Per page**")
    per_page_choice = st.selectbox(
        "Per page", ["25", "50", "100", "All"], index=0, label_visibility="collapsed"
    )

# ── Sidebar export ────────────────────────────────────────────────────────────
with st.sidebar:
    if not filtered.empty:
        export = filtered[
            ["full_name", "current_title", "current_company", "location", "profile_url"]
        ].copy()
        export.columns = ["Name", "Current Title", "Company", "Location", "LinkedIn URL"]
        export["Research Areas"] = filtered["research_tags_list"].apply(
            lambda x: "; ".join(x) if isinstance(x, list) else ""
        )
        st.download_button(
            "📥 Download Filtered Results",
            export.to_csv(index=False),
            "hbi_community_filtered.csv",
            "text/csv",
            use_container_width=True,
        )

# ── Pagination ────────────────────────────────────────────────────────────────
PER_PAGE = len(filtered) if per_page_choice == "All" else int(per_page_choice)
total_pages = max(1, -(-len(filtered) // PER_PAGE)) if PER_PAGE > 0 else 1

_fhash = hash((search_query, filter_area, filter_employer, filter_location, filter_edu, tuple(sorted(filter_institution)), per_page_choice, lookback, st.session_state.get("community_map_location_id", "")))
if st.session_state.get("_comm_fh") != _fhash:
    st.session_state["comm_page"] = 0
    st.session_state["_comm_fh"] = _fhash

page = max(0, min(st.session_state.get("comm_page", 0), total_pages - 1))
start_idx = page * PER_PAGE
page_data = filtered.iloc[start_idx : start_idx + PER_PAGE]

# ── Cards / List ──────────────────────────────────────────────────────────────
if page_data.empty:
    st.info("No profiles match your current filters. Try broadening your search.")
else:
    if view_mode == "Grid":
        cards = []
        for _, row in page_data.iterrows():
            _pp = row.get("photo_path", "")
            _photo = f"/app/static/images/community/{_pp}" if _pp and pd.notna(_pp) else None
            cards.append(
                render_community_card_html(
                    name=str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown",
                    current_title=str(row["current_title"]) if pd.notna(row.get("current_title")) else "",
                    current_company=str(row["current_company"]) if pd.notna(row.get("current_company")) else "",
                    location=str(row["location"]) if pd.notna(row.get("location")) else "",
                    tags=row.get("research_tags_list", []),
                    profile_id=str(row["profile_id"]),
                    institution_tags=row.get("institution_tags_list", []),
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                )
            )
        st.markdown(render_card_grid(cards), unsafe_allow_html=True)
    else:
        rows = []
        for _, row in page_data.iterrows():
            _pp = row.get("photo_path", "")
            _photo = f"/app/static/images/community/{_pp}" if _pp and pd.notna(_pp) else None
            rows.append(
                render_community_list_row_html(
                    name=str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown",
                    current_title=str(row["current_title"]) if pd.notna(row.get("current_title")) else "",
                    current_company=str(row["current_company"]) if pd.notna(row.get("current_company")) else "",
                    location=str(row["location"]) if pd.notna(row.get("location")) else "",
                    tags=row.get("research_tags_list", []),
                    profile_id=str(row["profile_id"]),
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                )
            )
        st.markdown(render_list_view(rows), unsafe_allow_html=True)

# ── Pagination controls ───────────────────────────────────────────────────────
if total_pages > 1:
    st.markdown("")
    prev_col, info_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if page > 0 and st.button("← Previous", use_container_width=True):
            st.session_state["comm_page"] = page - 1
            st.rerun()
    with info_col:
        st.markdown(
            f'<div style="text-align:center;color:#666;font-size:0.9rem;padding-top:8px;">'
            f'Page {page + 1} of {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with next_col:
        if page < total_pages - 1 and st.button("Next →", use_container_width=True):
            st.session_state["comm_page"] = page + 1
            st.rerun()

st.markdown("---")
st.caption("Data sourced via HBI Crawler · Hotchkiss Brain Institute")
