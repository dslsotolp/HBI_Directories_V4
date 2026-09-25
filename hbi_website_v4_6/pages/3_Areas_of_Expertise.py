"""Research Area — explorer and drill-down for research topics."""

import html as _html

import pandas as pd
import streamlit as st
from utils.page_config import BLANK_PAGE_ICON
from urllib.parse import quote, unquote

from utils.data_loader import (
    load_members,
    load_positions,
    load_research_areas,
    build_directory_data,
    load_publishable_research_tags,
)
from utils.components import (
    format_research_label,
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_html,
    render_card_grid,
    render_list_row_html,
    render_list_view,
    render_community_card_html,
    render_community_list_row_html,
    UCALGARY_RED,
    COMMUNITY_TEAL,
    render_disclaimer,
)
from utils.linkedin_data_loader import build_community_directory_data

st.set_page_config(
    page_title="Research Explorer – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
)
inject_custom_css()
render_public_sidebar_navigation()

_esc = lambda s: _html.escape(str(s)) if s else ""

# ── Get area from query params ───────────────────────────────────────────────
area_param = st.query_params.get("area", "")
area = unquote(area_param) if area_param else ""

if not area:
    # ── Research Explorer ────────────────────────────────────────────────────
    st.markdown(
        '<div class="hbi-banner">'
        '<h1>Explore Expertise</h1>'
        '<p style="font-size:1.1rem;opacity:0.9;">'
        'Browse all areas of expertise · Discover the areas of expertise of our HBI Members and Community</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Build tag summary ─────────────────────────────────────────────────────
    _ra = load_publishable_research_tags()          # member_id, area
    _dir = build_directory_data()                   # includes hbi_membership

    # Member type options from actual data
    _member_types = sorted(
        _dir["hbi_membership"].dropna().unique().tolist()
    )
    _member_types = [m for m in _member_types if m.strip()]

    # Build per-area member counts (optionally filtered by member type)
    def _build_member_counts(type_filter=None):
        _d = _dir.copy()
        if type_filter:
            _d = _d[_d["hbi_membership"] == type_filter]
        merged = _ra.merge(_d[["member_id"]], on="member_id", how="inner")
        return (
            merged.groupby("area")["member_id"]
            .nunique()
            .reset_index()
            .rename(columns={"member_id": "member_count"})
        )

    _cd = build_community_directory_data()
    _comm_exploded = (
        _cd[["profile_id", "research_tags_list"]]
        .explode("research_tags_list")
        .rename(columns={"research_tags_list": "area"})
        .dropna(subset=["area"])
    )
    community_counts = (
        _comm_exploded.groupby("area")["profile_id"]
        .nunique()
        .reset_index()
        .rename(columns={"profile_id": "community_count"})
    )

    # ── Controls ──────────────────────────────────────────────────────────────
    col_s, col_f, col_sort = st.columns([3, 2, 1.8])
    with col_s:
        search_q = st.text_input(
            "Search topics",
            placeholder="e.g. Alzheimer, sleep, pain, autism…",
            label_visibility="collapsed",
        )
    with col_f:
        _filter_options = ["All"] + _member_types + ["HBI Community"]
        show_filter = st.selectbox(
            "Filter by",
            _filter_options,
            label_visibility="collapsed",
        )
    with col_sort:
        sort_by = st.selectbox(
            "Sort",
            [
                "HBI Members  ↓",
                "HBI Members  ↑",
                "Community  ↓",
                "Community  ↑",
                "Expertise  A → Z",
                "Expertise  Z → A",
            ],
            label_visibility="collapsed",
        )

    # Resolve active member type
    _is_community_only = show_filter == "HBI Community"
    _active_type = None if show_filter in ("All", "HBI Community") else show_filter
    member_counts = _build_member_counts(_active_type)

    topic_summary = (
        member_counts
        .merge(community_counts, on="area", how="outer")
        .fillna(0)
        .assign(
            member_count=lambda d: d["member_count"].astype(int),
            community_count=lambda d: d["community_count"].astype(int),
        )
    )

    # ── Filter + sort ─────────────────────────────────────────────────────────
    if search_q.strip():
        _mask = topic_summary["area"].str.lower().str.contains(
            search_q.strip().lower(), na=False, regex=False
        )
        _topics = topic_summary[_mask].copy()
    else:
        _topics = topic_summary.copy()

    if _is_community_only:
        _topics = _topics[_topics["community_count"] > 0]
    elif _active_type:
        _topics = _topics[_topics["member_count"] > 0]

    _sort_map = {
        "HBI Members  ↓":       (["member_count", "area"],    [False, True]),
        "HBI Members  ↑":       (["member_count", "area"],    [True,  True]),
        "Community  ↓":         (["community_count", "area"], [False, True]),
        "Community  ↑":         (["community_count", "area"], [True,  True]),
        "Expertise  A → Z": (["area"],                   [True]),
        "Expertise  Z → A": (["area"],                   [False]),
    }
    _scols, _sasc = _sort_map[sort_by]
    _topics = _topics.sort_values(_scols, ascending=_sasc).reset_index(drop=True)

    _filter_label = f" · {show_filter}" if show_filter != "All" else ""
    st.caption(f"{len(_topics)} area{'s' if len(_topics) != 1 else ''} of expertise{_filter_label}")

    # ── Render topic cards ────────────────────────────────────────────────────
    cards_html = ""
    for _, _row in _topics.iterrows():
        _tag = _row["area"]
        _display_tag = format_research_label(_tag)
        _mc = int(_row["member_count"])
        _cc = int(_row["community_count"])
        _href = f"/Research_Area?area={quote(str(_tag))}"
        _mc_txt = f'{_mc} HBI member{"s" if _mc != 1 else ""}'
        _cc_txt = f'{_cc} community' if _cc > 0 else ""
        _show_members = not _is_community_only
        _show_community = show_filter in ("All", "HBI Community")
        _mc_part = (
            f'<span style="color:{UCALGARY_RED};font-weight:600;">👨\u200d🔬 {_mc_txt}</span>'
            if _show_members and _mc > 0 else ""
        )
        _sep = "&nbsp;·&nbsp;" if _mc_part and _cc_txt and _show_community else ""
        _cc_part = (
            f'<span style="color:{COMMUNITY_TEAL};font-weight:600;">🤝 {_cc_txt}</span>'
            if _show_community and _cc_txt else ""
        )
        cards_html += (
            f'<a href="{_href}" class="topic-card-link">'
            f'<div class="topic-card">'
            f'<div class="topic-card-name">{_esc(_display_tag)}</div>'
            f'<div class="topic-card-counts">'
            f'{_mc_part}{_sep}{_cc_part}'
            f'</div>'
            f'</div></a>'
        )

    st.markdown(
        f'<style>'
        f'.topic-card-link{{text-decoration:none;}}'
        f'.topic-card{{background:#fff;border:1px solid #e4e4e4;border-radius:10px;'
        f'padding:16px 18px;margin:5px;min-height:80px;display:flex;flex-direction:column;'
        f'justify-content:space-between;box-shadow:0 1px 4px rgba(0,0,0,0.05);'
        f'transition:box-shadow 0.15s,border-color 0.15s,transform 0.1s;}}'
        f'.topic-card:hover{{box-shadow:0 5px 18px rgba(0,0,0,0.13);'
        f'border-color:#CC0000;transform:translateY(-2px);}}'
        f'.topic-card-name{{font-size:0.97rem;font-weight:600;color:#1A1A1A;'
        f'line-height:1.4;margin-bottom:10px;}}'
        f'.topic-card-counts{{font-size:0.81rem;}}'
        f'.topic-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(255px,1fr));gap:0;}}'
        f'</style>'
        f'<div class="topic-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

    render_disclaimer()
    st.stop()

# ── Load data ────────────────────────────────────────────────────────────────
research_areas = load_publishable_research_tags()
directory = build_directory_data()

# Find members with this area (exact match)
matching_ids = set(
    research_areas[research_areas["area"] == area]["member_id"]
)
# Fallback: case-insensitive partial match
if not matching_ids:
    matching_ids = set(
        research_areas[
            research_areas["area"].str.lower().str.contains(area.lower(), na=False)
        ]["member_id"]
    )

filtered = (
    directory[directory["member_id"].isin(matching_ids)]
    .sort_values("name")
    .reset_index(drop=True)
)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="hbi-banner">'
    f'<h1>Expertise</h1>'
    f'<p style="font-size:1.4rem;font-weight:700;">'
    f'{_esc(format_research_label(area))}</p>'
    f'</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("← Research Explorer"):
        st.query_params.clear()
        st.rerun()

st.markdown(f'<p style="font-size:1.15rem;">{len(filtered)} members with this area of expertise</p>', unsafe_allow_html=True)

# ── View toggle ──────────────────────────────────────────────────────────────
view_mode = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

# ── Render members ───────────────────────────────────────────────────────────
if filtered.empty:
    st.info("No members found for this area of expertise.")
else:
    if view_mode == "Grid":
        cards = []
        for _, row in filtered.iterrows():
            mid = row["member_id"]
            name = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
            title = str(row["title"]) if pd.notna(row.get("title")) else ""
            dept = str(row["department"]) if pd.notna(row.get("department")) else ""
            areas = row.get("research_areas_list", [])
            if not isinstance(areas, list):
                areas = []
            cards.append(render_card_html(
                name,
                title,
                dept,
                areas,
                member_id=mid,
                declared_areas=row.get("researcher_declared_areas_list", []),
            ))
        st.markdown(render_card_grid(cards), unsafe_allow_html=True)
    else:
        rows = []
        for _, row in filtered.iterrows():
            mid = row["member_id"]
            name = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
            title = str(row["title"]) if pd.notna(row.get("title")) else ""
            dept = str(row["department"]) if pd.notna(row.get("department")) else ""
            areas = row.get("research_areas_list", [])
            if not isinstance(areas, list):
                areas = []
            rows.append(render_list_row_html(
                name,
                title,
                dept,
                areas,
                member_id=mid,
                declared_areas=row.get("researcher_declared_areas_list", []),
            ))
        st.markdown(render_list_view(rows), unsafe_allow_html=True)

# ── Community profiles with the same research area ───────────────────────────
_community_dir = build_community_directory_data()


def _tag_matches(tags, area_str: str) -> bool:
    if not isinstance(tags, list):
        return False
    area_lower = area_str.lower()
    return any(t.lower() == area_lower for t in tags)


community_matches = (
    _community_dir[
        _community_dir["research_tags_list"].apply(lambda t: _tag_matches(t, area))
    ]
    .sort_values("full_name")
    .reset_index(drop=True)
)

if not community_matches.empty:
    st.markdown("---")
    st.markdown(
        f'<div style="border-bottom:3px solid {COMMUNITY_TEAL};padding-bottom:8px;'
        f'margin-bottom:16px;">'
        f'<h3 style="color:{COMMUNITY_TEAL};margin:0;">'
        f'\U0001f91d HBI Community Profiles</h3></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"{len(community_matches)} community profiles with this area of expertise")

    if view_mode == "Grid":
        comm_cards = []
        for _, row in community_matches.iterrows():
            pid = row["profile_id"]
            fname = str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown"
            headline = str(row["headline"]) if pd.notna(row.get("headline")) else ""
            employer = str(row["current_company"]) if pd.notna(row.get("current_company")) else ""
            location = str(row["location"]) if pd.notna(row.get("location")) else ""
            tags = row.get("research_tags_list", [])
            if not isinstance(tags, list):
                tags = []
            comm_cards.append(render_community_card_html(
                fname,
                headline,
                employer,
                location,
                tags,
                profile_id=pid,
                declared_areas=row.get("researcher_declared_areas_list", []),
            ))
        st.markdown(render_card_grid(comm_cards), unsafe_allow_html=True)
    else:
        comm_rows = []
        for _, row in community_matches.iterrows():
            pid = row["profile_id"]
            fname = str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown"
            headline = str(row["headline"]) if pd.notna(row.get("headline")) else ""
            employer = str(row["current_company"]) if pd.notna(row.get("current_company")) else ""
            location = str(row["location"]) if pd.notna(row.get("location")) else ""
            tags = row.get("research_tags_list", [])
            if not isinstance(tags, list):
                tags = []
            comm_rows.append(render_community_list_row_html(
                fname,
                headline,
                employer,
                location,
                tags,
                profile_id=pid,
                declared_areas=row.get("researcher_declared_areas_list", []),
            ))
        st.markdown(render_list_view(comm_rows), unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
render_disclaimer()
