"""Shared UI components for the HBI Members website."""

import base64
from functools import lru_cache
import hashlib
import html as html_mod
import mimetypes
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote

import streamlit as st
from utils.collaboration_summary import collaboration_count_band
from utils.education_background import education_display_text

UCALGARY_RED = "#CF0722"
UCALGARY_DARK = "#8B0015"
UCALGARY_GOLD = "#FFCD00"

COMMUNITY_TEAL = "#33716D"
COMMUNITY_DARK = "#245A55"

INSTITUTION_COLOR = "#5B4FBE"

AVATAR_COLORS = [
    "#CF0722", "#2D6A4F", "#264653", "#2A6F97", "#014F86",
    "#6A040F", "#7B2CBF", "#5A189A", "#3C096C", "#D4A373",
    "#1B4332", "#A30519", "#9D0208", "#370617", "#10002B",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    return html_mod.escape(str(text)) if text else ""


def clean_biography_text(value: object) -> str:
    """Remove a crawler-captured leading Biography heading from display text."""
    text = str(value or "").strip()
    return re.sub(
        r"^(?:#+\s*)?Biography\b\s*(?:[:\-\u2013\u2014]\s*)?",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def clean_looking_for_text(value: object) -> str:
    """Remove the UCalgary source prompt while preserving the member's response."""
    text = str(value or "").strip()
    return re.sub(
        r"^I(?:['’]m|\s+am)\s+looking\s+for\b\s*(?:\.{3}|…)?\s*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def render_public_sidebar_navigation(active: str = "") -> None:
    """Render the stable public menu and keep utility routes out of the sidebar."""
    active_key = str(active or "").strip().casefold()
    items = (
        ("home", "Home", "/"),
        ("members", "Members", "/HBI_Members"),
        ("community", "Community", "/HBI_Community"),
    )
    links = []
    for key, label, url in items:
        is_active = key == active_key
        active_class = " is-active" if is_active else ""
        current = ' aria-current="page"' if is_active else ""
        links.append(
            f'<a class="hbi-public-sidebar-link{active_class}" '
            f'href="{url}" target="_self"{current}>{_esc(label)}</a>'
        )
    st.sidebar.markdown(
        '<nav class="hbi-public-sidebar-nav" aria-label="Primary">'
        + "".join(links)
        + "</nav>",
        unsafe_allow_html=True,
    )


_RESEARCH_LABEL_SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
}
_RESEARCH_LABEL_CANONICAL_TOKENS = {
    "adhd": "ADHD",
    "ai": "AI",
    "als": "ALS",
    "apoe": "APOE",
    "bci": "BCI",
    "bmi": "BMI",
    "cns": "CNS",
    "covid": "COVID",
    "csf": "CSF",
    "ct": "CT",
    "dna": "DNA",
    "dti": "DTI",
    "ecg": "ECG",
    "eeg": "EEG",
    "ekg": "EKG",
    "emg": "EMG",
    "fmri": "fMRI",
    "fnirs": "fNIRS",
    "hiv": "HIV",
    "ibd": "IBD",
    "icu": "ICU",
    "meg": "MEG",
    "mesh": "MeSH",
    "mri": "MRI",
    "ms": "MS",
    "mtor": "mTOR",
    "ocd": "OCD",
    "pet": "PET",
    "pns": "PNS",
    "ptsd": "PTSD",
    "rna": "RNA",
    "rtms": "rTMS",
    "tms": "TMS",
    "umls": "UMLS",
}
_RESEARCH_LABEL_WORD_PATTERN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def format_research_label(value: object) -> str:
    """Return a readable research-term label without changing its stored key.

    Ordinary words use title-style capitalization, common scientific acronyms
    use their conventional casing, and mixed-case scientific tokens such as
    ``mTOR`` are preserved. This function is intentionally display-only.
    """
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value).replace("_", " ")).strip()
    if not text:
        return ""

    word_index = 0

    def _format_word(match: re.Match) -> str:
        nonlocal word_index
        token = match.group(0)
        key = token.casefold()
        previous = text[: match.start()].rstrip()
        starts_phrase = word_index == 0 or (previous and previous[-1] in ":;.!?")
        word_index += 1

        canonical = _RESEARCH_LABEL_CANONICAL_TOKENS.get(key)
        if canonical:
            return canonical
        if not any(character.isalpha() for character in token):
            return token
        if any(character.isdigit() for character in token):
            return token
        if (
            any(character.isupper() for character in token[1:])
            and any(character.islower() for character in token)
        ):
            return token
        if key in _RESEARCH_LABEL_SMALL_WORDS and not starts_phrase:
            return token.lower()
        lowered = token.lower()
        return lowered[:1].upper() + lowered[1:]

    return _RESEARCH_LABEL_WORD_PATTERN.sub(_format_word, text)


def get_initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    if parts:
        return parts[0][0].upper()
    return "?"


def get_avatar_color(name: str) -> str:
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(AVATAR_COLORS)
    return AVATAR_COLORS[idx]


_POSITION_ROLE_PATTERN = re.compile(
    r"\b(professor|dean|director|member|chair|lead|head|scientist|researcher|"
    r"clinician|instructor|lecturer|coordinator|fellow|advisor|officer|manager|"
    r"specialist|physician|surgeon)\b",
    re.IGNORECASE,
)
_AFFILIATION_NAME_PATTERN = re.compile(
    r"\b(school|faculty|department|institute|centre|center|university|hospital|"
    r"health|network|laboratory|lab|program|clinic|foundation|academy|society|"
    r"college|campus)\b|\.net\b",
    re.IGNORECASE,
)


def _clean_position_value(value) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "none", "<na>"} else text


def _unique_position_values(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = _clean_position_value(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            output.append(text)
    return output


def group_profile_positions(positions) -> list[dict[str, object]]:
    """Associate each affiliation row with its preceding role without merging."""
    groups: list[dict[str, object]] = []
    current_role = ""
    current_role_used = False
    for _, row in positions.iterrows():
        title = _clean_position_value(row.get("title"))
        related = _unique_position_values(
            [row.get("department"), row.get("faculty"), row.get("institution")]
        )
        raw_text = _clean_position_value(row.get("raw_text"))
        # Some comma-containing organization names were split across the title
        # and department columns by older extracts. Prefer the preserved raw
        # value when it contains every split fragment, so the organization stays
        # intact and remains paired with the role immediately above it.
        reconstructed_affiliation = bool(
            raw_text
            and title
            and raw_text != title
            and title.casefold() in raw_text.casefold()
            and related
            and all(value.casefold() in raw_text.casefold() for value in related)
            and _AFFILIATION_NAME_PATTERN.search(raw_text)
        )
        display_title = raw_text if reconstructed_affiliation else title
        display_related = [] if reconstructed_affiliation else related
        is_role = bool(
            display_title
            and (
                _POSITION_ROLE_PATTERN.search(display_title)
                or not _AFFILIATION_NAME_PATTERN.search(display_title)
            )
        )
        if is_role:
            if current_role and not current_role_used:
                groups.append({"title": current_role, "details": []})
            current_role = display_title
            current_role_used = bool(display_related)
            if display_related:
                groups.append({"title": display_title, "details": display_related})
            continue

        details = _unique_position_values([display_title, *display_related])
        if not details:
            continue
        if current_role:
            groups.append({"title": current_role, "details": details})
            current_role_used = True
        else:
            groups.append({"title": details[0], "details": details[1:]})
    if current_role and not current_role_used:
        groups.append({"title": current_role, "details": []})
    return groups


def render_profile_help_badge_html(
    help_text: str,
    aria_label: str = "More information",
) -> str:
    """Render the shared accessible question-mark tooltip for HTML headings."""
    if not str(help_text or "").strip():
        return ""
    return (
        '<span class="hbi-profile-help" tabindex="0" role="button" '
        f'aria-label="{_esc(aria_label)}">?'
        '<span class="hbi-profile-help-text" role="tooltip">'
        f"{_esc(help_text)}</span></span>"
    )


def render_profile_positions_html(positions, source_affiliations=None) -> str:
    """Render bold role titles with affiliation details stacked underneath."""
    if source_affiliations is not None and len(source_affiliations):
        groups = []
        for row in source_affiliations:
            title = _clean_position_value(row.get("title"))
            affiliation = _clean_position_value(row.get("affiliation"))
            if title or affiliation:
                groups.append(
                    {
                        "title": title or affiliation,
                        "details": [affiliation] if title and affiliation else [],
                    }
                )
    else:
        groups = group_profile_positions(positions)
    items: list[str] = []
    for group in groups:
        details = group["details"]
        details_html = (
            f'<div class="hbi-position-details">{_esc(", ".join(details))}</div>'
            if details
            else ""
        )
        items.append(
            '<div class="hbi-position-group">'
            f'<div class="hbi-position-title">{_esc(group["title"])}</div>'
            f"{details_html}</div>"
        )
    return (
        '<section class="hbi-affiliation-panel">'
        '<div class="hbi-affiliation-heading hbi-heading-with-help">Affiliations'
        + render_profile_help_badge_html(
            "Positions and affiliations are drawn from the researcher’s "
            "public UCalgary Research profile.",
            "About the source of affiliations",
        )
        + "</div>"
        '<div class="hbi-position-list">'
        + "".join(items[:4])
        + (
            '<details class="hbi-position-more">'
            '<summary><span class="hbi-position-view-label">View All</span>'
            '<span class="hbi-position-hide-label">Hide All</span></summary>'
            '<div class="hbi-position-more-list">'
            + "".join(items[4:])
            + "</div></details>"
            if len(items) > 4
            else ""
        )
        + "</div></section>"
    )


_DIGITAL_LINK_BADGES = {
    "ucalgary": "UC",
    "scopus": "S",
    "google scholar": "GS",
    "researchgate": "RG",
    "academia.edu": "A",
    "orcid": "OR",
    "pubmed": "PM",
    "research lab": "LAB",
    "research group": "GRP",
}

_DIGITAL_PROFILE_ORDER = {
    "ucalgary": 10,
    "google scholar": 20,
    "orcid": 30,
    "researchgate": 40,
    "scopus": 50,
    "pubmed": 60,
    "academia.edu": 70,
}


def _valid_professional_phone(value: object) -> bool:
    """Reject empty or visibly truncated phone values such as '+1'."""
    digits = re.sub(r"\D", "", str(value or ""))
    return 7 <= len(digits) <= 15


def render_contact_research_links_html(
    contacts: list[dict[str, object]],
    links: list[dict[str, object]],
    research_highlights: dict[str, object] | None = None,
    *,
    show_contact: bool = True,
) -> str:
    """Render contact details and verified digital-footprint links in one card."""
    contact_items: list[str] = []
    preferred_emails = {
        str(contact.get("value") or contact.get("email") or "").strip().casefold()
        for contact in contacts
        if str(contact.get("label") or "").strip().casefold()
        == "preferred method of communication"
    }
    seen_contacts: set[tuple[str, str]] = set()
    for contact in contacts:
        contact_type = str(contact.get("contact_type") or "").strip().casefold()
        value = str(contact.get("value") or contact.get("email") or "").strip()
        url = str(contact.get("url") or "").strip()
        label = str(contact.get("label") or "").strip()
        if not contact_type and contact.get("email"):
            contact_type = "email"
        if contact_type == "email" and value:
            is_preferred = label.casefold() == "preferred method of communication"
            if value.casefold() in preferred_emails and not is_preferred:
                continue
            contact_key = (contact_type, value.casefold())
            if contact_key in seen_contacts:
                continue
            seen_contacts.add(contact_key)
            href = url if url.startswith("mailto:") else f"mailto:{value}"
            display_label = label if is_preferred else "Email"
            contact_items.append(
                '<div class="hbi-digital-contact-row">'
                f'<span class="hbi-digital-contact-label">{_esc(display_label)}</span>'
                f'<a href="{_esc(href)}">{_esc(value)}</a></div>'
            )
        elif contact_type == "phone" and _valid_professional_phone(value):
            digits = re.sub(r"[^\d+]", "", value)
            contact_items.append(
                '<div class="hbi-digital-contact-row">'
                '<span class="hbi-digital-contact-label">Phone</span>'
                f'<a href="tel:{_esc(digits)}">{_esc(value)}</a></div>'
            )

    def _link_rows(group: str) -> str:
        rows: list[str] = []
        group_links = [
            link for link in links
            if str(link.get("link_group") or "") == group
        ]
        if group == "research_profile":
            group_links.sort(
                key=lambda link: (
                    _DIGITAL_PROFILE_ORDER.get(
                        str(link.get("platform") or "").strip().casefold(), 999
                    ),
                    str(link.get("label") or "").casefold(),
                )
            )
        for link in group_links:
            platform = str(link.get("platform") or "Website").strip()
            label = str(link.get("label") or platform).strip()
            identifier = str(link.get("identifier") or "").strip()
            relationship = str(link.get("relationship_type") or "").strip()
            url = str(link.get("url") or "").strip()
            if not url:
                continue
            badge = _DIGITAL_LINK_BADGES.get(platform.casefold(), "WEB")
            meta = identifier or relationship
            meta_html = (
                f'<span class="hbi-digital-link-meta">{_esc(meta)}</span>'
                if meta
                else ""
            )
            rows.append(
                f'<a class="hbi-digital-link" href="{_esc(url)}" target="_blank" '
                'rel="noopener noreferrer">'
                f'<span class="hbi-digital-badge">{_esc(badge)}</span>'
                '<span class="hbi-digital-link-copy">'
                f'<span class="hbi-digital-link-label">{_esc(label)}</span>'
                f'{meta_html}</span>'
                '<span class="hbi-digital-arrow" aria-hidden="true">↗</span></a>'
            )
        return "".join(rows)

    def _highlight_section() -> str:
        if not research_highlights:
            return ""
        contributions = research_highlights.get("contributions") or []
        if not contributions:
            return ""

        tab_items: list[str] = []
        for index, contribution in enumerate(contributions):
            if not isinstance(contribution, dict):
                continue
            title = str(contribution.get("title") or "").strip()
            text = str(contribution.get("text") or "").strip()
            if not title or not text:
                continue
            source_links: list[str] = []
            for source in contribution.get("sources") or []:
                if not isinstance(source, dict):
                    continue
                label = str(source.get("label") or "").strip()
                url = str(source.get("url") or "").strip()
                if not label or not url.startswith("https://"):
                    continue
                source_links.append(
                    f'<a href="{_esc(url)}" target="_blank" '
                    f'rel="noopener noreferrer">{_esc(label)} ↗</a>'
                )
            evidence_html = (
                '<div class="hbi-highlight-evidence"><span>Supporting papers</span>'
                + "".join(source_links)
                + "</div>"
                if source_links
                else ""
            )
            tab_items.append(
                '<details class="hbi-highlight-tab-item" name="hbi-highlight-tabs"'
                + (" open" if not tab_items else "")
                + ">"
                f'<summary class="hbi-highlight-tab">{_esc(title)}</summary>'
                '<article class="hbi-highlight-tab-panel">'
                f'<div class="hbi-highlight-tab-panel-title">{_esc(title)}</div>'
                f'<p>{_esc(text)}</p>'
                f'{evidence_html}</article></details>'
            )

        if not tab_items:
            return ""

        limitations = str(research_highlights.get("limitations") or "").strip()
        source_note = str(research_highlights.get("source_note") or "").strip()
        reviewed_at = str(research_highlights.get("reviewed_at") or "").strip()
        help_parts = [
            "This pilot used Consensus to discover and synthesize relevant "
            "peer-reviewed publications. The displayed wording was independently "
            "edited, author identity was checked, and representative publication "
            "metadata was reviewed against publisher or PubMed records. Linked "
            "collaborative papers support program-level contributions and do not "
            "imply sole authorship. Select a tab to view its explanation and "
            "supporting publications. The Long-term Research Focus and Current "
            "Direction are concise conclusions synthesized across the reviewed "
            "contributions; they do not repeat individual publication details, "
            "and Current Direction is not presented as a researcher-declared plan.",
            limitations,
            source_note,
            f"Reviewed {reviewed_at}." if reviewed_at else "",
        ]
        help_text = " ".join(part for part in help_parts if part)

        def _emphasized_text(value: object, phrases: object = None) -> str:
            rendered = _esc(str(value or "").strip())
            if not rendered:
                return ""
            clean_phrases = [
                str(phrase).strip()
                for phrase in (phrases or [])
                if str(phrase).strip()
            ]
            for phrase in sorted(clean_phrases, key=len, reverse=True):
                safe_phrase = _esc(phrase)
                rendered = rendered.replace(
                    safe_phrase, f"<strong>{safe_phrase}</strong>"
                )
            return rendered

        synthesis_help = {
            "Long-term Research Focus": (
                "Synthesized from the reviewed research contributions and the "
                "publication-based executive summary. It shows the enduring "
                "research focus connecting work across time and is not a direct "
                "quotation from the researcher."
            ),
            "Current Direction": (
                "Inferred from the researcher’s most recent reviewed peer-reviewed "
                "publications and considered alongside the longer-running research "
                "program. It shows the direction supported by recent evidence, not "
                "a researcher-declared future plan."
            ),
        }

        def _synthesis_card(label: str, payload: object) -> str:
            if not isinstance(payload, dict):
                return ""
            headline = str(payload.get("headline") or "").strip()
            text = str(payload.get("text") or payload.get("summary") or "").strip()
            if not headline or not text:
                return ""
            help_html = render_profile_help_badge_html(
                synthesis_help.get(label, ""),
                f"About {label}",
            )
            return (
                '<section class="hbi-highlight-context-card">'
                '<div class="hbi-highlight-context-title hbi-heading-with-help">'
                f'{_esc(label)}{help_html}</div>'
                f'<div class="hbi-highlight-context-headline">{_esc(headline)}</div>'
                f'<p>{_emphasized_text(text, payload.get("emphasis"))}</p>'
                '</section>'
            )

        through_line_html = _synthesis_card(
            "Long-term Research Focus",
            research_highlights.get("research_through_line") or {},
        )
        direction_html = _synthesis_card(
            "Current Direction",
            research_highlights.get("current_direction") or {},
        )
        context_html = (
            f'<div class="hbi-highlight-context-grid">{through_line_html}'
            f'{direction_html}</div>'
            if through_line_html or direction_html
            else ""
        )
        contributions_help = (
            "These tabs summarize major research contributions identified across "
            "the reviewed peer-reviewed publications. Select a tab to see a concise "
            "explanation and representative supporting papers. The examples support "
            "program-level contributions, do not imply sole authorship, and are not "
            "an exhaustive publication list."
        )
        return (
            '<div class="hbi-digital-subheading hbi-highlight-heading hbi-heading-with-help">'
            'Highlights &amp; Contributions'
            + render_profile_help_badge_html(
                help_text,
                "About this research synthesis",
            )
            + '<span class="hbi-highlight-pilot">Pilot</span></div>'
            '<div class="hbi-highlight-panel">'
            '<div class="hbi-highlight-context-title hbi-highlight-tabs-title '
            'hbi-heading-with-help">Key Contributions'
            + render_profile_help_badge_html(
                contributions_help,
                "About Key Contributions",
            )
            + '</div>'
            '<div class="hbi-highlight-tabs">'
            f'<div class="hbi-highlight-tab-list" aria-label="Research highlights">'
            f'{"".join(tab_items)}</div>'
            f"</div>{context_html}</div>"
        )

    research_profiles = _link_rows("research_profile")
    research_ecosystem = _link_rows("research_ecosystem")
    sections: list[str] = []
    highlights_html = _highlight_section()
    if highlights_html:
        sections.append(highlights_html)
    if show_contact and contact_items:
        sections.append(
            '<div class="hbi-digital-subheading">Contact</div>'
            '<div class="hbi-digital-contact-list">'
            + "".join(contact_items)
            + "</div>"
        )
    if research_profiles:
        sections.append(
            '<div class="hbi-digital-subheading">Research Profiles</div>'
            f'<div class="hbi-digital-link-list">{research_profiles}</div>'
        )
    if research_ecosystem:
        sections.append(
            '<div class="hbi-digital-subheading">Labs, Groups &amp; Ventures</div>'
            f'<div class="hbi-digital-link-list">{research_ecosystem}</div>'
        )
    if not sections:
        sections.append(
            '<div class="hbi-digital-empty">'
            + (
                "No verified professional contact or research-profile links are "
                "currently available."
                if show_contact
                else "No verified research-profile links are currently available."
            )
            + "</div>"
        )
    return (
        '<section class="hbi-digital-panel">'
        '<div class="hbi-digital-heading hbi-heading-with-help">Research Footprint'
        + render_profile_help_badge_html(
            (
                "Professional contact details and research links are drawn from "
                "public research profiles and other verified professional or "
                "research pages associated with the researcher."
                if show_contact
                else "Research links are drawn from public research profiles and "
                "other verified professional or research pages associated with "
                "the researcher."
            ),
            "About the source of the research footprint",
        )
        + "</div>"
        '<div class="hbi-digital-intro">'
        + (
            "Professional contact, scholarly profiles, and associated research websites."
            if show_contact
            else "Scholarly profiles and associated research websites."
        )
        + "</div>"
        + "".join(sections)
        + "</section>"
    )


def render_profile_background_html(
    biography: str,
    looking_for: str,
    education: list[dict[str, object]],
    institution_tags: list[str],
    looking_for_links: list[dict[str, object]] | None = None,
) -> str:
    """Render profile background content in the shared soft-gray panel style."""

    def _value(value: object) -> str:
        text = str(value or "").strip()
        return "" if text.casefold() in {"nan", "none", "nat"} else text

    def _linked_copy(text: str, links: list[dict[str, object]]) -> str:
        """Safely link the final matching anchor for each verified source link."""
        rendered = _esc(text)
        # Narrative link sets are deliberately small. Apply in reverse source
        # order so replacements cannot invalidate earlier match positions.
        replacements: list[tuple[int, int, str]] = []
        for link in links:
            anchor = str(link.get("anchor_text") or "").strip()
            url = str(link.get("url") or "").strip()
            if not anchor or not url.startswith("https://"):
                continue
            matches = list(re.finditer(rf"\b{re.escape(anchor)}\b", text, re.IGNORECASE))
            if not matches:
                continue
            match = matches[-1]
            linked = (
                f'<a class="hbi-background-inline-link" href="{_esc(url)}" '
                'target="_blank" rel="noopener noreferrer">'
                f'{_esc(match.group(0))}</a>'
            )
            replacements.append((match.start(), match.end(), linked))
        if not replacements:
            return rendered
        rendered_parts: list[str] = []
        cursor = 0
        for start, end, linked in sorted(replacements):
            if start < cursor:
                continue
            rendered_parts.append(_esc(text[cursor:start]))
            rendered_parts.append(linked)
            cursor = end
        rendered_parts.append(_esc(text[cursor:]))
        return "".join(rendered_parts)

    sections: list[str] = []
    if biography:
        sections.append(
            '<div class="hbi-background-subheading">Biography</div>'
            f'<div class="hbi-background-copy">{_esc(biography)}</div>'
        )
    if looking_for:
        sections.append(
            '<div class="hbi-background-subheading">Looking For</div>'
            '<div class="hbi-background-copy">'
            + _linked_copy(looking_for, looking_for_links or [])
            + "</div>"
        )

    education_items: list[str] = []
    for row in education:
        display_text = education_display_text(row)
        if display_text:
            education_items.append(f'<li>{_esc(display_text)}</li>')
    if education_items:
        sections.append(
            '<div class="hbi-background-subheading">Educational Background</div>'
            '<ul class="hbi-background-list">'
            + "".join(education_items)
            + "</ul>"
        )

    if institution_tags:
        sections.append(
            '<div class="hbi-background-subheading">Affiliated Organizations</div>'
            '<div class="hbi-background-tags">'
            + render_institution_tags(institution_tags, max_show=50)
            + "</div>"
        )

    return (
        '<section class="hbi-background-panel">'
        '<div class="hbi-background-heading hbi-heading-with-help">Background'
        + render_profile_help_badge_html(
            "Biography, Looking For, and educational information are drawn "
            "from the researcher’s public UCalgary Research profile. "
            "Affiliated organizations summarize organizations connected to "
            "the profile’s public research information.",
            "About the source of background information",
        )
        + "</div>"
        + "".join(sections)
        + "</section>"
    )


# ── Avatar ───────────────────────────────────────────────────────────────────

_APP_DIR = Path(__file__).resolve().parent.parent
_STATIC_DIR = (_APP_DIR / "static").resolve()


@lru_cache(maxsize=1024)
def _portable_photo_source(photo_url: str) -> str:
    """Embed app-local photos so they work without a cloud static-file route."""
    prefix = "/app/static/"
    if not photo_url.startswith(prefix):
        return photo_url

    relative_path = photo_url[len(prefix):].lstrip("/")
    path = (_STATIC_DIR / relative_path).resolve()
    try:
        path.relative_to(_STATIC_DIR)
    except ValueError:
        return ""
    if not path.is_file():
        return ""

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"

def render_avatar_html(name: str, size: int = 60, photo_url: str | None = None) -> str:
    """Render a 4:5 portrait avatar at 150% of the former avatar width."""
    initials = _esc(get_initials(name))
    color = get_avatar_color(name)
    width = max(1, round(size * 1.5))
    height = max(1, round(width * 1.25))
    corner_radius = max(8, round(width * 0.08))
    fs = max(12, round(width * 0.38))
    frame_style = (
        f"width:{width}px;height:{height}px;border-radius:{corner_radius}px;"
        f"overflow:hidden;flex-shrink:0;background:{color};"
        "display:inline-flex;align-items:center;justify-content:center;position:relative;"
    )
    photo_source = _portable_photo_source(photo_url) if photo_url else ""
    if photo_source:
        # Layered: initials as background, photo overlaid; hide photo on error.
        return (
            f'<div class="hbi-avatar hbi-avatar-portrait" '
            f'data-avatar-width="{width}" data-avatar-height="{height}" '
            f'style="{frame_style}">'
            f'<div style="position:absolute;color:#fff;font-size:{fs}px;'
            f'font-weight:700;line-height:1;user-select:none;">{initials}</div>'
            f'<img src="{photo_source}" '
            f'style="position:absolute;width:100%;height:100%;object-fit:contain;'
            f'object-position:center center;background:#FFFFFF;z-index:1;" '
            f"onerror=\"this.style.display='none'\" "
            f'alt="{initials}">'
            f'</div>'
        )
    return (
        f'<div class="hbi-avatar hbi-avatar-portrait" '
        f'data-avatar-width="{width}" data-avatar-height="{height}" '
        f'style="{frame_style}color:#fff;font-size:{fs}px;font-weight:700;'
        f'line-height:1;">{initials}</div>'
    )


def profile_hero_detail_lines(positions, source_affiliations=None) -> list[str]:
    """Return a concise position and affiliation pair for the profile hero."""
    groups: list[dict[str, object]] = []
    if source_affiliations is not None and len(source_affiliations):
        for row in source_affiliations:
            title = _clean_position_value(row.get("title"))
            affiliation = _clean_position_value(row.get("affiliation"))
            if title or affiliation:
                groups.append(
                    {
                        "title": title or affiliation,
                        "details": [affiliation] if title and affiliation else [],
                    }
                )
    elif positions is not None and len(positions):
        groups = group_profile_positions(positions)

    if not groups:
        return []

    first = groups[0]
    lines = [_clean_position_value(first.get("title"))]
    lines.extend(
        _clean_position_value(value) for value in first.get("details", [])
    )
    return _unique_position_values(lines)[:2]


def render_profile_action_bar_html(change_url: str) -> str:
    """Render the public profile actions above the animated identity hero."""
    return (
        '<nav class="hbi-profile-action-bar" aria-label="Profile actions">'
        '<a class="hbi-profile-action hbi-profile-action-back" '
        'href="/HBI_Members" target="_self">← Back to Directory</a>'
        '<a class="hbi-profile-action hbi-profile-action-change" '
        f'href="{_esc(change_url)}">Suggest a change</a>'
        '</nav>'
    )


def render_collapsing_profile_hero_html(
    name: str,
    photo_url: str | None = None,
    detail_lines: list[str] | None = None,
    contacts: list[dict[str, object]] | None = None,
) -> str:
    """Render the portrait hero that contracts into a sticky identity bar."""
    avatar = render_avatar_html(name, 125, photo_url=photo_url)
    details_html = "".join(
        f"<p>{_esc(line)}</p>" for line in (detail_lines or []) if line
    )
    contact_candidates: list[tuple[int, str, str]] = []
    for contact in contacts or []:
        contact_type = str(contact.get("contact_type") or "").strip().casefold()
        value = str(contact.get("value") or contact.get("email") or "").strip()
        label = str(contact.get("label") or "").strip()
        if not contact_type and contact.get("email"):
            contact_type = "email"
        if contact_type != "email" or "@" not in value:
            continue
        is_preferred = label.casefold() == "preferred method of communication"
        display_label = label if is_preferred else "Email"
        contact_candidates.append((0 if is_preferred else 1, display_label, value))
    contact_html = ""
    if contact_candidates:
        _, contact_label, contact_email = sorted(contact_candidates)[0]
        contact_html = (
            '<div class="hbi-collapsing-profile-contact-slot">'
            '<aside class="hbi-collapsing-profile-contact" aria-label="Profile contact">'
            f'<span>{_esc(contact_label)}</span>'
            f'<a href="mailto:{_esc(contact_email)}">{_esc(contact_email)}</a>'
            "</aside></div>"
        )
    return (
        '<section class="hbi-collapsing-profile-hero" aria-label="Profile identity">'
        f"{avatar}"
        '<div class="hbi-collapsing-profile-copy">'
        f"<h1>{_esc(name)}</h1>{details_html}"
        f"</div>{contact_html}</section>"
    )


def format_display_year(value: object) -> str:
    """Return a clean display year without spreadsheet-style decimal suffixes."""
    text = str(value or "").strip()
    if text.casefold() in {"", "nan", "nat", "none"}:
        return ""
    whole_year = re.fullmatch(r"(\d{4})\.0+", text)
    return whole_year.group(1) if whole_year else text


def _format_profile_metric(value: object) -> str:
    """Format a numeric profile metric while tolerating CSV float coercion."""
    text = str(value or "").strip()
    if text.casefold() in {"", "nan", "nat", "none"}:
        return ""
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if not number.is_integer():
        return f"{number:g}"
    return f"{int(number):,}"


def _recognition_sort_year(recognition: dict[str, object]) -> int:
    """Return the latest four-digit year in a recognition date for sorting."""
    years = re.findall(r"\b(?:19|20)\d{2}\b", str(recognition.get("year") or ""))
    return max((int(year) for year in years), default=-1)


def _recognition_display_title(recognition: dict[str, object]) -> str:
    """Omit a repeated display year from the selected-recognition title only."""
    title = str(recognition.get("title") or "").strip()
    year = format_display_year(recognition.get("year"))
    if not re.fullmatch(r"\d{4}(?:\s*[-–—/]\s*\d{4})?", year):
        return title
    year_parts = re.split(r"\s*[-–—/]\s*", year)
    date_pattern = r"\s*[-–—/]\s*".join(map(re.escape, year_parts))
    # Keep unrelated numbers and longer dates, e.g. a 2012–2013 award term.
    token = rf"(?<![\w/–—-]){date_pattern}(?![\w/–—-])"
    cleaned = re.sub(rf"[\[(]\s*{token}\s*[\])]", "", title)
    cleaned = re.sub(token, "", cleaned)
    cleaned = re.sub(r"\s+([,;:.])", r"\1", cleaned)
    cleaned = re.sub(r"([,;:])\s*[,;:]", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;:–—-")
    return cleaned or title


def _recognition_exclusion_reason(recognition: dict[str, object]) -> str:
    """Screen incomplete award labels for the selected panel, not source records."""
    title = _recognition_display_title(recognition)
    # Dates cannot make an otherwise generic award label informative.
    title = re.sub(r"\b(?:19|20)\d{2}(?:\.0+)?\b", " ", title)
    key = _research_label_key(title)
    words = set(key.split())
    if not any(char.isalpha() for char in key):
        return "Empty or date-only title"
    if key in {"n a", "na", "nan", "none", "null", "tba", "tbd", "unknown", "not available", "not applicable"}:
        return "Placeholder title"
    generic_words = {
        "award", "awards", "honor", "honors", "honour", "honours", "recognition",
        "recognitions", "prize", "prizes", "bursary", "bursaries", "scholarship",
        "scholarships", "fellowship", "fellowships", "studentship", "studentships",
        "grant", "grants", "commendation", "commendations", "letter", "letters",
        "professorship", "professorships", "elected", "selected", "received",
        "recipient", "winner", "of", "the", "a", "an", "and", "or", "for",
        "honourable", "honorable", "mention",
    }
    if words <= generic_words:
        return "Generic award label without identifying details"
    if key in {
        "travel grant", "research prize", "senior scholar", "honourary member",
        "honorary member", "honour certificate", "clinical fellowship",
        "graduate studentship", "doctorate fellowship", "postdoctoral fellowship",
        "short term fellowship", "salary support award",
    }:
        return "Generic award type without identifying details"
    if re.match(
        r"^(?:media coverage|significant portrayal in media|guest author|board member|"
        r"keynote speaker|keynote lecturer|invited comments|evaluation|funded workshops|"
        r"training support|cbc[- ]+radio interview)(?:\s*[,.;:]|\s*$)",
        title.strip(), flags=re.IGNORECASE,
    ):
        return "Activity or media entry rather than a named recognition"
    # Some source 'awards' lists contain administrative appointments. Keep
    # explicit honors (e.g. an Outstanding Reviewer Award), not ordinary roles.
    role = _research_label_key(re.split(r"[,;]", title, maxsplit=1)[0])
    if re.search(r"\b(?:coordinator|consultant|advisor|adviser|reviewer|vice president|secretary general|secreary general|visiting professor)\b", role):
        if not re.search(r"\b(?:award|prize|honou?r|distinguished|exceptional|outstanding|recognition|honou?rary|medal|fellow)\b", role):
            return "Administrative or professional role rather than a named recognition"
    return ""


def filter_profile_awards(recognitions: list[dict[str, object]] | None) -> list[dict[str, object]]:
    """Return sufficiently described awards, newest first, without changing records."""
    return sorted(
        (recognition for recognition in (recognitions or [])
         if not _recognition_exclusion_reason(recognition)),
        key=_recognition_sort_year,
        reverse=True,
    )


def render_profile_awards(recognitions: list[dict[str, object]] | None) -> None:
    """Show an Awards panel only when source awards pass the shared quality filter."""
    items, seen = [], set()
    for recognition in filter_profile_awards(recognitions):
        title = _recognition_display_title(recognition)
        year = format_display_year(recognition.get("year"))
        key = (_research_label_key(title), year)
        if key in seen:
            continue
        seen.add(key)
        display = f"{year} — {title}" if year else title
        items.append(f"<li>{_esc(display)}</li>")
    if not items:
        return
    with st.container(key="hbi_panel_awards"):
        profile_panel_header(
            "Awards",
            "Awards and recognitions listed on the researcher’s public UCalgary "
            "Research profile. Generic placeholders and non-award activities are "
            "omitted using the same quality filter as Selected Recognition.",
        )
        st.markdown('<ul>' + ''.join(items[:5]) + '</ul>', unsafe_allow_html=True)
        if len(items) > 5:
            with st.expander(f"Show all {len(items)} awards"):
                st.markdown('<ul>' + ''.join(items[5:]) + '</ul>', unsafe_allow_html=True)


def render_profile_at_a_glance_html(
    publication_summary: dict[str, object] | None = None,
    recognitions: list[dict[str, object]] | None = None,
    collaboration_summary: dict[str, object] | None = None,
) -> str:
    """Render the compact research KPI and selected-recognition profile panel."""
    summary = publication_summary or {}
    valid_recognitions = filter_profile_awards(recognitions)

    metrics: list[tuple[str, str]] = []
    publication_count = _format_profile_metric(summary.get("publication_count"))
    first_year = format_display_year(summary.get("first_year"))
    latest_year = format_display_year(summary.get("latest_year"))
    if publication_count:
        metrics.append((publication_count, "Publications"))
    if first_year and latest_year:
        span = first_year if first_year == latest_year else f"{first_year}–{latest_year}"
        metrics.append((span, "Publication span"))

    if not metrics and not valid_recognitions:
        return ""

    metrics_html = ""
    if metrics:
        cards = "".join(
            '<div class="hbi-profile-kpi">'
            f"<strong>{_esc(value)}</strong><span>{_esc(label)}</span></div>"
            for value, label in metrics
        )
        if collaboration_summary is not None:
            collaboration = collaboration_summary
            topics = collaboration.get("topics") or []
            topic_values = "".join(
                f'<span class="hbi-glance-topic">{_esc(format_research_label(topic["label"]))}</span>'
                for topic in topics
            ) or '<span class="hbi-glance-topic">Not available</span>'
            cards += (
                '<div class="hbi-profile-kpi hbi-profile-kpi--topics">'
                f'<div class="hbi-glance-topics">{topic_values}</div>'
                '<span class="hbi-glance-card-label">Top 3 Collaborating Topics in the last 5 years</span>'
                '</div>'
                '<div class="hbi-profile-kpi">'
                f'<strong>{collaboration_count_band(collaboration.get("country_count"))}</strong>'
                '<span>Countries of collaboration</span>'
                '</div>'
            )
        metrics_html = (
            '<div class="hbi-profile-glance-metrics">'
            '<div class="hbi-profile-glance-label hbi-profile-glance-label-with-help">'
            'RESEARCH AT A GLANCE'
            '<span class="hbi-profile-help" tabindex="0" role="button" '
            'aria-label="About the source of research-at-a-glance figures">?'
            '<span class="hbi-profile-help-text" role="tooltip">'
            "Publication totals and publication span "
            "are calculated from the publication records connected to this "
            "profile, across all available years. Collaborative topics use "
            "five calendar years ending in the researcher’s latest publication "
            "year. Topics are ranked by distinct coauthored publications with "
            "matching author keywords, then by recency. Countries are counted "
            "once across the full publication history from coauthors’ recorded "
            "institutional affiliations; they "
            "do not represent nationality. Counts above 10 use decade bands. "
            "A dash means country information is unavailable.</span></span></div>"
            f'<div class="hbi-profile-kpi-grid">{cards}</div></div>'
        )

    recognitions_html = ""
    if valid_recognitions:
        items = "".join(
            '<div class="hbi-profile-recognition">'
            + (
                f'<span>{_esc(format_display_year(recognition.get("year")))}</span>'
                if format_display_year(recognition.get("year"))
                else ""
            )
            + f'<strong>{_esc(_recognition_display_title(recognition))}</strong></div>'
            for recognition in valid_recognitions[:3]
        )
        recognitions_html = (
            '<div class="hbi-profile-glance-recognitions">'
            '<div class="hbi-profile-glance-label hbi-profile-glance-label-with-help">'
            'SELECTED RECOGNITION'
            '<span class="hbi-profile-help" tabindex="0" role="button" '
            'aria-label="About the source of selected recognition">?'
            '<span class="hbi-profile-help-text" role="tooltip">'
            "Selected recognitions are drawn from awards listed on the "
            "researcher’s public UCalgary Research profile. Up to three of the most "
            "recent sufficiently described entries are shown. Generic placeholders "
            "and non-award activity entries are omitted.</span></span></div>"
            f'<div class="hbi-profile-recognition-list">{items}</div></div>'
        )

    single_class = " hbi-profile-glance--single" if not metrics_html or not recognitions_html else ""
    return (
        f'<section class="hbi-profile-glance{single_class}" aria-label="Profile overview">'
        f"{metrics_html}{recognitions_html}</section>"
    )


# ── Research tags ────────────────────────────────────────────────────────────

def render_research_tags(areas: list, max_show: int = 6, clickable: bool = True) -> str:
    if not areas:
        return ""
    tags = ""
    for area in areas[:max_show]:
        display_area = format_research_label(area)
        if clickable:
            href = f'/Areas_of_Research?type=mesh&area={quote(str(area), safe="")}'
            tags += f'<a class="hbi-tag" href="{href}">{_esc(display_area)}</a>'
        else:
            tags += f'<span class="hbi-tag">{_esc(display_area)}</span>'
    if len(areas) > max_show:
        tags += (
            f'<span class="hbi-tag hbi-tag-more">'
            f'+{len(areas) - max_show} more</span>'
        )
    return f'<div style="margin-top:6px;line-height:1.9;">{tags}</div>'


def _research_label_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("’", "'").casefold()
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def _dedupe_research_layers(
    declared_areas: list | None,
    standardized_areas: list | None,
) -> tuple[list[str], list[str]]:
    """Deduplicate each card layer and suppress cross-layer label repeats."""
    declared: list[str] = []
    declared_keys: set[str] = set()
    for value in declared_areas or []:
        label = str(value or "").strip()
        key = _research_label_key(label)
        if label and key and key not in declared_keys:
            declared.append(label)
            declared_keys.add(key)

    standardized: list[str] = []
    standardized_keys: set[str] = set()
    for value in standardized_areas or []:
        label = str(value or "").strip()
        key = _research_label_key(label)
        if (
            label
            and key
            and key not in declared_keys
            and key not in standardized_keys
        ):
            standardized.append(label)
            standardized_keys.add(key)
    return declared, standardized


def render_card_research_layers(
    declared_areas: list | None,
    standardized_areas: list | None,
    standardized_label: str = "Standardized",
    declared_label: str = "Researcher-declared",
) -> str:
    """Render compact declared and standardized card tags without duplicates."""
    declared, standardized = _dedupe_research_layers(
        declared_areas, standardized_areas
    )
    sections: list[str] = []
    if declared:
        sections.append(
            '<div class="hbi-card-research-layer">'
            '<div style="font-size:0.68rem;color:#715700;font-weight:700;">'
            f'{_esc(declared_label)}</div>'
            f'{render_research_tags_v2(declared, max_show=3, preserve_case=True)}'
            '</div>'
        )
    if standardized:
        sections.append(
            '<div class="hbi-card-research-layer">'
            '<div style="font-size:0.68rem;color:#28698F;font-weight:700;">'
            f'{_esc(standardized_label)}</div>'
            f'{render_standardized_research_tags_v2(standardized, "mesh_concept", max_show=3)}'
            '</div>'
        )
    return "".join(sections)


def _render_member_card_term_heading(label, help_text, color):
    return (
        f'<div class="hbi-card-term-heading" style="color:{color};">'
        f'<div>{_esc(label)}</div>'
        + render_profile_help_badge_html(help_text, f"About {label} research keywords")
        + '</div>'
    )


def _render_hbi_card_research_layers(member_id, declared_areas, standardized_areas):
    """Merge card-only standardized/publication tags into unified discovery links."""
    declared, standardized = _dedupe_research_layers(declared_areas, standardized_areas)
    rendered = ""
    if declared:
        rendered = (
            '<div class="hbi-card-research-layer">'
            + _render_member_card_term_heading(
                "Self-declared",
                "Research interests listed on the researcher's UCalgary profile, "
                "shown using the source wording.",
                "#715700",
            )
            + render_research_tags_v2(declared, max_show=3, preserve_case=True)
            + '</div>'
        )
    terms = [
        (label, f'/Research_Terms_and_Areas_of_Interest?term={quote(label, safe="")}',
         "Find profiles through Areas of Research and Research Keywords from Publications")
        for label in standardized[:3]
    ]
    seen = {_research_label_key(label) for label in declared + standardized}
    if not declared and member_id:
        from utils.data_loader import load_card_publication_keywords
        keywords = load_card_publication_keywords().get(str(member_id), [])
        for row in keywords[:5]:
            label = str(row["keyword"]).strip()
            key = _research_label_key(label)
            if not key or key in seen:
                continue
            seen.add(key)
            terms.append(
                (label, '/Research_Terms_and_Areas_of_Interest?term='
                 + quote(label, safe=""),
                 "Find profiles through Areas of Research and Research Keywords from Publications")
            )
    if terms:
        pills = ''.join(
            f'<a class="hbi-tag hbi-tag-v2-mesh" href="{_esc(href)}" '
            f'onclick="event.stopPropagation();" title="{_esc(title)}">'
            f'{_esc(format_research_label(label))}</a>'
            for label, href, title in terms
        )
        if len(standardized) > 3:
            pills += f'<span class="hbi-tag hbi-tag-v2-mesh">+{len(standardized) - 3} more</span>'
        rendered += (
            '<div class="hbi-card-research-layer hbi-card-standardized-terms">'
            + _render_member_card_term_heading(
                "Standardized Terms",
                "Standardized research terms derived from the researcher's UCalgary "
                "profile, including research interests and activities. When no "
                "self-declared terms are available, this section also includes up to "
                "five keywords from indexed publications, ranked by publication count "
                "and then recency. Publication keywords keep their source wording; "
                "duplicate labels are removed from the card.",
                "#28698F",
            )
            + f'<div style="margin-top:6px;line-height:1.9;">{pills}</div></div>'
        )
    return rendered


def render_research_tags_v2(
    areas: list,
    max_show: int = 50,
    clickable: bool = True,
    preserve_case: bool = False,
    exclude_member_id: str = "",
) -> str:
    """Render source research tags, optionally preserving their exact casing."""
    if not areas:
        return ""
    tags = ""
    for area in areas[:max_show]:
        display_area = str(area).strip() if preserve_case else format_research_label(area)
        if clickable:
            href = f'/Areas_of_Research?type=source&area={quote(str(area), safe="")}'
            if exclude_member_id:
                href += f'&exclude={quote(str(exclude_member_id), safe="")}'
            tags += (
                f'<a class="hbi-tag hbi-tag-v2" href="{href}" '
                f'onclick="event.stopPropagation();" '
                f'title="Find other profiles with this researcher-declared Area of Research">'
                f'{_esc(display_area)}</a>'
            )
        else:
            tags += f'<span class="hbi-tag hbi-tag-v2">{_esc(display_area)}</span>'
    if len(areas) > max_show:
        tags += (
            f'<span class="hbi-tag hbi-tag-v2">'
            f'+{len(areas) - max_show} more</span>'
        )
    return f'<div style="margin-top:6px;line-height:1.9;">{tags}</div>'


def render_standardized_research_tags_v2(
    tags_to_render: list,
    tag_type: str,
    max_show: int = 50,
    clickable: bool = True,
    exclude_member_id: str = "",
) -> str:
    """Render accepted MeSH concepts or reusable HBI umbrella tags."""
    if not tags_to_render:
        return ""
    query_type = "mesh" if tag_type == "mesh_concept" else "umbrella"
    css_class = "hbi-tag-v2-mesh" if query_type == "mesh" else "hbi-tag-v2-umbrella"
    title = (
        "Find other profiles with this standardized research term"
        if query_type == "mesh"
        else "Find other profiles in this Research Theme"
    )
    rendered = ""
    for tag in tags_to_render[:max_show]:
        display_tag = format_research_label(tag)
        if clickable:
            href = (
                f'/Areas_of_Research?type={query_type}'
                f'&area={quote(str(tag), safe="")}'
            )
            if exclude_member_id:
                href += f'&exclude={quote(str(exclude_member_id), safe="")}'
            rendered += (
                f'<a class="hbi-tag {css_class}" href="{href}" '
                f'onclick="event.stopPropagation();" title="{title}">'
                f'{_esc(display_tag)}</a>'
            )
        else:
            rendered += f'<span class="hbi-tag {css_class}">{_esc(display_tag)}</span>'
    if len(tags_to_render) > max_show:
        rendered += (
            f'<span class="hbi-tag {css_class}">'
            f'+{len(tags_to_render) - max_show} more</span>'
        )
    return f'<div style="margin-top:6px;line-height:1.9;">{rendered}</div>'


def render_scopus_keyword_tags(
    keywords: list,
    normalized_keywords: list | None = None,
    max_show: int = 20,
) -> str:
    """Render research-keyword pills from publications with explorer links."""
    if not keywords:
        return ""
    normalized_keywords = normalized_keywords or keywords
    tags = ""
    for keyword, normalized in list(zip(keywords, normalized_keywords))[:max_show]:
        display_keyword = format_research_label(keyword)
        href = f'/Research_Keywords_from_Publications?keyword={quote(str(normalized), safe="")}'
        tags += (
            f'<a class="hbi-tag" href="{href}" '
            'onclick="event.stopPropagation();" '
            f'title="Find HBI profiles with this research keyword from publications">'
            f'{_esc(display_keyword)}</a>'
        )
    if len(keywords) > max_show:
        tags += (
            f'<span style="display:inline-block;padding:3px 10px;margin:2px;'
            f'border-radius:12px;background:{UCALGARY_RED};font-size:0.78rem;'
            f'color:#fff;font-weight:700;">+{len(keywords) - max_show} more</span>'
        )
    return f'<div style="margin-top:6px;line-height:1.9;">{tags}</div>'


def render_scopus_keyword_table(
    rows: list[dict],
    member_id: str = "",
) -> str:
    """Render a compact table with in-place client-side column sorting."""
    if not rows:
        return ""

    def _fmt_int(value) -> str:
        try:
            return f"{int(float(value)):,}"
        except (TypeError, ValueError):
            return ""

    def _fmt_year(value) -> str:
        try:
            return str(int(float(value)))
        except (TypeError, ValueError):
            return ""

    body = ""
    for row in rows:
        keyword = row.get("keyword", "")
        normalized = row.get("normalized_keyphrase", keyword)
        if not keyword:
            continue
        display_keyword = format_research_label(keyword)
        href = f'/Research_Keywords_from_Publications?keyword={quote(str(normalized), safe="")}'
        body += (
            f'<tr data-keyword="{_esc(str(keyword).casefold())}" '
            f'data-publication-count="{_fmt_int(row.get("publication_count")).replace(",", "")}" '
            f'data-latest-year="{_fmt_year(row.get("latest_year"))}">'
            f'<td><a href="{href}" target="_top">{_esc(display_keyword)}</a></td>'
            f'<td>{_fmt_int(row.get("publication_count"))}</td>'
            f'<td>{_fmt_year(row.get("latest_year"))}</td>'
            "</tr>"
        )

    def _sortable_header(
        label: str,
        column: str,
        value_type: str,
        arrow: str = "↕",
    ) -> str:
        return (
            f'<th><button class="scopus-sort-header" type="button" '
            f'data-column="{column}" data-type="{value_type}" '
            f'title="Sort {label.lower()}">'
            f'{_esc(label)} <span class="sort-arrow">{arrow}</span>'
            "</button></th>"
        )

    headers = (
        _sortable_header("Keyword", "keyword", "text")
        + _sortable_header(
            "Supporting publications",
            "publication-count",
            "number",
            "↓",
        )
        + _sortable_header("Latest year", "latest-year", "number")
    )
    table_id = "scopus-keywords-" + hashlib.sha1(
        str(member_id).encode("utf-8")
    ).hexdigest()[:12]

    return (
        "<style>"
        "html,body{margin:0;padding:0;font-family:Arial,sans-serif;color:#1A1A1A;}"
        ".scopus-keyword-table-wrap{max-height:520px;overflow:auto;"
        "border:1px solid #e5e5e5;border-radius:8px;}"
        ".scopus-keyword-table{width:100%;border-collapse:collapse;font-size:.88rem;}"
        ".scopus-keyword-table th{position:sticky;top:0;background:#f6f6f6;"
        "text-align:left;padding:9px 12px;border-bottom:1px solid #ddd;z-index:1;}"
        ".scopus-keyword-table .scopus-sort-header{appearance:none;border:0;"
        "background:transparent;color:#1A1A1A;font:inherit;font-weight:700;padding:0;"
        "cursor:pointer;display:inline-flex;align-items:center;gap:5px;"
        "white-space:nowrap;}"
        ".scopus-keyword-table .scopus-sort-header:hover{color:#A30519;}"
        ".scopus-keyword-table .scopus-sort-header:focus-visible{outline:2px solid "
        "#A30519;outline-offset:3px;border-radius:2px;}"
        ".scopus-keyword-table .scopus-sort-header span{font-size:.78rem;"
        "color:#3F3F3F;line-height:1;}"
        ".scopus-keyword-table td{padding:8px 12px;border-bottom:1px solid #eee;}"
        ".scopus-keyword-table td:nth-child(2),"
        ".scopus-keyword-table td:nth-child(3){text-align:right;white-space:nowrap;}"
        ".scopus-keyword-table a{color:#8B0015;text-decoration:none;font-weight:700;}"
        ".scopus-keyword-table a:hover{text-decoration:underline;}"
        "</style>"
        f'<div id="{table_id}" class="scopus-keyword-table-wrap">'
        '<table class="scopus-keyword-table">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
        "<script>"
        "(() => {"
        f"const root=document.getElementById('{table_id}');"
        "if(!root)return;"
        "const tbody=root.querySelector('tbody');"
        "const buttons=[...root.querySelectorAll('.scopus-sort-header')];"
        "let active='publication-count';"
        "let ascending=false;"
        "const updateArrows=()=>buttons.forEach(button=>{"
        "const arrow=button.querySelector('.sort-arrow');"
        "if(button.dataset.column===active){"
        "arrow.textContent=ascending?'↑':'↓';"
        "button.closest('th').setAttribute('aria-sort',"
        "ascending?'ascending':'descending');"
        "}else{arrow.textContent='↕';"
        "button.closest('th').removeAttribute('aria-sort');}});"
        "buttons.forEach(button=>button.addEventListener('click',()=>{"
        "const column=button.dataset.column;"
        "const type=button.dataset.type;"
        "if(active===column){ascending=!ascending;}else{"
        "active=column;ascending=type==='text';}"
        "const rows=[...tbody.querySelectorAll('tr')];"
        "rows.sort((a,b)=>{"
        "let av=a.getAttribute('data-'+column)||'';"
        "let bv=b.getAttribute('data-'+column)||'';"
        "let result=type==='number'?(Number(av)-Number(bv)):"
        "av.localeCompare(bv,undefined,{sensitivity:'base'});"
        "if(result===0&&column!=='keyword'){"
        "result=(a.dataset.keyword||'').localeCompare("
        "b.dataset.keyword||'',undefined,{sensitivity:'base'});}"
        "return ascending?result:-result;});"
        "rows.forEach(row=>tbody.appendChild(row));"
        "updateArrows();"
        "}));"
        "updateArrows();"
        "})();"
        "</script>"
    )


# ── Noise filtering ──────────────────────────────────────────────────────────

_NOISE_VALUES = frozenset({
    "fulltime", "faculty", "adjuncts", "emeriti", "specialization",
    "clinical", "calgary campus", "member", "clinical research",
})


def _clean_field(text: str | None) -> str:
    """Return the text if meaningful, otherwise empty string."""
    if not text:
        return ""
    if text.strip().lower() in _NOISE_VALUES:
        return ""
    return text.strip()


# ── Member card (directory) ──────────────────────────────────────────────────

def render_card_html(name: str, title: str, department: str, areas: list,
                     member_id: str = "", institution_tags: list | None = None,
                     photo_url: str | None = None, context_text: str = "",
                     tag_version: int = 1,
                     declared_areas: list | None = None) -> str:
    avatar = render_avatar_html(name, 48, photo_url=photo_url)
    safe_name = _esc(name)
    safe_title = _esc(_clean_field(title))
    safe_dept = _esc(_clean_field(department))
    if not safe_title and not safe_dept:
        safe_title = "HBI Member"
    if declared_areas is not None:
        tags = _render_hbi_card_research_layers(member_id, declared_areas, areas)
    elif tag_version == 2:
        tags = render_research_tags_v2(areas, max_show=6, preserve_case=True)
    elif tag_version == 3:
        tags = render_standardized_research_tags_v2(
            areas, "mesh_concept", max_show=6
        )
    elif tag_version == 4:
        tags = render_standardized_research_tags_v2(
            areas, "hbi_umbrella", max_show=6
        )
    else:
        tags = render_research_tags(areas)
    inst_html = render_institution_tags(institution_tags or [], max_show=2)
    context_html = (
        f'<div style="font-size:0.8rem;color:#A30519;font-weight:600;'
        f'margin:7px 0 3px;">{_esc(context_text)}</div>'
        if context_text else ""
    )
    href = f"/HBI_Members?id={_esc(member_id)}" if member_id else "#"
    # Use &nbsp; placeholders to keep consistent height for empty lines
    title_html = safe_title if safe_title else "&nbsp;"
    dept_html = safe_dept if safe_dept else "&nbsp;"
    return (
        f'<div class="hbi-card" onclick="window.location.href=\'{href}\'" style="cursor:pointer;">'
        f'  <div class="hbi-card-body">'
        f'    <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:2px;">'
        f'      {avatar}'
        f'      <div style="min-width:0;">'
        f'        <div style="font-weight:600;font-size:1rem;color:#1A1A1A;line-height:1.3;">{safe_name}</div>'
        f'        <div style="font-size:0.85rem;color:#555;margin-top:2px;min-height:1.2em;">{title_html}</div>'
        f'        <div style="font-size:0.8rem;color:#888;min-height:1.1em;">{dept_html}</div>'
        f'      </div>'
        f'    </div>'
        f'    {context_html}'
        f'    {tags}'
        f'    {inst_html}'
        f'  </div>'
        f'  <a class="hbi-card-btn" href="{href}" onclick="event.stopPropagation();">View Profile →</a>'
        f'</div>'
    )


def render_card_grid(cards_html: list[str]) -> str:
    """Wrap a list of card HTML strings in a CSS Grid container."""
    return '<div class="hbi-grid">' + '\n'.join(cards_html) + '</div>'


# ── List row (directory list view) ───────────────────────────────────────────

def render_list_row_html(name: str, title: str, department: str, areas: list,
                         member_id: str = "", photo_url: str | None = None,
                         context_text: str = "", tag_version: int = 1,
                         declared_areas: list | None = None) -> str:
    avatar = render_avatar_html(name, 40, photo_url=photo_url)
    safe_name = _esc(name)
    safe_title = _esc(_clean_field(title))
    safe_dept = _esc(_clean_field(department))
    if not safe_title and not safe_dept:
        safe_title = "HBI Member"
    if declared_areas is not None:
        tags = _render_hbi_card_research_layers(member_id, declared_areas, areas)
    elif tag_version == 2:
        tags = render_research_tags_v2(areas, max_show=6, preserve_case=True)
    elif tag_version == 3:
        tags = render_standardized_research_tags_v2(
            areas, "mesh_concept", max_show=6
        )
    elif tag_version == 4:
        tags = render_standardized_research_tags_v2(
            areas, "hbi_umbrella", max_show=6
        )
    else:
        tags = render_research_tags(areas, max_show=6)
    context_html = (
        f'<div style="font-size:0.78rem;color:#A30519;font-weight:600;'
        f'margin-top:3px;">{_esc(context_text)}</div>'
        if context_text else ""
    )
    href = f"/HBI_Members?id={_esc(member_id)}" if member_id else "#"
    subtitle = " · ".join(p for p in [safe_title, safe_dept] if p)
    return (
        f'<div class="hbi-list-row" onclick="window.location.href=\'{href}\'" style="cursor:pointer;">'
        f'  <div class="hbi-list-left">'
        f'    {avatar}'
        f'    <div style="min-width:0;">'
        f'      <div style="font-weight:600;font-size:0.95rem;color:#1A1A1A;">{safe_name}</div>'
        f'      <div style="font-size:0.82rem;color:#666;margin-top:2px;">{subtitle}</div>'
        f'      {context_html}'
        f'    </div>'
        f'  </div>'
        f'  <div class="hbi-list-tags">{tags}</div>'
        f'  <a class="hbi-list-action" href="{href}" onclick="event.stopPropagation();">View →</a>'
        f'</div>'
    )


def render_list_view(rows_html: list[str]) -> str:
    """Wrap list row HTML strings in a list container."""
    return '<div class="hbi-list">' + '\n'.join(rows_html) + '</div>'


def render_community_research_tags(
    tags: list,
    max_show: int = 6,
    clickable: bool = True,
) -> str:
    if not tags:
        return ""
    html_tags = ""
    for tag in tags[:max_show]:
        display_tag = format_research_label(tag)
        if clickable:
            href = f'/Areas_of_Research?type=mesh&area={quote(str(tag), safe="")}'
            html_tags += f'<a class="li-tag" href="{href}">{_esc(display_tag)}</a>'
        else:
            html_tags += f'<span class="li-tag">{_esc(display_tag)}</span>'
    if len(tags) > max_show:
        html_tags += (
            f'<span style="display:inline-block;padding:3px 10px;margin:2px;'
            f'border-radius:12px;background:{COMMUNITY_TEAL};font-size:0.78rem;'
            f'color:#fff;font-weight:700;">+{len(tags) - max_show} more</span>'
        )
    return f'<div style="margin-top:6px;line-height:1.9;">{html_tags}</div>'


def render_institution_tags(tags: list, max_show: int = 4) -> str:
    """Render institution tags as pill badges linking to the Organizations page."""
    if not tags:
        return ""
    html_tags = ""
    for tag in tags[:max_show]:
        href = f'/Organizations?org={quote(str(tag))}'
        html_tags += (
            f'<a href="{href}" style="display:inline-block;padding:2px 9px;margin:2px;'
            f'border-radius:12px;background:{INSTITUTION_COLOR};font-size:0.76rem;'
            f'color:#fff;font-weight:700;text-decoration:none;">{_esc(tag)}</a>'
        )
    if len(tags) > max_show:
        html_tags += (
            f'<span style="display:inline-block;padding:2px 9px;margin:2px;'
            f'border-radius:12px;background:{INSTITUTION_COLOR};font-size:0.76rem;'
            f'color:#fff;font-weight:700;">+{len(tags) - max_show} more</span>'
        )
    return f'<div style="margin-top:4px;line-height:1.9;">{html_tags}</div>'


def render_community_card_html(
    name: str,
    current_title: str,
    current_company: str,
    location: str,
    tags: list,
    profile_id: str = "",
    institution_tags: list | None = None,
    photo_url: str | None = None,
    declared_areas: list | None = None,
) -> str:
    avatar = render_avatar_html(name, 48, photo_url=photo_url)
    safe_name = _esc(name)
    safe_title = _esc(_clean_field(current_title))
    safe_company = _esc(_clean_field(current_company))
    safe_location = _esc(_clean_field(location))
    subtitle = " · ".join(p for p in [safe_title, safe_company] if p)
    if not subtitle:
        subtitle = "HBI Community Member"
    tag_html = (
        render_card_research_layers(declared_areas, tags)
        if declared_areas is not None
        else render_community_research_tags(tags)
    )
    inst_html = render_institution_tags(institution_tags or [], max_show=2)
    href = f"/Community_Profile?id={_esc(profile_id)}" if profile_id else "#"
    return (
        f'<div class="li-card" onclick="window.location.href=\'{href}\'" style="cursor:pointer;">'
        f'  <div class="hbi-card-body">'
        f'    <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:2px;">'
        f'      {avatar}'
        f'      <div style="min-width:0;">'
        f'        <div style="font-weight:600;font-size:1rem;color:#1A1A1A;line-height:1.3;">{safe_name}</div>'
        f'        <div style="font-size:0.85rem;color:#555;margin-top:2px;min-height:1.2em;">{subtitle}</div>'
        f'        <div style="font-size:0.78rem;color:#888;min-height:1.1em;">{safe_location}</div>'
        f'      </div>'
        f'    </div>'
        f'    {tag_html}'
        f'    {inst_html}'
        f'  </div>'
        f'  <a class="li-card-btn" href="{href}" onclick="event.stopPropagation();">View Profile →</a>'
        f'</div>'
    )


def render_community_list_row_html(
    name: str,
    current_title: str,
    current_company: str,
    location: str,
    tags: list,
    profile_id: str = "",
    photo_url: str | None = None,
    declared_areas: list | None = None,
) -> str:
    avatar = render_avatar_html(name, 40, photo_url=photo_url)
    safe_name = _esc(name)
    safe_title = _esc(_clean_field(current_title))
    safe_company = _esc(_clean_field(current_company))
    safe_location = _esc(_clean_field(location))
    subtitle_parts = [p for p in [safe_title, safe_company, safe_location] if p]
    subtitle = " · ".join(subtitle_parts)
    if not subtitle:
        subtitle = "HBI Community Member"
    tag_html = (
        render_card_research_layers(declared_areas, tags)
        if declared_areas is not None
        else render_community_research_tags(tags, max_show=6)
    )
    href = f"/Community_Profile?id={_esc(profile_id)}" if profile_id else "#"
    return (
        f'<div class="hbi-list-row" onclick="window.location.href=\'{href}\'" style="cursor:pointer;">'
        f'  <div class="hbi-list-left">'
        f'    {avatar}'
        f'    <div style="min-width:0;">'
        f'      <div style="font-weight:600;font-size:0.95rem;color:#1A1A1A;">{safe_name}</div>'
        f'      <div style="font-size:0.82rem;color:#666;margin-top:2px;">{subtitle}</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="hbi-list-tags">{tag_html}</div>'
        f'  <a class="hbi-list-action" href="{href}" onclick="event.stopPropagation();" '
        f'     style="color:{COMMUNITY_TEAL};">View →</a>'
        f'</div>'
    )


# ── Section header (profile page) ───────────────────────────────────────────

def section_header(title: str, color: str = UCALGARY_RED):
    st.markdown(
        f'<div style="border-bottom:3px solid {color};padding-bottom:6px;'
        f'margin:2rem 0 1rem 0;">'
        f'<h3 style="margin:0;font-size:1.05rem;text-transform:uppercase;'
        f'letter-spacing:0.5px;color:#1A1A1A;">{_esc(title)}</h3></div>',
        unsafe_allow_html=True,
    )


def profile_panel_header(title: str, help_text: str = ""):
    """Render the shared heading used inside soft-gray profile panels."""
    help_html = render_profile_help_badge_html(
        help_text,
        f"About {title}",
    )
    help_class = " hbi-heading-with-help" if help_html else ""
    st.markdown(
        f'<div class="hbi-profile-panel-heading{help_class}">'
        f"{_esc(title)}{help_html}</div>",
        unsafe_allow_html=True,
    )


# ── Global CSS injection ────────────────────────────────────────────────────

def inject_custom_css():
    st.markdown(
        """
    <style>
    /* ── Banner ── */
    .hbi-banner {
        background: linear-gradient(135deg, #CF0722 0%, #8B0015 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
    }
    .hbi-banner h1 { margin:0; font-size:2.88rem; font-weight:700; color:white !important; }
    .hbi-banner p  { margin:0.3rem 0 0 0; font-size:0.8rem; opacity:0.9; color: white !important; }

    /* ── Animated member-profile hero ── */
    .hbi-profile-action-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin: 0.15rem 0 0.8rem;
    }
    .hbi-profile-action {
        display: inline-flex;
        min-height: 2.6rem;
        box-sizing: border-box;
        align-items: center;
        justify-content: center;
        padding: 0.62rem 1rem;
        border: 1px solid #CF0722;
        border-radius: 9px;
        font-size: 0.9rem;
        font-weight: 750;
        line-height: 1.2;
        text-decoration: none !important;
        transition: background-color 0.15s, border-color 0.15s, color 0.15s,
            box-shadow 0.15s;
    }
    .hbi-profile-action-back {
        background: #FFFFFF;
        color: #8B0015 !important;
    }
    .hbi-profile-action-back:hover {
        border-color: #8B0015;
        background: #FCE8EB;
        color: #8B0015 !important;
        box-shadow: 0 3px 10px rgba(139, 0, 21, 0.12);
    }
    .hbi-profile-action-change {
        background: #CF0722;
        color: #FFFFFF !important;
    }
    .hbi-profile-action-change:hover {
        border-color: #8B0015;
        background: #8B0015;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(139, 0, 21, 0.2);
    }
    section.stMain {
        scroll-timeline-name: --hbi-profile-page;
        scroll-timeline-axis: block;
    }
    @supports (animation-timeline: scroll()) {
        div[data-testid="stElementContainer"]:has(.hbi-collapsing-profile-hero) {
            position: sticky !important;
            top: 3.5rem;
            z-index: 900;
        }
    }
    .hbi-collapsing-profile-hero {
        --hbi-hero-expanded-padding: 1.75rem 2.5rem;
        --hbi-hero-collapsed-padding: 0.78125rem 1.953125rem;
        --hbi-hero-expanded-name-size: 2.625rem;
        --hbi-hero-collapsed-name-size: 2.05078125rem;
        --hbi-hero-detail-size: 1.38rem;
        display: flex;
        height: 306px;
        align-items: center;
        gap: 2rem;
        box-sizing: border-box;
        margin-bottom: 1.25rem;
        padding: 1.75rem 2.5rem;
        overflow: hidden;
        border-radius: 18px;
        color: #FFFFFF;
        background: linear-gradient(125deg, #E00029 0%, #870015 100%);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.16);
        animation: hbi-profile-hero-collapse linear both;
        animation-timeline: --hbi-profile-page;
        animation-range: 0 340px;
    }
    .hbi-collapsing-profile-hero .hbi-avatar {
        box-sizing: border-box;
        border: 5px solid #FFFFFF;
        box-shadow: 0 5px 18px rgba(0, 0, 0, 0.22);
        animation: hbi-profile-photo-collapse linear both;
        animation-timeline: --hbi-profile-page;
        animation-range: 0 340px;
    }
    .hbi-collapsing-profile-copy {
        flex: 1 1 auto;
        min-width: 0;
    }
    .hbi-collapsing-profile-copy h1 {
        margin: 0;
        color: #FFFFFF !important;
        font-size: 2.625rem;
        line-height: 1.2;
        animation: hbi-profile-name-collapse linear both;
        animation-timeline: --hbi-profile-page;
        animation-range: 0 340px;
    }
    .hbi-collapsing-profile-copy p {
        margin: 0.3rem 0 0;
        overflow: hidden;
        color: #FFFFFF !important;
        font-size: var(--hbi-hero-detail-size);
        line-height: 1.35;
        animation: hbi-profile-detail-collapse linear both;
        animation-timeline: --hbi-profile-page;
        animation-range: 0 240px;
    }
    .hbi-collapsing-profile-contact-slot {
        position: relative;
        flex: 0 1 20rem;
        align-self: stretch;
        min-width: 0;
        max-width: 20rem;
        margin-left: auto;
    }
    .hbi-collapsing-profile-contact {
        position: absolute;
        right: 0;
        bottom: 0;
        display: flex;
        width: 100%;
        box-sizing: border-box;
        padding: 0.8rem 0.95rem;
        flex-direction: column;
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 11px;
        background: rgba(255, 255, 255, 0.13);
        backdrop-filter: blur(3px);
        animation: hbi-profile-contact-collapse linear both;
        animation-timeline: --hbi-profile-page;
        animation-range: 0 340px;
    }
    .hbi-collapsing-profile-contact span {
        color: rgba(255, 255, 255, 0.82);
        font-size: 0.871rem;
        font-weight: 750;
        letter-spacing: 0.09em;
        line-height: 1.3;
        text-transform: uppercase;
    }
    .hbi-collapsing-profile-contact a {
        min-width: 0;
        margin-top: 0.18rem;
        overflow-wrap: anywhere;
        color: #FFFFFF !important;
        font-size: 1.144rem;
        font-weight: 700;
        line-height: 1.35;
        text-decoration: none !important;
    }
    .hbi-collapsing-profile-contact a:hover { text-decoration: underline !important; }
    @keyframes hbi-profile-contact-collapse {
        from { bottom: 0; transform: translateY(0); }
        to { bottom: 50%; transform: translateY(50%); }
    }
    @keyframes hbi-profile-hero-collapse {
        from { height: 306px; padding: var(--hbi-hero-expanded-padding); border-radius: 18px; }
        to { height: 149px; padding: var(--hbi-hero-collapsed-padding); border-radius: 0 0 20px 20px; }
    }
    @keyframes hbi-profile-photo-collapse {
        from { width: 188px; height: 235px; border-radius: 16px; border-width: 5px; }
        to { width: 94px; height: 118px; border-radius: 16px; border-width: 3.75px; }
    }
    @keyframes hbi-profile-name-collapse {
        from { font-size: var(--hbi-hero-expanded-name-size); }
        to { font-size: var(--hbi-hero-collapsed-name-size); }
    }
    @keyframes hbi-profile-detail-collapse {
        from { opacity: 1; max-height: 4rem; }
        to { opacity: 0; max-height: 0; margin-top: 0; }
    }
    @supports not (animation-timeline: scroll()) {
        .hbi-collapsing-profile-hero,
        .hbi-collapsing-profile-hero .hbi-avatar,
        .hbi-collapsing-profile-copy h1,
        .hbi-collapsing-profile-copy p,
        .hbi-collapsing-profile-contact {
            animation: none;
        }
    }

    /* ── Research-at-a-glance profile summary ── */
    .hbi-profile-glance {
        display: grid;
        grid-template-columns: 1.15fr 1fr;
        gap: 1rem;
        margin: 0 0 1.25rem;
        padding: 1.3rem;
        border: 1px solid #DDDDDD;
        border-top: 6px solid #CF0722;
        border-radius: 12px;
        background: #F4F4F4;
    }
    .hbi-profile-glance--single {
        grid-template-columns: 1fr;
    }
    .hbi-profile-glance-label {
        margin-bottom: 1rem;
        color: #8B0015;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hbi-profile-glance-label-with-help {
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .hbi-heading-with-help {
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .hbi-profile-glance-metrics,
    .hbi-profile-glance-recognitions {
        display: flex;
        min-width: 0;
        flex-direction: column;
    }
    .hbi-profile-help {
        position: relative;
        display: inline-flex;
        width: 1rem;
        height: 1rem;
        align-items: center;
        justify-content: center;
        border: 1px solid #8B0015;
        border-radius: 50%;
        color: #8B0015;
        font-size: 0.68rem;
        font-weight: 800;
        line-height: 1;
        cursor: help;
        letter-spacing: normal;
    }
    .hbi-profile-help-text {
        position: absolute;
        z-index: 950;
        top: calc(100% + 0.55rem);
        left: -0.7rem;
        display: none;
        width: min(300px, 70vw);
        box-sizing: border-box;
        padding: 0.7rem 0.8rem;
        border-radius: 8px;
        background: #262626;
        color: #FFFFFF;
        box-shadow: 0 5px 16px rgba(0, 0, 0, 0.2);
        font-size: 0.75rem;
        font-weight: 500;
        line-height: 1.4;
        letter-spacing: normal;
        text-transform: none;
    }
    .hbi-profile-help:hover .hbi-profile-help-text,
    .hbi-profile-help:focus .hbi-profile-help-text,
    .hbi-profile-help:focus-visible .hbi-profile-help-text {
        display: block;
    }
    .hbi-profile-kpi-grid {
        display: grid;
        flex: 1;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
    }
    .hbi-profile-kpi {
        display: flex;
        min-width: 0;
        flex-direction: column;
        padding: 0.68rem 0.8rem;
        border-radius: 10px;
        background: #FFFFFF;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
    }
    .hbi-profile-kpi strong {
        color: #8B0015;
        font-size: 1.35rem;
    }
    .hbi-profile-kpi span {
        color: #555555;
        font-size: 0.72rem;
    }
    .hbi-profile-kpi .hbi-glance-card-label {
        margin-top: 0.35rem;
    }
    .hbi-glance-topics {
        display: flex;
        flex-wrap: wrap;
        gap: 0.28rem 0.75rem;
    }
    .hbi-profile-kpi .hbi-glance-topic {
        color: #8B0015;
        font-size: 0.85rem;
        font-weight: 650;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    .hbi-glance-topic:not(:last-child)::after {
        content: " |";
        margin-left: 0.5rem;
        color: #717171;
        font-weight: 400;
        white-space: nowrap;
    }
    .hbi-profile-kpi .hbi-glance-period {
        margin-top: auto;
        padding-top: 0.45rem;
        color: #717171;
        font-size: 0.68rem;
    }
    .hbi-profile-recognition {
        display: grid;
        flex: 1;
        grid-template-columns: 54px minmax(0, 1fr);
        align-items: center;
        gap: 0.7rem;
        padding: 0.6rem 0;
        border-bottom: 1px solid #D4D4D4;
    }
    .hbi-profile-recognition-list {
        display: flex;
        flex: 1;
        flex-direction: column;
        padding: 0 0.8rem;
        border-radius: 10px;
        background: #FFFFFF;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
    }
    .hbi-profile-recognition:last-child {
        border-bottom: 0;
    }
    .hbi-profile-recognition span {
        color: #8B0015;
        font-weight: 800;
    }
    .hbi-profile-recognition strong {
        font-size: 0.82rem;
        line-height: 1.35;
    }
    .hbi-profile-recognition strong:first-child {
        grid-column: 1 / -1;
    }
    @media (max-width: 800px) {
        .hbi-profile-glance {
            grid-template-columns: 1fr;
            padding: 1.1rem;
        }
        .hbi-profile-help-text {
            left: -0.7rem;
        }
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] .stMarkdown h2 { color: #CF0722; }
    section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p {
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    .hbi-public-sidebar-nav {
        display: flex;
        flex-direction: column;
        gap: 0.18rem;
        padding: 0.65rem 0.35rem 0.45rem;
    }
    .hbi-public-sidebar-link {
        display: block;
        padding: 0.58rem 0.72rem;
        border-left: 3px solid transparent;
        border-radius: 0 7px 7px 0;
        color: #333333 !important;
        font-size: 0.9rem;
        font-weight: 600;
        line-height: 1.3;
        text-decoration: none !important;
    }
    .hbi-public-sidebar-link:hover {
        border-left-color: #CF0722;
        background: #FCE8EB;
        color: #8B0015 !important;
    }
    .hbi-public-sidebar-link.is-active {
        border-left-color: #CF0722;
        background: #FCE8EB;
        color: #8B0015 !important;
        font-weight: 750;
    }

    /* ── Card action buttons ── */
    div[data-testid="stVerticalBlock"] .stButton > button[kind="primary"] {
        background-color: #CF0722;
        border: none;
        font-size: 0.82rem;
    }

    /* ── Home page nav cards ── */
    .hbi-nav-card {
        display: block;
        text-decoration: none !important;
        color: inherit !important;
        background: #fff;
        border: 1px solid #e4e4e4;
        border-radius: 12px;
        padding: 28px 24px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
    }
    .hbi-nav-card:hover {
        border-color: #CF0722;
        box-shadow: 0 6px 20px rgba(207,7,34,0.15);
        transform: translateY(-2px);
        color: inherit !important;
        text-decoration: none !important;
    }

    /* ── Card grid ── */
    .hbi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .hbi-card {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem;
        max-width: 480px;
        display: flex;
        flex-direction: column;
        transition: box-shadow 0.15s, border-color 0.15s;
        cursor: pointer;
    }
    .hbi-card:hover {
        border-color: #CF0722;
        box-shadow: 0 4px 16px rgba(207,7,34,0.12);
    }
    .hbi-card-body {
        flex: 1;
    }
    .hbi-card .hbi-card-body > :not(.hbi-card-research-layer) + .hbi-card-research-layer {
        margin-top: 14px;
    }
    .hbi-card-term-heading {
        position: relative;
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        line-height: 1.4;
    }
    .hbi-card-term-heading .hbi-profile-help {
        position: static;
        flex-shrink: 0;
        color: inherit;
        border-color: currentColor;
    }
    .hbi-card-term-heading .hbi-profile-help-text {
        left: 0;
        width: 300px;
        max-width: 100%;
    }
    .hbi-list-tags:has(.hbi-card-term-heading) { overflow: visible; }
    .hbi-card-btn {
        display: block;
        margin-top: auto;
        padding: 8px 0;
        text-align: center;
        background: #CF0722;
        color: #fff !important;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none !important;
    }
    .hbi-card a {
        position: relative;
        z-index: 1;
    }
    .hbi-card-btn:hover {
        background: #A50519;
    }

    /* ── List view ── */
    .hbi-list {
        display: flex;
        flex-direction: column;
        gap: 0;
    }
    .hbi-list-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #E8E8E8;
        transition: background 0.12s;
        cursor: pointer;
    }
    .hbi-list-row:first-child {
        border-top: 1px solid #E8E8E8;
    }
    .hbi-list-row:hover {
        background: #FEF0F1;
    }
    .hbi-list-left {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 260px;
        flex-shrink: 0;
    }
    .hbi-list-tags {
        flex: 1;
        min-width: 0;
        overflow: hidden;
    }
    .hbi-list-action {
        flex-shrink: 0;
        color: #CF0722;
        font-weight: 600;
        font-size: 0.85rem;
        white-space: nowrap;
        text-decoration: none !important;
    }

    /* ── Research tags ── */
    .hbi-tag {
        display: inline-block;
        padding: 3px 10px;
        margin: 2px;
        border-radius: 12px;
        background: #E8E8E8;
        font-size: 0.78rem;
        font-weight: 650;
        color: #111111;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-decoration: none !important;
        border: 1px solid #B8B8B8;
        transition: border-color 0.15s;
    }
    .hbi-tag:hover {
        background: #FFFFFF;
        border-color: #8B0015;
        color: #8B0015;
        text-decoration: none;
    }
    .hbi-tag:active {
        border-color: #8B0015;
    }
    .hbi-tag-more,
    .hbi-tag-more:hover {
        background: #CF0722;
        border-color: #CF0722;
        color: #FFFFFF;
        font-weight: 700;
    }
    .hbi-tag-v2 {
        background: #FFF2C2;
        border-color: #B98200;
        color: #3D2C00;
    }
    .hbi-tag-v2:hover {
        background: #FFF1C2;
        border-color: #B98200;
        color: #3D2C00;
    }
    .hbi-tag-v2-mesh {
        background: #DCEEF9;
        border-color: #397FA8;
        color: #103C57;
    }
    .hbi-tag-v2-mesh:hover {
        background: #DCEEF9;
        border-color: #397FA8;
        color: #103C57;
    }
    .hbi-tag-v2-umbrella {
        background: #E6DCF6;
        border-color: #7052A7;
        color: #362357;
    }
    .hbi-tag-v2-umbrella:hover {
        background: #E6DCF6;
        border-color: #7052A7;
        color: #362357;
    }

    /* ── Profile positions and affiliations ── */
    .hbi-affiliation-panel {
        width: 100%;
        max-width: none;
        box-sizing: border-box;
        margin: 1.25rem 0 2.5rem;
        padding: 1.8rem 2rem 1.9rem;
        border-radius: 0 0 14px 14px;
        background: #F4F4F4;
    }
    .hbi-affiliation-heading {
        margin: 0 0 1.35rem;
        color: #8B0015;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hbi-position-group {
        padding: 0;
        margin: 0;
    }
    .hbi-position-group:last-child {
        margin-bottom: 0;
    }
    .hbi-position-title {
        color: #1A1A1A;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.4;
    }
    .hbi-position-details {
        margin-top: 0.45rem;
        color: #1A1A1A;
        font-size: 0.98rem;
        line-height: 1.6;
    }
    .hbi-position-more {
        grid-column: 1 / -1;
        margin-top: 0.15rem;
    }
    .hbi-position-list,
    .hbi-position-more-list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1.35rem 2.5rem;
    }
    .hbi-position-more > summary {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 0.58rem 0.95rem;
        border: 1px solid #B7B7B7;
        border-radius: 8px;
        background: #FFFFFF;
        color: #8B0015;
        font-size: 0.9rem;
        font-weight: 700;
        line-height: 1.2;
        cursor: pointer;
        list-style: none;
        transition: border-color 0.15s, background 0.15s;
    }
    .hbi-position-more > summary::-webkit-details-marker { display: none; }
    .hbi-position-hide-label { display: none; }
    .hbi-position-more[open] .hbi-position-view-label { display: none; }
    .hbi-position-more[open] .hbi-position-hide-label { display: inline; }
    .hbi-position-more > summary:hover {
        border-color: #CF0722;
        background: #FCE8EB;
    }
    .hbi-position-more[open] {
        display: flex;
        flex-direction: column;
    }
    .hbi-position-more[open] > summary {
        order: 2;
        align-self: flex-start;
        margin-top: 1.6rem;
    }
    .hbi-position-more[open] > .hbi-position-more-list {
        order: 1;
    }
    .hbi-position-more-list .hbi-position-group:last-child {
        margin-bottom: 0;
    }

    /* ── Contact and research digital footprint ── */
    .hbi-digital-panel {
        width: 100%;
        box-sizing: border-box;
        margin: 1.25rem 0 2.5rem;
        padding: 1.8rem 1.65rem 1.9rem;
        border-radius: 0 0 14px 14px;
        background: #F4F4F4;
    }
    .hbi-footprint-layout .hbi-affiliation-panel { margin-bottom: 1rem; }
    .hbi-footprint-layout .hbi-digital-panel { margin-top: 0; }
    .hbi-digital-heading {
        margin: 0 0 0.35rem;
        color: #8B0015;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hbi-digital-intro {
        margin: 0 0 1.25rem;
        color: #4B4B4B;
        font-size: 0.82rem;
        line-height: 1.45;
    }
    .hbi-digital-empty {
        color: #3F3F3F;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .hbi-digital-subheading {
        margin: 1.35rem 0 0.6rem;
        color: #292929;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .hbi-digital-subheading:first-of-type { margin-top: 0; }
    .hbi-highlight-pilot {
        display: inline-flex;
        align-items: center;
        min-height: 1.25rem;
        margin-left: auto;
        padding: 0.1rem 0.48rem;
        border: 1px solid #C8C8C8;
        border-radius: 999px;
        background: #FFFFFF;
        color: #555555;
        font-size: 0.744rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .hbi-highlight-panel {
        padding: 0.75rem;
        overflow-anchor: none;
        border: 1px solid #DEDEDE;
        border-radius: 10px;
        background: #FFFFFF;
    }
    .hbi-highlight-heading { font-size: 0.912rem; }
    .hbi-highlight-tabs-title {
        margin-bottom: 0.55rem;
    }
    .hbi-highlight-tab-list {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.35rem;
    }
    .hbi-highlight-tab-item,
    .hbi-highlight-tab-item::details-content { display: contents; }
    .hbi-highlight-tab-item:not([open]) > .hbi-highlight-tab-panel { display: none; }
    .hbi-highlight-tab {
        display: grid;
        grid-row: 1;
        min-height: 3rem;
        min-width: 0;
        place-items: center;
        padding: 0.45rem 0.55rem;
        border: 1px solid #DDDDDD;
        border-radius: 7px;
        background: #FAFAFA;
        color: #3F3F3F !important;
        font-size: 0.864rem;
        font-weight: 700;
        line-height: 1.25;
        text-align: center;
        text-decoration: none !important;
        cursor: pointer;
        list-style: none;
    }
    .hbi-highlight-tab::-webkit-details-marker { display: none; }
    .hbi-highlight-tab-item:nth-child(1) > .hbi-highlight-tab { grid-column: 1; }
    .hbi-highlight-tab-item:nth-child(2) > .hbi-highlight-tab { grid-column: 2; }
    .hbi-highlight-tab-item:nth-child(3) > .hbi-highlight-tab { grid-column: 3; }
    .hbi-highlight-tab-item:nth-child(4) > .hbi-highlight-tab { grid-column: 4; }
    .hbi-highlight-tab-item[open] > .hbi-highlight-tab {
        border-color: #A5001A;
        background: #FFF4F5;
        color: #8B0015 !important;
    }
    .hbi-highlight-tab:hover {
        border-color: #CF0722;
        color: #8B0015 !important;
    }
    .hbi-highlight-tab-panel {
        grid-row: 2;
        grid-column: 1 / -1;
        margin-top: 0.3rem;
        padding: 0.82rem 0.92rem;
        border-left: 3px solid #B20A24;
        background: #F8F8F8;
    }
    .hbi-highlight-tab-panel-title {
        margin: 0 0 0.35rem;
        color: #222222;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.3;
    }
    .hbi-highlight-tab-panel p {
        margin: 0;
        color: #3F3F3F;
        font-size: 0.984rem;
        line-height: 1.5;
    }
    .hbi-highlight-evidence {
        display: flex;
        flex-wrap: wrap;
        gap: 0.28rem 0.55rem;
        align-items: baseline;
        margin-top: 0.62rem;
        font-size: 0.828rem;
        line-height: 1.35;
    }
    .hbi-highlight-evidence span {
        color: #666666;
        font-weight: 700;
    }
    .hbi-highlight-evidence a {
        color: #8B0015 !important;
        text-decoration: none !important;
    }
    .hbi-highlight-evidence a:hover { text-decoration: underline !important; }
    .hbi-highlight-context-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.6rem;
        margin-top: 0.65rem;
    }
    .hbi-highlight-context-card {
        min-width: 0;
        padding: 0.65rem 0.72rem;
        border: 1px solid #E3E3E3;
        border-radius: 7px;
        background: #FAFAFA;
    }
    .hbi-highlight-context-card:only-child { grid-column: 1 / -1; }
    .hbi-highlight-context-title {
        margin: 0 0 0.3rem;
        color: #8B0015;
        font-size: 0.912rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        line-height: 1.3;
        text-transform: uppercase;
    }
    .hbi-highlight-context-card > p {
        margin: 0;
        color: #383838;
        font-size: 0.98rem;
        line-height: 1.48;
    }
    .hbi-highlight-context-headline {
        margin: 0 0 0.32rem;
        color: #202020;
        font-size: 1.02rem;
        font-weight: 750;
        line-height: 1.35;
    }
    .hbi-digital-contact-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem 2rem;
    }
    .hbi-digital-contact-row {
        display: grid;
        grid-template-columns: 4.2rem minmax(0, 1fr);
        gap: 0.55rem;
        align-items: baseline;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .hbi-digital-contact-label { color: #3F3F3F; font-weight: 700; }
    .hbi-digital-contact-row a {
        min-width: 0;
        color: #8B0015 !important;
        overflow-wrap: anywhere;
        text-decoration: none !important;
    }
    .hbi-digital-contact-row a:hover {
        color: #CF0722 !important;
        text-decoration: underline !important;
    }
    .hbi-digital-link-list {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
        gap: 0.5rem;
    }
    .hbi-digital-link {
        display: grid;
        grid-template-columns: 2rem minmax(0, 1fr) auto;
        gap: 0.65rem;
        align-items: center;
        padding: 0.58rem 0.7rem;
        border: 1px solid #DEDEDE;
        border-radius: 8px;
        background: #FFFFFF;
        color: #222 !important;
        text-decoration: none !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .hbi-digital-link:hover {
        border-color: #CF0722;
        box-shadow: 0 2px 8px rgba(207, 7, 34, 0.10);
    }

    /* ── Profile background panel ── */
    .hbi-background-panel {
        width: 100%;
        box-sizing: border-box;
        margin: 0 0 2.5rem;
        padding: 1.8rem 2rem 1.9rem;
        border-radius: 0 0 14px 14px;
        background: #F4F4F4;
    }
    .hbi-background-heading {
        margin: 0 0 1.35rem;
        color: #8B0015;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hbi-background-subheading {
        margin: 1.45rem 0 0.5rem;
        color: #1A1A1A;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.4;
    }
    .hbi-background-subheading:first-of-type { margin-top: 0; }
    .hbi-background-copy {
        color: #1A1A1A;
        font-size: 0.98rem;
        line-height: 1.65;
        white-space: pre-line;
    }
    .hbi-background-inline-link {
        color: #8B0015 !important;
        font-weight: 700;
        text-decoration: underline !important;
        text-underline-offset: 0.12em;
    }
    .hbi-background-inline-link:hover { color: #CF0722 !important; }
    .hbi-background-list {
        margin: 0.3rem 0 0;
        padding-left: 1.25rem;
        color: #1A1A1A;
        font-size: 0.98rem;
        line-height: 1.6;
    }
    .hbi-background-list li { margin-bottom: 0.45rem; }
    .hbi-background-list li:last-child { margin-bottom: 0; }
    .hbi-background-tags { margin: 0 -2px; }

    /* ── Interactive profile section panels ── */
    .st-key-hbi_panel_research,
    .st-key-hbi_panel_publications,
    .st-key-hbi_panel_awards,
    .st-key-hbi_panel_news,
    .st-key-hbi_panel_related_profiles {
        width: 100%;
        box-sizing: border-box;
        margin: 0 0 2.5rem;
        padding: 1.8rem 2rem 1.9rem;
        border-radius: 0 0 14px 14px;
        background: #F4F4F4;
    }
    .hbi-profile-panel-heading {
        margin: 0 0 1.35rem;
        color: #8B0015;
        font-size: 0.96rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .st-key-hbi_panel_research h5,
    .st-key-hbi_panel_publications h5,
    .st-key-hbi_panel_awards h5,
    .st-key-hbi_panel_news h5,
    .st-key-hbi_panel_related_profiles h5 {
        color: #1A1A1A;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.4;
    }
    .st-key-hbi_panel_research,
    .st-key-hbi_panel_publications,
    .st-key-hbi_panel_awards,
    .st-key-hbi_panel_news,
    .st-key-hbi_panel_related_profiles,
    .hbi-affiliation-panel,
    .hbi-digital-panel,
    .hbi-background-panel {
        color: #1A1A1A;
    }
    .st-key-hbi_panel_research p,
    .st-key-hbi_panel_publications p,
    .st-key-hbi_panel_awards p,
    .st-key-hbi_panel_news p,
    .st-key-hbi_panel_related_profiles p {
        color: #1A1A1A;
    }
    .st-key-hbi_panel_research [data-testid="stCaptionContainer"] p,
    .st-key-hbi_panel_publications [data-testid="stCaptionContainer"] p,
    .st-key-hbi_panel_awards [data-testid="stCaptionContainer"] p,
    .st-key-hbi_panel_news [data-testid="stCaptionContainer"] p,
    .st-key-hbi_panel_related_profiles [data-testid="stCaptionContainer"] p {
        color: #4B4B4B !important;
    }
    .hbi-declared-guidance {
        margin: 0.15rem 0 0.65rem;
        color: #5A5A5A;
        font-size: 0.78rem;
        line-height: 1.45;
    }
    .hbi-declared-guidance strong {
        color: #444444;
        font-weight: 650;
    }
    .hbi-declared-empty {
        box-sizing: border-box;
        margin: 0.2rem 0 0.85rem;
        padding: 0.72rem 0.85rem;
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        background: #F8F9FA;
        color: #5A5A5A;
        font-size: 0.82rem;
        line-height: 1.45;
    }
    .st-key-hbi_panel_research [data-testid="stWidgetLabel"] p,
    .st-key-hbi_panel_publications [data-testid="stWidgetLabel"] p,
    .st-key-hbi_panel_awards [data-testid="stWidgetLabel"] p,
    .st-key-hbi_panel_news [data-testid="stWidgetLabel"] p {
        color: #1A1A1A !important;
        font-weight: 600;
    }
    .st-key-hbi_panel_research [data-testid="stMetricLabel"] p,
    .st-key-hbi_panel_research [data-testid="stMetricValue"] {
        color: #1A1A1A !important;
    }
    .st-key-hbi_panel_research .stMarkdown a:not([class]),
    .st-key-hbi_panel_publications .stMarkdown a:not([class]),
    .st-key-hbi_panel_awards .stMarkdown a:not([class]),
    .st-key-hbi_panel_news .stMarkdown a:not([class]) {
        color: #8B0015 !important;
        font-weight: 600;
    }
    .st-key-hbi_panel_research .stMarkdown a:not([class]):hover,
    .st-key-hbi_panel_publications .stMarkdown a:not([class]):hover,
    .st-key-hbi_panel_awards .stMarkdown a:not([class]):hover,
    .st-key-hbi_panel_news .stMarkdown a:not([class]):hover {
        color: #CF0722 !important;
    }
    .st-key-hbi_panel_related_profiles [data-testid="column"] {
        min-width: 0;
    }
    .hbi-related-empty {
        display: flex;
        min-height: 5rem;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        margin-bottom: 1.5rem;
        padding: 1rem;
        border: 1px dashed #A6A6A6;
        border-radius: 10px;
        background: #FAFAFA;
        color: #4B4B4B;
        font-size: 0.92rem;
        font-weight: 600;
        text-align: center;
    }
    .hbi-related-directory-link {
        display: flex;
        width: 100%;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 0.65rem 1rem;
        border: 1px solid #C9C9C9;
        border-radius: 8px;
        background: #FFFFFF;
        color: #8B0015 !important;
        font-size: 0.94rem;
        font-weight: 700;
        line-height: 1.3;
        text-align: center;
        text-decoration: none !important;
        transition: border-color 0.15s, background 0.15s, color 0.15s;
    }
    .hbi-related-directory-link:hover {
        border-color: #CF0722;
        background: #FCE8EB;
        color: #8B0015 !important;
        text-decoration: none !important;
    }
    @media (max-width: 700px) {
        .hbi-profile-action-bar {
            align-items: stretch;
        }
        .hbi-profile-action {
            flex: 1 1 0;
            padding-inline: 0.7rem;
            font-size: 0.82rem;
            text-align: center;
        }
        .hbi-collapsing-profile-hero {
            --hbi-hero-expanded-padding: 1.25rem;
            --hbi-hero-expanded-name-size: 1.875rem;
            gap: 1rem;
            padding: 1.25rem;
        }
        .hbi-collapsing-profile-copy h1 { font-size: 1.875rem; }
        .hbi-collapsing-profile-copy p { font-size: 0.9375rem; }
        .hbi-collapsing-profile-contact-slot {
            flex-basis: 8rem;
            max-width: 8rem;
        }
        .hbi-collapsing-profile-contact {
            padding: 0.55rem 0.6rem;
        }
        .hbi-collapsing-profile-contact span { font-size: 0.702rem; }
        .hbi-collapsing-profile-contact a { font-size: 0.858rem; }
        .st-key-hbi_panel_research,
        .st-key-hbi_panel_publications,
        .st-key-hbi_panel_awards,
        .st-key-hbi_panel_news,
        .st-key-hbi_panel_related_profiles,
        .hbi-affiliation-panel,
        .hbi-digital-panel,
        .hbi-background-panel {
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }
    }
    .hbi-digital-badge {
        display: inline-flex;
        width: 2rem;
        height: 2rem;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: #FCE8EB;
        color: #A30519;
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .hbi-digital-link-copy { display: flex; min-width: 0; flex-direction: column; }
    .hbi-digital-link-label {
        overflow: hidden;
        color: #1A1A1A;
        font-size: 0.88rem;
        font-weight: 700;
        line-height: 1.3;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .hbi-digital-link-meta {
        overflow: hidden;
        margin-top: 0.08rem;
        color: #555555;
        font-size: 0.72rem;
        line-height: 1.3;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .hbi-digital-arrow { color: #555555; font-size: 0.9rem; }
    @media (max-width: 760px) {
        .hbi-digital-panel, .hbi-affiliation-panel {
            margin-bottom: 1rem;
            padding: 1.45rem 1.25rem 1.55rem;
        }
        .hbi-position-list,
        .hbi-position-more-list {
            grid-template-columns: 1fr;
        }
        .hbi-highlight-tab-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .hbi-highlight-tab-item:nth-child(1) > .hbi-highlight-tab { grid-column: 1; grid-row: 1; }
        .hbi-highlight-tab-item:nth-child(2) > .hbi-highlight-tab { grid-column: 2; grid-row: 1; }
        .hbi-highlight-tab-item:nth-child(3) > .hbi-highlight-tab { grid-column: 1; grid-row: 2; }
        .hbi-highlight-tab-item:nth-child(4) > .hbi-highlight-tab { grid-column: 2; grid-row: 2; }
        .hbi-highlight-tab-panel { grid-row: 3; }
        .hbi-highlight-context-grid,
        .hbi-highlight-contributors { grid-template-columns: 1fr; }
    }

    /* ── Hide Streamlit chrome ── */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* ── Community (LinkedIn) banner ── */
    .li-banner {
        background: linear-gradient(135deg, #33716D 0%, #245A55 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
    }
    .li-banner h1 { margin:0; font-size:2.88rem; font-weight:700; color:white !important; }
    .li-banner p  { margin:0.3rem 0 0 0; font-size:0.8rem; opacity:0.9; color: white !important; }

    /* ── Community card ── */
    .li-card {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem;
        max-width: 480px;
        display: flex;
        flex-direction: column;
        transition: box-shadow 0.15s, border-color 0.15s;
        cursor: pointer;
    }
    .li-card:hover {
        border-color: #33716D;
        box-shadow: 0 4px 16px rgba(51,113,109,0.13);
    }
    .li-card-btn {
        display: block;
        margin-top: auto;
        padding: 8px 0;
        text-align: center;
        background: #33716D;
        color: #fff !important;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none !important;
    }
    .li-card a {
        position: relative;
        z-index: 1;
    }
    .li-card-btn:hover {
        background: #245A55;
    }

    /* ── Community research tags ── */
    .li-tag {
        display: inline-block;
        padding: 3px 10px;
        margin: 2px;
        border-radius: 12px;
        background: #E8F0F1;
        font-size: 0.78rem;
        color: #294C52;
        font-weight: 700;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        border: 1px solid #33716D;
        text-decoration: none !important;
        transition: border-color 0.15s, background 0.15s;
    }
    .li-tag:hover {
        border-color: #245A55;
        background: #FFFFFF;
        color: #245A55;
        text-decoration: none;
    }

    /* ── List row hover (community teal) ── */
    .li-list-row-hover:hover { background: #F1F5F5; }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_disclaimer():
    st.markdown("---")
    st.caption(
        "Data sourced from UCalgary Profiles and publicly indexed "
        "publication records, supplemented by HBI internal records. "
        "Compliant with UCalgary privacy policies (FOIP and PIPA). "
        "Anyone listed in the community directory may claim, edit, or delete their profile. "
        "For questions or concerns, contact **hbi@ucalgary.ca**."
    )
