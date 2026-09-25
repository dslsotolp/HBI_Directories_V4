"""Year-aware access to the isolated LinkedIn research expertise pilot."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[2]
PILOT_OUTPUT_DIR = PROJECT_DIR / "linkedin_research_taxonomy_pilot" / "output"
FULL_EVIDENCE_CSV = PILOT_OUTPUT_DIR / "linkedin_hybrid_all_evidence.csv"
FULL_DETAIL_CSV = PILOT_OUTPUT_DIR / "linkedin_hybrid_all_details.csv"
FULL_SUMMARY_CSV = PILOT_OUTPUT_DIR / "linkedin_hybrid_all_profile_summary.csv"
EVIDENCE_CSV = (
    FULL_EVIDENCE_CSV
    if FULL_EVIDENCE_CSV.exists()
    else PILOT_OUTPUT_DIR / "linkedin_hybrid_pilot_evidence.csv"
)
DETAIL_CSV = (
    FULL_DETAIL_CSV
    if FULL_DETAIL_CSV.exists()
    else PILOT_OUTPUT_DIR / "linkedin_hybrid_pilot_details.csv"
)
SUMMARY_CSV = (
    FULL_SUMMARY_CSV
    if FULL_SUMMARY_CSV.exists()
    else PILOT_OUTPUT_DIR / "linkedin_hybrid_pilot_profile_summary.csv"
)

SOURCE_LABELS = {
    "linkedin_skill": "Skills",
    "linkedin_headline": "Headline",
    "linkedin_about_explicit": "About — explicit statement",
    "linkedin_about": "About",
    "linkedin_experience_title_current": "Current experience title",
    "linkedin_experience_description_current": "Current experience",
    "linkedin_experience_title_recent": "Previous experience title",
    "linkedin_experience_description_recent": "Previous experience",
    "linkedin_publication_title": "Publication title",
    "linkedin_publication_description": "Publication description",
    "linkedin_education": "Education",
}


def _normalise(value: object) -> str:
    text = str(value or "").replace("’", "'").casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#]+", " ", text)).strip()


def _as_bool(value: object) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes"}


@st.cache_data(ttl=3600, show_spinner=False)
def load_linkedin_expertise_evidence() -> pd.DataFrame:
    if not EVIDENCE_CSV.exists():
        return pd.DataFrame()
    evidence = pd.read_csv(EVIDENCE_CSV).fillna("")
    for column in ("evidence_year", "evidence_start_year", "evidence_end_year"):
        if column not in evidence.columns:
            evidence[column] = evidence.get("evidence_year", 0)
        evidence[column] = pd.to_numeric(evidence[column], errors="coerce").fillna(0).astype(int)
    evidence["source_weight"] = pd.to_numeric(
        evidence.get("source_weight", 0), errors="coerce"
    ).fillna(0.0)
    evidence["explicit"] = evidence.get("explicit", False).apply(_as_bool)
    evidence["controlled"] = evidence.get("controlled", False).apply(_as_bool)
    evidence["_term_key"] = evidence["canonical_label"].apply(_normalise)
    return evidence


@st.cache_data(ttl=3600, show_spinner=False)
def load_linkedin_expertise_details() -> pd.DataFrame:
    if not DETAIL_CSV.exists():
        return pd.DataFrame()
    details = pd.read_csv(DETAIL_CSV).fillna("")
    details["_term_key"] = details["display_label"].apply(_normalise)
    return details


@st.cache_data(ttl=3600, show_spinner=False)
def load_linkedin_expertise_summary() -> pd.DataFrame:
    if not SUMMARY_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(SUMMARY_CSV).fillna("")


def get_linkedin_expertise_year_bounds() -> tuple[int, int] | None:
    """Return the dated evidence span represented in the pilot."""

    evidence = load_linkedin_expertise_evidence()
    if evidence.empty:
        return None
    years: list[int] = []
    for column in ("evidence_start_year", "evidence_end_year"):
        years.extend(
            int(value)
            for value in evidence[column].tolist()
            if int(value) > 0
        )
    return (min(years), max(years)) if years else None


def _overlaps_year_range(row: pd.Series, minimum_year: int, maximum_year: int) -> bool:
    start = int(row.get("evidence_start_year", 0) or 0)
    end = int(row.get("evidence_end_year", 0) or 0)
    if start <= 0 and end <= 0:
        return True
    start = start or end
    end = end or start
    return start <= maximum_year and end >= minimum_year


def _candidate_score(group: pd.DataFrame) -> float:
    base = float(group["source_weight"].max())
    source_count = int(group["source_section"].nunique())
    evidence_bonus = min(0.10, 0.025 * max(0, len(group) - 1))
    source_bonus = min(0.10, 0.04 * max(0, source_count - 1))
    explicit_bonus = 0.035 if bool(group["explicit"].any()) else 0.0
    controlled_bonus = 0.035 if bool(group["controlled"].any()) else 0.0
    return round(min(0.99, base + evidence_bonus + source_bonus + explicit_bonus + controlled_bonus), 3)


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        key = _normalise(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def get_profile_linkedin_expertise(
    profile_id: str,
    minimum_year: int,
    maximum_year: int,
) -> dict[str, object] | None:
    """Return visible pilot layers after filtering dated evidence by overlap.

    Headline, About, and skills evidence has no reliable year and remains
    visible for every range. Experience/education spans and publication dates
    must overlap the selected range. Candidate confidence is recalculated after
    filtering, so a term can disappear if its remaining evidence is too weak.
    """

    evidence = load_linkedin_expertise_evidence()
    details = load_linkedin_expertise_details()
    summary = load_linkedin_expertise_summary()
    profile_is_in_scope = (
        not summary.empty
        and summary["profile_id"].astype(str).eq(str(profile_id)).any()
    )
    if not profile_is_in_scope:
        return None
    profile_evidence = evidence[evidence["profile_id"].astype(str).eq(str(profile_id))].copy()
    profile_details = details[details["profile_id"].astype(str).eq(str(profile_id))].copy()
    if profile_evidence.empty or profile_details.empty:
        return {
            "declared_terms": [],
            "standardized_terms": [],
            "umbrella_terms": [],
            "evidence_table": pd.DataFrame(),
            "dated_evidence_total": 0,
            "dated_evidence_visible": 0,
            "minimum_year": int(minimum_year),
            "maximum_year": int(maximum_year),
        }

    visible_evidence = profile_evidence[
        profile_evidence.apply(
            _overlaps_year_range,
            axis=1,
            minimum_year=int(minimum_year),
            maximum_year=int(maximum_year),
        )
    ].copy()

    visible_candidates: list[dict[str, object]] = []
    for term_key, group in visible_evidence.groupby("_term_key", sort=False):
        score = _candidate_score(group)
        controlled = bool(group["controlled"].any())
        threshold = 0.68 if controlled else 0.84
        if score < threshold:
            continue
        detail_rows = profile_details[profile_details["_term_key"].eq(term_key)]
        if detail_rows.empty:
            continue
        detail = detail_rows.iloc[0]
        dated_years = [
            int(value)
            for value in group["evidence_end_year"].tolist()
            if int(value) > 0
        ]
        sources = [
            SOURCE_LABELS.get(str(source), str(source).replace("linkedin_", "").replace("_", " ").title())
            for source in sorted(group["source_section"].astype(str).unique())
        ]
        visible_candidates.append(
            {
                "display_label": str(detail.get("display_label", "")),
                "confidence": round(score * 10, 1),
                "sources": " · ".join(sources),
                "latest_year": max(dated_years) if dated_years else 0,
                "standardization_disposition": str(detail.get("standardization_disposition", "")),
                "standardized_label": str(detail.get("standardized_label", "")),
                "public_umbrella": str(detail.get("public_umbrella", "")),
            }
        )

    visible_candidates.sort(
        key=lambda row: (-float(row["confidence"]), str(row["display_label"]).casefold())
    )
    declared = _unique_in_order([str(row["display_label"]) for row in visible_candidates])
    standardized = _unique_in_order(
        [
            str(row["standardized_label"])
            for row in visible_candidates
            if row["standardization_disposition"] == "accepted"
        ]
    )
    umbrellas = _unique_in_order(
        [str(row["public_umbrella"]) for row in visible_candidates]
    )
    evidence_table = pd.DataFrame(
        [
            {
                "Research term": row["display_label"],
                "Confidence": row["confidence"],
                "Evidence sources": row["sources"],
                "Latest dated evidence": (
                    str(row["latest_year"]) if row["latest_year"] else "Undated"
                ),
            }
            for row in visible_candidates
        ]
    )
    dated_total = int(
        (
            (profile_evidence["evidence_start_year"] > 0)
            | (profile_evidence["evidence_end_year"] > 0)
        ).sum()
    )
    dated_visible = int(
        (
            (visible_evidence["evidence_start_year"] > 0)
            | (visible_evidence["evidence_end_year"] > 0)
        ).sum()
    )
    return {
        "declared_terms": declared,
        "standardized_terms": standardized,
        "umbrella_terms": umbrellas,
        "evidence_table": evidence_table,
        "dated_evidence_total": dated_total,
        "dated_evidence_visible": dated_visible,
        "minimum_year": int(minimum_year),
        "maximum_year": int(maximum_year),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_profiles_linkedin_expertise(
    minimum_year: int,
    maximum_year: int,
) -> dict[str, dict[str, object]]:
    """Return year-filtered expertise layers for every in-scope profile."""
    summary = load_linkedin_expertise_summary()
    if summary.empty or "profile_id" not in summary.columns:
        return {}
    result: dict[str, dict[str, object]] = {}
    for profile_id in summary["profile_id"].dropna().astype(str).unique():
        expertise = get_profile_linkedin_expertise(
            profile_id,
            minimum_year,
            maximum_year,
        )
        if expertise is not None:
            result[profile_id] = expertise
    return result
