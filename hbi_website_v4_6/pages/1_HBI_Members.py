"""HBI Members — Directory listing + individual profile view (dual-mode)."""

import html as html_mod
from urllib.parse import quote

import pandas as pd
import streamlit as st
from st_keyup import st_keyup
from utils.page_config import BLANK_PAGE_ICON

from utils.data_loader import (
    load_members,
    load_positions,
    load_education,
    load_publications,
    load_activities,
    load_contact_info,
    load_member_digital_footprint,
    load_research_footprint_highlights,
    load_preferred_contact_methods,
    load_source_affiliations,
    load_source_research_phrases,
    load_member_inline_links,
    load_news,
    load_publishable_research_tags,
    load_hybrid_research_taxonomy,
    load_scopus_research_keywords,
    load_scopus_member_summary,
    load_scopus_keyword_years,
    load_scopus_member_year_summary,
    load_member_institution_tags,
    build_directory_data,
)
from utils.linkedin_data_loader import build_community_directory_data
from utils.scopus_profile import (
    publication_panel_help_text,
    render_scopus_research_keywords,
)
from utils.hybrid_expertise import render_hybrid_expertise
from utils.collaboration_summary import load_profile_collaboration_summary
from utils.profile_search import search_member_profiles
from utils.home_layout import render_member_directory_welcome
from utils.components import (
    inject_custom_css,
    render_public_sidebar_navigation,
    profile_hero_detail_lines,
    render_profile_action_bar_html,
    render_collapsing_profile_hero_html,
    render_profile_at_a_glance_html,
    render_profile_awards,
    render_community_card_html,
    render_card_html,
    render_card_grid,
    render_list_row_html,
    render_list_view,
    render_profile_positions_html,
    render_contact_research_links_html,
    clean_biography_text,
    clean_looking_for_text,
    render_profile_background_html,
    profile_panel_header,
    UCALGARY_RED,
    INSTITUTION_COLOR,
    render_disclaimer,
)

_esc = lambda s: html_mod.escape(str(s)) if s else ""

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="HBI Members", page_icon=BLANK_PAGE_ICON, layout="wide",
                   initial_sidebar_state="expanded")
inject_custom_css()
render_public_sidebar_navigation("members")

# ── Route: directory vs individual profile ───────────────────────────────────
member_id = st.query_params.get("id")

# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORY MODE
# ═══════════════════════════════════════════════════════════════════════════════
if not member_id:

    # ── Header banner ─────────────────────────────────────────────────────────
    render_member_directory_welcome()

    # ── Cached data ───────────────────────────────────────────────────────────
    directory = build_directory_data()
    members = load_members()
    positions = load_positions()
    research_areas = load_publishable_research_tags()

    # ── Sidebar filters ───────────────────────────────────────────────────────
    _MEM_FILTER_KEYS = ["mem_search", "mem_membership", "mem_area", "mem_dept", "mem_faculty"]

    # Apply pending reset BEFORE widgets are instantiated.
    if st.session_state.pop("_mem_reset", False):
        st.session_state["mem_search_generation"] = (
            st.session_state.get("mem_search_generation", 0) + 1
        )
        st.session_state["mem_membership"] = "All"
        st.session_state["mem_area"] = ""
        st.session_state["mem_dept"] = "All"
        st.session_state["mem_faculty"] = "All"
        st.session_state["mem_page"] = 0

    with st.sidebar:
        st.markdown('<div style="height:70px"></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:0.4rem;">Search</p>', unsafe_allow_html=True)
        search_query = st_keyup(
            "Search",
            placeholder="Name, keyword, expertise…",
            label_visibility="collapsed",
            key=f"mem_search_{st.session_state.get('mem_search_generation', 0)}",
            debounce=250,
        )

        st.markdown('<p style="font-size:1.4rem; font-weight:700; margin-bottom:0.4rem;">Filters</p>', unsafe_allow_html=True)

        _membership_order = ["Full Member", "Associate Member", "Emeritus Member"]
        hbi_statuses_raw = directory["hbi_membership"].replace("", pd.NA).dropna().unique().tolist()
        hbi_statuses = [s for s in _membership_order if s in hbi_statuses_raw] + \
                       [s for s in sorted(hbi_statuses_raw) if s not in _membership_order]
        sel_membership = st.selectbox(
            "Membership Status",
            ["All"] + hbi_statuses,
            index=0,
            key="mem_membership",
        )

        filter_area = st.text_input("Research area", placeholder="e.g. neuroscience", key="mem_area")

        _dept_options = sorted(
            positions["department"]
            .dropna()
            .loc[lambda s: s.str.startswith("Department of")]
            .str.split("|").str[0]
            .str.strip()
            .str.replace(r"^Department of\s+", "", regex=True)
            .unique()
            .tolist()
        )
        sel_dept = st.selectbox("Department", ["All"] + _dept_options, index=0, key="mem_dept")

        _known_faculties = {
            "cumming school of medicine",
            "schulich school of engineering",
            "faculty of science",
            "faculty of arts",
            "faculty of nursing",
            "faculty of kinesiology",
            "faculty of veterinary medicine",
            "faculty of social work",
            "faculty of education",
            "faculty of law",
            "haskayne school of business",
            "werklund school of education",
        }
        _faculty_options = sorted(
            v for v in positions["faculty"].dropna().unique().tolist()
            if v.lower() in _known_faculties
        )
        sel_faculty = st.selectbox("Faculty", ["All"] + _faculty_options, index=0, key="mem_faculty")

        st.markdown("---")
        if st.button("🔄 Reset All Filters", use_container_width=True):
            st.session_state["_mem_reset"] = True
            st.rerun()

    # ── Apply filters ─────────────────────────────────────────────────────────
    ids = set(members["member_id"])
    search_scores = {}

    if search_query:
        search_results = search_member_profiles(search_query)
        search_scores = search_results.set_index("member_id")["search_score"].to_dict()
        ids &= set(search_results["member_id"])

    if filter_area:
        fa = filter_area.lower()
        ids &= set(
            research_areas[
                research_areas["area"].str.lower().str.contains(fa, na=False)
            ]["member_id"]
        )

    if sel_membership != "All":
        ids &= set(directory[directory["hbi_membership"] == sel_membership]["member_id"])

    if sel_dept != "All":
        _dept_full = f"Department of {sel_dept}"
        ids &= set(
            positions[positions["department"].str.split("|").str[0].str.strip() == _dept_full]["member_id"]
        )

    if sel_faculty != "All":
        ids &= set(
            positions[positions["faculty"] == sel_faculty]["member_id"]
        )

    filtered = directory[directory["member_id"].isin(ids)].copy()
    if search_query:
        filtered["search_score"] = filtered["member_id"].map(search_scores).fillna(0)
        filtered = filtered.sort_values(["search_score", "name"], ascending=[False, True])
    else:
        filtered = filtered.sort_values("name")
    filtered = filtered.reset_index(drop=True)

    # ── Results count + view toggle + per-page selector ───────────────────────
    with st.container(key="member_directory_controls"):
        rcount_col, toggle_col, perpage_col = st.columns([3, 1, 1])
        with rcount_col:
            st.markdown(f"Showing **{len(filtered)}** of **{len(members)}** members")
        with toggle_col:
            st.markdown("**View mode**")
            view_mode = st.selectbox(
                "View mode", ["Grid", "List"], index=0, label_visibility="collapsed"
            )
        with perpage_col:
            st.markdown("**Profiles per Page**")
            per_page_options = ["25", "50", "100", "All"]
            per_page_choice = st.selectbox(
                "Profiles per Page", per_page_options, index=0, label_visibility="collapsed"
            )

    # ── Export button (sidebar) ───────────────────────────────────────────────
    with st.sidebar:
        if not filtered.empty:
            export = filtered[["name", "title", "department", "faculty", "profile_url"]].copy()
            export.columns = ["Name", "Primary Position", "Department", "Faculty", "Profile URL"]
            export["Research Areas"] = filtered["research_areas_list"].apply(
                lambda x: "; ".join(str(a) for a in x) if isinstance(x, list) else ""
            )
            st.download_button(
                "📥 Download Filtered Results",
                export.to_csv(index=False),
                "hbi_members_filtered.csv",
                "text/csv",
                use_container_width=True,
            )

    # ── Pagination setup ──────────────────────────────────────────────────────
    PER_PAGE = len(filtered) if per_page_choice == "All" else int(per_page_choice)
    total_pages = max(1, -(-len(filtered) // PER_PAGE)) if PER_PAGE > 0 else 1

    _fhash = hash((
        search_query, filter_area, sel_membership,
        sel_dept, sel_faculty, per_page_choice,
    ))
    if st.session_state.get("_fh") != _fhash:
        st.session_state["dir_page"] = 0
        st.session_state["_fh"] = _fhash

    page = max(0, min(st.session_state.get("dir_page", 0), total_pages - 1))
    start_idx = page * PER_PAGE
    page_data = filtered.iloc[start_idx : start_idx + PER_PAGE]

    # ── Member card grid / list ───────────────────────────────────────────────
    if page_data.empty:
        st.info("No members match your current filters. Try broadening your search.")
    else:
        if view_mode == "Grid":
            cards = []
            for _, row in page_data.iterrows():
                mid = row["member_id"]
                nm = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
                title = str(row["title"]) if pd.notna(row.get("title")) else ""
                dept = str(row["department"]) if pd.notna(row.get("department")) else ""
                areas = row.get("research_areas_list", [])
                if not isinstance(areas, list):
                    areas = []
                _pp = row.get("photo_path", "")
                _photo = f"/app/static/images/member/{_pp}" if _pp and pd.notna(_pp) else None
                cards.append(render_card_html(
                    nm,
                    title,
                    dept,
                    areas,
                    member_id=mid,
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                ))
            st.markdown(render_card_grid(cards), unsafe_allow_html=True)
        else:
            rows_html = []
            for _, row in page_data.iterrows():
                mid = row["member_id"]
                nm = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
                title = str(row["title"]) if pd.notna(row.get("title")) else ""
                dept = str(row["department"]) if pd.notna(row.get("department")) else ""
                areas = row.get("research_areas_list", [])
                if not isinstance(areas, list):
                    areas = []
                _pp = row.get("photo_path", "")
                _photo = f"/app/static/images/member/{_pp}" if _pp and pd.notna(_pp) else None
                rows_html.append(render_list_row_html(
                    nm,
                    title,
                    dept,
                    areas,
                    member_id=mid,
                    photo_url=_photo,
                    declared_areas=row.get("researcher_declared_areas_list", []),
                ))
            st.markdown(render_list_view(rows_html), unsafe_allow_html=True)

        # ── Pagination controls ───────────────────────────────────────────────
        st.markdown("")
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("⏮ First", disabled=page == 0, key="pg_first"):
                st.session_state["dir_page"] = 0
                st.rerun()
        with c2:
            if st.button("◀ Prev", disabled=page == 0, key="pg_prev"):
                st.session_state["dir_page"] = page - 1
                st.rerun()
        with c3:
            st.markdown(
                f"<div style='text-align:center;padding:8px 0;'>"
                f"Page <b>{page + 1}</b> of <b>{total_pages}</b></div>",
                unsafe_allow_html=True,
            )
        with c4:
            if st.button("Next ▶", disabled=page >= total_pages - 1, key="pg_next"):
                st.session_state["dir_page"] = page + 1
                st.rerun()
        with c5:
            if st.button("Last ⏭", disabled=page >= total_pages - 1, key="pg_last"):
                st.session_state["dir_page"] = total_pages - 1
                st.rerun()

    render_disclaimer()

# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE MODE
# ═══════════════════════════════════════════════════════════════════════════════
else:
    # Keep URL bookmarkable
    st.query_params["id"] = member_id

    # ── Load member ───────────────────────────────────────────────────────────
    members = load_members()
    member = members[members["member_id"] == member_id]

    if member.empty:
        st.error(f"Member not found: {member_id}")
        if st.button("← Back to Directory"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    m = member.iloc[0]
    name = str(m["name"]) if pd.notna(m["name"]) else "Unknown"
    profile_url = str(m["profile_url"]) if pd.notna(m.get("profile_url")) else None
    biography = clean_biography_text(
        m["biography"] if pd.notna(m.get("biography")) else ""
    )
    looking_for = clean_looking_for_text(
        m["looking_for"] if pd.notna(m.get("looking_for")) else ""
    )

    # ── Related data ──────────────────────────────────────────────────────────
    mem_positions = (
        load_positions()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_areas = (
        load_publishable_research_tags()
        .query("member_id == @member_id")
        .sort_values("area")
    )
    mem_hybrid_taxonomy = (
        load_hybrid_research_taxonomy()
        .query("member_id == @member_id")
    )
    mem_scopus_keywords = (
        load_scopus_research_keywords()
        .query("member_id == @member_id")
        .sort_values("display_rank")
    )
    mem_scopus_summary = (
        load_scopus_member_summary()
        .query("member_id == @member_id")
    )
    mem_scopus_keyword_years = (
        load_scopus_keyword_years()
        .query("member_id == @member_id")
    )
    mem_scopus_year_summary = (
        load_scopus_member_year_summary()
        .query("member_id == @member_id")
        .sort_values("publication_year")
    )
    mem_edu = (
        load_education()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_pubs = (
        load_publications()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_acts = (
        load_activities()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_contact = load_contact_info().query("member_id == @member_id")
    mem_preferred_contact = (
        load_preferred_contact_methods().query("member_id == @member_id")
    )
    mem_source_affiliations = (
        load_source_affiliations()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_source_research_phrases = (
        load_source_research_phrases()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )
    mem_digital_links = (
        load_member_digital_footprint()
        .query("member_id == @member_id")
        .sort_values("display_order")
    )
    mem_research_highlights = load_research_footprint_highlights().get(member_id)
    mem_looking_for_links = (
        load_member_inline_links()
        .query("member_id == @member_id and section == 'looking_for'")
    )
    if not mem_digital_links.empty and not mem_pubs.empty:
        _digital_urls = set(mem_digital_links["url"].dropna().astype(str))
        _digital_urls.update(
            mem_digital_links["source_url"].dropna().astype(str)
        )
        _digital_urls.discard("")
        mem_pubs = mem_pubs[
            ~mem_pubs["url"].fillna("").astype(str).isin(_digital_urls)
        ]
    mem_news = (
        load_news()
        .query("member_id == @member_id")
        .sort_values("sort_order")
    )

    # ── Profile actions ───────────────────────────────────────────────────────
    # TODO: swap _CHANGE_FORM_URL for SharePoint form URL when ready
    _CHANGE_FORM_URL = (
        f"mailto:daniel.sotolopez@ucalgary.ca"
        f"?subject=Profile%20Change%20Request%20%E2%80%93%20{quote(name)}"
        f"&body=Member%20ID%3A%20{quote(member_id)}%0A"
        f"Member%20Name%3A%20{quote(name)}%0A%0A"
        f"REQUESTED%20CHANGE%3A%0A"
        f"%5BDescribe%20the%20change%20here%5D%0A%0A"
        f"-----%0A"
        f"ADMIN%20INSTRUCTIONS%0A"
        f"-----%0A"
        f"UCalgary-sourced%20fields%20%28positions%2C%20education%2C%20biography%2C%20expertise%29%3A%0A"
        f"%E2%86%92%20Preferred%3A%20ask%20member%20to%20update%20at%20profiles.ucalgary.ca%20%28auto-syncs%20on%20next%20crawl%29%0A"
        f"%E2%86%92%20Manual%20override%3A%20edit%20the%20relevant%20file%20in%20output%2Fcsv%2F%2C%20find%20row%20with%20member_id%20above%0A%0A"
        f"Key%20files%20%28output%2Fcsv%2F%29%3A%0A"
        f"%20%20dim_members.csv%20%20%20%20%20%20%20%20%20%3C%E2%80%94%20name%2C%20biography%2C%20looking_for%0A"
        f"%20%20dim_positions.csv%20%20%20%20%20%20%20%3C%E2%80%94%20title%2C%20department%2C%20faculty%0A"
        f"%20%20dim_research_areas.csv%20%20%3C%E2%80%94%20expertise%20tags%0A"
        f"%20%20dim_education.csv%20%20%20%20%20%20%20%3C%E2%80%94%20degrees%2C%20institutions%0A%0A"
        f"After%20any%20edit%3A%20restart%20the%20website%20server%20to%20clear%20the%20data%20cache."
    )
    st.markdown(
        render_profile_action_bar_html(_CHANGE_FORM_URL),
        unsafe_allow_html=True,
    )

    # ── Animated profile hero ─────────────────────────────────────────────────
    _pp = m.get("photo_path", "")
    _photo_url = f"/app/static/images/member/{_pp}" if _pp and pd.notna(_pp) else None
    _hero_details = profile_hero_detail_lines(
        mem_positions, mem_source_affiliations.to_dict("records")
    )
    _hero_contacts = (
        mem_contact.to_dict("records") + mem_preferred_contact.to_dict("records")
    )
    st.markdown(
        render_collapsing_profile_hero_html(
            name, _photo_url, _hero_details, _hero_contacts
        ),
        unsafe_allow_html=True,
    )

    # ── Research at a glance and selected recognition ────────────────────────
    _publication_summary = (
        mem_scopus_summary.iloc[0].to_dict() if not mem_scopus_summary.empty else {}
    )
    _recognitions = mem_acts[
        mem_acts["category"].fillna("").astype(str).str.casefold().eq("awards")
    ].to_dict("records")
    _at_a_glance_html = render_profile_at_a_glance_html(
        _publication_summary,
        _recognitions,
        load_profile_collaboration_summary(member_id),
    )
    if _at_a_glance_html:
        st.markdown(_at_a_glance_html, unsafe_allow_html=True)

    # ── Affiliations and Research Footprint ───────────────────────────────────
    # All HBI member records originate from official UCalgary profile pages.
    # The footprint is therefore shown consistently for every member, even when
    # no additional scholarly or research-ecosystem links have been verified yet.
    _profile_details = []
    if not mem_positions.empty:
        _profile_details.append(
            render_profile_positions_html(
                mem_positions, mem_source_affiliations.to_dict("records")
            )
        )
    _profile_details.append(
        render_contact_research_links_html(
            [],
            mem_digital_links.to_dict("records"),
            mem_research_highlights,
            show_contact=False,
        )
    )
    st.markdown(
        '<div class="hbi-footprint-layout">'
        + "".join(_profile_details)
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Background ────────────────────────────────────────────────────────────
    if biography or looking_for or not mem_edu.empty:
        # Affiliated Organizations
        _member_inst_tags = load_member_institution_tags()
        _this_inst_tags = sorted(
            _member_inst_tags.loc[
                _member_inst_tags["member_id"] == member_id, "institution_tag"
            ].dropna().unique().tolist()
        )
        st.markdown(
            render_profile_background_html(
                biography,
                looking_for,
                mem_edu.to_dict("records"),
                _this_inst_tags,
                mem_looking_for_links.to_dict("records"),
            ),
            unsafe_allow_html=True,
        )

    # ── Research ────────────────────────────────────────────────────────────────
    if not mem_hybrid_taxonomy.empty or not mem_source_research_phrases.empty:
        with st.container(key="hbi_panel_research"):
            profile_panel_header(
                "Areas of Research",
                "Researcher-declared wording is drawn from the public research "
                "profile. Standardized terms and Research Themes "
                "organize that wording using recognized research terminology.",
            )
            render_hybrid_expertise(
                mem_hybrid_taxonomy,
                mem_source_research_phrases.to_dict("records"),
            )

    # ── Publications and publication-derived research ────────────────────────
    if not mem_scopus_summary.empty or not mem_pubs.empty:
        with st.container(key="hbi_panel_publications"):
            profile_panel_header(
                "Publications",
                publication_panel_help_text(mem_scopus_summary),
            )
            if not mem_scopus_summary.empty:
                render_scopus_research_keywords(
                    member_id=member_id,
                    summary=mem_scopus_summary,
                    keywords=mem_scopus_keywords,
                    keyword_years=mem_scopus_keyword_years,
                    year_summary=mem_scopus_year_summary,
                )

            if not mem_pubs.empty:
                st.markdown(
                    "##### Publications Listed on the UCalgary Profile",
                    help=(
                        "These publication links are reproduced from the "
                        "researcher’s public UCalgary Research profile."
                    ),
                )
                for _, pub in mem_pubs.iterrows():
                    ptitle = str(pub["title"]) if pd.notna(pub["title"]) else ""
                    purl = str(pub["url"]) if pd.notna(pub["url"]) else ""
                    raw = str(pub["raw_text"]) if pd.notna(pub["raw_text"]) else ""
                    display = ptitle or raw
                    if purl and display:
                        st.markdown(f"- [{_esc(display)}]({purl})")
                    elif display:
                        st.markdown(f"- {_esc(display)}")
                    elif purl:
                        st.markdown(f"- [{purl}]({purl})")

    # ── Awards ───────────────────────────────────────────────────────────────
    render_profile_awards(_recognitions)

    # ── News ──────────────────────────────────────────────────────────────────
    if not mem_news.empty:
        with st.container(key="hbi_panel_news"):
            profile_panel_header(
                "News",
                "News items are drawn from the researcher’s public UCalgary "
                "Research profile and retain their original source links.",
            )
            for _, n in mem_news.iterrows():
                headline = str(n["headline"]) if pd.notna(n["headline"]) else ""
                source = str(n["source"]) if pd.notna(n["source"]) else ""
                date = str(int(n["date"])) if pd.notna(n["date"]) else ""
                nurl = str(n["url"]) if pd.notna(n["url"]) else ""
                if headline:
                    if nurl:
                        st.markdown(f"📰 [{_esc(headline)}]({nurl})")
                    else:
                        st.markdown(f"📰 {_esc(headline)}")
                    meta = " · ".join(p for p in [source, date] if p)
                    if meta:
                        st.caption(meta)

    # ── Related HBI Member and Community Profiles ──────────────────────────────
    _self_tags = {
        str(tag).strip().lower()
        for tag in mem_areas.get("area", pd.Series(dtype=str)).dropna().tolist()
        if str(tag).strip()
    }
    _related_mems = pd.DataFrame()
    _related_community = pd.DataFrame()

    if _self_tags:
        _all_members = build_directory_data()

        def _member_overlap(areas: list) -> int:
            return sum(
                1
                for area in (areas or [])
                if str(area).strip().lower() in _self_tags
            )

        _all_members["_overlap"] = _all_members["research_areas_list"].apply(
            _member_overlap
        )
        _related_mems = (
            _all_members[
                (_all_members["_overlap"] > 0)
                & (_all_members["member_id"] != member_id)
            ]
            .sort_values("_overlap", ascending=False)
            .head(6)
        )

        _community = build_community_directory_data()

        def _community_overlap(tags: list) -> int:
            return sum(
                1
                for tag in (tags or [])
                if str(tag).strip().lower() in _self_tags
            )

        _community["_overlap"] = _community["research_tags_list"].apply(
            _community_overlap
        )
        _related_community = (
            _community[_community["_overlap"] > 0]
            .sort_values("_overlap", ascending=False)
            .head(6)
        )

    with st.container(key="hbi_panel_related_profiles"):
        profile_panel_header(
            "Related HBI Member Profiles",
            "These directory suggestions are based on overlapping research "
            "areas. They are directory matches, not recommendations from the "
            "researcher’s source profile.",
        )
        st.caption(
            "HBI Members and HBI Community Members with overlapping research areas."
        )
        _member_column, _community_column = st.columns(2, gap="large")

        with _member_column:
            st.markdown("##### HBI Members")
            if _related_mems.empty:
                st.markdown(
                    '<div class="hbi-related-empty">No members were found.</div>',
                    unsafe_allow_html=True,
                )
            else:
                _member_cards = []
                for _, related_member in _related_mems.iterrows():
                    _related_photo_path = related_member.get("photo_path", "")
                    _related_photo_url = (
                        f"/app/static/images/member/{_related_photo_path}"
                        if _related_photo_path and pd.notna(_related_photo_path)
                        else None
                    )
                    _member_cards.append(
                        render_card_html(
                            name=(
                                str(related_member["name"])
                                if pd.notna(related_member.get("name"))
                                else "Unknown"
                            ),
                            title=(
                                str(related_member["title"])
                                if pd.notna(related_member.get("title"))
                                else ""
                            ),
                            department=(
                                str(related_member["department"])
                                if pd.notna(related_member.get("department"))
                                else ""
                            ),
                            areas=related_member.get("research_areas_list") or [],
                            member_id=str(related_member["member_id"]),
                            photo_url=_related_photo_url,
                            declared_areas=related_member.get(
                                "researcher_declared_areas_list", []
                            ),
                        )
                    )
                st.markdown(
                    render_card_grid(_member_cards),
                    unsafe_allow_html=True,
                )

        with _community_column:
            st.markdown("##### HBI Community Members")
            if _related_community.empty:
                st.markdown(
                    '<div class="hbi-related-empty">No members were found.</div>',
                    unsafe_allow_html=True,
                )
            else:
                _community_cards = []
                for _, community_member in _related_community.iterrows():
                    _community_photo_path = community_member.get("photo_path", "")
                    _community_photo_url = (
                        f"/app/static/images/community/{_community_photo_path}"
                        if _community_photo_path
                        and pd.notna(_community_photo_path)
                        else None
                    )
                    _community_cards.append(
                        render_community_card_html(
                            name=(
                                str(community_member["full_name"])
                                if pd.notna(community_member["full_name"])
                                else "Unknown"
                            ),
                            current_title=(
                                str(community_member["current_title"])
                                if pd.notna(community_member.get("current_title"))
                                else ""
                            ),
                            current_company=(
                                str(community_member["current_company"])
                                if pd.notna(community_member.get("current_company"))
                                else ""
                            ),
                            location=(
                                str(community_member["location"])
                                if pd.notna(community_member.get("location"))
                                else ""
                            ),
                            tags=community_member.get("research_tags_list", []),
                            profile_id=str(community_member["profile_id"]),
                            declared_areas=community_member.get(
                                "researcher_declared_areas_list", []
                            ),
                            photo_url=_community_photo_url,
                        )
                    )
                st.markdown(
                    render_card_grid(_community_cards),
                    unsafe_allow_html=True,
                )

        # Keep each directory link directly beneath its own profile list.
        with _member_column:
            st.markdown(
                '<a class="hbi-related-directory-link" href="/HBI_Members">'
                'View All HBI Member Profiles →</a>',
                unsafe_allow_html=True,
            )
        with _community_column:
            st.markdown(
                '<a class="hbi-related-directory-link" href="/HBI_Community">'
                'View All HBI Community Profiles →</a>',
                unsafe_allow_html=True,
            )

    render_disclaimer()
