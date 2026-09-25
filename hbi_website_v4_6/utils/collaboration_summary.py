"""Summaries of collaboration evidence within selected publication years."""

from __future__ import annotations

from collections import defaultdict

from utils.country_topic_names import COUNTRY_TOPIC_NAMES, normalize_country_label

NON_TOPIC_LABELS = frozenset({
    "mechanism", "mechanisms", "consensus", "review", "article",
    "journal article", "editorial",
})


def recent_publication_years(years: list[int], *, mode: str) -> list[int]:
    """Select either the latest five calendar years or five publication years."""
    available = sorted({int(year) for year in years if 0 < int(year) < 10000})
    if not available:
        return []
    if mode == "calendar":
        return list(range(max(1, available[-1] - 4), available[-1] + 1))
    if mode == "publication_years":
        return available[-5:]
    raise ValueError("Unknown collaboration-year selection")


def collaboration_count_band(count: int | None) -> str:
    """Show 1–10 exactly, then decade bands; distinguish missing evidence."""
    if count is None:
        return "—"
    if count < 0:
        raise ValueError("Collaboration count cannot be negative")
    return str(count) if count <= 10 else f"{(count // 10) * 10}+"


def summarize_collaboration(payload: dict, years: list[int]) -> dict:
    """Rank recent topics and count distinct countries across the full history."""
    selected = set(years)
    country_labels = COUNTRY_TOPIC_NAMES | {
        normalize_country_label(row["id"])
        for row in payload.get("countries", []) if row.get("id")
    }
    totals: dict[str, int] = defaultdict(int)
    latest: dict[str, int] = {}
    labels: dict[str, str] = {}
    for key, label, year, count in payload.get("collaborative_keyword_years", []):
        if int(year) not in selected or int(count) <= 0:
            continue
        if not str(label).strip() or str(label).strip().casefold() in NON_TOPIC_LABELS:
            continue
        if any(normalize_country_label(value) in country_labels for value in (key, label)):
            continue
        totals[key] += int(count)
        latest[key] = max(latest.get(key, 0), int(year))
        labels.setdefault(key, str(label))
    ranked = sorted(totals, key=lambda key: (-totals[key], -latest[key], key))

    def matching_entities(field: str, year_filter: set[int] | None = None) -> set[str]:
        return {
            str(row["id"]).strip().casefold()
            for row in payload.get(field, [])
            if str(row.get("id", "")).strip()
            and not str(row["id"]).startswith("unknown:")
            and any(
                (year_filter is None or int(y[0]) in year_filter) and int(y[1]) > 0
                for y in row.get("years", [])
            )
        }

    countries = matching_entities("countries")
    all_researchers = matching_entities("collaborators")
    researchers = matching_entities("collaborators", selected)
    return {
        "years": sorted(selected),
        "topics": [
            {"key": key, "label": labels[key], "publication_count": totals[key]}
            for key in ranked[:3]
        ],
        "country_count": (
            len(countries) if payload and (countries or not all_researchers) else None
        ),
        "researcher_count": len(researchers) if payload and selected else None,
    }


def load_profile_collaboration_summary(member_id: str) -> dict:
    """Use the full history for countries and the latest five years for topics."""
    from utils.data_loader import load_scopus_member_year_summary
    from utils.scopus_connections import load_scopus_connections

    yearly = load_scopus_member_year_summary()
    years = yearly.loc[
        yearly["member_id"].eq(member_id) & yearly["publication_count"].gt(0),
        "publication_year",
    ].dropna().astype(int).tolist()
    return summarize_collaboration(
        load_scopus_connections(member_id), recent_publication_years(years, mode="calendar"),
    )
