"""Validation and source-preserving display helpers for education records."""

from __future__ import annotations

import re
from typing import Mapping


_INVALID_EXACT_TEXT = {
    "biography",
    "curriculum vitae",
    "cv",
    "media",
}
_CREDENTIAL_RE = re.compile(
    r"\b(?:"
    r"ph\.?\s*d\.?|d\.?\s*phil\.?|ed\.?\s*d\.?|"
    r"m\.?\s*d\.?|m\.?\s*b\.?\s*b\.?\s*s\.?|"
    r"[bms]\.?\s*(?:a|s|sc|eng|ed|sw|n|pharm|bus)\.?|bse|bsn|"
    r"bachelor(?:'s)?|master(?:'s|s)?|doctor(?:ate|al)?|"
    r"bach(?:elor)? of eng|dr\.? habilitated|dr\.? rer\.? nat\.?|"
    r"fellow(?:ship)?|residen(?:cy|t)|diploma(?:te)?|"
    r"certificate|certification|licentiate|specialist|"
    r"frcp\s*\(?c?\)?|frcpc|abpp|ucns|cscn|asn|"
    r"post[- ]?doctoral|postgraduate|medical consultant"
    r")\b",
    re.IGNORECASE,
)
_INSTITUTION_RE = re.compile(
    r"\b(?:univers\w*|universtiy|univ\.?|"
    r"college|institute|institut|school|"
    r"centre|center|hospital|academy|polytechnic|faculty|committee|"
    r"council|society|board|olympic)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_PROSE_START_RE = re.compile(
    r"^(?:i|my|we|our|he|his|she|her|they|their|while|"
    r"dr\.?\s+(?!(?:habilitated|rer\.?\s+nat\.?)\b)[a-z]+)\b",
    re.IGNORECASE,
)
_NAMED_PERSON_PROSE_RE = re.compile(
    r"^[A-Z][A-Za-z.'’\-]+(?:\s+[A-Z][A-Za-z.'’\-]+){1,3}\s+(?:is|was|has)\b"
)
_PROSE_MARKER_RE = re.compile(
    r"\b(?:my research|my lab|her research|his research|her work|his work|"
    r"program of research|research interests?|media engagement|"
    r"peer[- ]reviewed articles?|appointed as|joined ucalgary|"
    r"current projects?|principal investigator|co-principal investigator)\b",
    re.IGNORECASE,
)
_INSTITUTION_ROLE_PREFIX_RE = re.compile(
    r"\b(?:neuro-oncologist|oncologist|consultant|clinician|researcher)\b",
    re.IGNORECASE,
)


def _value(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.casefold() in {"nan", "none", "nat"} else text


def is_publishable_education_text(value: object) -> bool:
    """Return whether text resembles one concise education credential."""
    text = _value(value)
    if (
        not text
        or len(text) > 300
        or len(text.split()) > 30
        or text.casefold() in _INVALID_EXACT_TEXT
    ):
        return False
    if (
        _PROSE_START_RE.search(text)
        or _NAMED_PERSON_PROSE_RE.search(text)
        or _PROSE_MARKER_RE.search(text)
    ):
        return False

    has_credential = bool(_CREDENTIAL_RE.search(text))
    has_institution = bool(_INSTITUTION_RE.search(text))
    has_year = bool(_YEAR_RE.search(text))
    return has_credential or (has_institution and has_year) or (
        has_institution and len(text.split()) <= 20
    )


def education_display_text(row: Mapping[str, object]) -> str:
    """Return source wording for a valid education row, else an empty string."""
    raw_text = _value(row.get("raw_text", ""))
    if raw_text:
        return raw_text if is_publishable_education_text(raw_text) else ""

    year = _value(row.get("year", ""))
    if re.fullmatch(r"\d{4}\.0", year):
        year = year[:-2]
    reconstructed = ", ".join(
        part
        for part in (
            _value(row.get("degree", "")),
            _value(row.get("field_of_study", "")),
            _value(row.get("institution", "")),
            year,
        )
        if part
    )
    return reconstructed if is_publishable_education_text(reconstructed) else ""


def education_institution_text(row: Mapping[str, object]) -> str:
    """Return a validated institution name suitable for organization tags."""
    if not education_display_text(row):
        return ""

    institution = _value(row.get("institution", ""))
    if not institution:
        return ""
    raw_text = _value(row.get("raw_text", ""))
    source_segments = [
        part.strip().casefold().strip(" .")
        for part in re.split(r"[,;]", raw_text)
        if part.strip()
    ]
    if institution.casefold().strip(" .") in source_segments[1:]:
        return institution

    marker = _INSTITUTION_RE.search(institution)
    prefix = institution[: marker.start()].strip(" ,-:") if marker else ""
    if marker and (
        _CREDENTIAL_RE.search(prefix)
        or _INSTITUTION_ROLE_PREFIX_RE.search(prefix)
    ):
        return institution[marker.start():].strip(" ,-:")
    if _CREDENTIAL_RE.search(institution):
        return ""
    return institution
