"""Research-keyword-from-publications explorer and profile drill-down."""

import html as html_mod
import re
import unicodedata
from urllib.parse import quote, unquote

import pandas as pd
import streamlit as st
from utils.page_config import BLANK_PAGE_ICON

from utils.components import (
    UCALGARY_RED,
    format_research_label,
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_grid,
    render_card_html,
    render_community_card_html,
    render_community_list_row_html,
    render_disclaimer,
    render_list_row_html,
    render_list_view,
)
from utils.data_loader import build_directory_data, load_scopus_research_keywords
from utils.linkedin_data_loader import build_community_directory_data
from utils.profile_search import search_community_profiles
from utils.publication_coverage import publication_coverage_label


st.set_page_config(
    page_title="Research Keywords from Publications – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
)
inject_custom_css()
render_public_sidebar_navigation("areas")

_esc = lambda value: html_mod.escape(str(value)) if value else ""


def _normalize_keyphrase(value: str) -> str:
    """Match the normalization used by the Scopus collection pipeline."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+/#-]+", " ", text)).strip()


keywords = load_scopus_research_keywords().copy()
if keywords.empty:
    st.warning("Research keyword data from publications is not currently available.")
    render_disclaimer()
    st.stop()

for column in ("publication_count", "first_year", "latest_year"):
    keywords[column] = pd.to_numeric(keywords[column], errors="coerce")
keywords["normalized_keyphrase"] = (
    keywords["normalized_keyphrase"].fillna("").astype(str).str.strip()
)
keywords = keywords[
    keywords["member_id"].notna()
    & keywords["keyword"].notna()
    & (keywords["normalized_keyphrase"] != "")
].copy()
directory = build_directory_data()
visible_member_ids = set(directory["member_id"].astype(str))
keywords = keywords[keywords["member_id"].astype(str).isin(visible_member_ids)].copy()

keyword_param = st.query_params.get("keyword", "")
requested_keyword = unquote(str(keyword_param)).strip() if keyword_param else ""


if not requested_keyword:
    st.markdown(
        '<div class="hbi-banner">'
        "<h1>Research Keywords from Publications</h1>"
        '<p style="font-size:1.1rem;opacity:0.9;">'
        "Browse research keywords found in HBI member publications from "
        f"{publication_coverage_label()}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Choose a stable display variant for each normalized Scopus keyphrase.
    display_variants = (
        keywords.sort_values(
            ["normalized_keyphrase", "publication_count", "latest_year", "keyword"],
            ascending=[True, False, False, True],
        )
        .drop_duplicates("normalized_keyphrase")
        [["normalized_keyphrase", "keyword"]]
    )
    keyword_summary = (
        keywords.groupby("normalized_keyphrase", as_index=False)
        .agg(
            member_count=("member_id", "nunique"),
            supporting_publications=("publication_count", "sum"),
            latest_year=("latest_year", "max"),
        )
        .merge(display_variants, on="normalized_keyphrase", how="left")
    )

    search_col, scope_col, sort_col = st.columns([3, 2, 2])
    with search_col:
        search_query = st.text_input(
            "Search research keywords from publications",
            placeholder="e.g. cognition, stroke, Parkinson’s disease…",
        )
    with scope_col:
        scope = st.selectbox(
            "Profile coverage",
            ["Shared by 2+ profiles", "All keywords"],
        )
    with sort_col:
        sort_by = st.selectbox(
            "Sort",
            ["Most profiles", "Most supporting publications", "Keyword A–Z"],
        )

    filtered_summary = keyword_summary.copy()
    if scope == "Shared by 2+ profiles":
        filtered_summary = filtered_summary[
            filtered_summary["member_count"] >= 2
        ]
    if search_query.strip():
        query = search_query.strip().casefold()
        filtered_summary = filtered_summary[
            filtered_summary["keyword"].str.casefold().str.contains(
                query, na=False, regex=False
            )
            | filtered_summary["normalized_keyphrase"].str.casefold().str.contains(
                query, na=False, regex=False
            )
        ]

    if sort_by == "Most profiles":
        filtered_summary = filtered_summary.sort_values(
            ["member_count", "supporting_publications", "keyword"],
            ascending=[False, False, True],
        )
    elif sort_by == "Most supporting publications":
        filtered_summary = filtered_summary.sort_values(
            ["supporting_publications", "member_count", "keyword"],
            ascending=[False, False, True],
        )
    else:
        filtered_summary = filtered_summary.sort_values(
            "keyword",
            key=lambda series: series.str.casefold(),
        )
    filtered_summary = filtered_summary.reset_index(drop=True)

    st.caption(
        f"{len(filtered_summary):,} research keyword"
        f"{'s' if len(filtered_summary) != 1 else ''} match the current filters. "
        "Keywords retain the wording found in publication records; only case "
        "and punctuation variants are grouped for discovery."
    )

    per_page = 60
    total_pages = max(1, -(-len(filtered_summary) // per_page))
    filter_hash = hash((search_query, scope, sort_by))
    if st.session_state.get("_scopus_keyword_filter_hash") != filter_hash:
        st.session_state["_scopus_keyword_filter_hash"] = filter_hash
        st.session_state["scopus_keyword_page"] = 0

    page_number = max(
        0,
        min(
            int(st.session_state.get("scopus_keyword_page", 0)),
            total_pages - 1,
        ),
    )
    page_data = filtered_summary.iloc[
        page_number * per_page : (page_number + 1) * per_page
    ]

    cards_html = ""
    for _, row in page_data.iterrows():
        label = str(row["keyword"])
        display_label = format_research_label(label)
        normalized = str(row["normalized_keyphrase"])
        member_count = int(row["member_count"])
        supporting_count = int(row["supporting_publications"])
        latest_year = int(row["latest_year"])
        href = f'/Research_Keywords_from_Publications?keyword={quote(normalized, safe="")}'
        cards_html += (
            f'<a href="{href}" class="scopus-topic-link">'
            '<div class="scopus-topic-card">'
            f'<div class="scopus-topic-name">{_esc(display_label)}</div>'
            '<div class="scopus-topic-meta">'
            f'<span>{member_count:,} profile'
            f'{"s" if member_count != 1 else ""}</span>'
            f"<span>{supporting_count:,} supporting publication"
            f'{"s" if supporting_count != 1 else ""}</span>'
            f"<span>Latest: {latest_year}</span>"
            "</div></div></a>"
        )

    if page_data.empty:
        st.info("No research keywords from publications match the current filters.")
    else:
        st.markdown(
            "<style>"
            ".scopus-topic-link{text-decoration:none;}"
            ".scopus-topic-grid{display:grid;"
            "grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px;}"
            ".scopus-topic-card{background:#fff;border:1px solid #e4e4e4;"
            "border-radius:10px;padding:15px 17px;min-height:108px;"
            "box-shadow:0 1px 4px rgba(0,0,0,.05);transition:.15s;}"
            ".scopus-topic-card:hover{box-shadow:0 5px 18px rgba(0,0,0,.13);"
            f"border-color:{UCALGARY_RED};transform:translateY(-2px);}}"
            ".scopus-topic-name{font-size:.97rem;font-weight:650;color:#1A1A1A;"
            "line-height:1.35;margin-bottom:10px;}"
            ".scopus-topic-meta{display:flex;flex-direction:column;gap:2px;"
            "font-size:.78rem;color:#666;}"
            ".scopus-topic-meta span:first-child{color:#A30519;font-weight:650;}"
            "</style>"
            f'<div class="scopus-topic-grid">{cards_html}</div>',
            unsafe_allow_html=True,
        )

        first_col, prev_col, page_col, next_col, last_col = st.columns(
            [1, 1, 2, 1, 1]
        )
        with first_col:
            if st.button(
                "⏮ First",
                disabled=page_number == 0,
                key="scopus_kw_first",
            ):
                st.session_state["scopus_keyword_page"] = 0
                st.rerun()
        with prev_col:
            if st.button(
                "◀ Prev",
                disabled=page_number == 0,
                key="scopus_kw_prev",
            ):
                st.session_state["scopus_keyword_page"] = page_number - 1
                st.rerun()
        with page_col:
            st.markdown(
                f"<p style='text-align:center;padding-top:8px;'>"
                f"Page {page_number + 1:,} of {total_pages:,}</p>",
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button(
                "Next ▶",
                disabled=page_number >= total_pages - 1,
                key="scopus_kw_next",
            ):
                st.session_state["scopus_keyword_page"] = page_number + 1
                st.rerun()
        with last_col:
            if st.button(
                "Last ⏭",
                disabled=page_number >= total_pages - 1,
                key="scopus_kw_last",
            ):
                st.session_state["scopus_keyword_page"] = total_pages - 1
                st.rerun()

    render_disclaimer()
    st.stop()


# A profile link passes the normalized value. The fallback also accepts a raw
# display keyword pasted into the URL.
match_key = requested_keyword.casefold()
if match_key not in set(keywords["normalized_keyphrase"].str.casefold()):
    match_key = _normalize_keyphrase(requested_keyword)

keyword_matches = keywords[
    keywords["normalized_keyphrase"].str.casefold() == match_key
].copy()

community_profiles = search_community_profiles(requested_keyword).merge(
    build_community_directory_data(), on="profile_id", how="inner"
).sort_values(["search_score", "full_name"], ascending=[False, True])

if keyword_matches.empty and community_profiles.empty:
    st.error("No HBI member or Community profiles were found for this keyword.")
    if st.button("← Research Keyword Explorer"):
        st.query_params.clear()
        st.rerun()
    render_disclaimer()
    st.stop()

display_keyword = str(
    keyword_matches.sort_values(
        ["publication_count", "latest_year", "keyword"],
        ascending=[False, False, True],
    ).iloc[0]["keyword"] if not keyword_matches.empty else requested_keyword
)
display_keyword = format_research_label(display_keyword)

evidence = (
    keyword_matches.groupby("member_id", as_index=False)
    .agg(
        supporting_publications=("publication_count", "sum"),
        first_year=("first_year", "min"),
        latest_year=("latest_year", "max"),
    )
)
profiles = (
    directory.merge(evidence, on="member_id", how="inner")
    .sort_values(
        ["supporting_publications", "latest_year", "name"],
        ascending=[False, False, True],
    )
    .reset_index(drop=True)
)

st.markdown(
    '<div class="hbi-banner">'
    "<h1>Research Keyword from Publications</h1>"
    f'<p style="font-size:1.4rem;font-weight:700;">{_esc(display_keyword)}</p>'
    "</div>",
    unsafe_allow_html=True,
)

back_col, _ = st.columns([1.3, 3])
with back_col:
    if st.button("← Research Keyword Explorer"):
        st.query_params.clear()
        st.rerun()

st.caption(
    f"{len(profiles):,} HBI member results · "
    f"{len(community_profiles):,} community results"
)

view_mode = st.radio(
    "View",
    ["Grid", "List"],
    horizontal=True,
    label_visibility="collapsed",
)

member_column, community_column = st.columns(2, gap="large")
render_results = render_card_grid if view_mode == "Grid" else render_list_view

with member_column:
    st.markdown("##### HBI Members")
    st.caption(
        "Exact matches in publication keywords. Supporting-publication counts "
        f"use the directory’s {publication_coverage_label()} publication dataset."
    )
    if profiles.empty:
        st.info("No HBI members have this exact publication keyword.")
    renderer = render_card_html if view_mode == "Grid" else render_list_row_html
    cards = []
    for _, row in profiles.iterrows():
        member_id = str(row["member_id"])
        name = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
        title = str(row["title"]) if pd.notna(row.get("title")) else ""
        department = (
            str(row["department"]) if pd.notna(row.get("department")) else ""
        )
        areas = row.get("research_areas_list", [])
        if not isinstance(areas, list):
            areas = []
        photo_path = row.get("photo_path", "")
        photo_url = (
            f"/app/static/images/member/{photo_path}"
            if photo_path and pd.notna(photo_path)
            else None
        )
        publication_count = int(row["supporting_publications"])
        latest_year = int(row["latest_year"])
        context = (
            f"{publication_count:,} supporting publication"
            f"{'s' if publication_count != 1 else ''} · latest {latest_year}"
        )
        cards.append(
            renderer(
                name,
                title,
                department,
                areas,
                member_id=member_id,
                photo_url=photo_url,
                context_text=context,
                declared_areas=row.get("researcher_declared_areas_list", []),
            )
        )
    if cards:
        st.markdown(render_results(cards), unsafe_allow_html=True)

with community_column:
    st.markdown("##### HBI Community Members")
    st.caption(
        "Related matches in saved LinkedIn profiles, including research terms, "
        "experience, education, and listed publications."
    )
    if community_profiles.empty:
        st.info("No Community profiles match this keyword.")
    renderer = (
        render_community_card_html if view_mode == "Grid"
        else render_community_list_row_html
    )
    cards = []
    for _, row in community_profiles.iterrows():
        photo_path = row.get("photo_path", "")
        photo_url = (
            f"/app/static/images/community/{photo_path}"
            if photo_path and pd.notna(photo_path)
            else None
        )
        cards.append(
            renderer(
                name=str(row.get("full_name") or ""),
                current_title=str(row.get("current_title") or ""),
                current_company=str(row.get("current_company") or ""),
                location=str(row.get("location") or ""),
                tags=row.get("research_tags_list") or [],
                profile_id=str(row.get("profile_id") or ""),
                photo_url=photo_url,
                declared_areas=row.get("researcher_declared_areas_list", []),
            )
        )
    if cards:
        st.markdown(render_results(cards), unsafe_allow_html=True)

render_disclaimer()
