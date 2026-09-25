"""Organizations Explorer — browse all institutions and drill down to affiliated members."""

import html as _html

import pandas as pd
import streamlit as st
from utils.page_config import BLANK_PAGE_ICON
from urllib.parse import quote, unquote

from utils.data_loader import (
    build_directory_data,
    load_member_institution_tags,
)
from utils.components import (
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
    INSTITUTION_COLOR,
    render_disclaimer,
)
from utils.linkedin_data_loader import (
    build_community_directory_data,
    load_li_institution_tags,
)

st.set_page_config(
    page_title="Organizations Explorer – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
)
inject_custom_css()
render_public_sidebar_navigation("organizations")

_esc = lambda s: _html.escape(str(s)) if s else ""

# ── Get org from query params ─────────────────────────────────────────────────
org_param = st.query_params.get("org", "")
org = unquote(org_param) if org_param else ""

if not org:
    # ════════════════════════════════════════════════════════════════════════
    # ORGANIZATIONS EXPLORER
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="hbi-banner" style="background:linear-gradient(135deg,'
        f'{INSTITUTION_COLOR} 0%,#3D3480 100%);">'
        '<h1>Explore Organizations</h1>'
        '<p style="font-size:1.1rem;opacity:0.9;">'
        'Browse all affiliated universities, research institutes, and organizations · '
        'discover HBI Members and Community Profiles for each</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Build institution count tables ────────────────────────────────────────
    _member_inst = load_member_institution_tags()      # member_id, institution_tag
    _community_inst = load_li_institution_tags()       # profile_id, institution_tag
    _member_dir = build_directory_data()               # for member_id validity check

    # HBI member counts per institution (only include valid members)
    _valid_member_ids = set(_member_dir["member_id"].dropna().tolist())
    _mem_inst_valid = _member_inst[_member_inst["member_id"].isin(_valid_member_ids)]
    member_counts = (
        _mem_inst_valid.groupby("institution_tag")["member_id"]
        .nunique()
        .reset_index()
        .rename(columns={"member_id": "member_count"})
    )

    # Community profile counts per institution
    community_counts = (
        _community_inst.groupby("institution_tag")["profile_id"]
        .nunique()
        .reset_index()
        .rename(columns={"profile_id": "community_count"})
    )

    # Combined summary
    org_summary = (
        member_counts
        .merge(community_counts, on="institution_tag", how="outer")
        .fillna(0)
        .assign(
            member_count=lambda d: d["member_count"].astype(int),
            community_count=lambda d: d["community_count"].astype(int),
        )
        .rename(columns={"institution_tag": "org"})
    )

    # ── Controls ──────────────────────────────────────────────────────────────
    col_s, col_sort = st.columns([4, 2])
    with col_s:
        search_q = st.text_input(
            "Search organizations",
            placeholder="e.g. Calgary, McGill, hospital…",
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
                "Organization  A → Z",
                "Organization  Z → A",
            ],
            label_visibility="collapsed",
        )

    # ── Filter + sort ─────────────────────────────────────────────────────────
    _orgs = org_summary.copy()
    if search_q.strip():
        _orgs = _orgs[
            _orgs["org"].str.lower().str.contains(search_q.strip().lower(), na=False, regex=False)
        ]

    _sort_map = {
        "HBI Members  ↓":        (["member_count", "org"],    [False, True]),
        "HBI Members  ↑":        (["member_count", "org"],    [True,  True]),
        "Community  ↓":          (["community_count", "org"], [False, True]),
        "Community  ↑":          (["community_count", "org"], [True,  True]),
        "Organization  A → Z":   (["org"],                    [True]),
        "Organization  Z → A":   (["org"],                    [False]),
    }
    _scols, _sasc = _sort_map[sort_by]
    _orgs = _orgs.sort_values(_scols, ascending=_sasc).reset_index(drop=True)

    st.caption(f"{len(_orgs)} organization{'s' if len(_orgs) != 1 else ''}")

    # ── Render organization cards ─────────────────────────────────────────────
    cards_html = ""
    for _, _row in _orgs.iterrows():
        _org = _row["org"]
        _mc = int(_row["member_count"])
        _cc = int(_row["community_count"])
        _href = f"/Organizations?org={quote(str(_org))}"
        _mc_txt = f'{_mc} HBI member{"s" if _mc != 1 else ""}' if _mc > 0 else ""
        _cc_txt = f'{_cc} community profile{"s" if _cc != 1 else ""}' if _cc > 0 else ""
        _mc_part = (
            f'<span style="color:{UCALGARY_RED};font-weight:600;">👨\u200d🔬 {_mc_txt}</span>'
            if _mc_txt else ""
        )
        _sep = "&nbsp;·&nbsp;" if _mc_part and _cc_txt else ""
        _cc_part = (
            f'<span style="color:{COMMUNITY_TEAL};font-weight:600;">🤝 {_cc_txt}</span>'
            if _cc_txt else ""
        )
        cards_html += (
            f'<a href="{_href}" class="topic-card-link">'
            f'<div class="topic-card" style="border-left:3px solid {INSTITUTION_COLOR};">'
            f'<div class="topic-card-name">{_esc(_org)}</div>'
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
        f'border-color:{INSTITUTION_COLOR};transform:translateY(-2px);}}'
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


# ════════════════════════════════════════════════════════════════════════════
# DRILL-DOWN VIEW
# ════════════════════════════════════════════════════════════════════════════

# ── Load data ─────────────────────────────────────────────────────────────────
member_inst = load_member_institution_tags()
community_inst = load_li_institution_tags()
member_dir = build_directory_data()
community_dir = build_community_directory_data()

# ── Find matching member IDs ──────────────────────────────────────────────────
matching_member_ids = set(
    member_inst.loc[member_inst["institution_tag"] == org, "member_id"]
)
filtered_members = (
    member_dir[member_dir["member_id"].isin(matching_member_ids)]
    .sort_values("name")
    .reset_index(drop=True)
)

# ── Find matching community profile IDs ──────────────────────────────────────
matching_profile_ids = set(
    community_inst.loc[community_inst["institution_tag"] == org, "profile_id"]
)
filtered_community = (
    community_dir[community_dir["profile_id"].isin(matching_profile_ids)]
    .sort_values("full_name")
    .reset_index(drop=True)
)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="hbi-banner" style="background:linear-gradient(135deg,'
    f'{INSTITUTION_COLOR} 0%,#3D3480 100%);">'
    f'<h1>🏛️ Organization</h1>'
    f'<p style="font-size:1.4rem;font-weight:700;">{_esc(org)}</p>'
    f'</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("← Organizations"):
        st.query_params.clear()
        st.rerun()

st.markdown(
    f'<p style="font-size:1.1rem;">'
    f'<strong style="color:{UCALGARY_RED};">{len(filtered_members)}</strong> HBI member{"s" if len(filtered_members) != 1 else ""} &nbsp;·&nbsp; '
    f'<strong style="color:{COMMUNITY_TEAL};">{len(filtered_community)}</strong> community profile{"s" if len(filtered_community) != 1 else ""}'
    f'</p>',
    unsafe_allow_html=True,
)

if filtered_members.empty and filtered_community.empty:
    st.info("No profiles found for this organization.")
    st.stop()

# ── View toggle ───────────────────────────────────────────────────────────────
view_mode = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

# ── HBI Members section ───────────────────────────────────────────────────────
if not filtered_members.empty:
    st.markdown(
        f'<div style="border-bottom:3px solid {UCALGARY_RED};padding-bottom:8px;'
        f'margin-bottom:16px;">'
        f'<h3 style="color:{UCALGARY_RED};margin:0;">🧠 HBI Members</h3></div>',
        unsafe_allow_html=True,
    )
    if view_mode == "Grid":
        cards = []
        for _, row in filtered_members.iterrows():
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
        for _, row in filtered_members.iterrows():
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

# ── Community Profiles section ────────────────────────────────────────────────
if not filtered_community.empty:
    st.markdown("---")
    st.markdown(
        f'<div style="border-bottom:3px solid {COMMUNITY_TEAL};padding-bottom:8px;'
        f'margin-bottom:16px;">'
        f'<h3 style="color:{COMMUNITY_TEAL};margin:0;">🤝 HBI Community Profiles</h3></div>',
        unsafe_allow_html=True,
    )
    if view_mode == "Grid":
        comm_cards = []
        for _, row in filtered_community.iterrows():
            pid = row["profile_id"]
            fname = str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown"
            ctitle = str(row["current_title"]) if pd.notna(row.get("current_title")) else ""
            ccompany = str(row["current_company"]) if pd.notna(row.get("current_company")) else ""
            location = str(row["location"]) if pd.notna(row.get("location")) else ""
            tags = row.get("research_tags_list", [])
            if not isinstance(tags, list):
                tags = []
            comm_cards.append(
                render_community_card_html(
                    fname,
                    ctitle,
                    ccompany,
                    location,
                    tags,
                    profile_id=pid,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                )
            )
        st.markdown(render_card_grid(comm_cards), unsafe_allow_html=True)
    else:
        comm_rows = []
        for _, row in filtered_community.iterrows():
            pid = row["profile_id"]
            fname = str(row["full_name"]) if pd.notna(row["full_name"]) else "Unknown"
            ctitle = str(row["current_title"]) if pd.notna(row.get("current_title")) else ""
            ccompany = str(row["current_company"]) if pd.notna(row.get("current_company")) else ""
            location = str(row["location"]) if pd.notna(row.get("location")) else ""
            tags = row.get("research_tags_list", [])
            if not isinstance(tags, list):
                tags = []
            comm_rows.append(
                render_community_list_row_html(
                    fname,
                    ctitle,
                    ccompany,
                    location,
                    tags,
                    profile_id=pid,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                )
            )
        st.markdown(render_list_view(comm_rows), unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────════════════════
render_disclaimer()
