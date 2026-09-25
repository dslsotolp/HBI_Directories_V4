"""Cached data loading for the HBI Members website."""

import json

from pathlib import Path

import pandas as pd
import streamlit as st

from utils.education_background import (
    education_display_text,
    education_institution_text,
)
from utils.institution_aliases import normalize_institution

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "csv"
KEYWORD_DIR = Path(__file__).resolve().parent.parent.parent / "keyword_dictionary"
SCOPUS_DIR = Path(__file__).resolve().parent.parent / "data"
DISPLAY_CORRECTIONS_PATH = SCOPUS_DIR / "profile_display_corrections.csv"
RESEARCH_FOOTPRINT_HIGHLIGHTS_PATH = (
    SCOPUS_DIR / "research_footprint_highlights.json"
)
PUBLIC_EXCLUDED_RESEARCH_LABELS = {
    "3 neurobiological circuits",
    "hotchkiss brain institute",
    "interests",
    "journal article",
    "ph",
}
PROFILE_RESEARCH_PHRASE_OVERRIDES = {
    "mem_414b7b0e40": (
        "developmental",
        "ecological",
        "family systems",
        "positive youth development",
        "resiliency",
        "Adolescent development",
        "Child development",
        "International community development",
        "Family psychology (military-connected and first responder families)",
        "Social development",
        "Media studies and literacy",
        "School-based mental health",
        "Stress and child/family impacts",
    ),
}


def _apply_profile_display_corrections(
    data: pd.DataFrame,
    *,
    scope: str,
) -> pd.DataFrame:
    """Apply reviewed exact-value corrections only within an approved field scope."""
    if (
        data.empty
        or not DISPLAY_CORRECTIONS_PATH.exists()
        or DISPLAY_CORRECTIONS_PATH.stat().st_size == 0
    ):
        return data

    corrections = pd.read_csv(DISPLAY_CORRECTIONS_PATH, dtype=str).fillna("")
    required = {
        "scope",
        "member_id",
        "field",
        "source_value",
        "display_value",
    }
    if not required.issubset(corrections.columns):
        return data

    corrections = corrections[corrections["scope"] == scope]
    if corrections.empty or "member_id" not in data.columns:
        return data

    corrected = data.copy()
    member_ids = corrected["member_id"].fillna("").astype(str)
    for row in corrections.to_dict("records"):
        field = str(row["field"])
        if field not in corrected.columns:
            continue
        mask = member_ids.eq(str(row["member_id"])) & corrected[field].fillna(
            ""
        ).astype(str).eq(str(row["source_value"]))
        corrected.loc[mask, field] = str(row["display_value"])
    return corrected


@st.cache_data(ttl=3600)
def load_members():
    data = pd.read_csv(DATA_DIR / "dim_members.csv")
    return _apply_profile_display_corrections(data, scope="member_name")


@st.cache_data(ttl=3600)
def load_positions():
    data = pd.read_csv(DATA_DIR / "dim_positions.csv")
    return _apply_profile_display_corrections(data, scope="position_title")


@st.cache_data(ttl=3600)
def load_research_areas():
    return pd.read_csv(DATA_DIR / "dim_research_areas.csv")


def _load_legacy_publishable_research_tags() -> pd.DataFrame:
    """Return the original UMLS-derived public tags for fallback use only."""
    tags = pd.read_csv(KEYWORD_DIR / "umls_match_all_profiles_final.csv")
    members = load_members()[["member_id", "source_url"]]

    tags = tags.merge(members, on="source_url", how="left")
    tags = tags[tags["member_id"].notna()]
    tags = tags[tags["research_tag_publishable"].notna()]
    tags = tags[tags["research_tag_publishable"].str.strip() != ""]
    tags = tags[
        ~tags["research_tag_publishable"]
        .str.strip()
        .str.casefold()
        .isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
    ]

    # Deduplicate: one row per (member_id, tag)
    result = (
        tags[["member_id", "research_tag_publishable"]]
        .drop_duplicates()
        .rename(columns={"research_tag_publishable": "area"})
        .sort_values(["member_id", "area"])
        .reset_index(drop=True)
    )
    return result


@st.cache_data(ttl=3600)
def load_publishable_research_tags() -> pd.DataFrame:
    """Return methodology-3 standardized terms used across public member views.

    Legacy tags are retained only for members absent from the all-profile hybrid
    run, such as profiles whose source page could not be fetched.
    """
    hybrid = load_hybrid_research_taxonomy()
    accepted = hybrid[
        hybrid["disposition"].eq("accepted")
        & hybrid["preferred_display_label"].ne("")
    ][["member_id", "preferred_display_label"]].rename(
        columns={"preferred_display_label": "area"}
    )

    processed_ids = set(
        load_hybrid_research_taxonomy_summary()["member_id"]
        .dropna()
        .astype(str)
    )
    legacy_fallback = _load_legacy_publishable_research_tags()
    legacy_fallback = legacy_fallback[
        ~legacy_fallback["member_id"].astype(str).isin(processed_ids)
    ]

    result = pd.concat([accepted, legacy_fallback], ignore_index=True)
    result["area"] = result["area"].fillna("").astype(str).str.strip()
    result = result[
        result["member_id"].notna()
        & result["area"].ne("")
        & ~result["area"].str.casefold().isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
    ].copy()
    result["_area_key"] = result["area"].str.casefold()
    return (
        result.drop_duplicates(["member_id", "_area_key"], keep="first")
        .drop(columns="_area_key")
        .sort_values(["member_id", "area"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_publishable_research_tags_v2() -> pd.DataFrame:
    """Return researcher-declared UCalgary areas for Areas of Expertise 2.

    These labels intentionally remain separate from the original UMLS-derived
    methodology so both outputs can be compared without either overwriting the
    other. Canonical MeSH concepts and HBI umbrellas are matching metadata; the
    researcher-declared ``visible_source_label`` is the public display value.
    """
    path = SCOPUS_DIR / "research_areas_v2.csv"
    columns = [
        "member_id",
        "profile_name",
        "source_url",
        "visible_source_label",
        "normalized_label",
        "source_type",
        "visibility_policy",
        "is_public",
        "sort_order",
        "canonical_mesh_ids",
        "canonical_mesh_concepts",
        "hbi_umbrella_ids",
        "hbi_umbrella_tags",
        "taxonomy_status",
        "taxonomy_notes",
        "built_at_utc",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype={"member_id": str})
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    public_mask = data["is_public"].astype(str).str.lower().isin({"true", "1", "yes"})
    data = data[public_mask].copy()
    data["visible_source_label"] = data["visible_source_label"].fillna("").astype(str).str.strip()
    data["normalized_label"] = data["normalized_label"].fillna("").astype(str).str.strip()
    data = data[
        data["member_id"].notna()
        & data["visible_source_label"].ne("")
        & data["normalized_label"].ne("")
    ]
    data["sort_order"] = pd.to_numeric(data["sort_order"], errors="coerce").fillna(9999).astype(int)
    return (
        data[columns]
        .drop_duplicates(["member_id", "normalized_label"], keep="first")
        .sort_values(["member_id", "sort_order", "visible_source_label"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_standardized_research_tags_v2() -> pd.DataFrame:
    """Return accepted MeSH concepts and HBI umbrella tags for methodology v2.

    This is the generated classification layer. It is intentionally separate
    from the researcher-declared source labels returned by
    :func:`load_publishable_research_tags_v2`.
    """
    path = SCOPUS_DIR / "research_tags_v2.csv"
    columns = [
        "member_id",
        "profile_name",
        "source_url",
        "tag_type",
        "tag",
        "normalized_tag",
        "taxonomy_status",
        "source_types",
        "supporting_source_count",
        "supporting_source_labels",
        "includes_legacy_narrative",
        "built_at_utc",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype={"member_id": str})
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    data["tag"] = data["tag"].fillna("").astype(str).str.strip()
    data["normalized_tag"] = data["normalized_tag"].fillna("").astype(str).str.strip()
    data = data[
        data["member_id"].notna()
        & data["tag_type"].isin({"mesh_concept", "hbi_umbrella"})
        & data["taxonomy_status"].eq("accepted")
        & data["tag"].ne("")
        & data["normalized_tag"].ne("")
    ].copy()
    data["supporting_source_count"] = pd.to_numeric(
        data["supporting_source_count"], errors="coerce"
    ).fillna(0).astype(int)
    return (
        data[columns]
        .drop_duplicates(["member_id", "tag_type", "normalized_tag"], keep="first")
        .sort_values(["member_id", "tag_type", "tag"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_hybrid_research_taxonomy() -> pd.DataFrame:
    """Return the all-profile UMLS–MeSH hybrid comparison dataset.

    The file contains accepted, review, rejected, and unresolved audit rows so
    the profile component can preserve source wording and report quality-control
    counts. Only accepted standardized concepts are rendered as public tags.
    """
    path = SCOPUS_DIR / "research_taxonomy_hybrid_all.csv"
    columns = [
        "profile",
        "member_id",
        "source_url",
        "input_phrase",
        "candidate_origin",
        "resolved_phrase",
        "disposition",
        "reason",
        "concept_id",
        "concept_id_system",
        "umls_canonical_label",
        "preferred_display_label",
        "mesh_preferred_label",
        "source_vocabulary",
        "semantic_types",
        "match_method",
        "lexical_score",
        "confidence_0_10",
        "umbrella_id",
        "umbrella_label",
        "umbrella_rule_id",
        "scopus_supporting_publications",
        "scopus_latest_year",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype={"member_id": str})
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    for column in [
        "input_phrase",
        "candidate_origin",
        "disposition",
        "preferred_display_label",
        "umbrella_label",
    ]:
        data[column] = data[column].fillna("").astype(str).str.strip()
    data = data[data["member_id"].notna() & data["input_phrase"].ne("")].copy()
    data["confidence_0_10"] = pd.to_numeric(
        data["confidence_0_10"], errors="coerce"
    ).fillna(0.0)
    # Suppress the erroneous standalone PH term while retaining the source
    # phrase and independently useful Research Theme carried by the same row.
    data.loc[
        data["preferred_display_label"].str.casefold().eq("ph"),
        "preferred_display_label",
    ] = ""
    public_label_mask = (
        data["preferred_display_label"].str.casefold().isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
        | data["umbrella_label"].str.casefold().isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
    )
    data = data[~public_label_mask].copy()
    return data[columns].reset_index(drop=True)


@st.cache_data(ttl=3600)
def load_hybrid_research_taxonomy_summary() -> pd.DataFrame:
    """Return one hybrid-processing summary row for every valid profile."""
    path = SCOPUS_DIR / "research_taxonomy_hybrid_all_profile_summary.csv"
    columns = ["profile", "member_id"]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype={"member_id": str})
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    return data


@st.cache_data(ttl=3600)
def load_scopus_research_keywords() -> pd.DataFrame:
    """Return public-safe, member-linked keywords for all collected publication years."""
    path = SCOPUS_DIR / "scopus_member_keywords.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(
            columns=[
                "member_id", "scopus_author_id", "keyword",
                "normalized_keyphrase", "publication_count",
                "first_year", "latest_year", "display_rank",
            ]
        )
    return pd.read_csv(
        path,
        dtype={"member_id": str, "scopus_author_id": str},
    )


@st.cache_data(ttl=3600)
def load_card_publication_keywords() -> dict[str, list[dict[str, str]]]:
    """Top five full-history publication keywords per member, ranked like profiles."""
    keywords = load_scopus_research_keywords().copy()
    if keywords.empty:
        return {}
    for column in ("keyword", "normalized_keyphrase"):
        keywords[column] = keywords[column].fillna("").astype(str).str.strip()
    keywords = keywords[
        keywords["keyword"].ne("") & keywords["normalized_keyphrase"].ne("")
    ].copy()
    for column in ("publication_count", "latest_year"):
        keywords[column] = pd.to_numeric(keywords[column], errors="coerce").fillna(0)
    keywords = keywords[keywords["publication_count"].gt(0)]
    keywords = keywords.sort_values(
        ["publication_count", "latest_year", "normalized_keyphrase"],
        ascending=[False, False, True], kind="stable",
    ).drop_duplicates(["member_id", "normalized_keyphrase"])
    return {
        str(member_id): group.head(5)[["keyword", "normalized_keyphrase"]].to_dict("records")
        for member_id, group in keywords.groupby("member_id", sort=False)
    }


@st.cache_data(ttl=3600)
def load_scopus_member_summary() -> pd.DataFrame:
    """Return publication and keyword coverage totals for linked HBI members."""
    path = SCOPUS_DIR / "scopus_member_summary.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(
            columns=[
                "member_id", "scopus_author_id", "researcher_name",
                "publication_count", "publications_with_keywords",
                "unique_keyword_count", "first_year", "latest_year",
            ]
        )
    return pd.read_csv(
        path,
        dtype={"member_id": str, "scopus_author_id": str},
    )


@st.cache_data(ttl=3600)
def load_scopus_keyword_years() -> pd.DataFrame:
    """Return public-safe per-member keyword evidence grouped by publication year."""
    path = SCOPUS_DIR / "scopus_member_keyword_years.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(
            columns=[
                "member_id",
                "keyword",
                "normalized_keyphrase",
                "publication_year",
                "publication_count",
            ]
        )
    return pd.read_csv(path, dtype={"member_id": str})


@st.cache_data(ttl=3600)
def load_scopus_member_year_summary() -> pd.DataFrame:
    """Return public-safe publication coverage totals by member and year."""
    path = SCOPUS_DIR / "scopus_member_year_summary.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(
            columns=[
                "member_id",
                "publication_year",
                "publication_count",
                "publications_with_keywords",
            ]
        )
    return pd.read_csv(path, dtype={"member_id": str})


@st.cache_data(ttl=3600)
def load_education():
    return pd.read_csv(DATA_DIR / "dim_education.csv")


@st.cache_data(ttl=3600)
def load_member_institution_tags() -> pd.DataFrame:
    """Return (member_id, institution_tag) rows from members' educational background."""
    edu = load_education()
    edu = edu[
        edu.apply(lambda row: bool(education_display_text(row)), axis=1)
    ].copy()
    edu["raw_name"] = edu.apply(education_institution_text, axis=1)
    edu = edu[["member_id", "raw_name"]]
    combined = edu.dropna(subset=["raw_name"]).copy()
    combined["institution_tag"] = combined["raw_name"].apply(normalize_institution)
    return (
        combined[combined["institution_tag"].str.strip() != ""]
        [["member_id", "institution_tag"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_publications():
    path = DATA_DIR / "dim_publications.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["member_id", "sort_order"])
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def load_activities():
    path = DATA_DIR / "dim_activities.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["member_id", "sort_order"])
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def load_contact_info():
    return pd.read_csv(DATA_DIR / "dim_contact_info.csv")


@st.cache_data(ttl=3600)
def load_member_digital_footprint() -> pd.DataFrame:
    """Return directory-wide verified and UCalgary-declared footprint links."""
    path = SCOPUS_DIR / "member_digital_footprint.csv"
    columns = [
        "member_id", "link_group", "platform", "label", "identifier", "url",
        "relationship_type", "source_url", "verification_status", "display_order",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype=str).fillna("")
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    data["display_order"] = pd.to_numeric(
        data["display_order"], errors="coerce"
    ).fillna(999).astype(int)
    return (
        data[columns]
        .drop_duplicates(["member_id", "url"], keep="first")
        .sort_values(["member_id", "display_order", "label"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_research_footprint_highlights() -> dict[str, dict[str, object]]:
    """Return reviewed member-specific research-footprint synthesis pilots."""
    path = RESEARCH_FOOTPRINT_HIGHLIGHTS_PATH
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    members = payload.get("members", [])
    if not isinstance(members, list):
        return {}
    return {
        str(item.get("member_id")): item
        for item in members
        if isinstance(item, dict) and str(item.get("member_id") or "").strip()
    }


@st.cache_data(ttl=3600)
def load_preferred_contact_methods() -> pd.DataFrame:
    """Return emails explicitly designated as a preferred communication method."""
    path = SCOPUS_DIR / "preferred_contact_methods.csv"
    columns = [
        "member_id", "label", "email", "source_url", "verification_status"
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype=str).fillna("")
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    return data[columns].drop_duplicates(["member_id", "email"]).reset_index(drop=True)


@st.cache_data(ttl=3600)
def load_source_affiliations() -> pd.DataFrame:
    """Return source-preserved UCalgary affiliation cards in published order."""
    path = SCOPUS_DIR / "ucalgary_profile_affiliations.csv"
    columns = [
        "member_id", "title", "affiliation", "sort_order", "source_url",
        "verification_status",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype=str).fillna("")
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    data["sort_order"] = pd.to_numeric(
        data["sort_order"], errors="coerce"
    ).fillna(999).astype(int)
    data = _apply_profile_display_corrections(
        data,
        scope="position_title",
    )
    return (
        data[columns]
        .drop_duplicates(["member_id", "sort_order", "title", "affiliation"])
        .sort_values(["member_id", "sort_order"], kind="stable")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_source_research_phrases() -> pd.DataFrame:
    """Return atomic research phrases preserved from official profile markup."""
    path = SCOPUS_DIR / "ucalgary_profile_research_phrases.csv"
    columns = [
        "member_id", "phrase", "source_type", "sort_order", "source_url",
        "verification_status",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype=str).fillna("")
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    data["sort_order"] = pd.to_numeric(
        data["sort_order"], errors="coerce"
    ).fillna(999).astype(int)
    data = data[
        ~data["phrase"].str.strip().str.casefold().isin(
            PUBLIC_EXCLUDED_RESEARCH_LABELS
        )
    ]
    for member_id, phrases in PROFILE_RESEARCH_PHRASE_OVERRIDES.items():
        member_rows = data[data["member_id"].eq(member_id)]
        source_url = member_rows["source_url"].iloc[0] if not member_rows.empty else ""
        data = data[~data["member_id"].eq(member_id)]
        override_rows = pd.DataFrame(
            [
                {
                    "member_id": member_id,
                    "phrase": phrase,
                    "source_type": "declared_area_detail",
                    "sort_order": sort_order,
                    "source_url": source_url,
                    "verification_status": "source_declared",
                }
                for sort_order, phrase in enumerate(phrases)
            ],
            columns=columns,
        )
        data = pd.concat([data, override_rows], ignore_index=True)
    return (
        data[columns]
        .drop_duplicates(["member_id", "phrase", "source_type"])
        .sort_values(["member_id", "sort_order"], kind="stable")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_researcher_declared_areas() -> pd.DataFrame:
    """Return source-preserved declared areas with hybrid fallback by member."""
    source = load_source_research_phrases()[["member_id", "phrase"]].rename(
        columns={"phrase": "area"}
    )
    source_member_ids = set(source["member_id"].dropna().astype(str))
    hybrid = load_hybrid_research_taxonomy()
    fallback = hybrid.loc[
        hybrid["candidate_origin"].str.contains(
            r"structured_source|legacy_research_narrative|biography_",
            case=False,
            na=False,
            regex=True,
        )
        & ~hybrid["member_id"].astype(str).isin(source_member_ids),
        ["member_id", "input_phrase"],
    ].rename(columns={"input_phrase": "area"})
    result = pd.concat([source, fallback], ignore_index=True)
    result["area"] = result["area"].fillna("").astype(str).str.strip()
    result = result[
        result["member_id"].notna()
        & result["area"].ne("")
        & ~result["area"].str.casefold().isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
    ].copy()
    result["_area_key"] = result["area"].str.casefold()
    return (
        result.drop_duplicates(["member_id", "_area_key"], keep="first")
        .drop(columns="_area_key")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_member_inline_links() -> pd.DataFrame:
    """Return source-verified links embedded in narrative profile fields."""
    path = SCOPUS_DIR / "member_inline_links.csv"
    columns = [
        "member_id",
        "section",
        "anchor_text",
        "url",
        "source_url",
        "verification_status",
    ]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    data = pd.read_csv(path, dtype=str).fillna("")
    for column in columns:
        if column not in data.columns:
            data[column] = ""
    return (
        data[columns]
        .query("member_id != '' and section != '' and anchor_text != '' and url != ''")
        .drop_duplicates(["member_id", "section", "anchor_text", "url"])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def load_news():
    path = DATA_DIR / "dim_news.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["member_id", "sort_order"])
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def build_directory_data():
    """Pre-join members with primary position and research areas for the directory."""
    members = load_members()
    positions = load_positions()
    research_areas = load_publishable_research_tags()
    declared_areas = load_researcher_declared_areas()

    # Primary position per member (lowest sort_order)
    pos_sorted = positions.sort_values(["member_id", "sort_order"])
    primary_pos = (
        pos_sorted.groupby("member_id")
        .first()[["title", "department", "faculty"]]
        .reset_index()
    )

    # Research areas as list per member
    areas_by_member = (
        research_areas.groupby("member_id")["area"]
        .apply(lambda x: x.dropna().tolist())
        .to_dict()
    )
    declared_by_member = (
        declared_areas.groupby("member_id")["area"]
        .apply(lambda x: x.dropna().tolist())
        .to_dict()
    )

    # HBI membership status (Full Member, Associate Member, etc. followed by HBI row)
    _HBI_STATUSES = {
        "Full Member", "Associate Member", "Affiliate Member",
        "Emeritus Member", "Full Member and Chair", "Joint Member",
        "Primary Member", "Principal Member",
    }
    hbi_rows = set(
        zip(
            positions[positions["title"] == "Hotchkiss Brain Institute"]["member_id"],
            positions[positions["title"] == "Hotchkiss Brain Institute"]["sort_order"],
        )
    )
    status_rows = positions[positions["title"].isin(_HBI_STATUSES)].copy()
    status_rows["hbi_follows"] = [
        (mid, so + 1) in hbi_rows
        for mid, so in zip(status_rows["member_id"], status_rows["sort_order"])
    ]
    hbi_status = (
        status_rows[status_rows["hbi_follows"]]
        .sort_values("sort_order")
        .drop_duplicates("member_id", keep="first")
        .set_index("member_id")["title"]
        .to_dict()
    )

    # Merge
    directory = members.merge(primary_pos, on="member_id", how="left")
    directory["research_areas_list"] = directory["member_id"].map(
        lambda mid: areas_by_member.get(mid, [])
    )
    directory["researcher_declared_areas_list"] = directory["member_id"].map(
        lambda mid: declared_by_member.get(mid, [])
    )
    directory["hbi_membership"] = directory["member_id"].map(
        lambda mid: hbi_status.get(mid, "")
    )

    # Apply directory visibility overrides (admin-controlled via dim_directory_overrides.csv)
    overrides_path = DATA_DIR / "dim_directory_overrides.csv"
    if overrides_path.exists():
        try:
            overrides = pd.read_csv(overrides_path, dtype=str)
            if not overrides.empty and "member_id" in overrides.columns and "show_in_directory" in overrides.columns:
                hidden_ids = set(
                    overrides.loc[
                        overrides["show_in_directory"].str.lower() == "false", "member_id"
                    ]
                )
                if hidden_ids:
                    directory = directory[~directory["member_id"].astype(str).isin(hidden_ids)]
        except Exception:
            pass  # Never block the public site due to a bad overrides file

    return directory
