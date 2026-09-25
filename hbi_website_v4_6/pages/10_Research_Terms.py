"""Unified discovery from member-card standardized terms."""

import html

import pandas as pd
import streamlit as st

from utils.components import (
    format_research_label, inject_custom_css, render_public_sidebar_navigation,
    render_card_grid, render_list_view, render_card_html, render_list_row_html,
    render_community_card_html, render_community_list_row_html, render_disclaimer,
)
from utils.data_loader import build_directory_data
from utils.linkedin_data_loader import build_community_directory_data
from utils.page_config import BLANK_PAGE_ICON
from utils.profile_search import search_community_profiles
from utils.research_terms import AREAS, PUBLICATIONS, load_term_index, match_term

st.set_page_config(page_title="Research Terms and Areas of Interest – HBI",
                   page_icon=BLANK_PAGE_ICON, layout="wide")
inject_custom_css()
render_public_sidebar_navigation("areas")
term = str(st.query_params.get("term", "")).strip()
st.markdown(
    '<div class="hbi-banner"><h1>Research Terms and Areas of Interest</h1>'
    + (f'<p style="font-size:1.4rem;font-weight:700;">{html.escape(format_research_label(term))}</p>' if term else '')
    + '</div>', unsafe_allow_html=True,
)
with st.form("research_term_search"):
    entered = st.text_input("Research term", value=term,
                            placeholder="e.g. spinal cord injury")
    if st.form_submit_button("Explore"):
        st.query_params["term"] = entered.strip()
        st.rerun()
if not term:
    st.info("Enter a research term to find people through Areas of Research and Research Keywords from Publications.")
    render_disclaimer()
    st.stop()

matches = match_term(load_term_index(), term)
profiles = build_directory_data().merge(matches, on="member_id", how="inner")
profiles = profiles.sort_values("name", key=lambda values: values.fillna("").str.casefold())
community = search_community_profiles(term).merge(
    build_community_directory_data(), on="profile_id", how="inner"
).sort_values(["search_score", "full_name"], ascending=[False, True]).drop_duplicates("profile_id")
area_count = sum(AREAS in sources for sources in matches["sources"])
pub_count = sum(PUBLICATIONS in sources for sources in matches["sources"])
st.caption(f"{len(profiles):,} HBI members · {area_count:,} Areas of Research matches · "
           f"{pub_count:,} Research Keywords from Publications matches · {len(community):,} Community results")
st.caption("Member results combine both sources, with each person shown once. "
           "Matching ignores case, accents and punctuation; related words are not automatically treated as the same term.")
view = st.radio("View", ["Grid", "List"], horizontal=True)
member_col, community_col = st.columns(2, gap="large")
wrap = render_card_grid if view == "Grid" else render_list_view


def text(value):
    return str(value) if pd.notna(value) else ""


def photo(row, group):
    filename = text(row.get("photo_path", ""))
    return f"/app/static/images/{group}/{filename}" if filename else None


with member_col:
    st.markdown("##### HBI Members")
    source = st.radio("Member match source", ["All sources", AREAS, PUBLICATIONS], horizontal=True)
    visible = profiles if source == "All sources" else profiles[
        profiles["sources"].map(lambda sources: source in sources).astype(bool)
    ]
    st.caption(f"{len(visible):,} members · Areas include self-declared areas, standardized profile terms and research themes.")
    if visible.empty:
        st.info("No HBI members match this term in the selected source.")
    renderer = render_card_html if view == "Grid" else render_list_row_html
    cards = [renderer(
        text(row["name"]), text(row.get("title", "")), text(row.get("department", "")),
        row.get("research_areas_list", []), member_id=str(row["member_id"]),
        photo_url=photo(row, "member"), context_text="Matched in: " + " · ".join(row["sources"]),
        declared_areas=row.get("researcher_declared_areas_list", []),
    ) for _, row in visible.iterrows()]
    if cards:
        st.markdown(wrap(cards), unsafe_allow_html=True)

with community_col:
    st.markdown("##### HBI Community Members")
    st.caption("Related matches in saved Community profiles, including research terms, "
               "experience, education and listed publications. These are profile-text matches, "
               "not verified publication-keyword matches.")
    if community.empty:
        st.info("No Community profiles match this term.")
    renderer = render_community_card_html if view == "Grid" else render_community_list_row_html
    cards = [renderer(
        name=text(row.get("full_name", "")), current_title=text(row.get("current_title", "")),
        current_company=text(row.get("current_company", "")), location=text(row.get("location", "")),
        tags=row.get("research_tags_list") or [], profile_id=str(row["profile_id"]),
        photo_url=photo(row, "community"), declared_areas=row.get("researcher_declared_areas_list", []),
    ) for _, row in community.iterrows()]
    if cards:
        st.markdown(wrap(cards), unsafe_allow_html=True)

render_disclaimer()
