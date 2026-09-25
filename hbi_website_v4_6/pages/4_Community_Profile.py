"""HBI Community Profile — Individual LinkedIn profile view."""

import html as html_mod
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import streamlit as st
from utils.page_config import BLANK_PAGE_ICON

from utils.components import (
    inject_custom_css,
    render_public_sidebar_navigation,
    render_avatar_html,
    render_community_research_tags,
    render_institution_tags,
    render_card_html,
    render_card_grid,
    section_header,
    COMMUNITY_TEAL,
    COMMUNITY_DARK,
    INSTITUTION_COLOR,
    UCALGARY_RED,
    render_disclaimer,
)
from utils.data_loader import build_directory_data
from utils.linkedin_data_loader import (
    load_li_profiles,
    load_li_experience,
    load_li_education,
    load_li_skills,
    load_li_publications,
    load_li_certifications,
    load_li_research_tags,
    get_filtered_profile_tags,
    get_filtered_profile_tags_recent,
    get_profile_institution_tags,
)
from utils.linkedin_expertise import (
    get_linkedin_expertise_year_bounds,
    get_profile_linkedin_expertise,
)

_esc = lambda s: html_mod.escape(str(s)) if s else ""

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Community Profile – HBI", page_icon=BLANK_PAGE_ICON, layout="wide")
inject_custom_css()
render_public_sidebar_navigation("community")

# ── Resolve profile ID ────────────────────────────────────────────────────────
profile_id = st.session_state.get("selected_community_profile") or st.query_params.get("id")

if not profile_id:
    st.warning("No profile selected.")
    if st.button("← Back to Community"):
        st.switch_page("pages/2_HBI_Community.py")
    st.stop()

st.query_params["id"] = profile_id

# ── Load profile ──────────────────────────────────────────────────────────────
profiles = load_li_profiles()
profile = profiles[profiles["profile_id"] == profile_id]

if profile.empty:
    st.error(f"Profile not found: {profile_id}")
    if st.button("← Back to Community"):
        st.switch_page("pages/2_HBI_Community.py")
    st.stop()

p = profile.iloc[0]
name = str(p["full_name"]) if pd.notna(p["full_name"]) else "Unknown"
headline = str(p["headline"]) if pd.notna(p.get("headline")) else ""
location = str(p["location"]) if pd.notna(p.get("location")) else ""
about = str(p["about"]) if pd.notna(p.get("about")) else ""
li_url = str(p["profile_url"]) if pd.notna(p.get("profile_url")) else ""

# ── Related data ──────────────────────────────────────────────────────────────
def _sort(df):
    return df.sort_values("sort_order") if "sort_order" in df.columns else df

mem_exp    = _sort(load_li_experience()   .query("profile_id == @profile_id"))
mem_edu    = _sort(load_li_education()    .query("profile_id == @profile_id"))
mem_skills = _sort(load_li_skills()       .query("profile_id == @profile_id"))
mem_pubs   = _sort(load_li_publications() .query("profile_id == @profile_id"))
_AD_TERMS  = ("why am i seeing this ad", "manage your ad preferences")
mem_certs  = _sort(
    load_li_certifications()
    .query("profile_id == @profile_id")
    .pipe(lambda df: df[~df["title"].astype(str).str.lower().apply(lambda v: any(t in v for t in _AD_TERMS))])
)

# ── Sidebar: research evidence year range ────────────────────────────────────
_pilot_bounds = get_linkedin_expertise_year_bounds()
_default_min_year = _pilot_bounds[0] if _pilot_bounds else 2016
_default_max_year = _pilot_bounds[1] if _pilot_bounds else datetime.now().year
with st.sidebar:
    st.markdown("### Filter")
    research_year_range = st.slider(
        "Research evidence years",
        min_value=int(_default_min_year),
        max_value=int(_default_max_year),
        value=(int(_default_min_year), int(_default_max_year)),
        step=1,
        key=f"community_research_year_range_{profile_id}",
        help=(
            "Filters research terms supported by dated LinkedIn publications, "
            "education, and experience. Headline, About, and skills have no "
            "reliable year and remain visible for every range. Organizations "
            "and institutions are filtered to education and experience "
            "affiliations that overlap the selected years."
        ),
    )

_min_year, _max_year = research_year_range

# Research tags — current method and pilot use the same date range
research_tags = get_filtered_profile_tags_recent(
    profile_id,
    min_year=_min_year,
    max_year=_max_year,
)
pilot_expertise = get_profile_linkedin_expertise(
    profile_id,
    minimum_year=_min_year,
    maximum_year=_max_year,
)

# ── Current title for subtitle ────────────────────────────────────────────────
current_exp = mem_exp[
    mem_exp["end_date"].isna()
    | mem_exp["end_date"].astype(str).str.strip().isin(["", "nan", "None", "Present"])
]
if not current_exp.empty:
    c = current_exp.iloc[0]
    current_title = str(c["title"]) if pd.notna(c["title"]) else ""
    current_company = str(c["company"]) if pd.notna(c["company"]) else ""
elif not mem_exp.empty:
    c = mem_exp.iloc[0]
    current_title = str(c["title"]) if pd.notna(c["title"]) else ""
    current_company = str(c["company"]) if pd.notna(c["company"]) else ""
else:
    current_title = ""
    current_company = ""

# ── Profile banner ────────────────────────────────────────────────────────────
_pp = p.get("photo_path", "")
_photo_url = f"/app/static/images/community/{_pp}" if _pp and pd.notna(_pp) else None
avatar = render_avatar_html(name, 110, photo_url=_photo_url)

banner_html = (
    f'<div style="background:linear-gradient(135deg,{COMMUNITY_TEAL} 0%,{COMMUNITY_DARK} 100%);'
    f'height:180px;border-radius:10px;"></div>'
    f'<div style="margin-top:-60px;padding-left:2rem;display:flex;'
    f'align-items:flex-end;gap:1.5rem;margin-bottom:1.2rem;">'
    f'<div style="border:4px solid #fff;border-radius:16px;overflow:hidden;'
    f'box-shadow:0 2px 10px rgba(0,0,0,0.15);line-height:0;">{avatar}</div>'
    f'<div style="padding-bottom:8px;">'
    f'<div style="font-size:1.8rem;font-weight:700;color:#1A1A1A;'
    f'margin:0;line-height:1.3;">{_esc(name)}</div>'
    f'</div></div>'
)
st.markdown(banner_html, unsafe_allow_html=True)

# ── Navigation row ────────────────────────────────────────────────────────────
# TODO: swap _CHANGE_FORM_URL / _DELETE_FORM_URL for SharePoint form URLs when ready
_CHANGE_FORM_URL = (
    f"mailto:daniel.sotolopez@ucalgary.ca"
    f"?subject=Community%20Profile%20Change%20Request%20%E2%80%93%20{quote(name)}"
    f"&body=Profile%20ID%3A%20{quote(profile_id)}%0A"
    f"Name%3A%20{quote(name)}%0A%0A"
    f"REQUESTED%20CHANGE%3A%0A"
    f"%5BDescribe%20the%20change%20here%5D%0A%0A"
    f"-----%0A"
    f"ADMIN%20INSTRUCTIONS%0A"
    f"-----%0A"
    f"Edit%20the%20relevant%20file%20in%20linkedin_output%2Fcsv%2F%2C%20find%20row%20where%20profile_id%20%3D%20above%0A%0A"
    f"Key%20files%3A%0A"
    f"%20%20linkedin_dim_profiles.csv%20%20%20%20%20%20%20%3C%E2%80%94%20name%2C%20headline%2C%20about%2C%20location%0A"
    f"%20%20linkedin_dim_experience.csv%20%20%20%20%20%3C%E2%80%94%20work%20history%0A"
    f"%20%20linkedin_dim_education.csv%20%20%20%20%20%20%3C%E2%80%94%20degrees%0A"
    f"%20%20linkedin_dim_skills.csv%20%20%20%20%20%20%20%20%20%3C%E2%80%94%20skills%0A"
    f"%20%20linkedin_dim_research_tags.csv%20%20%3C%E2%80%94%20expertise%20tags%0A%0A"
    f"After%20any%20edit%3A%20restart%20the%20website%20server%20to%20clear%20the%20data%20cache."
)
_DELETE_FORM_URL = (
    f"mailto:daniel.sotolopez@ucalgary.ca"
    f"?subject=Profile%20Deletion%20Request%20%E2%80%93%20{quote(name)}"
    f"&body=Profile%20ID%3A%20{quote(profile_id)}%0A"
    f"Name%3A%20{quote(name)}%0A%0A"
    f"REASON%20FOR%20REMOVAL%3A%0A"
    f"%5BDescribe%20reason%20here%5D%0A%0A"
    f"-----%0A"
    f"ADMIN%20INSTRUCTIONS%20%E2%80%94%20DELETE%20ALL%20ROWS%20WHERE%20profile_id%20%3D%20above%20FROM%3A%0A"
    f"-----%0A"
    f"%201.%20linkedin_output%2Fcsv%2Flinkedin_dim_profiles.csv%0A"
    f"%202.%20linkedin_output%2Fcsv%2Flinkedin_dim_experience.csv%0A"
    f"%203.%20linkedin_output%2Fcsv%2Flinkedin_dim_education.csv%0A"
    f"%204.%20linkedin_output%2Fcsv%2Flinkedin_dim_skills.csv%0A"
    f"%205.%20linkedin_output%2Fcsv%2Flinkedin_dim_publications.csv%0A"
    f"%206.%20linkedin_output%2Fcsv%2Flinkedin_dim_certifications.csv%0A"
    f"%207.%20linkedin_output%2Fcsv%2Flinkedin_dim_research_tags.csv%0A%0A"
    f"After%20deleting%3A%20restart%20the%20website%20server%20to%20clear%20the%20data%20cache."
)
nav1, nav2, nav3, nav4 = st.columns([1, 1, 1, 1])
with nav1:
    if st.button("← Back to Community"):
        st.switch_page("pages/2_HBI_Community.py")
with nav2:
    if li_url:
        st.link_button("View on LinkedIn ↗", li_url)
with nav3:
    st.link_button("📬 Suggest a change", _CHANGE_FORM_URL)
with nav4:
    st.link_button("🗑️ Request deletion", _DELETE_FORM_URL)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ── About ─────────────────────────────────────────────────────────────────────
if about:
    section_header("About", color=COMMUNITY_TEAL)
    st.markdown(about)

# ── Research Areas ────────────────────────────────────────────────────────────
if research_tags:
    section_header("Areas of Expertise", color=COMMUNITY_TEAL)
    st.markdown(
        render_community_research_tags(research_tags, max_show=50),
        unsafe_allow_html=True,
    )

# ── Research Areas 2: evidence-scored LinkedIn pilot ─────────────────────────
if pilot_expertise is not None:
    section_header("Areas of Expertise 2 — LinkedIn Evidence", color=COMMUNITY_TEAL)
    st.caption(
        f"Research terms supported by this profile's LinkedIn evidence for "
        f"{_min_year}–{_max_year}. Dated publications, education, and experience "
        "respond to the year filter; undated headline, About, and skills evidence "
        "remains visible."
    )

    declared_terms = pilot_expertise["declared_terms"]
    standardized_terms = pilot_expertise["standardized_terms"]
    umbrella_terms = pilot_expertise["umbrella_terms"]
    metric_declared, metric_standardized, metric_umbrella = st.columns(3)
    metric_declared.metric("Research terms", len(declared_terms))
    metric_standardized.metric("Standardized biomedical terms", len(standardized_terms))
    metric_umbrella.metric("Umbrella research areas", len(umbrella_terms))

    if declared_terms:
        st.markdown("**Researcher/Profile-Declared Wording**")
        st.markdown(
            render_community_research_tags(
                declared_terms,
                max_show=50,
                clickable=False,
            ),
            unsafe_allow_html=True,
        )
    else:
        st.info("No research terms have qualifying evidence in this year range.")

    if standardized_terms:
        st.markdown("**Standardized Biomedical Terms**")
        st.markdown(
            render_community_research_tags(
                standardized_terms,
                max_show=50,
                clickable=False,
            ),
            unsafe_allow_html=True,
        )

    if umbrella_terms:
        st.markdown("**Umbrella Research Areas**")
        st.markdown(
            render_community_research_tags(
                umbrella_terms,
                max_show=50,
                clickable=False,
            ),
            unsafe_allow_html=True,
        )

    evidence_table = pilot_expertise["evidence_table"]
    if not evidence_table.empty:
        with st.expander(
            f"View supporting evidence ({pilot_expertise['dated_evidence_visible']} "
            f"of {pilot_expertise['dated_evidence_total']} dated evidence records in range)"
        ):
            st.dataframe(
                evidence_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "Confidence": st.column_config.NumberColumn(format="%.1f"),
                },
            )
# ── Organizations & Institutions ─────────────────────────────────────────────
profile_institution_tags = get_profile_institution_tags(
    profile_id,
    min_year=_min_year,
    max_year=_max_year,
)
if profile_institution_tags:
    section_header("Organizations & Institutions", color=INSTITUTION_COLOR)
    st.caption(
        f"Affiliations supported by education or experience records overlapping "
        f"{_min_year}–{_max_year}. Undated affiliations remain included."
    )
    st.markdown(
        render_institution_tags(profile_institution_tags, max_show=50),
        unsafe_allow_html=True,
    )
# ── Experience ────────────────────────────────────────────────────────────────
if not mem_exp.empty:
    section_header("Experience", color=COMMUNITY_TEAL)
    for _, exp in mem_exp.iterrows():
        title = str(exp["title"]) if pd.notna(exp["title"]) else ""
        company = str(exp["company"]) if pd.notna(exp["company"]) else ""
        emp_type = str(exp["employment_type"]) if pd.notna(exp.get("employment_type")) else ""
        loc = str(exp["location"]) if pd.notna(exp.get("location")) else ""
        start = str(exp["start_date"]) if pd.notna(exp.get("start_date")) else ""
        end = str(exp["end_date"]) if pd.notna(exp.get("end_date")) else "Present"
        duration = str(exp["duration"]) if pd.notna(exp.get("duration")) else ""
        desc = str(exp["description"]) if pd.notna(exp.get("description")) else ""

        header_parts = [p for p in [title, emp_type] if p]
        if header_parts:
            st.markdown(f"**{_esc(' · '.join(header_parts))}**")
        if company:
            meta = " · ".join(p for p in [company, loc] if p)
            st.caption(meta)
        if start or end:
            date_range = f"{start} – {end}" if start else end
            if duration:
                date_range += f" · {duration}"
            st.caption(date_range)
        if desc:
            with st.expander("Details"):
                st.markdown(desc)
        st.markdown("")

# ── Education ─────────────────────────────────────────────────────────────────
if not mem_edu.empty:
    section_header("Education", color=COMMUNITY_TEAL)
    for _, ed in mem_edu.iterrows():
        school = str(ed["school"]) if pd.notna(ed["school"]) else ""
        degree = str(ed["degree"]) if pd.notna(ed.get("degree")) else ""
        field = str(ed["field_of_study"]) if pd.notna(ed.get("field_of_study")) else ""
        start = str(ed["start_date"]) if pd.notna(ed.get("start_date")) else ""
        end = str(ed["end_date"]) if pd.notna(ed.get("end_date")) else ""
        desc = str(ed["description"]) if pd.notna(ed.get("description")) else ""

        degree_parts = [p for p in [degree, field] if p]
        if degree_parts:
            st.markdown(f"**{_esc(', '.join(degree_parts))}**")
        if school:
            st.caption(school)
        if start or end:
            st.caption(" – ".join(p for p in [start, end] if p))
        if desc:
            with st.expander("Details"):
                st.markdown(desc)
        st.markdown("")

# ── Skills ────────────────────────────────────────────────────────────────────
if not mem_skills.empty:
    section_header("Skills", color=COMMUNITY_TEAL)
    skill_names = mem_skills["skill_name"].dropna().tolist()
    pills_html = "".join(
        f'<span class="li-tag">{_esc(s)}</span>' for s in skill_names[:15]
    )
    if len(skill_names) > 15:
        pills_html += f'<span class="li-tag">+{len(skill_names)-15} more</span>'
    st.markdown(
        f'<div style="line-height:2;">{pills_html}</div>',
        unsafe_allow_html=True,
    )

# ── Publications ──────────────────────────────────────────────────────────────
if not mem_pubs.empty:
    section_header("Publications", color=COMMUNITY_TEAL)
    for _, pub in mem_pubs.iterrows():
        ptitle = str(pub["title"]) if pd.notna(pub["title"]) else ""
        publisher = str(pub["publisher"]) if pd.notna(pub.get("publisher")) else ""
        pub_date = str(pub["pub_date"]) if pd.notna(pub.get("pub_date")) else ""
        purl = str(pub["url"]) if pd.notna(pub.get("url")) else ""
        raw = str(pub["raw_text"]) if pd.notna(pub.get("raw_text")) else ""
        display = ptitle or raw
        if display:
            if purl:
                st.markdown(f"- [{_esc(display)}]({purl})")
            else:
                st.markdown(f"- {_esc(display)}")
            meta = " · ".join(p for p in [publisher, pub_date] if p)
            if meta:
                st.caption(f"  {meta}")

# ── Certifications ────────────────────────────────────────────────────────────
if not mem_certs.empty:
    section_header("Certifications", color=COMMUNITY_TEAL)
    for _, cert in mem_certs.iterrows():
        ctitle = str(cert["title"]) if pd.notna(cert["title"]) else ""
        issuer = str(cert["issuer"]) if pd.notna(cert.get("issuer")) else ""
        issue_date = str(cert["issue_date"]) if pd.notna(cert.get("issue_date")) else ""
        expiry = str(cert["expiry_date"]) if pd.notna(cert.get("expiry_date")) else ""
        curl = str(cert["credential_url"]) if pd.notna(cert.get("credential_url")) else ""

        if ctitle:
            if curl:
                st.markdown(f"**[{_esc(ctitle)}]({curl})**")
            else:
                st.markdown(f"**{_esc(ctitle)}**")
        meta_parts = [p for p in [issuer, issue_date] if p]
        if expiry:
            meta_parts.append(f"Expires {expiry}")
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        st.markdown("")

# ── Related HBI Members ─────────────────────────────────────────────────────
if research_tags:
    _comm_tags = set(t.lower() for t in research_tags)
    _members_dir = build_directory_data()

    def _member_overlap(areas: list) -> int:
        return sum(1 for a in (areas or []) if a.lower() in _comm_tags)

    _members_dir["_overlap"] = _members_dir["research_areas_list"].apply(_member_overlap)
    _related_members = (
        _members_dir[_members_dir["_overlap"] > 0]
        .sort_values("_overlap", ascending=False)
        .head(6)
    )

    if not _related_members.empty:
        st.markdown("---")
        section_header("Related HBI Members", color=UCALGARY_RED)
        st.caption("HBI Members with overlapping areas of expertise.")
        _mcards = []
        for _, _mr in _related_members.iterrows():
            _mcards.append(
                render_card_html(
                    name=str(_mr["name"]) if pd.notna(_mr.get("name")) else "Unknown",
                    title=str(_mr["title"]) if pd.notna(_mr.get("title")) else "",
                    department=str(_mr["department"]) if pd.notna(_mr.get("department")) else "",
                    areas=_mr.get("research_areas_list") or [],
                    member_id=str(_mr["member_id"]),
                    declared_areas=_mr.get("researcher_declared_areas_list", []),
                )
            )
        st.markdown(render_card_grid(_mcards), unsafe_allow_html=True)
        st.page_link("pages/1_HBI_Members.py", label="View all HBI Members →", icon="🧠")

# ── Footer ────────────────────────────────────────────────────────────────────
render_disclaimer()
