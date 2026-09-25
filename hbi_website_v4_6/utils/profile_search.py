"""Shared search indexes for HBI member and community profiles."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd
import streamlit as st

from utils.data_loader import (
    build_directory_data,
    load_activities,
    load_education,
    load_hybrid_research_taxonomy,
    load_members,
    load_publications,
    load_publishable_research_tags_v2,
    load_scopus_research_keywords,
    load_source_affiliations,
    load_source_research_phrases,
    load_standardized_research_tags_v2,
)
from utils.linkedin_data_loader import (
    build_community_directory_data,
    load_li_education,
    load_li_experience,
    load_li_profiles,
    load_li_publications,
    load_li_research_tags,
    load_li_skills,
)

_NON_WORD = re.compile(r"[^a-z0-9]+")
_SEARCH_COLUMNS = ("name_text", "expertise_text", "affiliation_text", "publication_text", "other_text")
_SEARCH_WEIGHTS = {
    "name_text": 100,
    "expertise_text": 50,
    "affiliation_text": 25,
    "publication_text": 10,
    "other_text": 5,
}


def normalize_search_text(value: object) -> str:
    """Return case-, accent-, and punctuation-insensitive searchable text."""
    if value is None or (not isinstance(value, (str, list, tuple, set)) and pd.isna(value)):
        return ""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value if item is not None)
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return _NON_WORD.sub(" ", text.casefold()).strip()


def query_matches(value: object, query: str) -> bool:
    """Match every normalized query token as a substring of the indexed text."""
    text = normalize_search_text(value)
    tokens = normalize_search_text(query).split()
    return bool(tokens) and all(token in text for token in tokens)


def _empty_index(id_column: str, ids: pd.Series) -> pd.DataFrame:
    index = pd.DataFrame({id_column: ids.dropna().astype(str).drop_duplicates()})
    for column in _SEARCH_COLUMNS:
        index[column] = ""
    return index.set_index(id_column)


def _append_frame_text(
    index: pd.DataFrame,
    data: pd.DataFrame,
    id_column: str,
    source_columns: tuple[str, ...],
    target_column: str,
) -> None:
    available = [column for column in source_columns if column in data.columns]
    if data.empty or id_column not in data.columns or not available:
        return
    rows = data[[id_column, *available]].copy()
    rows[id_column] = rows[id_column].fillna("").astype(str)
    rows = rows[rows[id_column].isin(index.index)]
    if rows.empty:
        return
    row_text = rows[available].apply(
        lambda row: " ".join(normalize_search_text(value) for value in row), axis=1
    )
    grouped = row_text.groupby(rows[id_column]).apply(lambda values: " ".join(values))
    additions = index.index.to_series().map(grouped).fillna("")
    index[target_column] = (index[target_column] + " " + additions).str.strip()


def _finalize_index(index: pd.DataFrame) -> pd.DataFrame:
    for column in _SEARCH_COLUMNS:
        index[column] = index[column].map(normalize_search_text)
    index["search_text"] = index[list(_SEARCH_COLUMNS)].agg(" ".join, axis=1).str.strip()
    return index.reset_index()


@st.cache_data(ttl=3600)
def build_member_search_index() -> pd.DataFrame:
    """Build one complete, public-data search document per visible HBI member."""
    directory = build_directory_data()
    index = _empty_index("member_id", directory["member_id"])

    _append_frame_text(index, directory, "member_id", ("name",), "name_text")
    _append_frame_text(
        index, directory, "member_id", ("title", "department", "faculty", "hbi_membership"), "affiliation_text"
    )
    _append_frame_text(index, directory, "member_id", ("research_areas_list",), "expertise_text")
    _append_frame_text(
        index, load_members(), "member_id", ("page_title", "biography", "looking_for"), "other_text"
    )
    _append_frame_text(
        index, load_publishable_research_tags_v2(), "member_id",
        ("visible_source_label", "normalized_label", "canonical_mesh_concepts", "hbi_umbrella_tags"),
        "expertise_text",
    )
    _append_frame_text(
        index, load_standardized_research_tags_v2(), "member_id", ("tag", "supporting_source_labels"), "expertise_text"
    )
    _append_frame_text(index, load_source_research_phrases(), "member_id", ("phrase",), "expertise_text")

    hybrid = load_hybrid_research_taxonomy()
    if not hybrid.empty and "disposition" in hybrid.columns:
        hybrid = hybrid[hybrid["disposition"].eq("accepted")]
    _append_frame_text(
        index, hybrid, "member_id",
        ("input_phrase", "resolved_phrase", "preferred_display_label", "mesh_preferred_label", "umbrella_label"),
        "expertise_text",
    )
    _append_frame_text(
        index, load_scopus_research_keywords(), "member_id", ("keyword", "normalized_keyphrase"), "expertise_text"
    )
    _append_frame_text(
        index, load_source_affiliations(), "member_id", ("title", "affiliation"), "affiliation_text"
    )
    _append_frame_text(
        index, load_education(), "member_id", ("degree", "field", "institution"), "affiliation_text"
    )
    _append_frame_text(
        index, load_publications(), "member_id", ("title", "authors", "journal", "raw_text"), "publication_text"
    )
    _append_frame_text(
        index, load_activities(), "member_id", ("title", "description", "raw_text"), "other_text"
    )
    return _finalize_index(index)


@st.cache_data(ttl=3600)
def build_community_search_index() -> pd.DataFrame:
    """Build one complete search document per public community profile."""
    directory = build_community_directory_data()
    index = _empty_index("profile_id", directory["profile_id"])

    _append_frame_text(index, directory, "profile_id", ("full_name",), "name_text")
    _append_frame_text(
        index, directory, "profile_id",
        ("headline", "current_title", "current_company", "location", "education_list", "institution_tags_list"),
        "affiliation_text",
    )
    _append_frame_text(index, directory, "profile_id", ("research_tags_list",), "expertise_text")
    _append_frame_text(index, load_li_profiles(), "profile_id", ("about",), "other_text")
    _append_frame_text(
        index, load_li_experience(), "profile_id", ("title", "company", "location", "description", "raw_text"), "other_text"
    )
    _append_frame_text(
        index, load_li_education(), "profile_id", ("school", "degree", "field", "description", "raw_text"), "affiliation_text"
    )
    _append_frame_text(index, load_li_skills(), "profile_id", ("skill_name",), "expertise_text")
    _append_frame_text(
        index, load_li_publications(), "profile_id", ("title", "publisher", "description", "raw_text"), "publication_text"
    )
    _append_frame_text(
        index, load_li_research_tags(), "profile_id",
        ("original", "research_area_normalized", "final_output", "final_output_simplified_cleaned", "research_tag_publishable"),
        "expertise_text",
    )
    return _finalize_index(index)


def _search_index(index: pd.DataFrame, id_column: str, query: str) -> pd.DataFrame:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return pd.DataFrame(columns=[id_column, "search_score"])

    matched = index[index["search_text"].map(lambda value: query_matches(value, normalized_query))].copy()
    if matched.empty:
        return pd.DataFrame(columns=[id_column, "search_score"])
    matched["search_score"] = 0
    for column, weight in _SEARCH_WEIGHTS.items():
        matched["search_score"] += matched[column].map(
            lambda value: weight if query_matches(value, normalized_query) else 0
        )
    matched.loc[matched["name_text"].eq(normalized_query), "search_score"] += 200
    return matched[[id_column, "search_score"]].sort_values(
        ["search_score", id_column], ascending=[False, True]
    ).reset_index(drop=True)


def search_member_profiles(query: str) -> pd.DataFrame:
    if not normalize_search_text(query):
        return pd.DataFrame(columns=["member_id", "search_score"])
    return _search_index(build_member_search_index(), "member_id", query)


def search_community_profiles(query: str) -> pd.DataFrame:
    if not normalize_search_text(query):
        return pd.DataFrame(columns=["profile_id", "search_score"])
    return _search_index(build_community_search_index(), "profile_id", query)