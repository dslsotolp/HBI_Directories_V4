"""Temporary KPI and selected-recognition profile design explorations."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from utils.components import (
    format_display_year,
    inject_custom_css,
    profile_hero_detail_lines,
    render_avatar_html,
    render_disclaimer,
)
from utils.data_loader import (
    load_activities,
    load_members,
    load_positions,
    load_scopus_member_summary,
    load_scopus_research_keywords,
    load_source_affiliations,
)


AARON_ID = "mem_c57a8f39f9"
AARON_PROFILE = f"/HBI_Members?id={AARON_ID}"
APPROACH_NAMES = {
    1: "Impact dashboard in hero",
    2: "Recognition-led hero",
    3: "At-a-glance panel below hero",
}


def _esc(value: object) -> str:
    return html.escape(str(value or ""))


def _load_aaron_preview_data() -> dict[str, object]:
    member = load_members().query("member_id == @AARON_ID").iloc[0]
    positions = load_positions().query("member_id == @AARON_ID").sort_values(
        "sort_order"
    )
    affiliations = (
        load_source_affiliations()
        .query("member_id == @AARON_ID")
        .sort_values("sort_order")
    )
    summary = load_scopus_member_summary().query("member_id == @AARON_ID").iloc[0]
    keywords = (
        load_scopus_research_keywords()
        .query("member_id == @AARON_ID")
        .sort_values("display_rank")
    )
    awards = (
        load_activities()
        .query("member_id == @AARON_ID and category == 'awards'")
        .sort_values("sort_order")
    )
    photo_path = str(member.get("photo_path") or "")
    return {
        "name": str(member["name"]),
        "photo_url": (
            f"/app/static/images/member/{photo_path}" if photo_path else None
        ),
        "details": profile_hero_detail_lines(
            positions, affiliations.to_dict("records")
        ),
        "affiliations": affiliations.head(4).to_dict("records"),
        "keywords": keywords["keyword"].dropna().astype(str).head(8).tolist(),
        "awards": awards.head(3).to_dict("records"),
        "metrics": [
            (f"{int(summary['publication_count']):,}", "Publications"),
            (f"{int(summary['unique_keyword_count']):,}", "Research keywords"),
            (
                f"{int(summary['first_year'])}–{int(summary['latest_year'])}",
                "Publication span",
            ),
            (f"{len(awards):,}", "Recognitions listed"),
        ],
    }


def _navigation(approach: int) -> str:
    links = []
    for number, name in APPROACH_NAMES.items():
        active = " explore-nav-active" if approach == number else ""
        links.append(
            f'<a class="explore-nav-link{active}" '
            f'href="/Profile_Summary_Examples?approach={number}">'
            f"{number}. {_esc(name)}</a>"
        )
    return (
        '<div class="explore-topline"><div><strong>Temporary profile design '
        "exploration</strong><span>Aaron Phillips · live profile unchanged</span></div>"
        '<div class="explore-nav">'
        + "".join(links)
        + f'<a class="explore-nav-link" href="{AARON_PROFILE}">Live profile</a>'
        "</div></div>"
    )


def _identity_html(data: dict[str, object]) -> str:
    details = "".join(f"<p>{_esc(line)}</p>" for line in data["details"])
    return (
        render_avatar_html(str(data["name"]), 125, data["photo_url"])
        + '<div class="hbi-collapsing-profile-copy">'
        + f"<h1>{_esc(data['name'])}</h1>{details}</div>"
    )


def _kpis(metrics: list[tuple[str, str]], *, hero: bool = False) -> str:
    css_class = "explore-hero-kpis" if hero else "explore-kpi-strip"
    return (
        f'<div class="{css_class}">'
        + "".join(
            '<div class="explore-kpi"><strong>'
            f"{_esc(value)}</strong><span>{_esc(label)}</span></div>"
            for value, label in metrics
        )
        + "</div>"
    )


def _recognition_feature(award: dict[str, object], *, hero: bool = False) -> str:
    css_class = "explore-hero-recognition" if hero else "explore-recognition-feature"
    return (
        f'<div class="{css_class}"><span>Selected recognition · '
        f"{_esc(format_display_year(award.get('year')))}</span><strong>{_esc(award.get('title'))}</strong>"
        "</div>"
    )


def _recognition_panel(awards: list[dict[str, object]]) -> str:
    cards = "".join(
        '<div class="explore-recognition-card">'
        f'<span>{_esc(format_display_year(award.get("year")))}</span>'
        f'<strong>{_esc(award.get("title"))}</strong></div>'
        for award in awards
    )
    return (
        '<section class="explore-panel explore-recognition-panel">'
        '<div class="explore-section-label">SELECTED RECOGNITION</div>'
        f'<div class="explore-recognition-grid">{cards}</div></section>'
    )


def _at_a_glance(data: dict[str, object]) -> str:
    return (
        '<section class="explore-glance">'
        '<div class="explore-glance-metrics"><div class="explore-section-label">'
        "RESEARCH AT A GLANCE</div>"
        + _kpis(data["metrics"])
        + "</div><div class=\"explore-glance-recognition\">"
        '<div class="explore-section-label">SELECTED RECOGNITION</div>'
        + "".join(
            '<div class="explore-glance-award"><span>'
            f'{_esc(format_display_year(award.get("year")))}</span><strong>{_esc(award.get("title"))}</strong></div>'
            for award in data["awards"]
        )
        + "</div></section>"
    )


def _common_body(data: dict[str, object], *, show_recognition: bool) -> str:
    affiliations = "".join(
        '<div class="explore-affiliation"><strong>'
        f'{_esc(row.get("title"))}</strong><span>{_esc(row.get("affiliation"))}</span></div>'
        for row in data["affiliations"]
    )
    keywords = "".join(
        f'<span class="explore-tag">{_esc(keyword)}</span>'
        for keyword in data["keywords"]
    )
    recognition = _recognition_panel(data["awards"]) if show_recognition else ""
    return (
        '<div class="explore-body">'
        '<section class="explore-panel"><div class="explore-section-label">AFFILIATIONS</div>'
        f'<div class="explore-affiliation-grid">{affiliations}</div></section>'
        '<section class="explore-panel"><div class="explore-section-label">RESEARCH</div>'
        '<h3>Research Keywords from Publications</h3>'
        f'<div class="explore-tags">{keywords}</div>'
        '<div class="explore-placeholder-copy">The final profile would retain the full '
        "research-area, publication, and connection controls beneath this summary.</div></section>"
        + recognition
        + '<section class="explore-panel explore-tall-panel"><div class="explore-section-label">'
        "BACKGROUND & RESEARCH CONNECTIONS</div>"
        '<div class="explore-placeholder-lines"><span></span><span></span><span></span>'
        "<span></span><span></span></div></section></div>"
    )


def _styles() -> str:
    return """
    <style>
    .explore-topline{display:flex;align-items:center;justify-content:space-between;gap:1rem;
      margin-bottom:1rem;padding:.75rem 1rem;border:1px solid #ddd;border-radius:10px;background:#fff;font-size:.82rem}
    .explore-topline>div:first-child{display:flex;flex-direction:column}.explore-topline span{color:#666}
    .explore-nav{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:.35rem}
    .explore-nav-link{padding:.35rem .58rem;border:1px solid #ccc;border-radius:7px;background:#fff;
      color:#333!important;text-decoration:none!important}.explore-nav-active,.explore-nav-link:hover{border-color:#cf0722;color:#8b0015!important}
    .exploration-hero{position:relative;animation-name:explore-hero-collapse}
    .explore-hero-integrated,.explore-hero-recognition-led{--explore-expanded-height:360px}
    @keyframes explore-hero-collapse{from{height:var(--explore-expanded-height,306px);padding:1.75rem 2.5rem;border-radius:18px}
      to{height:149px;padding:.78125rem 1.953125rem;border-radius:0 0 20px 20px}}
    .explore-hero-extra{margin-left:auto;animation:explore-extra-collapse linear both;
      animation-timeline:--hbi-profile-page;animation-range:0 220px}
    @keyframes explore-extra-collapse{from{opacity:1;max-width:620px;max-height:170px}
      to{opacity:0;max-width:0;max-height:0;transform:translateY(-12px)}}
    .explore-hero-kpis{display:grid;grid-template-columns:repeat(2,minmax(130px,1fr));gap:.55rem;width:360px}
    .explore-kpi{display:flex;min-width:0;flex-direction:column;padding:.68rem .8rem;border-radius:10px;
      background:#fff;color:#1a1a1a;box-shadow:0 3px 12px rgba(0,0,0,.12)}
    .explore-kpi strong{font-size:1.35rem;color:#8b0015}.explore-kpi span{font-size:.72rem;color:#555}
    .explore-hero-kpis .explore-kpi{background:rgba(255,255,255,.95)}
    .explore-hero-integrated .explore-hero-recognition{position:absolute;right:2.5rem;bottom:1.6rem;width:360px}
    .explore-hero-recognition{display:flex;flex-direction:column;box-sizing:border-box;padding:.75rem 1rem;
      border:1px solid rgba(255,255,255,.35);border-radius:10px;background:rgba(80,0,12,.35);color:#fff}
    .explore-hero-recognition span{font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;opacity:.9}
    .explore-hero-recognition strong{margin-top:.25rem;font-size:.9rem;line-height:1.3}
    .explore-hero-integrated .explore-hero-kpis{transform:translateY(-34px)}
    .explore-hero-recognition-led .explore-hero-extra{width:min(42%,480px)}
    .explore-kpi-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem;margin:0 0 1rem}
    .explore-recognition-feature{margin:0 0 1rem;padding:1rem 1.25rem;border-left:5px solid #cf0722;
      border-radius:0 10px 10px 0;background:#f4f4f4}.explore-recognition-feature span,.explore-recognition-feature strong{display:block}
    .explore-recognition-feature span{color:#8b0015;font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
    .explore-recognition-feature strong{margin-top:.25rem;font-size:1rem}
    .explore-glance{display:grid;grid-template-columns:1.15fr 1fr;gap:1rem;margin-bottom:1rem;padding:1.3rem;
      border:1px solid #ddd;border-top:6px solid #cf0722;border-radius:12px;background:#f4f4f4}
    .explore-glance .explore-kpi-strip{grid-template-columns:repeat(2,1fr);margin:0}
    .explore-glance-award{display:grid;grid-template-columns:54px 1fr;gap:.7rem;padding:.6rem 0;border-bottom:1px solid #d4d4d4}
    .explore-glance-award span{color:#8b0015;font-weight:800}.explore-glance-award strong{font-size:.82rem;line-height:1.35}
    .explore-body{display:flex;flex-direction:column;gap:1rem}.explore-panel{padding:1.6rem 1.8rem;border:1px solid #e1e1e1;
      border-radius:12px;background:#f7f7f7}.explore-section-label{margin-bottom:1rem;color:#8b0015;font-size:.76rem;font-weight:850;letter-spacing:.16em}
    .explore-affiliation-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem 2rem}.explore-affiliation{display:flex;flex-direction:column}
    .explore-affiliation span{margin-top:.22rem;color:#555;font-size:.82rem}.explore-tags{display:flex;flex-wrap:wrap;gap:.45rem}
    .explore-tag{padding:.38rem .62rem;border:1px solid #258ac4;border-radius:999px;background:#fff;color:#005b8f;font-size:.75rem;font-weight:700}
    .explore-placeholder-copy{margin-top:1.3rem;color:#666;line-height:1.55}.explore-recognition-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem}
    .explore-recognition-card{display:flex;flex-direction:column;padding:1rem;border-radius:10px;background:#fff;border:1px solid #ddd}
    .explore-recognition-card span{color:#8b0015;font-weight:850}.explore-recognition-card strong{margin-top:.35rem;font-size:.85rem;line-height:1.4}
    .explore-tall-panel{min-height:360px}.explore-placeholder-lines{display:grid;gap:.8rem}.explore-placeholder-lines span{display:block;height:16px;border-radius:5px;background:#e5e5e5}
    .explore-placeholder-lines span:nth-child(2){width:86%}.explore-placeholder-lines span:nth-child(3){width:92%}.explore-placeholder-lines span:nth-child(4){width:76%}
    @media(max-width:800px){.explore-topline{align-items:flex-start;flex-direction:column}.explore-nav{justify-content:flex-start}
      .explore-hero-integrated,.explore-hero-recognition-led{--explore-expanded-height:440px;align-items:flex-start}
      .explore-hero-integrated .explore-hero-extra,.explore-hero-recognition-led .explore-hero-extra{position:absolute;left:1.25rem;right:1.25rem;bottom:1.25rem;width:auto;margin:0}
      .explore-hero-integrated .explore-hero-kpis{width:auto;transform:none}.explore-hero-integrated .explore-hero-recognition{display:none}
      .explore-kpi-strip,.explore-glance .explore-kpi-strip{grid-template-columns:repeat(2,1fr)}.explore-glance{grid-template-columns:1fr}
      .explore-affiliation-grid,.explore-recognition-grid{grid-template-columns:1fr}.explore-panel{padding:1.25rem}}
    </style>
    """


def render_profile_summary_exploration(approach: int) -> None:
    if approach not in APPROACH_NAMES:
        approach = 1
    data = _load_aaron_preview_data()
    inject_custom_css()
    st.markdown(_styles(), unsafe_allow_html=True)
    st.markdown(_navigation(approach), unsafe_allow_html=True)

    identity = _identity_html(data)
    if approach == 1:
        hero = (
            '<section class="hbi-collapsing-profile-hero exploration-hero explore-hero-integrated">'
            + identity
            + '<div class="explore-hero-extra">'
            + _kpis(data["metrics"], hero=True)
            + "</div>"
            + _recognition_feature(data["awards"][0], hero=True)
            + "</section>"
        )
        st.markdown(hero, unsafe_allow_html=True)
        st.markdown(_common_body(data, show_recognition=True), unsafe_allow_html=True)
    elif approach == 2:
        hero = (
            '<section class="hbi-collapsing-profile-hero exploration-hero explore-hero-recognition-led">'
            + identity
            + '<div class="explore-hero-extra">'
            + _recognition_feature(data["awards"][0], hero=True)
            + "</div></section>"
        )
        st.markdown(hero, unsafe_allow_html=True)
        st.markdown(_kpis(data["metrics"]), unsafe_allow_html=True)
        st.markdown(_common_body(data, show_recognition=True), unsafe_allow_html=True)
    else:
        st.markdown(
            '<section class="hbi-collapsing-profile-hero exploration-hero">'
            + identity
            + "</section>",
            unsafe_allow_html=True,
        )
        st.markdown(_at_a_glance(data), unsafe_allow_html=True)
        st.markdown(_common_body(data, show_recognition=False), unsafe_allow_html=True)

    render_disclaimer()
