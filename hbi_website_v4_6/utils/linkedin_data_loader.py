"""Cached data loading for LinkedIn Community profiles."""

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.data_loader import (
    PUBLIC_EXCLUDED_RESEARCH_LABELS,
    load_hybrid_research_taxonomy,
)
from utils.institution_aliases import normalize_institution
from utils.linkedin_expertise import (
    get_all_profiles_linkedin_expertise,
    get_linkedin_expertise_year_bounds,
)

LINKEDIN_DIR = Path(__file__).resolve().parent.parent.parent / "linkedin_output" / "csv"

_MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€™", "â€“", "â€”", "ðŸ", "ï¿½")
_CANONICAL_PROFILE_NAMES = {
    "46f9fd7a-681a-433b-9b1b-b1b97419df7f": "Guillermo Delgado-García",
    "c482b87a-e1fb-469c-bc13-0fe781d721cb": "Karla Batista García-Ramó",
}

# Reviewed photo suppressions are intentionally profile-specific. This avoids
# showing a known incorrect portrait while preserving every other photo.
_SUPPRESSED_PROFILE_PHOTO_IDS = {
    "192f55da-ccb8-4044-aaa6-85ecbb975620",  # M. Reza Zamani
    "05294035-6509-4928-8f61-52aaa10ad166",  # Randall Marusyk
    "2c06bb8b-d6a1-4741-8970-4ce0860de006",  # Ehsan Hakimi
    "41d3dad9-2a92-40ad-8922-3ec7fd60894a",  # Yasmeen Naseem
    "835db8ff-2a81-4470-a51f-3a9567827e6b",  # Rafee Al Ahsan
    "cc357ee5-52d2-4f98-b44d-f5006ad3650a",  # Indrajit Prajapati
    "64c97947-aec6-4706-9332-cfbb7267a75e",  # Jaanya Lal
    "6da8654b-0024-4612-b1bc-7bb110709506",  # Badee Khnaijer
}


def _repair_mojibake(value):
    """Repair UTF-8 text that was accidentally decoded as Latin-1/CP1252."""
    if not isinstance(value, str) or not any(marker in value for marker in _MOJIBAKE_MARKERS):
        return value

    def _score(text: str) -> int:
        return sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)

    best = value
    for encoding in ("latin-1", "cp1252"):
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if _score(candidate) < _score(best):
            best = candidate
    return best


@st.cache_data(ttl=3600)
def load_li_profiles() -> pd.DataFrame:
    profiles = pd.read_csv(LINKEDIN_DIR / "linkedin_dim_profiles.csv")
    profiles["full_name"] = profiles["full_name"].apply(_repair_mojibake)
    profiles["full_name"] = profiles.apply(
        lambda row: _CANONICAL_PROFILE_NAMES.get(row["profile_id"], row["full_name"]),
        axis=1,
    )
    if "photo_path" in profiles.columns:
        profiles.loc[
            profiles["profile_id"].isin(_SUPPRESSED_PROFILE_PHOTO_IDS),
            "photo_path",
        ] = ""
    return profiles


@st.cache_data(ttl=3600)
def load_li_experience() -> pd.DataFrame:
    return pd.read_csv(LINKEDIN_DIR / "linkedin_dim_experience.csv")


@st.cache_data(ttl=3600)
def load_li_education() -> pd.DataFrame:
    return pd.read_csv(LINKEDIN_DIR / "linkedin_dim_education.csv")


@st.cache_data(ttl=3600)
def load_li_skills() -> pd.DataFrame:
    return pd.read_csv(LINKEDIN_DIR / "linkedin_dim_skills.csv")


@st.cache_data(ttl=3600)
def load_li_publications() -> pd.DataFrame:
    df = pd.read_csv(LINKEDIN_DIR / "linkedin_dim_publications.csv")
    # Drop rows where pub_date contains a LinkedIn connection-degree badge
    # (e.g. "1st", "2nd", "3rd", "3rd+") — these are mistakenly scraped
    # connection/suggested-people entries, not real publications.
    connection_degree = df["pub_date"].astype(str).str.match(r"^\d(?:st|nd|rd)\+?$")
    return df[~connection_degree].reset_index(drop=True)


@st.cache_data(ttl=3600)
def load_li_certifications() -> pd.DataFrame:
    return pd.read_csv(LINKEDIN_DIR / "linkedin_dim_certifications.csv")


@st.cache_data(ttl=3600)
def load_li_research_tags() -> pd.DataFrame:
    return pd.read_csv(LINKEDIN_DIR / "linkedin_dim_research_tags.csv")


@st.cache_data(ttl=3600)
def load_li_institution_tags() -> pd.DataFrame:
    """Return (profile_id, institution_tag) rows from education + experience data."""
    edu = load_li_education()[["profile_id", "school"]].rename(columns={"school": "raw_name"})
    exp = load_li_experience()[["profile_id", "company"]].rename(columns={"company": "raw_name"})
    combined = pd.concat([edu, exp], ignore_index=True).dropna(subset=["raw_name"])
    combined = combined.copy()
    combined["institution_tag"] = combined["raw_name"].apply(normalize_institution)
    return (
        combined[combined["institution_tag"].str.strip() != ""]
        [["profile_id", "institution_tag"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


def _affiliation_overlaps_range(
    row: pd.Series,
    min_year: int,
    max_year: int,
) -> bool:
    """Return whether an education or experience affiliation overlaps a range.

    A missing end year paired with a known start year is treated as ongoing.
    Completely undated affiliations remain visible because there is no reliable
    evidence for excluding them from a selected period.
    """
    import datetime as _dt

    def _known_year(value) -> int:
        text = str(value or "").strip()
        if not text or text.casefold() in {"nan", "none"}:
            return 0
        if text.casefold() == "present":
            return _dt.datetime.now().year
        match = re.search(r"\b(?:19|20)\d{2}\b", text)
        return int(match.group()) if match else 0

    start = _known_year(row.get("start_date", ""))
    end = _known_year(row.get("end_date", ""))
    if not start and not end:
        return True
    if start and not end:
        end = _dt.datetime.now().year
    elif end and not start:
        start = end
    return start <= max_year and end >= min_year


def get_profile_institution_tags(
    profile_id: str,
    min_year: int | None = None,
    max_year: int | None = None,
) -> list[str]:
    """Return sorted institution tags for one profile and optional year range."""
    if min_year is None and max_year is None:
        tags_df = load_li_institution_tags()
    else:
        import datetime as _dt

        range_min = int(min_year) if min_year is not None else 1900
        range_max = int(max_year) if max_year is not None else _dt.datetime.now().year
        edu = load_li_education()
        exp = load_li_experience()
        edu = edu[edu["profile_id"] == profile_id].copy()
        exp = exp[exp["profile_id"] == profile_id].copy()
        if not edu.empty:
            edu_mask = edu.apply(
                _affiliation_overlaps_range,
                axis=1,
                min_year=range_min,
                max_year=range_max,
            )
            edu = edu.loc[edu_mask.astype(bool)]
        if not exp.empty:
            exp_mask = exp.apply(
                _affiliation_overlaps_range,
                axis=1,
                min_year=range_min,
                max_year=range_max,
            )
            exp = exp.loc[exp_mask.astype(bool)]
        edu = edu[["profile_id", "school"]].rename(columns={"school": "raw_name"})
        exp = exp[["profile_id", "company"]].rename(columns={"company": "raw_name"})
        tags_df = pd.concat([edu, exp], ignore_index=True).dropna(subset=["raw_name"])
        tags_df["institution_tag"] = tags_df["raw_name"].apply(normalize_institution)

    return sorted(
        tags_df.loc[tags_df["profile_id"] == profile_id, "institution_tag"]
        .dropna()
        .loc[lambda values: values.str.strip() != ""]
        .unique()
        .tolist()
    )


@st.cache_data(ttl=3600)
def _load_members_tag_vocabulary() -> tuple[dict, dict]:
    """Build lookup tables from accepted methodology-3 member concepts.

    Returns
    -------
    cuis_to_tag : dict[str, str]
        Individual UMLS CUI code -> methodology-3 preferred display label.
    strings_to_tag : dict[str, str]
        Lowercase accepted phrase or concept label -> preferred display label.
    """
    taxonomy = load_hybrid_research_taxonomy()
    accepted = taxonomy[
        taxonomy["disposition"].eq("accepted")
        & taxonomy["preferred_display_label"].ne("")
        & ~taxonomy["preferred_display_label"]
        .str.casefold()
        .isin(PUBLIC_EXCLUDED_RESEARCH_LABELS)
    ]

    strings_to_tag: dict[str, str] = {}
    cuis_to_tag: dict[str, str] = {}
    alias_columns = (
        "input_phrase",
        "resolved_phrase",
        "preferred_display_label",
        "umls_canonical_label",
        "mesh_preferred_label",
    )
    for row in accepted.itertuples(index=False):
        canonical = str(row.preferred_display_label).strip()
        concept_id = str(row.concept_id).strip()
        if concept_id and concept_id.casefold() != "nan":
            cuis_to_tag.setdefault(concept_id, canonical)
        for column in alias_columns:
            alias = str(getattr(row, column)).strip()
            if alias and alias.casefold() != "nan":
                strings_to_tag.setdefault(alias.casefold(), canonical)

    return cuis_to_tag, strings_to_tag


def _filter_community_tags(rt_df: pd.DataFrame) -> pd.DataFrame:
    """Two-pass methodology-3 filter on a LinkedIn research_tags DataFrame.

    Pass 1 (CUI-based): keep rows whose matched_cuis intersects an accepted
    methodology-3 concept; display its preferred standardized label.

    Pass 2 (string fallback): for rows not yet matched, check whether
    final_output_simplified_cleaned matches an accepted methodology-3 phrase
    or label; display the same preferred standardized label.

    Returns a deduplicated DataFrame with columns [profile_id, display_tag].
    """
    cuis_to_tag, strings_to_tag = _load_members_tag_vocabulary()

    df = rt_df[["profile_id", "matched_cuis", "final_output_simplified_cleaned"]].copy()

    # Pass 1 — CUI match
    def _cui_hit(cuis_str) -> str | None:
        if not pd.notna(cuis_str):
            return None
        for cui in str(cuis_str).split("|"):
            canonical = cuis_to_tag.get(cui.strip())
            if canonical:
                return canonical
        return None

    df["_pass1"] = df["matched_cuis"].apply(_cui_hit)

    # Pass 2 — string match on final_output_simplified_cleaned (rows not yet matched)
    mask_no_hit = df["_pass1"].isna() & df["final_output_simplified_cleaned"].notna()
    df.loc[mask_no_hit, "_pass2"] = (
        df.loc[mask_no_hit, "final_output_simplified_cleaned"]
        .str.strip()
        .str.lower()
        .map(strings_to_tag)
    )

    df["display_tag"] = df["_pass1"].combine_first(df.get("_pass2", pd.Series(dtype=str)))
    df.loc[
        df["display_tag"].fillna("").str.strip().str.casefold().isin(
            PUBLIC_EXCLUDED_RESEARCH_LABELS
        ),
        "display_tag",
    ] = None

    matched = (
        df[df["display_tag"].notna()][["profile_id", "display_tag"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return matched


def get_filtered_profile_tags(profile_id: str) -> list[str]:
    """Return filtered, sorted research tags for a single community profile."""
    rt_df = load_li_research_tags()
    profile_rt = rt_df[rt_df["profile_id"] == profile_id]
    if profile_rt.empty:
        return []
    matched = _filter_community_tags(profile_rt)
    return sorted(matched["display_tag"].dropna().unique().tolist())


def _parse_exp_year(end_date_str) -> int:
    """Convert a date string to an integer year.

    Handles: "Present", NaN/None, "Jan 2022", "Feb 2016", bare "2022",
    and "Jun 14, 2021" (pub_date format with day).
    Returns the current year for anything that can't be parsed (safe fallback
    so unknown dates are always treated as recent).
    """
    import datetime as _dt
    import re as _re
    current = _dt.datetime.now().year
    if not end_date_str or not isinstance(end_date_str, str):
        return current
    s = end_date_str.strip()
    if s in ("", "nan", "None", "Present"):
        return current
    try:
        return _dt.datetime.strptime(s, "%b %Y").year
    except ValueError:
        pass
    try:
        return int(s)
    except ValueError:
        pass
    # Regex fallback: extract any 4-digit year (handles "Jun 14, 2021" etc.)
    m = _re.search(r'\b(19|20)\d{2}\b', s)
    if m:
        return int(m.group())
    return current


# Single generic words that exist in the vocabulary but add no value as
# standalone display tags.
_TAG_DISPLAY_BLOCKLIST: set[str] = {
    "Adults", "Analysis", "Clinical",
    "Hotchkiss Brain Institute",
    "New York",
    "Previously",
}


def _tags_from_text(text: str, strings_to_tag: dict) -> set:
    """Scan *text* (lowercase) for HBI Members vocabulary terms.

    Returns the set of canonical display tags whose lowercase vocabulary
    string appears anywhere in the text.  Terms shorter than 4 chars are
    skipped to avoid false positives on common words.
    """
    found = set()
    for term_lower, canonical in strings_to_tag.items():
        if len(term_lower) > 3 and term_lower in text:
            found.add(canonical)
    return found - _TAG_DISPLAY_BLOCKLIST


def _experience_overlaps_range(row: pd.Series, min_year: int, max_year: int) -> bool:
    """Return whether an experience position overlaps the selected years."""
    import datetime as _dt

    def _known_year(value) -> int:
        text = str(value or "").strip()
        if not text or text in {"nan", "None"}:
            return 0
        if text.casefold() == "present":
            return _dt.datetime.now().year
        match = re.search(r"\b(?:19|20)\d{2}\b", text)
        return int(match.group()) if match else 0

    start = _known_year(row.get("start_date", ""))
    end = _known_year(row.get("end_date", ""))
    start = start or end or _dt.datetime.now().year
    end = end or _dt.datetime.now().year
    return start <= max_year and end >= min_year


def _exp_text_for_profile(
    profile_exp: pd.DataFrame,
    min_year: int,
    max_year: int | None = None,
) -> str:
    """Concatenate experience descriptions whose position overlaps the range."""
    if profile_exp.empty or "description" not in profile_exp.columns:
        return ""
    import datetime as _dt

    max_year = max_year or _dt.datetime.now().year
    recent = profile_exp[
        profile_exp.apply(
            _experience_overlaps_range,
            axis=1,
            min_year=min_year,
            max_year=max_year,
        )
    ]
    return " ".join(
        str(d).lower()
        for d in recent["description"].dropna()
        if str(d).strip() not in ("", "nan")
    )


def _static_text_for_profile(
    profile_id: str,
    profiles_df: pd.DataFrame,
    skills_df: pd.DataFrame,
) -> str:
    """Return concatenated lowercase static (undated) text for a profile.

    Includes only the LinkedIn about text and skill names — the two sources
    that carry no date information.  Publications and experience are
    date-filtered separately.
    """
    parts: list[str] = []
    # About text
    for val in profiles_df.loc[profiles_df["profile_id"] == profile_id, "about"].dropna():
        s = str(val).strip()
        if s and s != "nan":
            parts.append(s.lower())
    # Skill names
    for val in skills_df.loc[skills_df["profile_id"] == profile_id, "skill_name"].dropna():
        s = str(val).strip()
        if s and s != "nan":
            parts.append(s.lower())
    return " ".join(parts)


def _recent_pubs_text_for_profile(
    profile_id: str,
    pubs_df: pd.DataFrame,
    min_year: int,
    max_year: int | None = None,
) -> str:
    """Concatenate publication title/description within the selected range.

    Publications without a parseable pub_date are always included
    (conservative fallback, same as experience with no end_date).
    """
    profile_pubs = pubs_df[pubs_df["profile_id"] == profile_id]
    import datetime as _dt

    max_year = max_year or _dt.datetime.now().year
    recent = profile_pubs[
        profile_pubs["pub_date"].apply(_parse_exp_year).between(min_year, max_year)
    ] if "pub_date" in profile_pubs.columns else profile_pubs
    parts: list[str] = []
    for col in ("title", "description"):
        if col in recent.columns:
            for val in recent[col].dropna():
                s = str(val).strip()
                if s and s != "nan":
                    parts.append(s.lower())
    return " ".join(parts)


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_profiles_recent_tags(
    min_year: int = 2016,
    max_year: int | None = None,
) -> dict:
    """Batch-compute recency-filtered research tags for every community profile.

    How it works
    ------------
    All tag sources are scanned via phrase-matching against the HBI Members
    vocabulary.  Only LinkedIn skills and about text are always included
    (they carry no date).  Experience descriptions and publications are
    included only when they fall within the lookback window (ended/published
    >= min_year).  This avoids false-positive CUI matches from the
    pre-extracted research_tags rows.  If no tags survive the filter, an
    empty list is returned (the UI hides the section gracefully).

    Returns {profile_id: [display_tags]}.
    """
    import datetime as _dt

    max_year = max_year or _dt.datetime.now().year
    exp_df = load_li_experience().copy()
    profiles_df = load_li_profiles()
    skills_df = load_li_skills()
    pubs_df = load_li_publications()
    _, strings_to_tag = _load_members_tag_vocabulary()

    # ── Pre-index static (undated) text sources by profile_id ───────────────
    about_by_pid: dict = (
        profiles_df[profiles_df["about"].notna()]
        .set_index("profile_id")["about"]
        .apply(lambda v: str(v).lower())
        .to_dict()
    )
    skills_by_pid: dict = (
        skills_df.dropna(subset=["skill_name"])
        .groupby("profile_id")["skill_name"]
        .apply(lambda x: " ".join(str(v).lower() for v in x))
        .to_dict()
    )

    # ── Recent publications (pub_date year >= min_year) ───────────────────────
    _pub_cols = [c for c in ("title", "description") if c in pubs_df.columns]
    if _pub_cols and "pub_date" in pubs_df.columns:
        pubs_copy = pubs_df.copy()
        pubs_copy["_year"] = pubs_copy["pub_date"].apply(_parse_exp_year)
        recent_pubs = pubs_copy[pubs_copy["_year"].between(min_year, max_year)]
        recent_pubs_by_pid: dict = (
            recent_pubs.dropna(subset=["title"])
            .groupby("profile_id")[_pub_cols]
            .apply(lambda df: " ".join(
                str(v).lower()
                for col in _pub_cols
                for v in df[col].dropna()
                if str(v).strip() not in ("", "nan")
            ))
            .to_dict()
        )
    else:
        recent_pubs_by_pid = {}

    # ── Recent-experience text blobs per profile ──────────────────────────────
    recent_exp = exp_df[
        exp_df.apply(
            _experience_overlaps_range,
            axis=1,
            min_year=min_year,
            max_year=max_year,
        )
    ]
    recent_texts: dict = {
        pid: " ".join(
            str(d).lower()
            for d in grp["description"].dropna()
            if str(d).strip() not in ("", "nan")
        )
        for pid, grp in recent_exp.groupby("profile_id")
    }

    # ── Assemble per-profile results ──────────────────────────────────────────
    all_pids = set(profiles_df["profile_id"].dropna().unique())
    result = {}
    for pid in all_pids:
        static_text = " ".join(filter(None, [
            about_by_pid.get(pid, ""),
            skills_by_pid.get(pid, ""),
        ]))
        static_tags = _tags_from_text(static_text, strings_to_tag)
        dated_text = " ".join(filter(None, [
            recent_pubs_by_pid.get(pid, ""),
            recent_texts.get(pid, ""),
        ]))
        dated_tags = _tags_from_text(dated_text, strings_to_tag)
        combined = sorted(static_tags | dated_tags)
        result[pid] = combined
    return result


@st.cache_data(ttl=3600)
def get_filtered_profile_tags_recent(
    profile_id: str,
    min_year: int = 2016,
    max_year: int | None = None,
) -> list[str]:
    """Return recency-filtered research tags for a single community profile.

    Skills and about text are always included (no date available).  Experience
    descriptions and publications are included only when they fall within the
    lookback window (ended/published >= min_year).  Returns an empty list if
    nothing qualifies; the UI hides the section gracefully.
    """
    _, strings_to_tag = _load_members_tag_vocabulary()

    # Static tags (no date): vocabulary scan on about + skills only
    static_text = _static_text_for_profile(
        profile_id, load_li_profiles(), load_li_skills()
    )
    static_tags = _tags_from_text(static_text, strings_to_tag)

    # Date-filtered tags: publications and experience within lookback window
    pubs_text = _recent_pubs_text_for_profile(
        profile_id,
        load_li_publications(),
        min_year,
        max_year,
    )
    profile_exp = load_li_experience()
    profile_exp = profile_exp[profile_exp["profile_id"] == profile_id].copy()
    exp_text = _exp_text_for_profile(profile_exp, min_year, max_year)
    dated_tags = _tags_from_text(
        (pubs_text + " " + exp_text).strip(), strings_to_tag
    )

    result = sorted(static_tags | dated_tags)
    return result


@st.cache_data(ttl=3600)
def build_community_directory_data() -> pd.DataFrame:
    """Pre-join profiles with current job, location, research tags, and institution tags for the directory."""
    profiles = load_li_profiles()
    experience = load_li_experience()
    research_tags = load_li_research_tags()
    education = load_li_education()

    # ── Current / most-recent experience per profile ──────────────────────────
    exp_sorted = experience.sort_values(["profile_id", "sort_order"])

    _current_mask = (
        exp_sorted["end_date"].isna()
        | exp_sorted["end_date"].astype(str).str.strip().isin(["", "nan", "None", "Present"])
    )
    current_exp = (
        exp_sorted[_current_mask]
        .groupby("profile_id", as_index=False)
        .first()[["profile_id", "title", "company"]]
        .rename(columns={"title": "current_title", "company": "current_company"})
    )
    # Fallback: most recent overall (for profiles with no "current" entry)
    most_recent_exp = (
        exp_sorted
        .groupby("profile_id", as_index=False)
        .first()[["profile_id", "title", "company"]]
        .rename(columns={"title": "recent_title", "company": "recent_company"})
    )

    # ── Research tags: two-pass Members-vocabulary filter ────────────────────
    matched_tags = _filter_community_tags(research_tags)
    tags_by_profile = (
        matched_tags.groupby("profile_id")["display_tag"]
        .apply(lambda x: sorted(set(x.dropna().tolist())))
        .reset_index()
        .rename(columns={"display_tag": "research_tags_list"})
    )

    # ── Education institutions per profile ───────────────────────────────────
    edu_by_profile = (
        education.dropna(subset=["school"])
        .groupby("profile_id")["school"]
        .apply(lambda x: sorted(set(x.dropna().tolist())))
        .reset_index()
        .rename(columns={"school": "education_list"})
    )

    # ── Institution tags per profile (education + experience, normalised) ────
    _edu_inst = education[["profile_id", "school"]].rename(columns={"school": "raw_name"})
    _exp_inst = experience[["profile_id", "company"]].rename(columns={"company": "raw_name"})
    _all_inst = pd.concat([_edu_inst, _exp_inst], ignore_index=True).dropna(subset=["raw_name"]).copy()
    _all_inst["institution_tag"] = _all_inst["raw_name"].apply(normalize_institution)
    _all_inst = _all_inst[_all_inst["institution_tag"].str.strip() != ""]
    inst_by_profile = (
        _all_inst.groupby("profile_id")["institution_tag"]
        .apply(lambda x: sorted(set(x.dropna().tolist())))
        .reset_index()
        .rename(columns={"institution_tag": "institution_tags_list"})
    )

    # ── Assemble directory DataFrame ─────────────────────────────────────────
    _profile_base_cols = ["profile_id", "profile_url", "full_name", "headline", "location"]
    if "photo_path" in profiles.columns:
        _profile_base_cols.append("photo_path")
    dir_df = profiles[_profile_base_cols].copy()

    dir_df = dir_df.merge(current_exp, on="profile_id", how="left")
    dir_df = dir_df.merge(most_recent_exp, on="profile_id", how="left")
    dir_df = dir_df.merge(tags_by_profile, on="profile_id", how="left")
    dir_df = dir_df.merge(edu_by_profile, on="profile_id", how="left")
    dir_df = dir_df.merge(inst_by_profile, on="profile_id", how="left")

    expertise_bounds = get_linkedin_expertise_year_bounds()
    all_expertise = (
        get_all_profiles_linkedin_expertise(*expertise_bounds)
        if expertise_bounds
        else {}
    )
    dir_df["researcher_declared_areas_list"] = dir_df["profile_id"].map(
        lambda profile_id: all_expertise.get(str(profile_id), {}).get(
            "declared_terms", []
        )
    )

    # Fill current_title / current_company from fallback when missing
    dir_df["current_title"] = dir_df["current_title"].fillna(dir_df["recent_title"])
    dir_df["current_company"] = dir_df["current_company"].fillna(dir_df["recent_company"])
    dir_df.drop(columns=["recent_title", "recent_company"], inplace=True)

    # ── Sanitize location: remove crawler noise ──────────────────────────────
    # The LinkedIn crawler sometimes stores mutual-connections text or a
    # job-title element in the location column instead of the city/region.
    #
    # Pattern 1 — connections strings, e.g.:
    #   "Turin, Calvin and 1 other mutual connection"
    #   "Nishan, Jenna and 32 other mutual connections"
    _conn_re = re.compile(r'connection', re.IGNORECASE)
    #
    # Pattern 2 — job-title keywords that indicate a corporate/academic title
    # was captured instead of a geographic location.
    _title_kw_re = re.compile(
        r'\b(Director|Manager|Officer|Researcher|Scientist|Engineer|Professor|'
        r'Instructor|Lecturer|Fellow|Postdoctoral|Advisor|Specialist|'
        r'Coordinator|Supervisor|Analyst|Consultant|Associate\s+\w|'
        r'Vice\s+President|Head\s*,)\b',
        re.IGNORECASE,
    )
    _geo_re = re.compile(
        r'\b(Canada|United States|USA|UK|Australia|Germany|France|'
        r'Alberta|Ontario|British Columbia|Quebec|Manitoba|Saskatchewan|'
        r'California|Texas|New York|Washington)\b',
        re.IGNORECASE,
    )

    def _sanitize_location(row):
        loc = str(row.get("location") or "").strip()
        if not loc or loc in ("nan", "None"):
            return None
        # Mutual-connections text (catches all "X other mutual connections" variants)
        if _conn_re.search(loc):
            return None
        # Exact-substring match against current_title
        title = str(row.get("current_title") or "").lower().strip()
        if title and len(title) > 10 and title in loc.lower():
            return None
        # Job-title keyword present AND no geographic indicator → likely a title string
        if _title_kw_re.search(loc) and not _geo_re.search(loc):
            return None
        return loc

    dir_df["location"] = dir_df.apply(_sanitize_location, axis=1)

    # Ensure list columns are proper lists, not NaN
    for _lc in (
        "research_tags_list",
        "researcher_declared_areas_list",
        "education_list",
        "institution_tags_list",
    ):
        dir_df[_lc] = dir_df[_lc].apply(lambda x: x if isinstance(x, list) else [])

    # ── Deduplicate by profile_url ────────────────────────────────────────────
    # The re-crawl may have assigned new UUIDs to existing profiles, leaving
    # multiple rows per URL with data split across them.  Collapse each URL
    # group into one row: keep the profile_id that has the richest exp data
    # (i.e. non-null current_title), union list columns across all duplicates.
    if dir_df["profile_url"].duplicated().any():
        scalar_cols = ["full_name", "headline", "location",
                       "current_title", "current_company"]
        if "photo_path" in dir_df.columns:
            scalar_cols.append("photo_path")
        list_cols = [
            "research_tags_list",
            "researcher_declared_areas_list",
            "education_list",
            "institution_tags_list",
        ]

        merged_rows = []
        for url, grp in dir_df.groupby("profile_url", sort=False):
            row: dict = {"profile_url": url}

            # Prefer the profile_id whose row has current_title; else first
            has_title = grp[grp["current_title"].notna()]
            best = has_title.iloc[0] if not has_title.empty else grp.iloc[0]
            row["profile_id"] = best["profile_id"]

            for col in scalar_cols:
                non_null = grp[col].dropna()
                row[col] = non_null.iloc[0] if not non_null.empty else None
            for col in list_cols:
                seen: set = set()
                merged: list = []
                for lst in grp[col]:
                    for item in (lst if isinstance(lst, list) else []):
                        if item not in seen:
                            seen.add(item)
                            merged.append(item)
                row[col] = sorted(merged)
            merged_rows.append(row)

        dir_df = pd.DataFrame(merged_rows)[
            ["profile_url", "profile_id"] + scalar_cols + list_cols
        ]

    return dir_df


@st.cache_data(ttl=3600)
def load_community_location_audit() -> pd.DataFrame:
    """Traceable location decisions using the current published profile table."""
    from utils.community_locations import build_location_audit
    return build_location_audit(load_li_profiles())


@st.cache_data(ttl=3600)
def load_community_map_data() -> pd.DataFrame:
    """Aggregate only resolved locations, keeping canonical geography and precision."""
    from utils.community_locations import aggregate_locations
    return aggregate_locations(load_community_location_audit())
