"""Shared Areas of Research explorer for HBI member profiles."""

from __future__ import annotations

import html as html_mod
import re
import unicodedata
from urllib.parse import quote, unquote

import pandas as pd
import streamlit as st
from utils.page_config import BLANK_PAGE_ICON
from utils.publication_coverage import publication_coverage_label

from utils.components import (
    UCALGARY_GOLD,
    UCALGARY_RED,
    format_research_label,
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_grid,
    render_card_html,
    render_disclaimer,
    render_list_row_html,
    render_list_view,
)
from utils.data_loader import (
    build_directory_data,
    load_hybrid_research_taxonomy,
    load_scopus_research_keywords,
    load_source_research_phrases,
)


st.set_page_config(
    page_title="Areas of Research – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
)
inject_custom_css()
render_public_sidebar_navigation("areas")

_esc = lambda value: html_mod.escape(str(value)) if value else ""

LAYER_SPECS = {
    "Self-declared research areas": {
        "query_type": "source",
        "source_group": "Public research profiles",
        "color": UCALGARY_GOLD,
        "tag_version": 2,
        "description": "Areas stated by researchers in public research profiles.",
    },
    "Standardized research terms": {
        "query_type": "mesh",
        "source_group": "Public research profiles",
        "color": "#397FA8",
        "tag_version": 3,
        "description": (
            "Research terms standardized from terminology found in public "
            "research profiles."
        ),
    },
    "Research Themes": {
        "query_type": "umbrella",
        "source_group": "Public research profiles",
        "color": "#7052A7",
        "tag_version": 4,
        "description": "Broad themes that connect related Areas of Research.",
    },
    "Research keywords from publications": {
        "query_type": "publication",
        "source_group": "Publications",
        "color": UCALGARY_RED,
        "tag_version": 1,
        "description": (
            "Research keywords associated with HBI member publications in the "
            f"directory’s {publication_coverage_label()} publication dataset."
        ),
    },
}
TYPE_TO_LAYER = {
    spec["query_type"]: label for label, spec in LAYER_SPECS.items()
}


def _normalize_label(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("’", "'").lower()
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_label(values: pd.Series) -> str:
    candidates = list(
        dict.fromkeys(str(value).strip() for value in values if str(value).strip())
    )
    return candidates[0] if candidates else ""


def _layer_frame(data: pd.DataFrame, label_column: str) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(
            columns=["member_id", "normalized_key", "display_label", "query_key"]
        )
    result = data[["member_id", label_column]].rename(
        columns={label_column: "display_label"}
    )
    result["display_label"] = (
        result["display_label"].fillna("").astype(str).str.strip()
    )
    result = result[
        result["member_id"].fillna("").astype(str).str.strip().ne("")
        & result["display_label"].ne("")
    ].copy()
    result["normalized_key"] = result["display_label"].map(_normalize_label)
    result["query_key"] = result["normalized_key"]
    return result.drop_duplicates(
        ["member_id", "normalized_key"], keep="first"
    ).reset_index(drop=True)


def _publication_layer_frame(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(
            columns=["member_id", "normalized_key", "display_label", "query_key"]
        )
    result = data[["member_id", "keyword", "normalized_keyphrase"]].rename(
        columns={"keyword": "display_label", "normalized_keyphrase": "query_key"}
    )
    for column in ("member_id", "display_label", "query_key"):
        result[column] = result[column].fillna("").astype(str).str.strip()
    result = result[
        result["member_id"].ne("")
        & result["display_label"].ne("")
        & result["query_key"].ne("")
    ].copy()
    result["normalized_key"] = result["display_label"].map(_normalize_label)
    return result.drop_duplicates(
        ["member_id", "query_key"], keep="first"
    ).reset_index(drop=True)


directory = build_directory_data()
hybrid = load_hybrid_research_taxonomy()
source_phrases = load_source_research_phrases()
publication_keywords = load_scopus_research_keywords()

# Use the same source wording shown on profiles. Profiles whose source page was
# unavailable during the latest refresh retain the profile renderer's hybrid
# fallback so every clickable label has a matching destination.
source_records = source_phrases[["member_id", "phrase"]].rename(
    columns={"phrase": "display_label"}
)
source_member_ids = set(source_records["member_id"])
source_fallback = hybrid.loc[
    hybrid["candidate_origin"].str.contains(
        r"structured_source|legacy_research_narrative|biography_",
        case=False,
        na=False,
        regex=True,
    )
    & ~hybrid["member_id"].isin(source_member_ids),
    ["member_id", "input_phrase"],
].rename(columns={"input_phrase": "display_label"})
source_records = pd.concat(
    [source_records, source_fallback], ignore_index=True
)

accepted = hybrid[hybrid["disposition"].eq("accepted")].copy()
layer_rows = {
    "source": _layer_frame(source_records, "display_label"),
    "mesh": _layer_frame(accepted, "preferred_display_label"),
    "umbrella": _layer_frame(accepted, "umbrella_label"),
    "publication": _publication_layer_frame(publication_keywords),
}
visible_member_ids = set(directory["member_id"].fillna("").astype(str))
layer_rows = {
    key: rows[rows["member_id"].astype(str).isin(visible_member_ids)].copy()
    for key, rows in layer_rows.items()
}

area_param = str(st.query_params.get("area", ""))
selected_area = unquote(area_param) if area_param else ""
requested_type = str(st.query_params.get("type", "source")).lower()
selected_type = requested_type if requested_type in TYPE_TO_LAYER else "source"
exclude_member_id = str(st.query_params.get("exclude", "")).strip()


if not selected_area:
    st.markdown(
        '<div class="hbi-banner">'
        '<h1>Areas of Research</h1>'
        '<p style="font-size:1.05rem;opacity:0.92;">'
        'Explore research areas found in public research profiles and '
        'research keywords identified from publications.</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="hbi-area-source-grid">'
        '<section><strong>Public research profiles</strong>'
        '<span>Researcher-declared wording, standardized research terms, and '
        'broader Research Themes.</span></section>'
        '<section><strong>Publications</strong>'
        '<span>Research keywords associated with HBI member publications and '
        'grouped for researcher discovery.</span></section>'
        '</div>'
        '<style>'
        '.hbi-area-source-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));'
        'gap:12px;margin:0 0 1rem;}'
        '.hbi-area-source-grid section{display:flex;flex-direction:column;gap:5px;'
        'padding:15px 17px;border:1px solid #E0E0E0;border-radius:10px;background:#F8F9FA;}'
        '.hbi-area-source-grid strong{color:#8B0015;font-size:.98rem;}'
        '.hbi-area-source-grid span{color:#555;font-size:.84rem;line-height:1.45;}'
        '@media(max-width:700px){.hbi-area-source-grid{grid-template-columns:1fr;}}'
        '</style>',
        unsafe_allow_html=True,
    )

    all_ids = set().union(
        *(set(rows["member_id"]) for rows in layer_rows.values())
    )
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Profiles represented", f"{len(all_ids):,}")
    k2.metric(
        "Self-declared research areas",
        f"{layer_rows['source']['normalized_key'].nunique():,}",
    )
    k3.metric(
        "Standardized terms",
        f"{layer_rows['mesh']['normalized_key'].nunique():,}",
    )
    k4.metric(
        "Research Themes",
        f"{layer_rows['umbrella']['normalized_key'].nunique():,}",
    )
    k5.metric(
        "Publication keywords",
        f"{layer_rows['publication']['query_key'].nunique():,}",
    )

    member_types = [
        value
        for value in sorted(directory["hbi_membership"].dropna().unique())
        if str(value).strip()
    ]
    c0, c1, c2, c3, c4, c5 = st.columns([2.1, 2.5, 2.8, 1.9, 2, 1.7])
    with c0:
        source_group = st.selectbox(
            "Source",
            ["Public research profiles", "Publications"],
        )
    available_layers = [
        label
        for label, spec in LAYER_SPECS.items()
        if spec["source_group"] == source_group
    ]
    with c1:
        default_index = 1 if source_group == "Public research profiles" else 0
        layer_label = st.selectbox(
            "Area type",
            available_layers,
            index=min(default_index, len(available_layers) - 1),
            key=f"areas_layer_{source_group}",
            disabled=len(available_layers) == 1,
        )
    layer_spec = LAYER_SPECS[layer_label]
    with c2:
        search_q = st.text_input(
            "Search this group",
            placeholder="e.g. autism, stroke, mental health…",
        )
    with c3:
        member_type = st.selectbox("Member type", ["All"] + member_types)
    with c4:
        coverage_options = (
            ["Shared by 2+ profiles", "All areas"]
            if source_group == "Publications"
            else ["All areas"]
        )
        coverage = st.selectbox(
            "Profile coverage",
            coverage_options,
            key=f"areas_coverage_{source_group}",
            disabled=len(coverage_options) == 1,
        )
    with c5:
        sort_by = st.selectbox(
            "Sort", ["Profiles ↓", "Area A → Z", "Area Z → A"]
        )
    st.caption(layer_spec["description"])

    eligible = directory
    if member_type != "All":
        eligible = eligible[eligible["hbi_membership"].eq(member_type)]
    rows = layer_rows[layer_spec["query_type"]]
    rows = rows[rows["member_id"].isin(set(eligible["member_id"]))]
    topics = (
        rows.groupby("normalized_key", as_index=False)
        .agg(
            display_label=("display_label", _display_label),
            query_key=("query_key", _display_label),
            member_count=("member_id", "nunique"),
        )
    )
    if coverage == "Shared by 2+ profiles":
        topics = topics[topics["member_count"] >= 2]
    if search_q.strip():
        query = search_q.strip().lower()
        topics = topics[
            topics["display_label"].str.lower().str.contains(
                query, na=False, regex=False
            )
            | topics["normalized_key"].str.contains(query, na=False, regex=False)
        ]
    if sort_by == "Profiles ↓":
        topics = topics.sort_values(
            ["member_count", "display_label"], ascending=[False, True]
        )
    elif sort_by == "Area A → Z":
        topics = topics.sort_values("display_label")
    else:
        topics = topics.sort_values("display_label", ascending=False)

    st.caption(f"{len(topics):,} terms match the current filters")
    per_page = 60
    total_pages = max(1, -(-len(topics) // per_page))
    filter_hash = hash(
        (source_group, layer_label, search_q, member_type, coverage, sort_by)
    )
    if st.session_state.get("_areas_filter_hash") != filter_hash:
        st.session_state["_areas_filter_hash"] = filter_hash
        st.session_state["areas_topic_page"] = 0
    page_number = max(
        0,
        min(
            int(st.session_state.get("areas_topic_page", 0)),
            total_pages - 1,
        ),
    )
    page_data = topics.iloc[
        page_number * per_page : (page_number + 1) * per_page
    ]

    cards = []
    for _, row in page_data.iterrows():
        label = str(row["display_label"])
        display = label if layer_spec["query_type"] == "source" else format_research_label(label)
        count = int(row["member_count"])
        if layer_spec["query_type"] == "publication":
            href = (
                "/Research_Keywords_from_Publications?keyword="
                f'{quote(str(row["query_key"]), safe="")}'
            )
        else:
            href = (
                f'/Areas_of_Research?type={layer_spec["query_type"]}'
                f'&area={quote(label, safe="")}'
            )
        cards.append(
            f'<a href="{href}" class="topic-card-link">'
            f'<div class="topic-card" style="border-top:3px solid {layer_spec["color"]};">'
            f'<div class="topic-card-name">{_esc(display)}</div>'
            f'<div class="topic-card-counts">{count} profile{"s" if count != 1 else ""}</div>'
            f'</div></a>'
        )
    if page_data.empty:
        st.info("No Areas of Research match the current filters.")
    else:
        st.markdown(
            '<style>'
            '.topic-card-link{text-decoration:none;}'
            '.topic-card{background:#fff;border:1px solid #e4e4e4;border-radius:10px;'
            'padding:16px 18px;margin:5px;min-height:82px;display:flex;flex-direction:column;'
            'justify-content:space-between;box-shadow:0 1px 4px rgba(0,0,0,.05);}'
            '.topic-card:hover{box-shadow:0 5px 18px rgba(0,0,0,.13);transform:translateY(-2px);}'
            '.topic-card-name{font-size:.97rem;font-weight:600;color:#1A1A1A;line-height:1.35;margin-bottom:9px;}'
            f'.topic-card-counts{{font-size:.82rem;color:{UCALGARY_RED};font-weight:600;}}'
            '.topic-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(255px,1fr));gap:0;}'
            '</style>'
            f'<div class="topic-grid">{"".join(cards)}</div>',
            unsafe_allow_html=True,
        )

        first_col, prev_col, page_col, next_col, last_col = st.columns(
            [1, 1, 2, 1, 1]
        )
        with first_col:
            if st.button(
                "⏮ First", disabled=page_number == 0, key="areas_first"
            ):
                st.session_state["areas_topic_page"] = 0
                st.rerun()
        with prev_col:
            if st.button(
                "◀ Prev", disabled=page_number == 0, key="areas_prev"
            ):
                st.session_state["areas_topic_page"] = page_number - 1
                st.rerun()
        with page_col:
            st.markdown(
                f"<p style='text-align:center;padding-top:8px;'>"
                f"Page {page_number + 1:,} of {total_pages:,}</p>",
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button(
                "Next ▶",
                disabled=page_number >= total_pages - 1,
                key="areas_next",
            ):
                st.session_state["areas_topic_page"] = page_number + 1
                st.rerun()
        with last_col:
            if st.button(
                "Last ⏭",
                disabled=page_number >= total_pages - 1,
                key="areas_last",
            ):
                st.session_state["areas_topic_page"] = total_pages - 1
                st.rerun()
    render_disclaimer()
    st.stop()


layer_label = TYPE_TO_LAYER[selected_type]
layer_spec = LAYER_SPECS[layer_label]
rows = layer_rows[selected_type]
selected_key = _normalize_label(selected_area)
matches = rows[rows["normalized_key"].eq(selected_key)].copy()

if matches.empty:
    st.error("No Areas of Research records were found for this term.")
    if st.button("← Explore Areas of Research"):
        st.query_params.clear()
        st.rerun()
    st.stop()

display = _display_label(matches["display_label"])
if selected_type != "source":
    display = format_research_label(display)
matching_ids = set(matches["member_id"])
if exclude_member_id:
    matching_ids.discard(exclude_member_id)
filtered = directory[directory["member_id"].isin(matching_ids)].sort_values("name")
tags_by_member = (
    rows.groupby("member_id")["display_label"]
    .apply(lambda values: list(dict.fromkeys(values.dropna().tolist())))
    .to_dict()
)

st.markdown(
    '<div class="hbi-banner">'
    '<h1>Areas of Research</h1>'
    f'<p style="font-size:1.35rem;font-weight:700;">{_esc(display)}</p>'
    f'<p>{_esc(layer_label)}</p>'
    '</div>',
    unsafe_allow_html=True,
)
if st.button("← Explore Areas of Research"):
    st.query_params.clear()
    st.rerun()

metric_label = "Other profiles" if exclude_member_id else "Profiles"
st.metric(metric_label, f"{len(filtered):,}")
view_mode = st.radio(
    "View", ["Grid", "List"], horizontal=True, label_visibility="collapsed"
)
if filtered.empty:
    message = (
        "No other current directory profiles share this selection."
        if exclude_member_id
        else "No current directory profiles were found for this selection."
    )
    st.info(message)
else:
    rendered = []
    for _, row in filtered.iterrows():
        member_id = str(row["member_id"])
        name = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
        title = str(row.get("title", "")) if pd.notna(row.get("title")) else ""
        department = (
            str(row.get("department", ""))
            if pd.notna(row.get("department"))
            else ""
        )
        photo = row.get("photo_path", "")
        photo_url = (
            f"/app/static/images/member/{photo}"
            if pd.notna(photo) and photo
            else None
        )
        renderer = render_card_html if view_mode == "Grid" else render_list_row_html
        rendered.append(
            renderer(
                name,
                title,
                department,
                tags_by_member.get(member_id, []),
                member_id=member_id,
                photo_url=photo_url,
                tag_version=layer_spec["tag_version"],
            )
        )
    st.markdown(
        render_card_grid(rendered)
        if view_mode == "Grid"
        else render_list_view(rendered),
        unsafe_allow_html=True,
    )

render_disclaimer()
