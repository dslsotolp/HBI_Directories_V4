"""Publication dates derived from exported records, without fixed year limits."""

from __future__ import annotations

import pandas as pd


def publication_year_bounds(summary: pd.DataFrame) -> tuple[int, int] | None:
    """Return valid earliest/latest years, or None when dates are unavailable."""
    if summary.empty or not {"first_year", "latest_year"}.issubset(summary.columns):
        return None
    first = pd.to_numeric(summary["first_year"], errors="coerce")
    last = pd.to_numeric(summary["latest_year"], errors="coerce")
    valid = first.between(1, 9999) & last.between(1, 9999) & first.le(last)
    if not valid.any():
        return None
    return int(first[valid].min()), int(last[valid].max())


def publication_coverage_label(summary: pd.DataFrame | None = None) -> str:
    """Format the actual collected coverage, including publications without keywords."""
    if summary is None:
        from utils.data_loader import load_scopus_member_summary

        summary = load_scopus_member_summary()
    bounds = publication_year_bounds(summary)
    if bounds is None:
        return "available years"
    first, last = bounds
    return str(first) if first == last else f"{first}–{last}"
