"""Exact term discovery across profile research areas and publication keywords."""

import re
import unicodedata

import pandas as pd
import streamlit as st

AREAS = "Areas of Research"
PUBLICATIONS = "Research Keywords from Publications"


def normalize_term(value):
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text.replace("’", "'"))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def build_term_index(directory, keywords, hybrid, source_phrases):
    """Index complete visible-member terms, retaining both evidence sources."""
    frames = []

    def add(frame, column, source):
        if frame.empty or column not in frame:
            return
        part = frame[["member_id", column]].rename(columns={column: "term"}).copy()
        part["source"] = source
        frames.append(part)

    for column in ("research_areas_list", "researcher_declared_areas_list"):
        if column in directory:
            add(directory[["member_id", column]].explode(column), column, AREAS)
    add(source_phrases, "phrase", AREAS)
    if not hybrid.empty:
        accepted = hybrid[hybrid["disposition"].eq("accepted")]
        add(accepted, "preferred_display_label", AREAS)
        add(accepted, "umbrella_label", AREAS)
        # Match the existing Areas explorer's fallback for unavailable source pages.
        fallback = hybrid[
            hybrid["candidate_origin"].str.contains(
                r"structured_source|legacy_research_narrative|biography_",
                case=False, na=False,
            ) & ~hybrid["member_id"].isin(source_phrases.get("member_id", []))
        ]
        add(fallback, "input_phrase", AREAS)
    add(keywords, "keyword", PUBLICATIONS)
    add(keywords, "normalized_keyphrase", PUBLICATIONS)
    if not frames:
        return pd.DataFrame(columns=["member_id", "term", "source", "key"])
    result = pd.concat(frames, ignore_index=True).dropna(subset=["member_id", "term"])
    result["member_id"] = result["member_id"].astype(str)
    result = result[result["member_id"].isin(directory["member_id"].astype(str))].copy()
    result["key"] = result["term"].map(normalize_term)
    return result[result["key"].ne("")].drop_duplicates(["member_id", "key", "source"])


@st.cache_data(ttl=3600)
def load_term_index():
    from utils.data_loader import (
        build_directory_data, load_scopus_research_keywords,
        load_hybrid_research_taxonomy, load_source_research_phrases,
    )
    return build_term_index(
        build_directory_data(), load_scopus_research_keywords(),
        load_hybrid_research_taxonomy(), load_source_research_phrases(),
    )


def match_term(index, term):
    """One result per member; punctuation/case variants match, substrings do not."""
    matches = index[index["key"].eq(normalize_term(term))]
    return matches.groupby("member_id", as_index=False).agg(
        sources=("source", lambda values: sorted(set(values)))
    )
