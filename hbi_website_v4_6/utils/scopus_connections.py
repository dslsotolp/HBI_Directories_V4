"""Interactive, profile-level Scopus topic and collaborator connections."""

from __future__ import annotations

import gzip
import html
import json
import math
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.data_loader import build_directory_data
from utils.components import format_research_label


CONNECTION_DIR = Path(__file__).resolve().parent.parent / "data" / "scopus_connections"
UCALGARY_RED = "#CF0722"
HBI_TEAL = "#33716D"
EXTERNAL_GRAY = "#77838F"
TOPIC_GOLD = "#D99B22"
INSTITUTION_PURPLE = "#7865A8"
COUNTRY_GREEN = "#4D8664"

# Distinctive names used by Scopus for UCalgary faculties, schools, institutes,
# and affiliated research centres. Generic Calgary organizations and AHS
# facilities are intentionally excluded.
_UCALGARY_AFFILIATION_MARKERS = (
    "university of calgary",
    "universite de calgary",
    "cumming school of medicine",
    "schulich school of engineering",
    "hotchkiss brain institute",
    "alberta childrens hospital research institute",
    "alberta children s hospital research institute",
    "o brien institute for public health",
    "o brien centre",
    "institut o brien de sante publique",
    "libin cardiovascular institute",
    "snyder institute for chronic diseases",
    "snyder institute of infection immunity and inflammation",
    "mathison centre for mental health research",
    "mathison institute for mental health research",
    "matheson centre for mental health research",
    "mccaig institute for bone and joint health",
    "mccaig institute for joint injury and arthritis",
    "mccaig centre for joint injury and arthritis research",
    "mccaig institute for bone and join healthy",
    "arnie charbonneau cancer institute",
    "owerko centre",
    "haskayne school of business",
    "werklund school of education",
    "school of architecture planning and landscape",
    "school of public policy",
    "institute for quantum science and technology",
    "international microbiome centre",
    "sport injury prevention research centre",
    "calgary institute of population and public health",
    "institute for public health",
)

_UCALGARY_EXACT_AFFILIATIONS = {
    "faculty of kinesiology",
    "faculty of social work",
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_scopus_connections(member_id: str) -> dict:
    """Load one public-safe, compressed member connection payload."""
    safe_member_id = "".join(
        character
        for character in str(member_id)
        if character.isalnum() or character in {"_", "-"}
    )
    if not safe_member_id:
        return {}
    path = CONNECTION_DIR / f"{safe_member_id}.json.gz"
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _normalize_affiliation(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).strip()


def _is_ucalgary_affiliation(value: str) -> bool:
    normalized = _normalize_affiliation(value)
    if not normalized:
        return False
    return (
        normalized in _UCALGARY_EXACT_AFFILIATIONS
        or any(
            marker in normalized
            for marker in _UCALGARY_AFFILIATION_MARKERS
        )
    )


def _has_ucalgary_connection(row: dict, connection_kind: str) -> bool:
    if connection_kind == "Collaborators":
        return any(
            _is_ucalgary_affiliation(affiliation)
            for affiliation in row.get("affiliations", [])
        )
    if connection_kind == "Institutions":
        return _is_ucalgary_affiliation(str(row.get("name") or ""))
    return False


def _connection_kpi_counts(
    *,
    collaborators: list[dict],
    institutions: list[dict],
    countries: list[dict],
    hbi_only: bool,
    ucalgary_only: bool,
) -> dict[str, int]:
    """Return connection totals for the currently active cohort filters."""
    if not hbi_only and not ucalgary_only:
        return {
            "collaborators": len(collaborators),
            "hbi_collaborators": sum(
                bool(row["hbi_member_id"]) for row in collaborators
            ),
            "institutions": len(institutions),
            "countries": len(countries),
        }

    selected_collaborators = [
        row
        for row in collaborators
        if (not hbi_only or bool(row["hbi_member_id"]))
        and (
            not ucalgary_only
            or _has_ucalgary_connection(row, "Collaborators")
        )
    ]
    selected_affiliations = {
        _normalize_affiliation(affiliation)
        for row in selected_collaborators
        for affiliation in row.get("affiliations", [])
        if affiliation
        and (
            not ucalgary_only
            or _is_ucalgary_affiliation(affiliation)
        )
    }
    selected_institutions = [
        row
        for row in institutions
        if _normalize_affiliation(str(row.get("name") or ""))
        in selected_affiliations
        and (
            not ucalgary_only
            or _has_ucalgary_connection(row, "Institutions")
        )
    ]
    selected_countries = {
        str(row.get("country") or "").strip()
        for row in selected_institutions
        if str(row.get("country") or "").strip()
    }
    if hbi_only and not ucalgary_only:
        selected_countries.update(
            str(country).strip()
            for row in selected_collaborators
            for country in row.get("countries", [])
            if str(country).strip()
        )

    return {
        "collaborators": len(selected_collaborators),
        "hbi_collaborators": sum(
            bool(row["hbi_member_id"]) for row in selected_collaborators
        ),
        "institutions": len(selected_institutions),
        "countries": len(selected_countries),
    }


def _summarize_collaborators(
    payload: dict,
    *,
    year_from: int,
    year_to: int,
    visible_member_ids: set[str],
) -> list[dict]:
    output = []
    for source in payload.get("collaborators", []):
        selected_years = [
            row
            for row in source.get("years", [])
            if year_from <= int(row[0]) <= year_to
        ]
        if not selected_years:
            continue
        selected_years.sort(key=lambda row: int(row[0]), reverse=True)
        shared_publications = sum(int(row[1]) for row in selected_years)
        countries = _unique(
            [
                str(country).strip()
                for row in selected_years
                for country in (row[2] if len(row) > 2 else [])
            ]
        )
        affiliations = _unique(
            [
                str(affiliation).strip()
                for row in selected_years
                for affiliation in (row[3] if len(row) > 3 else [])
            ]
        )
        hbi_member_id = str(source.get("hbi_member_id") or "").strip()
        if hbi_member_id not in visible_member_ids:
            hbi_member_id = ""
        output.append(
            {
                "id": str(source.get("id") or ""),
                "name": str(source.get("name") or "Unknown collaborator"),
                "hbi_member_id": hbi_member_id,
                "shared_publications": shared_publications,
                "first_year": min(int(row[0]) for row in selected_years),
                "latest_year": max(int(row[0]) for row in selected_years),
                "countries": countries,
                "affiliations": affiliations,
            }
        )
    return sorted(
        output,
        key=lambda row: (
            -row["shared_publications"],
            -row["latest_year"],
            row["name"].casefold(),
        ),
    )


def _summarize_institutions(
    payload: dict,
    *,
    year_from: int,
    year_to: int,
) -> list[dict]:
    output = []
    for source in payload.get("institutions", []):
        selected_years = [
            row
            for row in source.get("years", [])
            if year_from <= int(row[0]) <= year_to
        ]
        if not selected_years:
            continue
        output.append(
            {
                "id": str(source.get("id") or ""),
                "name": str(source.get("name") or "Unknown institution"),
                "hbi_member_id": "",
                "shared_publications": sum(
                    int(row[1]) for row in selected_years
                ),
                "first_year": min(int(row[0]) for row in selected_years),
                "latest_year": max(int(row[0]) for row in selected_years),
                "city": str(source.get("city") or ""),
                "country": str(source.get("country") or ""),
                "countries": (
                    [str(source["country"])] if source.get("country") else []
                ),
                "affiliations": [],
            }
        )
    return sorted(
        output,
        key=lambda row: (
            -row["shared_publications"],
            -row["latest_year"],
            row["name"].casefold(),
        ),
    )


def _summarize_countries(
    payload: dict,
    *,
    year_from: int,
    year_to: int,
) -> list[dict]:
    output = []
    for source in payload.get("countries", []):
        selected_years = [
            row
            for row in source.get("years", [])
            if year_from <= int(row[0]) <= year_to
        ]
        if not selected_years:
            continue
        selected_years.sort(key=lambda row: int(row[0]), reverse=True)
        institutions = _unique(
            [
                str(institution).strip()
                for row in selected_years
                for institution in (row[2] if len(row) > 2 else [])
            ]
        )
        country_name = str(source.get("name") or source.get("id") or "")
        output.append(
            {
                "id": str(source.get("id") or country_name),
                "name": country_name,
                "hbi_member_id": "",
                "shared_publications": sum(
                    int(row[1]) for row in selected_years
                ),
                "first_year": min(int(row[0]) for row in selected_years),
                "latest_year": max(int(row[0]) for row in selected_years),
                "city": "",
                "country": country_name,
                "countries": [country_name],
                "affiliations": institutions,
                "institution_count": len(institutions),
            }
        )
    return sorted(
        output,
        key=lambda row: (
            -row["shared_publications"],
            -row["latest_year"],
            row["name"].casefold(),
        ),
    )


def _edge_strengths(
    edge_rows: list,
    *,
    year_from: int,
    year_to: int,
    connection_ids: set[str],
    topic_keys: set[str],
) -> dict[tuple[str, str], int]:
    strengths: dict[tuple[str, str], int] = {}
    for connection_id, normalized, year, count in edge_rows:
        if (
            year_from <= int(year) <= year_to
            and connection_id in connection_ids
            and normalized in topic_keys
        ):
            key = (str(connection_id), str(normalized))
            strengths[key] = strengths.get(key, 0) + int(count)
    return strengths


def _short_label(value: str, limit: int = 31) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _spread_positions(
    count: int,
    *,
    low: float = 86,
    high: float = 490,
    step: float | None = None,
) -> list[float]:
    if count <= 0:
        return []
    if count == 1:
        return [(low + high) / 2]
    if step is None:
        step = (high - low) / (count - 1)
    else:
        midpoint = (low + high) / 2
        low = midpoint - ((step * (count - 1)) / 2)
    return [low + index * step for index in range(count)]


def _line_width(count: int, maximum: int, *, base: float = 1.2) -> float:
    if maximum <= 0:
        return base
    return base + 5.2 * math.sqrt(max(0, count) / maximum)


def _title_lines(*lines: str) -> str:
    return "&#10;".join(html.escape(str(line)) for line in lines if line)


def _network_html(
    *,
    researcher_name: str,
    topics: list[dict],
    connections: list[dict],
    edge_strengths: dict[tuple[str, str], int],
    mode: str,
    connection_kind: str,
    canvas_height: int,
) -> str:
    """Build a responsive, linked SVG research-connection diagram."""
    connection_singular = {
        "Collaborators": "collaborator",
        "Institutions": "institution",
        "Countries": "country",
    }[connection_kind]
    topic_column_x = 120.0
    connection_column_x = 880.0
    node_half_width = 100.0
    node_width = node_half_width * 2
    node_half_height = 12.0
    node_height = node_half_height * 2
    center_half_width = 55.0
    center_half_height = 28.0
    node_low = 62.0
    node_high = float(canvas_height - 62)
    node_step = node_height + 9
    topic_positions = _spread_positions(
        len(topics),
        low=node_low,
        high=node_high,
        step=node_step,
    )
    connection_positions = _spread_positions(
        len(connections),
        low=node_low,
        high=node_high,
        step=node_step,
    )
    topic_xy = {
        row["normalized_keyphrase"]: (topic_column_x, topic_positions[index])
        for index, row in enumerate(topics)
    }
    connection_xy = {
        row["id"]: (connection_column_x, connection_positions[index])
        for index, row in enumerate(connections)
    }
    center_x, center_y = 500.0, (86.0 + node_high) / 2
    all_counts = [
        int(row["publication_count"]) for row in topics
    ] + [
        int(row["shared_publications"]) for row in connections
    ]
    max_count = max(all_counts, default=1)

    svg_parts = [
        f'<svg viewBox="0 0 1000 {canvas_height}" role="img" '
        'aria-label="Research topic and connection network">'
    ]
    if topics:
        svg_parts.append(
            f'<text x="{topic_column_x:.0f}" y="38" text-anchor="middle" '
            'class="column-label">'
            "RESEARCH KEYWORDS FROM PUBLICATIONS</text>"
        )
    if connections:
        svg_parts.append(
            f'<text x="{connection_column_x:.0f}" y="38" '
            'text-anchor="middle" class="column-label">'
            f"{html.escape(connection_kind.upper())}</text>"
        )

    if mode == "Combined":
        cross_edges = sorted(
            (
                (strength, connection_id, topic_key)
                for (connection_id, topic_key), strength in edge_strengths.items()
                if connection_id in connection_xy and topic_key in topic_xy
            ),
            reverse=True,
        )[:36]
        max_cross = max((row[0] for row in cross_edges), default=1)
        for strength, connection_id, topic_key in cross_edges:
            topic_x, topic_y = topic_xy[topic_key]
            connection_x, connection_y = connection_xy[connection_id]
            width = _line_width(strength, max_cross, base=0.6)
            title = _title_lines(
                f"{strength} shared publication{'s' if strength != 1 else ''}",
                f"The publication links this keyword to the {connection_singular}.",
            )
            svg_parts.append(
                f'<path d="M {topic_x + node_half_width:.1f} {topic_y:.1f} '
                f'C 410 {topic_y:.1f}, 590 {connection_y:.1f}, '
                f'{connection_x - node_half_width:.1f} {connection_y:.1f}" '
                f'class="cross-edge" style="stroke-width:{width:.2f}px">'
                f"<title>{title}</title></path>"
            )

    for topic in topics:
        topic_x, topic_y = topic_xy[topic["normalized_keyphrase"]]
        width = _line_width(int(topic["publication_count"]), max_count)
        svg_parts.append(
            f'<path d="M {topic_x + node_half_width:.1f} {topic_y:.1f} '
            f'Q 380 {topic_y:.1f} {center_x - center_half_width:.1f} '
            f'{center_y:.1f}" '
            f'class="topic-edge" style="stroke-width:{width:.2f}px"/>'
        )
    for connection in connections:
        connection_x, connection_y = connection_xy[connection["id"]]
        width = _line_width(int(connection["shared_publications"]), max_count)
        svg_parts.append(
            f'<path d="M {center_x + center_half_width:.1f} {center_y:.1f} '
            f'Q 620 {connection_y:.1f} '
            f'{connection_x - node_half_width:.1f} {connection_y:.1f}" '
            f'class="connection-edge {connection_kind.lower()}-edge" '
            f'style="stroke-width:{width:.2f}px"/>'
        )

    center_title = _title_lines(
        researcher_name,
        "Current HBI member profile",
    )
    svg_parts.append(
        '<g class="center-node">'
        f"<title>{center_title}</title>"
        f'<rect x="{center_x - center_half_width:.1f}" '
        f'y="{center_y - center_half_height:.1f}" '
        f'width="{center_half_width * 2:.1f}" '
        f'height="{center_half_height * 2:.1f}" rx="16" '
        'class="center-node-box"/>'
        f'<text x="{center_x:.0f}" y="{center_y - 6:.1f}" text-anchor="middle">'
        f"{html.escape(_short_label(researcher_name, 32))}</text>"
        f'<text x="{center_x:.0f}" y="{center_y + 12:.1f}" text-anchor="middle" '
        'class="center-subtitle">HBI MEMBER</text>'
        "</g>"
    )

    for topic in topics:
        normalized = str(topic["normalized_keyphrase"])
        label = format_research_label(topic["keyword"])
        count = int(topic["publication_count"])
        topic_x, topic_y = topic_xy[normalized]
        href = f"/Research_Keywords_from_Publications?keyword={quote(normalized, safe='')}"
        title = _title_lines(
            label,
            f"{count} supporting publication{'s' if count != 1 else ''}",
            "Click to open the Research Keyword Explorer.",
        )
        svg_parts.append(
            f'<a href="{html.escape(href, quote=True)}" target="_blank" '
            'rel="noopener noreferrer">'
            '<g class="topic-node">'
            f"<title>{title}</title>"
            f'<rect x="{topic_x - node_half_width:.1f}" '
            f'y="{topic_y - node_half_height:.1f}" '
            f'width="{node_width:.1f}" height="{node_height:.1f}" rx="12"/>'
            f'<text x="{topic_x - 86:.1f}" y="{topic_y + 4:.1f}" '
            f'text-anchor="start">{html.escape(_short_label(label, 22))}</text>'
            f'<text x="{topic_x + 82:.1f}" y="{topic_y + 4:.1f}" '
            f'text-anchor="end" class="node-count">{count}</text>'
            "</g></a>"
        )

    for connection in connections:
        connection_id = str(connection["id"])
        name = str(connection["name"])
        count = int(connection["shared_publications"])
        connection_x, connection_y = connection_xy[connection_id]
        hbi_member_id = str(connection.get("hbi_member_id") or "")
        if connection_kind == "Collaborators":
            node_class = "hbi-node" if hbi_member_id else "external-node"
        elif connection_kind == "Institutions":
            node_class = "institution-node"
        else:
            node_class = "country-node"
        country_text = ", ".join(connection["countries"][:4])
        affiliation_text = "; ".join(connection["affiliations"][:3])
        detail_label = (
            "Affiliated institutions"
            if connection_kind == "Countries"
            else "Affiliations"
        )
        location = ", ".join(
            value
            for value in [
                str(connection.get("city") or ""),
                str(connection.get("country") or ""),
            ]
            if value
        )
        title = _title_lines(
            name,
            f"{count} linked publication{'s' if count != 1 else ''}",
            f"Years: {connection['first_year']}–{connection['latest_year']}",
            f"Countries: {country_text}" if country_text else "",
            f"{detail_label}: {affiliation_text}" if affiliation_text else "",
            f"Location: {location}" if connection_kind == "Institutions" and location else "",
            "Click to open the HBI profile." if hbi_member_id else "",
        )
        group = (
            f'<g class="connection-node {node_class}">'
            f"<title>{title}</title>"
            f'<rect x="{connection_x - node_half_width:.1f}" '
            f'y="{connection_y - node_half_height:.1f}" '
            f'width="{node_width:.1f}" height="{node_height:.1f}" rx="12"/>'
            f'<circle cx="{connection_x - 84:.1f}" '
            f'cy="{connection_y:.1f}" r="5"/>'
            f'<text x="{connection_x - 70:.1f}" y="{connection_y + 4:.1f}" '
            f'text-anchor="start">{html.escape(_short_label(name, 19))}</text>'
            f'<text x="{connection_x + 82:.1f}" y="{connection_y + 4:.1f}" '
            f'text-anchor="end" class="node-count">{count}</text>'
            "</g>"
        )
        if hbi_member_id:
            href = f"/HBI_Members?id={quote(hbi_member_id, safe='')}"
            group = (
                f'<a href="{html.escape(href, quote=True)}" target="_blank" '
                'rel="noopener noreferrer">'
                f"{group}</a>"
            )
        svg_parts.append(group)

    legend_y = canvas_height - 34
    legend_parts = [
        '<g class="legend">',
        f'<circle cx="270" cy="{legend_y}" r="6" class="legend-topic"/>',
        f'<text x="282" y="{legend_y + 5}">Research Keyword</text>',
    ]
    if connection_kind == "Collaborators":
        legend_parts.extend(
            [
                f'<circle cx="425" cy="{legend_y}" r="6" class="legend-hbi"/>',
                f'<text x="437" y="{legend_y + 5}">HBI Collaborator</text>',
                f'<circle cx="590" cy="{legend_y}" r="6" class="legend-external"/>',
                f'<text x="602" y="{legend_y + 5}">Other Collaborator</text>',
            ]
        )
    else:
        legend_class = (
            "legend-institution"
            if connection_kind == "Institutions"
            else "legend-country"
        )
        legend_parts.extend(
            [
                f'<circle cx="455" cy="{legend_y}" r="6" '
                f'class="{legend_class}"/>',
                f'<text x="467" y="{legend_y + 5}">{html.escape(connection_singular.title())}</text>',
            ]
        )
    legend_parts.extend(
        [
            f'<line x1="765" y1="{legend_y}" x2="795" y2="{legend_y}" '
            'class="legend-edge"/>',
            f'<text x="804" y="{legend_y + 5}">Shared Topic</text>',
            "</g></svg>",
        ]
    )
    svg_parts.extend(legend_parts)

    return f"""
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      html,body{{margin:0;padding:0;background:#fff;font-family:Arial,sans-serif;}}
      .network-card{{border:1px solid #e7e7e7;border-radius:12px;background:
        linear-gradient(180deg,#fbfcfd 0%,#fff 42%);padding:8px;
        box-sizing:border-box;width:100%;margin:0;
        overflow-x:auto;overflow-y:hidden;scrollbar-width:thin;}}
      .network-card::-webkit-scrollbar{{width:10px;height:10px;}}
      .network-card::-webkit-scrollbar-track{{background:#f1f1f1;border-radius:8px;}}
      .network-card::-webkit-scrollbar-thumb{{background:#a8adb3;border-radius:8px;}}
      .network-card::-webkit-scrollbar-thumb:hover{{background:#777d84;}}
      svg{{display:block;width:100%;height:auto;
        min-height:0;margin:0 auto;}}
      path{{fill:none;stroke-linecap:round;}}
      .topic-edge{{stroke:{TOPIC_GOLD};opacity:.42;}}
      .collaborators-edge{{stroke:{EXTERNAL_GRAY};opacity:.34;}}
      .institutions-edge{{stroke:{INSTITUTION_PURPLE};opacity:.38;}}
      .countries-edge{{stroke:{COUNTRY_GREEN};opacity:.38;}}
      .cross-edge{{stroke:#8d6dac;opacity:.20;}}
      .column-label{{fill:#4B4B4B;font-size:.65625rem;font-weight:700;
        letter-spacing:.075rem;}}
      .center-node rect{{fill:{UCALGARY_RED};stroke:#9d061a;stroke-width:2px;
        filter:drop-shadow(0 4px 8px rgba(0,0,0,.18));}}
      .center-node text{{fill:#fff;font-size:.8375rem;font-weight:700;}}
      .center-node .center-subtitle{{font-size:.5875rem;
        letter-spacing:.075rem;opacity:.86;}}
      .topic-node rect{{fill:#fff8e6;stroke:{TOPIC_GOLD};stroke-width:1.5px;}}
      .topic-node text,.connection-node text{{fill:#111111;
        font-size:.78125rem;font-weight:700;pointer-events:none;}}
      .topic-node .node-count{{fill:#885d00;}}
      .connection-node rect{{fill:#f2f4f5;stroke:{EXTERNAL_GRAY};stroke-width:1.5px;}}
      .connection-node circle{{fill:{EXTERNAL_GRAY};}}
      .connection-node.hbi-node rect{{fill:#f0f5f5;stroke:{HBI_TEAL};}}
      .connection-node.hbi-node circle{{fill:{HBI_TEAL};}}
      .connection-node.institution-node rect{{fill:#f3f0fa;stroke:{INSTITUTION_PURPLE};}}
      .connection-node.institution-node circle{{fill:{INSTITUTION_PURPLE};}}
      .connection-node.country-node rect{{fill:#eef7f1;stroke:{COUNTRY_GREEN};}}
      .connection-node.country-node circle{{fill:{COUNTRY_GREEN};}}
      .connection-node .node-count{{fill:#59636d;}}
      .connection-node.hbi-node .node-count{{fill:#245f6c;}}
      a .topic-node:hover rect,a .connection-node:hover rect{{
        stroke-width:3px;filter:drop-shadow(0 2px 5px rgba(0,0,0,.15));}}
      a{{cursor:pointer;text-decoration:none;}}
      .legend text{{fill:#4B4B4B;font-size:.65625rem;font-weight:600;}}
      .legend-topic{{fill:{TOPIC_GOLD};}}
      .legend-hbi{{fill:{HBI_TEAL};}}
      .legend-external{{fill:{EXTERNAL_GRAY};}}
      .legend-institution{{fill:{INSTITUTION_PURPLE};}}
      .legend-country{{fill:{COUNTRY_GREEN};}}
      .legend-edge{{stroke:#8d6dac;stroke-width:3px;opacity:.55;}}
      @media(max-width:700px){{
        .network-card{{width:100%;}}
        svg{{width:900px;min-width:900px;min-height:0;}}
        .column-label{{font-size:.8125rem;}}
        .topic-node text,.connection-node text{{font-size:.6875rem;}}
      }}
    </style>
    </head>
    <body><div class="network-card" id="research-network">
      {''.join(svg_parts)}
    </div>
    <script>
      const card = document.getElementById("research-network");
      const svg = card ? card.querySelector("svg") : null;
      const setVisualFontSize = (selector, targetPixels) => {{
        if (!svg || !svg.viewBox || !svg.viewBox.baseVal.width) return;
        const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
        if (!scale) return;
        svg.querySelectorAll(selector).forEach((element) => {{
          element.style.fontSize = `${{targetPixels / scale}}px`;
        }});
      }};
      const syncCenterNodeWidth = () => {{
        if (!svg || !svg.viewBox || !svg.viewBox.baseVal.width) return;
        const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
        if (!scale) return;
        const centerNode = svg.querySelector(".center-node");
        const centerBox = centerNode
          ? centerNode.querySelector(".center-node-box")
          : null;
        const mainLabel = centerNode
          ? centerNode.querySelector("text:not(.center-subtitle)")
          : null;
        const subtitle = centerNode
          ? centerNode.querySelector(".center-subtitle")
          : null;
        if (!centerBox || !mainLabel) return;
        const measuredWidth = Math.max(
          mainLabel.getComputedTextLength(),
          subtitle ? subtitle.getComputedTextLength() : 0
        );
        const horizontalPadding = 28 / scale;
        const minimumWidth = 110;
        const maximumWidth = 260;
        const nodeWidth = Math.min(
          maximumWidth,
          Math.max(minimumWidth, measuredWidth + horizontalPadding)
        );
        centerBox.setAttribute("x", 500 - nodeWidth / 2);
        centerBox.setAttribute("width", nodeWidth);
      }};
      const syncDiagramTypography = () => {{
        const browserTextSize =
          parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
        setVisualFontSize(
          ".topic-node text,.connection-node text",
          Math.max(10, browserTextSize - 2.667)
        );
        setVisualFontSize(".center-node > text:not(.center-subtitle)", browserTextSize);
        setVisualFontSize(
          ".center-subtitle",
          Math.max(9, browserTextSize - 5.5)
        );
        setVisualFontSize(
          ".column-label,.legend text",
          Math.max(10, browserTextSize - 4)
        );
        syncCenterNodeWidth();
      }};
      syncDiagramTypography();
      window.addEventListener("resize", syncDiagramTypography);
      const syncFrameHeight = () => {{
        if (!card) return;
        const requiredHeight = Math.ceil(card.getBoundingClientRect().height);
        if (window.frameElement) {{
          window.frameElement.style.setProperty(
            "height",
            `${{requiredHeight}}px`,
            "important"
          );
          if (window.frameElement.parentElement) {{
            window.frameElement.parentElement.style.setProperty(
              "height",
              `${{requiredHeight}}px`,
              "important"
            );
            window.frameElement.parentElement.style.setProperty(
              "min-height",
              "0",
              "important"
            );
            window.frameElement.parentElement.style.setProperty(
              "flex",
              `0 0 ${{requiredHeight}}px`,
              "important"
            );
          }}
        }}
        window.parent.postMessage(
          {{
            isStreamlitMessage: true,
            type: "streamlit:setFrameHeight",
            height: requiredHeight,
          }},
          "*"
        );
      }};
      requestAnimationFrame(() => requestAnimationFrame(syncFrameHeight));
      if (window.ResizeObserver && card) {{
        new ResizeObserver(syncFrameHeight).observe(card);
      }}
      window.addEventListener("resize", syncFrameHeight);
      if (card && card.clientWidth < 700) {{
        card.scrollLeft = Math.max(0, (card.scrollWidth - card.clientWidth) / 2);
      }}
    </script>
    </body>
    </html>
    """


def _compact_list(values: list[str], limit: int = 3) -> str:
    selected = values[:limit]
    suffix = f" · +{len(values) - limit} more" if len(values) > limit else ""
    return " · ".join(selected) + suffix


def render_scopus_connections(
    *,
    member_id: str,
    researcher_name: str,
    filtered_keywords: pd.DataFrame,
    year_from: int,
    year_to: int,
) -> None:
    """Render a filtered Scopus topic/collaborator profile network."""
    payload = load_scopus_connections(member_id)
    if not payload:
        return

    visible_member_ids = set(
        build_directory_data()["member_id"].dropna().astype(str)
    )
    collaborators = _summarize_collaborators(
        payload,
        year_from=year_from,
        year_to=year_to,
        visible_member_ids=visible_member_ids,
    )
    institutions = _summarize_institutions(
        payload,
        year_from=year_from,
        year_to=year_to,
    )
    countries = _summarize_countries(
        payload,
        year_from=year_from,
        year_to=year_to,
    )
    if (
        not collaborators
        and not institutions
        and not countries
        and filtered_keywords.empty
    ):
        return

    st.markdown(
        "##### Research Connections",
        help=(
            "These connections are built from publication records linked to "
            "this researcher. They connect exact research keywords from "
            "publications with coauthors, their institutions, and the countries "
            "of those institutions. Counts follow the publication years "
            f"selected above ({year_from}–{year_to}) and update with the HBI "
            "and UCalgary filters."
        ),
    )

    mode_state = st.session_state.get(
        f"scopus_connection_mode_select_{member_id}",
        "Combined",
    )
    group_state = st.session_state.get(
        f"scopus_connection_group_select_{member_id}",
        "Collaborators",
    )
    metric_hbi_only = (
        mode_state != "Topics"
        and group_state == "Collaborators"
        and bool(
            st.session_state.get(
                f"scopus_connection_hbi_only_{member_id}",
                False,
            )
        )
    )
    metric_ucalgary_only = (
        mode_state != "Topics"
        and group_state != "Countries"
        and bool(
            st.session_state.get(
                f"scopus_connection_ucalgary_only_{member_id}",
                False,
            )
        )
    )
    kpi_counts = _connection_kpi_counts(
        collaborators=collaborators,
        institutions=institutions,
        countries=countries,
        hbi_only=metric_hbi_only,
        ucalgary_only=metric_ucalgary_only,
    )
    metric_one, metric_two, metric_three, metric_four = st.columns(4)
    metric_one.metric(
        "Collaborators",
        f"{kpi_counts['collaborators']:,}",
        help=(
            "Distinct indexed coauthors connected to this researcher "
            "through publications in the selected years. Each collaborator is "
            "counted once, even when they share multiple publications."
        ),
    )
    metric_two.metric(
        "HBI collaborators",
        f"{kpi_counts['hbi_collaborators']:,}",
        help=(
            "Collaborators whose publication-author record is linked to a visible HBI "
            "directory profile. The selected publication years and active "
            "HBI/UCalgary connection filters apply."
        ),
    )
    metric_three.metric(
        "Institutions",
        f"{kpi_counts['institutions']:,}",
        help=(
            "Distinct affiliation entities indexed across these collaborations. "
            "Publication records may treat a laboratory, school, institute, "
            "and its parent university as separate institutions—for example, "
            "Libin, HBI, the Cumming School of Medicine (CSM), and the "
            "University of Calgary (UCalgary) may each appear individually "
            "under the same institutional umbrella."
        ),
    )
    metric_four.metric(
        "Countries",
        f"{kpi_counts['countries']:,}",
        help=(
            "Distinct countries represented in collaborators’ indexed "
            "affiliations during the selected years. The same collaborator may "
            "be associated with more than one country after changing locations "
            "or institutions, or when holding affiliations in multiple "
            "countries. Each country is counted once in this KPI."
        ),
    )

    with st.container(border=True):
        st.markdown("**Connection settings**")
        selector_one, selector_two = st.columns(
            2,
            vertical_alignment="bottom",
        )
        with selector_one:
            mode = st.selectbox(
                "View",
                ["Combined", "Topics", "Connections only"],
                key=f"scopus_connection_mode_select_{member_id}",
                help=(
                    "Combined shows keywords and the selected connection type. "
                    "Topics shows only the keyword side. Connections only shows "
                    "only collaborators, institutions, or countries."
                ),
            )
        with selector_two:
            group_by = st.selectbox(
                "Show connections as",
                ["Collaborators", "Institutions", "Countries"],
                key=f"scopus_connection_group_select_{member_id}",
                disabled=mode == "Topics",
                help=(
                    "Choose what the right side represents: individual "
                    "coauthors, their indexed institutions, or the "
                    "countries of those institutions."
                ),
            )

        st.markdown("**Connection filters**")
        filter_one, filter_two = st.columns(
            2,
            vertical_alignment="center",
        )
        with filter_one:
            hbi_only = st.toggle(
                "HBI only",
                key=f"scopus_connection_hbi_only_{member_id}",
                disabled=mode == "Topics" or group_by != "Collaborators",
                help=(
                    "This filter applies to named collaborator nodes. "
                    "Institution and country views already aggregate all "
                    "indexed coauthors."
                ),
            )
        with filter_two:
            ucalgary_only = st.toggle(
                "UCalgary only",
                key=f"scopus_connection_ucalgary_only_{member_id}",
                disabled=mode == "Topics" or group_by == "Countries",
                help=(
                    "Show collaborators or institutions with an indexed "
                    "University of Calgary affiliation.\n\n"
                    "**Included organizations:**\n\n"
                    "- University of Calgary\n"
                    "- Cumming School of Medicine\n"
                    "- Schulich School of Engineering\n"
                    "- Hotchkiss Brain Institute\n"
                    "- Alberta Children’s Hospital Research Institute\n"
                    "- O’Brien Institute for Public Health\n"
                    "- Libin Cardiovascular Institute\n"
                    "- Snyder Institute for Chronic Diseases\n"
                    "- Mathison Centre/Institute for Mental Health Research and "
                    "Education\n"
                    "- McCaig Institute for Bone and Joint Health\n"
                    "- Arnie Charbonneau Cancer Institute\n"
                    "- Owerko Centre\n"
                    "- Haskayne School of Business\n"
                    "- Werklund School of Education\n"
                    "- School of Architecture, Planning and Landscape\n"
                    "- School of Public Policy\n"
                    "- Faculty of Kinesiology\n"
                    "- Faculty of Social Work\n"
                    "- Institute for Quantum Science and Technology\n"
                    "- International Microbiome Centre\n"
                    "- Sport Injury Prevention Research Centre\n"
                    "- Calgary Institute of Population and Public Health\n"
                    "- Institute for Public Health\n\n"
                    "Spelling, punctuation, French-language, and "
                    "historical name variants are also recognized. This filter "
                    "is unavailable for country totals because those aggregates "
                    "cannot isolate individual institutions accurately."
                ),
            )

    connection_options = {
        "Collaborators": collaborators,
        "Institutions": institutions,
        "Countries": countries,
    }
    edge_options = {
        "Collaborators": payload.get("edges", []),
        "Institutions": payload.get("institution_edges", []),
        "Countries": payload.get("country_edges", []),
    }
    selected_connections = connection_options[group_by]
    node_limit_options = [5, 10, 20, 50]
    keyword_limit_key = f"scopus_keyword_node_limit_{member_id}"
    connection_limit_key = f"scopus_connection_limit_{member_id}"
    if (
        keyword_limit_key in st.session_state
        and st.session_state[keyword_limit_key] not in node_limit_options
    ):
        st.session_state[keyword_limit_key] = 10
    if (
        connection_limit_key in st.session_state
        and st.session_state[connection_limit_key] not in node_limit_options
    ):
        st.session_state[connection_limit_key] = 10

    keyword_controls, connection_controls = st.columns(2)
    with keyword_controls:
        st.caption("Left side · Research keywords from publications")
        keyword_control_one, keyword_control_two = st.columns(
            2,
            vertical_alignment="bottom",
        )
        with keyword_control_one:
            keyword_limit = st.selectbox(
                "Keywords shown",
                node_limit_options,
                index=1,
                key=keyword_limit_key,
                help=(
                    "Set the maximum number of strongest research-keyword nodes from publications "
                    "shown on the left side."
                ),
            )
        with keyword_control_two:
            keyword_minimum_options = [1, 2, 3, 5, 10]
            minimum_keyword_publications = st.selectbox(
                "Minimum keyword publications",
                keyword_minimum_options,
                index=0,
                key=f"scopus_keyword_node_minimum_{member_id}",
                help=(
                    "Hide keywords supported by fewer than this number of "
                    "publications in the selected year range."
                ),
            )

    with connection_controls:
        st.caption(f"Right side · {group_by}")
        connection_control_one, connection_control_two = st.columns(
            [1.25, 1],
            vertical_alignment="bottom",
        )
        with connection_control_one:
            minimum_options = [1, 2, 3, 5, 10]
            default_minimum = 2 if any(
                row["shared_publications"] >= 2
                for row in selected_connections
            ) else 1
            minimum_shared = st.selectbox(
                "Minimum linked publications",
                minimum_options,
                index=minimum_options.index(default_minimum),
                key=f"scopus_connection_minimum_{member_id}",
                help=(
                    "Hide right-side connections supported by fewer than this "
                    "number of publications in the selected year range."
                ),
            )
        with connection_control_two:
            connection_limit = st.selectbox(
                "Connections shown",
                node_limit_options,
                index=1,
                key=connection_limit_key,
                help=(
                    "Set the maximum number of strongest collaborator, "
                    "institution, or country nodes shown on the right side."
                ),
            )

    eligible_connections = [
        row
        for row in selected_connections
        if row["shared_publications"] >= int(minimum_shared)
        and (
            group_by != "Collaborators"
            or not hbi_only
            or bool(row["hbi_member_id"])
        )
        and (
            group_by == "Countries"
            or not ucalgary_only
            or _has_ucalgary_connection(row, group_by)
        )
    ]
    eligible_topics = filtered_keywords[
        filtered_keywords["publication_count"]
        >= int(minimum_keyword_publications)
    ]
    topic_rows = (
        eligible_topics.dropna(
            subset=["keyword", "normalized_keyphrase"]
        )
        .head(int(keyword_limit))
        .to_dict("records")
    )
    visible_topics = topic_rows
    visible_connections = eligible_connections[: int(connection_limit)]
    if mode == "Topics":
        visible_connections = []
    elif mode == "Connections only":
        visible_topics = []

    if not visible_topics and not visible_connections:
        st.info(
            "No connections meet the selected filters. Lower the minimum "
            "linked-publication threshold or expand the publication years."
        )
    else:
        strengths = _edge_strengths(
            edge_options[group_by],
            year_from=year_from,
            year_to=year_to,
            connection_ids={row["id"] for row in visible_connections},
            topic_keys={
                str(row["normalized_keyphrase"]) for row in visible_topics
            },
        )
        canvas_height = max(
            280,
            148
            + 33 * (
                max(len(visible_topics), len(visible_connections)) - 1
            ),
        )
        components.html(
            _network_html(
                researcher_name=researcher_name,
                topics=visible_topics,
                connections=visible_connections,
                edge_strengths=strengths,
                mode=mode,
                connection_kind=group_by,
                canvas_height=canvas_height,
            ),
            height=550,
            scrolling=False,
        )
        st.caption(
            "Hover for evidence details. Gold keywords and teal HBI "
            "collaborators open related pages in a new tab. Purple lines link "
            "a keyword to the selected connection type when the same publication "
            "supports both; the Combined view shows the 36 strongest such links. "
            "The left and right sides have independent display and publication "
            "thresholds. The visualization height adjusts to the selected node "
            "counts; on small screens, swipe horizontally as needed."
        )

    entity_label = group_by.lower()
    with st.expander(
        f"View all {len(selected_connections):,} {entity_label}"
    ):
        if group_by == "Collaborators" and selected_connections:
            table = pd.DataFrame(
                [
                    {
                        "Collaborator": row["name"],
                        "Shared publications": row["shared_publications"],
                        "First year": row["first_year"],
                        "Latest year": row["latest_year"],
                        "Countries": _compact_list(row["countries"], 4),
                        "Affiliations": _compact_list(row["affiliations"], 3),
                        "HBI profile": (
                            f"/HBI_Members?id={quote(row['hbi_member_id'], safe='')}"
                            if row["hbi_member_id"]
                            else ""
                        ),
                    }
                    for row in selected_connections
                ]
            )
            st.dataframe(
                table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Shared publications": st.column_config.NumberColumn(
                        format="%d"
                    ),
                    "First year": st.column_config.NumberColumn(format="%d"),
                    "Latest year": st.column_config.NumberColumn(format="%d"),
                    "HBI profile": st.column_config.LinkColumn(
                        "HBI profile",
                        display_text="Open profile",
                    ),
                },
            )
        elif group_by == "Institutions" and selected_connections:
            table = pd.DataFrame(
                [
                    {
                        "Institution": row["name"],
                        "Linked publications": row["shared_publications"],
                        "First year": row["first_year"],
                        "Latest year": row["latest_year"],
                        "City": row["city"],
                        "Country": row["country"],
                    }
                    for row in selected_connections
                ]
            )
            st.dataframe(
                table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Linked publications": st.column_config.NumberColumn(
                        format="%d"
                    ),
                    "First year": st.column_config.NumberColumn(format="%d"),
                    "Latest year": st.column_config.NumberColumn(format="%d"),
                },
            )
        elif group_by == "Countries" and selected_connections:
            table = pd.DataFrame(
                [
                    {
                        "Country": row["name"],
                        "Linked publications": row["shared_publications"],
                        "First year": row["first_year"],
                        "Latest year": row["latest_year"],
                        "Connected institutions": row["institution_count"],
                        "Example institutions": _compact_list(
                            row["affiliations"], 5
                        ),
                    }
                    for row in selected_connections
                ]
            )
            st.dataframe(
                table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Linked publications": st.column_config.NumberColumn(
                        format="%d"
                    ),
                    "First year": st.column_config.NumberColumn(format="%d"),
                    "Latest year": st.column_config.NumberColumn(format="%d"),
                    "Connected institutions": st.column_config.NumberColumn(
                        format="%d"
                    ),
                },
            )
        else:
            st.info(
                f"No indexed {entity_label} were returned for the selected "
                "publication years."
            )
