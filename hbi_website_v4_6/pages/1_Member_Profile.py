"""HBI Member Profile — Individual profile view."""

import html as html_mod
from urllib.parse import quote

import pandas as pd
import streamlit as st
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
    load_news,
    load_publishable_research_tags,
    load_hybrid_research_taxonomy,
    load_scopus_research_keywords,
    load_scopus_member_summary,
    load_scopus_keyword_years,
    load_scopus_member_year_summary,
    build_directory_data,
)
from utils.linkedin_data_loader import build_community_directory_data
from utils.scopus_profile import render_scopus_research_keywords
from utils.hybrid_expertise import render_hybrid_expertise
from utils.collaboration_summary import load_profile_collaboration_summary
from utils.components import (
    render_profile_at_a_glance_html,
    render_profile_awards,
    inject_custom_css,
    render_public_sidebar_navigation,
    profile_hero_detail_lines,
    render_collapsing_profile_hero_html,
    render_card_html,
    render_community_card_html,
    render_card_grid,
    render_profile_positions_html,
    render_contact_research_links_html,
    section_header,
    UCALGARY_RED,
    COMMUNITY_TEAL,
    render_disclaimer,
)

_esc = lambda s: html_mod.escape(str(s)) if s else ""

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Member Profile – HBI", page_icon=BLANK_PAGE_ICON, layout="wide")
inject_custom_css()
render_public_sidebar_navigation("members")

# ── Resolve member ID ────────────────────────────────────────────────────────
member_id = st.session_state.get("selected_member") or st.query_params.get("id")

if not member_id:
    st.warning("No member selected.")
    if st.button("← Back to Directory"):
        st.switch_page("Home.py")
    st.stop()

# Keep URL bookmarkable
st.query_params["id"] = member_id

# ── Load member ──────────────────────────────────────────────────────────────
members = load_members()
member = members[members["member_id"] == member_id]

if member.empty:
    st.error(f"Member not found: {member_id}")
    if st.button("← Back to Directory"):
        st.switch_page("Home.py")
    st.stop()

m = member.iloc[0]
name = str(m["name"]) if pd.notna(m["name"]) else "Unknown"
profile_url = str(m["profile_url"]) if pd.notna(m.get("profile_url")) else None
biography = str(m["biography"]) if pd.notna(m.get("biography")) else ""

# ── Related data ─────────────────────────────────────────────────────────────
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
if not mem_digital_links.empty and not mem_pubs.empty:
    _digital_urls = set(mem_digital_links["url"].dropna().astype(str))
    _digital_urls.update(mem_digital_links["source_url"].dropna().astype(str))
    _digital_urls.discard("")
    mem_pubs = mem_pubs[
        ~mem_pubs["url"].fillna("").astype(str).isin(_digital_urls)
    ]
mem_news = (
    load_news()
    .query("member_id == @member_id")
    .sort_values("sort_order")
)

# ── Animated profile hero ────────────────────────────────────────────────────
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

# ── Navigation row ───────────────────────────────────────────────────────────
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
nav1, nav2, _ = st.columns([1, 1, 2])
with nav1:
    if st.button("← Back to Directory"):
        st.switch_page("Home.py")
with nav2:
    st.link_button("📬 Suggest a change", _CHANGE_FORM_URL)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_publication_summary = mem_scopus_summary.iloc[0].to_dict() if not mem_scopus_summary.empty else {}
_recognitions = mem_acts[
    mem_acts["category"].fillna("").astype(str).str.casefold().eq("awards")
].to_dict("records")
_at_a_glance_html = render_profile_at_a_glance_html(
    _publication_summary, _recognitions, load_profile_collaboration_summary(member_id),
)
if _at_a_glance_html:
    st.markdown(_at_a_glance_html, unsafe_allow_html=True)

# ── Affiliations and Research Footprint ──────────────────────────────────────
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

# ── Background (Biography + Education) ──────────────────────────────────────
if biography or not mem_edu.empty:
    section_header("Background")

    if biography:
        st.markdown(biography)
        st.markdown("")

    if not mem_edu.empty:
        st.markdown("##### Educational Background")
        for _, ed in mem_edu.iterrows():
            degree = str(ed["degree"]) if pd.notna(ed["degree"]) else ""
            inst = str(ed["institution"]) if pd.notna(ed["institution"]) else ""
            year = str(int(ed["year"])) if pd.notna(ed["year"]) else ""
            parts = [p for p in [degree, inst, year] if p]
            if parts:
                st.markdown(f"- {', '.join(parts)}")

# ── Research ─────────────────────────────────────────────────────────────────
if not mem_hybrid_taxonomy.empty or not mem_source_research_phrases.empty:
    section_header("Areas of Research")
    render_hybrid_expertise(
        mem_hybrid_taxonomy,
        mem_source_research_phrases.to_dict("records"),
    )

# ── Publications and publication-derived research ──────────────────────────
if not mem_scopus_summary.empty or not mem_pubs.empty:
    section_header("Publications")
    if not mem_scopus_summary.empty:
        render_scopus_research_keywords(
            member_id=member_id,
            summary=mem_scopus_summary,
            keywords=mem_scopus_keywords,
            keyword_years=mem_scopus_keyword_years,
            year_summary=mem_scopus_year_summary,
        )

    if not mem_pubs.empty:
        st.markdown("##### Publications Listed on the UCalgary Profile")
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

# ── News ─────────────────────────────────────────────────────────────────────
if not mem_news.empty:
    section_header("News")
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

# ── Related HBI Member Profiles ─────────────────────────────────────────────
if not mem_areas.empty:
    _self_tags = set(t.lower() for t in mem_areas["area"].dropna().tolist())
    if _self_tags:
        _all_members = build_directory_data()

        def _mem_overlap(areas: list) -> int:
            return sum(1 for a in (areas or []) if a.lower() in _self_tags)

        _all_members["_overlap"] = _all_members["research_areas_list"].apply(_mem_overlap)
        _related_mems = (
            _all_members[
                (_all_members["_overlap"] > 0) &
                (_all_members["member_id"] != member_id)
            ]
            .sort_values("_overlap", ascending=False)
            .head(6)
        )

        if not _related_mems.empty:
            section_header("Related HBI Member Profiles", color=UCALGARY_RED)
            st.caption("HBI Members with overlapping research areas.")
            _rm_cards = []
            for _, _rm in _related_mems.iterrows():
                _rm_cards.append(
                    render_card_html(
                        name=str(_rm["name"]) if pd.notna(_rm.get("name")) else "Unknown",
                        title=str(_rm["title"]) if pd.notna(_rm.get("title")) else "",
                        department=str(_rm["department"]) if pd.notna(_rm.get("department")) else "",
                        areas=_rm.get("research_areas_list") or [],
                        member_id=str(_rm["member_id"]),
                        declared_areas=_rm.get("researcher_declared_areas_list", []),
                    )
                )
            st.markdown(render_card_grid(_rm_cards), unsafe_allow_html=True)
            st.page_link("pages/1_HBI_Members.py", label="View all HBI Members →", icon="🧠")

# ── Related HBI Community Profiles ───────────────────────────────────────────
if not mem_areas.empty:
    _member_tags = set(t.lower() for t in mem_areas["area"].dropna().tolist())
    if _member_tags:
        _community = build_community_directory_data()

        def _overlap(tags: list) -> int:
            return sum(1 for t in tags if t.lower() in _member_tags)

        _community["_overlap"] = _community["research_tags_list"].apply(_overlap)
        _related = (
            _community[_community["_overlap"] > 0]
            .sort_values("_overlap", ascending=False)
            .head(6)
        )

        if not _related.empty:
            section_header("Related HBI Community Profiles", color=COMMUNITY_TEAL)
            st.caption("LinkedIn profiles from the HBI Community with overlapping research areas.")
            _cards = []
            for _, cr in _related.iterrows():
                _cards.append(
                    render_community_card_html(
                        name=str(cr["full_name"]) if pd.notna(cr["full_name"]) else "Unknown",
                        current_title=str(cr["current_title"]) if pd.notna(cr.get("current_title")) else "",
                        current_company=str(cr["current_company"]) if pd.notna(cr.get("current_company")) else "",
                        location=str(cr["location"]) if pd.notna(cr.get("location")) else "",
                        tags=cr.get("research_tags_list", []),
                        profile_id=str(cr["profile_id"]),
                        declared_areas=cr.get("researcher_declared_areas_list", []),
                    )
                )
            st.markdown(render_card_grid(_cards), unsafe_allow_html=True)
            st.page_link(
                "pages/2_HBI_Community.py",
                label="View all Community profiles →",
                icon="🤝",
            )

# ── Footer ───────────────────────────────────────────────────────────────────
render_disclaimer()
