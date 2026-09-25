"""Profile rendering for the all-profile hybrid research taxonomy."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.components import (
    render_research_tags_v2,
    render_standardized_research_tags_v2,
)


def _unique_nonempty(values: pd.Series) -> list[str]:
    """Preserve first-seen order while removing blank and duplicate labels."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values.fillna("").astype(str):
        label = value.strip()
        key = label.casefold()
        if label and key not in seen:
            seen.add(key)
            result.append(label)
    return result


def _hybrid_expertise_values(
    rows: pd.DataFrame,
    source_phrases: list[dict[str, object]] | None = None,
) -> tuple[list[str], list[str], list[str], str]:
    """Return the public values used to decide which blocks should render."""

    if source_phrases:
        source_wording = _unique_nonempty(
            pd.Series(
                [phrase.get("phrase", "") for phrase in source_phrases],
                dtype="object",
            )
        )
    else:
        source_mask = rows["candidate_origin"].str.contains(
            r"structured_source|legacy_research_narrative|biography_",
            case=False,
            na=False,
            regex=True,
        )
        source_wording = _unique_nonempty(rows.loc[source_mask, "input_phrase"])
    accepted = rows[rows["disposition"].eq("accepted")]
    concepts = _unique_nonempty(accepted["preferred_display_label"])
    umbrellas = _unique_nonempty(accepted["umbrella_label"])
    member_ids = _unique_nonempty(rows["member_id"])
    member_id = member_ids[0] if member_ids else ""
    return source_wording, concepts, umbrellas, member_id


def render_hybrid_expertise(
    rows: pd.DataFrame,
    source_phrases: list[dict[str, object]] | None = None,
) -> None:
    """Render all research blocks, including a neutral empty declared-area state."""

    source_wording, concepts, umbrellas, member_id = _hybrid_expertise_values(
        rows, source_phrases
    )
    areas_column, themes_column = st.columns(2, gap="large")
    with areas_column:
        st.markdown(
            "##### Self-declared research areas",
            help=(
                "Self-declared research areas are topics or phrases the "
                "researcher uses to describe their work in their public "
                "research profile. They preserve the researcher’s "
                "own wording and are not standardized. For broader and "
                "more consistent matches with potential collaborators or "
                "partners, use the **Standardized research terms** and "
                "**Research Themes** sections."
            ),
        )
        if source_wording:
            st.markdown(
                '<div class="hbi-declared-guidance">These areas use the '
                "researcher’s own wording from their public research profile "
                "and may not be standardized. For more consistent matches, "
                "explore <strong>Standardized research terms</strong> and "
                "<strong>Research Themes</strong> to find other HBI profiles "
                "and identify potential collaborators or partners.</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                render_research_tags_v2(
                    source_wording,
                    max_show=50,
                    clickable=True,
                    preserve_case=True,
                    exclude_member_id=member_id,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="hbi-declared-empty">No self-declared research areas '
                "were found in the public research profile.</div>",
                unsafe_allow_html=True,
            )

    with themes_column:
        st.markdown(
            "##### Standardized research terms",
            help=(
                "These terms were standardized using research terminology "
                "found in the researcher’s UCalgary Research profile."
            ),
        )
        st.caption(
            "Click any standardized term or Research Theme to find other HBI "
            "profiles in the same field and identify potential collaborators "
            "or partners."
        )
        if concepts:
            st.markdown(
                render_standardized_research_tags_v2(
                    concepts,
                    "mesh_concept",
                    max_show=50,
                    clickable=True,
                    exclude_member_id=member_id,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.caption("No standardized research terms are available yet.")

        st.markdown(
            "##### Research Themes",
            help=(
                "Shows broad research themes that connect related Areas of "
                "Research. Select a theme to find other HBI profiles in the "
                "same field."
            ),
        )
        if umbrellas:
            st.markdown(
                render_standardized_research_tags_v2(
                    umbrellas,
                    "hbi_umbrella",
                    max_show=50,
                    clickable=True,
                    exclude_member_id=member_id,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.caption("No Research Themes are available yet.")
