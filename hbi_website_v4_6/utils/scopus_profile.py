"""Shared rendering for filterable Scopus research data on member profiles."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.components import (
    render_scopus_keyword_table,
    render_scopus_keyword_tags,
)
from utils.scopus_connections import render_scopus_connections
from utils.publication_coverage import publication_coverage_label, publication_year_bounds


def publication_panel_help_text(summary: pd.DataFrame) -> str:
    """Describe public publication coverage and the member-specific span."""
    span_text = ""
    if not summary.empty:
        row = summary.iloc[0]
        first_year = pd.to_numeric(row.get("first_year"), errors="coerce")
        latest_year = pd.to_numeric(row.get("latest_year"), errors="coerce")
        if pd.notna(first_year) and pd.notna(latest_year):
            if int(first_year) == int(latest_year):
                span_text = (
                    f" Publications for this researcher were found in {int(first_year)}."
                )
            else:
                span_text = (
                    " Publications for this researcher were found from "
                    f"{int(first_year)}–{int(latest_year)}."
                )
    return (
        "Publication metrics, research keywords, and research connections are "
        "compiled from publicly indexed publication records linked to this "
        f"researcher. The directory’s publication coverage spans {publication_coverage_label()}."
        f"{span_text} Use the publication-year control to change the period "
        "shown. Research keywords are ranked by supporting publication count "
        "and recency. Publications drawn directly from the public UCalgary "
        "Research profile are labeled separately."
    )


def _filtered_keywords(
    keywords: pd.DataFrame,
    keyword_years: pd.DataFrame,
    year_from: int,
    year_to: int,
) -> pd.DataFrame:
    selected = keyword_years[
        keyword_years["publication_year"].between(year_from, year_to)
    ].copy()
    if selected.empty:
        return pd.DataFrame(
            columns=[
                "keyword",
                "normalized_keyphrase",
                "publication_count",
                "first_year",
                "latest_year",
            ]
        )

    aggregated = (
        selected.groupby("normalized_keyphrase", as_index=False)
        .agg(
            publication_count=("publication_count", "sum"),
            first_year=("publication_year", "min"),
            latest_year=("publication_year", "max"),
        )
    )
    labels = keywords[
        ["normalized_keyphrase", "keyword"]
    ].drop_duplicates("normalized_keyphrase")
    return (
        aggregated.merge(labels, on="normalized_keyphrase", how="left")
        .assign(
            keyword=lambda frame: frame["keyword"].fillna(
                frame["normalized_keyphrase"]
            )
        )
        .sort_values(
            ["publication_count", "latest_year", "normalized_keyphrase"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )


def render_scopus_research_keywords(
    *,
    member_id: str,
    summary: pd.DataFrame,
    keywords: pd.DataFrame,
    keyword_years: pd.DataFrame,
    year_summary: pd.DataFrame,
) -> None:
    """Render publication metrics, year filter, keyword pills, and full table."""
    source_summary = summary.iloc[0]

    available_years = sorted(
        {
            int(year)
            for year in year_summary["publication_year"].dropna().tolist()
        }
    )
    if available_years:
        full_year_from, full_year_to = available_years[0], available_years[-1]
        if full_year_from < full_year_to:
            selected_years = st.slider(
                "Publication years",
                min_value=full_year_from,
                max_value=full_year_to,
                value=(full_year_from, full_year_to),
                key=f"scopus_year_range_{member_id}",
                help=(
                    "Move either end of the range to include or exclude "
                    "publication years from the metrics and research keywords."
                ),
            )
            year_from, year_to = selected_years
        else:
            year_from = year_to = full_year_from
            st.caption(f"Publication year: {full_year_from}")

        selected_year_summary = year_summary[
            year_summary["publication_year"].between(year_from, year_to)
        ]
        publication_count = int(
            selected_year_summary["publication_count"].sum()
        )
        keyword_publication_count = int(
            selected_year_summary["publications_with_keywords"].sum()
        )
        filtered_keywords = _filtered_keywords(
            keywords,
            keyword_years,
            year_from,
            year_to,
        )
    else:
        bounds = publication_year_bounds(summary)
        year_from, year_to = bounds if bounds else (None, None)
        publication_count = int(source_summary["publication_count"])
        keyword_publication_count = int(
            source_summary["publications_with_keywords"]
        )
        filtered_keywords = keywords.copy()

    period = (
        f"the selected period ({year_from}–{year_to})"
        if year_from is not None and year_to is not None
        else "the available publication records"
    )
    keyword_count = len(filtered_keywords)
    st.markdown(
        "##### Research Keywords from Publications",
        help=(
            "These research keywords were found in publication records linked "
            f"to this researcher. They reflect {period} "
            "and are ranked by supporting publication count and "
            "recency."
        ),
    )
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Publications", f"{publication_count:,}")
    metric_two.metric("With keywords", f"{keyword_publication_count:,}")
    metric_three.metric("Unique keywords", f"{keyword_count:,}")

    if not filtered_keywords.empty:
        top_keyword_rows = filtered_keywords.dropna(
            subset=["keyword", "normalized_keyphrase"]
        ).head(10)
        st.markdown(
            render_scopus_keyword_tags(
                top_keyword_rows["keyword"].tolist(),
                top_keyword_rows["normalized_keyphrase"].tolist(),
                max_show=10,
            ),
            unsafe_allow_html=True,
        )

        with st.expander(
            f"View all {len(filtered_keywords):,} research keywords from publications"
        ):
            keyword_table = filtered_keywords[
                [
                    "keyword",
                    "normalized_keyphrase",
                    "publication_count",
                    "latest_year",
                ]
            ].copy()
            table_height = min(540, 54 + (36 * len(keyword_table)))
            components.html(
                render_scopus_keyword_table(
                    keyword_table.to_dict("records"),
                    member_id=member_id,
                ),
                height=table_height,
                scrolling=False,
            )
    elif publication_count == 0:
        st.info(
            f"No indexed publications were found for this researcher in {period}."
        )
    else:
        st.info(
            "No research keywords were found in this researcher’s publications "
            f"in {period}."
        )

    if year_from is None or year_to is None:
        st.caption("Publication dates are unavailable for research connections.")
        return

    render_scopus_connections(
        member_id=member_id,
        researcher_name=str(source_summary.get("researcher_name") or "HBI member"),
        filtered_keywords=filtered_keywords,
        year_from=year_from,
        year_to=year_to,
    )
