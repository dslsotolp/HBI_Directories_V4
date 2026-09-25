# HBI Directory v4.6

The active public development site is `hbi_website_v4_6` at
<http://localhost:8509>. Run from this directory with:

```powershell
..\.venv\Scripts\python.exe -m streamlit run Home.py --server.port 8509
```

## Simplified public sidebar — 2026-09-25

The shared left menu now shows only Home, Members and Community across all pages.
Areas of Research and Organizations remain registered and functional, including
direct URLs and in-content links; only their sidebar links were removed.
Three navigation tests passed. Live checks verified the shared menu on Home,
both directories, a member profile, unified term results and both hidden explorers.
Backup: `backups/hide_sidebar_explorer_links_20260925_151236/`.

## Unified research-term discovery — 2026-09-25

All Standardized Terms pills on HBI member cards (Grid and List) now link to
`/Research_Terms_and_Areas_of_Interest?term=...`. The new page combines Areas of
Research and Research Keywords from Publications into one deduplicated member
list, identifies each result's evidence sources, and offers source filters.
Related HBI Community profile matches appear alongside members with a separate
explanation of their evidence. Existing source explorer URLs remain available.

The index includes full member-card terms, source research phrases, accepted
standardized terms/themes, source-page fallbacks and publication keywords.
Only directory-visible members appear. Matching folds case, accents, possessives
and punctuation; it does not infer synonyms or singular/plural equivalence.
At validation, Spinal Cord Injury returned 23 members (two also matched Areas of
Research); Brain-Computer Interfaces returned five area matches and no exact
publication-keyword matches. Each includes Community results.

Validation: 15 tests passed across term indexing, card rendering and publication
naming. Live checks covered both Aaron Phillips tag clicks, source filters,
Grid/List, empty results, search form navigation and mobile overflow.
Backup: `backups/unified_research_terms_20260925_150619/`.

## Member profile Awards section — 2026-09-25

Both member-profile routes now replace Activities with Awards. Only award-category
records passing the shared Selected Recognition quality filter appear. Profiles
with no eligible awards, including Paolo Federico, have no Awards section.
The newest five awards appear initially, with an expander for the rest. Full
titles are retained, repeated title/year pairs are deduplicated, and redundant
years are removed from titles. Source activity records remain unchanged.

Validation: 13 profile-at-a-glance tests and five publication-keyword naming tests
passed. Both routes were verified live: Aaron Phillips shows five awards and
expands to all 14; Paolo Federico shows no Awards panel. Mobile overflow was
checked on the main profile route.
Backup: `backups/member_profile_awards_section_20260925_145553/`.

## Selected Recognition quality filter — 2026-09-25

The selected-recognition panel now screens award titles before choosing the
three most recent entries. It omits empty/date-only records, placeholders,
generic labels such as “award” or “fellowship,” and clear media/activity or
ordinary administrative-role entries. Named awards and short honors such as
ASTech Award, FCAHS, and Order of Canada remain eligible; no arbitrary minimum
character count is used. This checks description quality, not award prestige.

If no eligible entries remain, the recognition panel is omitted and publication
metrics remain. Source activity records are unchanged; the detailed Awards section
now uses the same filter, as described above.
The shared renderer covers both member-profile routes. Aaron Phillips retains
his three named awards; Paolo Federico's generic “award + year” entries no longer
appear in the selected panel.

Audit: 209 of 1,467 award-category records excluded from this panel; selected
results change on 38 profiles, with nine recognition panels omitted. Reasons are
saved in `output/selected_recognition_excluded_20260925_144810.csv` at project root.
Eleven tests passed, including short honors, filtering before the three-entry
limit, source preservation, and retained metrics. Both example profiles were
verified on both profile routes.
Backup: `backups/selected_recognition_quality_20260925_144810/`.

## Member Directory banner — 2026-09-25

The Member Directory now shares the Home banner's red gradient, rounded shape,
and scroll contraction. The HBI Members logo sits beside the title and shrinks
with it. Search, Members, and Community shortcuts appear after the directory
controls pass behind the header; desktop shortcuts stay centered on the right.
Search links to the Home discovery search. Small screens use a second shortcut
row. Reduced motion keeps the banner static. Individual profile banners retain
their existing design.

Shared welcome styling and the new `render_member_directory_welcome` live in
`utils/home_layout.py`; the directory route calls it from `pages/1_HBI_Members.py`.
Verified logo loading, scroll/shortcut behavior, 1440/1024/768/390/320 px layouts,
small-screen text, search, List view, individual profile routing, Home appearance,
and reduced motion. Backup: `backups/member_directory_banner_20260925_143621/`.

## Member card research labels — 2026-09-25

HBI member cards now label source terms **Self-declared** and combine standardized
terms plus the existing publication fallback under **Standardized Terms**. This
applies to shared Grid/List member cards. Community card labels and full-profile
research sections are unchanged. Publication keywords retain their publication
explorer links; standardized terms retain their research-area links and source
tooltips. This is a card presentation change, not additional terminology mapping.

Duplicate comparison ignores case, accents, punctuation, and possessive variants.
The existing three standardized previews / +more count and top-five publication
fallback for cards without declared terms are preserved. All 370 visible member
cards passed a displayed-keyword uniqueness audit; 18 focused tests passed.
Live examples checked: Aaron Phillips, Abdul Rahman, Amanda Black, plus List view
and publication-keyword navigation.
Backup: `backups/member_card_standardized_terms_20260925_142618/` at project root.

Card headings are now 0.8rem (previously 0.68rem), with a keyboard-focusable `?`
beside each explaining its source. Self-declared describes UCalgary research
interests; Standardized Terms explains profile-derived standardization and the
top-five publication fallback. Tooltip widths stay within the card on mobile,
and List-view tooltips are not clipped. Verified hover, focus, click, mobile,
and List behavior; all seven card tests passed. Backup:
`backups/member_card_keyword_help_20260925_143336/`.

## Home map panel and optional details — 2026-09-25

“Where is our community?” now sits inside a bordered panel matching the discovery
section. A **Show map details** toggle is off by default. Turning it on reveals
the external counts, location explanations/help, location-coverage expander and
download, legend, and geographic-source notes. The map and the Members/Community
filters remain available with details off. The introductory image/title stay visible.

Verified all four group-filter combinations with details off/on: identical map
layer data and in-map tooltips in both states. Browser checks covered the default,
toggle, review-download visibility, panel border, and mobile widths down to 320 px.
Backup: `backups/home_map_details_panel_20260925_141523/` at project root.

## Home welcome and discovery redesign — 2026-09-25

Home now opens with a rounded HBI-red welcome banner and “Discover the people
behind brain research.” As the page scrolls, the banner contracts to a 76 px
desktop bar (114 px on smaller screens), keeping Search, Members, and Community
shortcuts available. It uses the same CSS scroll-animation approach as the
profiles. Reduced-motion settings and browsers without scroll-animation support
receive a static welcome banner.

Search leads a shared discovery panel, followed by “Or explore a directory” and
lighter Members/Community cards. Live search results appear immediately below
the input, before the directory links. The World image remains above its title,
with a brief invitation and no heavy horizontal divider. Existing search logic,
map data, map filters, and profile routes are preserved.

Implementation: `Home.py` and new `utils/home_layout.py`. Verified live search,
full-results navigation, both directory links, map filters, header contraction
at desktop/tablet/mobile widths (down to 320 px), Search shortcut placement,
and reduced motion. Existing search tests passed (4 tests).
Backup: `backups/home_welcome_redesign_20260925_140045/` at project root.

Banner follow-up: removed the University of Calgary/community-directory eyebrow.
The Search, Members, and Community shortcuts now stay hidden until the discovery
panel (including any search results and both directory cards) has passed behind
the compact header. A CSS view timeline follows the actual panel height; scrolling
back reveals the panel and hides the shortcuts. Buttons are anchored at the
banner's bottom-right, with space for the title on mobile. Verified at 1440, 768,
390, and 320 px, including expanded results and Search return navigation.
Backup: `backups/home_banner_shortcuts_20260925_140901/`.

## Home page brand images — 2026-09-25

The Home page now uses the supplied v4.5 images: `HBI Logo.png` above HBI
Members, `HBI Community.png` above HBI Community, and `HBI World.png` beside
“Where is our community?”. Unmodified copies live in `static/images/brand/`.
Images preserve their proportions and include alt text. Verified all three load
on the live site, desktop/mobile layout, and both directory link destinations.
Backup: `backups/home_brand_icons_20260925_134109/` at project root.

Follow-up: enlarged the Community image to 140 × 140 px so its visible artwork
matches the Members logo's width. Both navigation icons use a 112 px-high aligned
container. Community and World images use CSS contrast/brightness to render their
off-white backgrounds as pure white while preserving the source assets. Verified
live desktop/mobile appearance and no horizontal overflow. Follow-up backup:
`backups/home_icon_size_background_20260925_134402/`.

The World image is now centered above “Where is our community?” at 140 × 140 px,
following the navigation cards' image-before-title order. Verified desktop/mobile.
Backup: `backups/home_layout_brainstorm_20260925_135534/`. The subsequent approved
Home banner and search/navigation redesign is documented above.

## Publication-keyword Community results — 2026-09-25

Publication-keyword links now show HBI Members and HBI Community Members in
parallel columns, matching the Home search layout. Both Grid and List views
include all matches; the columns stack on mobile. Member results retain exact
publication-keyword matching, supporting-publication counts, and their original
ranking. Community results reuse the Home page's saved LinkedIn profile search,
with a separate source caption: these are related profile matches rather than
verified publication-keyword evidence. No new publication indexing was performed.

Validated Exercise: 53 HBI members and 34 Community profiles, profile navigation,
both views, mobile width, empty results, Community-only results, and the keyword
explorer. Existing search and publication-keyword naming tests passed (9 tests).
Backup: `backups/publication_keyword_community_20260925_105120/` at project root.

## Publication history update — 2026-09-11

The directory now includes all available earlier publications returned for its
linked Scopus authors, without a lower-year cutoff. The current public dataset
covers **1965–2026**. It is an indexed publication history, not a guarantee that
every publication in a researcher's career is represented.

- 28,642 distinct publications linked to the 295 approved website profiles,
  up from 24,811.
- 162 linked profiles gained publications; 159 have an earlier publication span.
- Publication totals, spans, keyword counts, year summaries, and research
  connections were regenerated together.
- Coverage text uses exported dates. Publications without native author keywords
  still contribute to publication totals and spans.
- The raw collection contains 30,164 publications across 312 author IDs, including
  authors whose links to website profiles have not been approved.
- Seven apparent C. A. Emery identity mismatches (dental papers from 1947–1980)
  are withheld from public exports, with raw records retained for review.

Example spans: Jane Shearer 2000–2026; Keith Alexander Sharkey 1982–2026;
Quentin Jerome Pittman 1973–2026; Paul Kubes 1988–2026; Carolyn Emery 1994–2026.

## Research at a glance update — 2026-09-11

Both profile routes now show Publications, Publication span, Top 3 Collaborating
Topics in the last 5 years, and Countries of collaboration. The topic and country
cards replace the research-keyword and recognition counts; the separate selected
recognition panel remains available.

Publication totals, spans, and collaboration country counts cover the full
indexed history. Only topics use five calendar years ending in the researcher's
latest indexed publication year, including years without publications. The topic
and country cards omit date ranges; Publication span retains its years.
Highlighted topics appear side by side, separated
by `|`, above their caption. Countries means distinct countries of coauthor institutions worldwide,
not collaborator nationality or the number of researchers. Counts 1–10 display
exactly; 11–19 show `10+`, 20–29 show `20+`, and so on. No country list is shown.
Missing country evidence displays an em dash.

The three leading topics use native author keywords from coauthored publications
within that window. Each publication contributes once per topic, regardless of
coauthor count; ties use recency, then normalized label. Generic document labels
such as review, editorial, consensus, and mechanisms are omitted from these
cards. Country/territory names and common aliases are also excluded before
selecting the top three, using whole-label matching with case, accent, spacing,
and punctuation normalization. The next eligible topic fills the available slot.
This summary-only filter preserves country keywords in all other profile sections
and leaves the full-history country count unchanged. Missing topics show
“Not available.” The local name list is in `utils/country_topic_names.py`.

All 295 connection payloads were regenerated locally with an additive
`collaborative_keyword_years` field; existing payload fields were verified
unchanged. No additional Scopus requests were needed. Validation passed 21
relevant website tests and one pipeline aggregation test, plus desktop/mobile
and both-profile-route browser checks.

Pre-change backup in the workspace root:
`hbi_website_backup_4_6_pre_collaboration_glance_20260911_194548/`.
This includes the active site and copies of the relevant pipeline source.

The subsequent full-history country-count and topic-caption changes passed nine
focused tests and browser checks on both profile routes and mobile. Their backup
is `backups/collaboration_country_full_span_20260911_200252/` in the workspace root.

## Data and refresh

### HBI card publication fallback — 2026-09-25

HBI grid cards and list rows with no researcher-declared terms now display up to
five native publication keywords under **From Publications**. This also applies
when standardized terms exist but declared terms do not. The full-history ranking
uses supporting publication count, latest year, then normalized keyword; it matches
the profile publication-keyword ranking. An empty publication dataset adds no
empty section. Existing declared terms suppress the fallback.

HBI cards label the standardized layer **Researcher-declared Standardized**.
The shared HBI renderers apply this consistently to directory, Home search,
keyword/area/organization results, and related-profile cards. Community card
labels remain unchanged. Publication pills link to the publication-keyword
explorer rather than the declared-area explorer.

Current coverage: 80 HBI profiles receive publication fallback, including 60
with standardized-only terms. Abdul Rahman and Amanda Black each show five terms.
Sixteen relevant tests passed, plus live grid/list, keyword-link, and example-card
checks. Backup: `backups/hbi_card_publication_fallback_20260925_104440/`.

### Affiliation pair repair — 2026-09-13

Restored complete source role–affiliation pairs for Alvin Joselin, Boguslaw
Tomanek, Jodie Burton, Oury Monchi, Paolo Federico, Rajiv Midha, Rodney Li Pi Shan,
Steven Peters, and Yingxu Wang. This adds 24 rows to
`data/ucalgary_profile_affiliations.csv`, preserving all 1,146 existing rows.
Oury's explicitly published `TBA` is included as requested.

The crawler now reads each structured UCalgary `.job` card as a complete pair,
retaining repeated institutions under different roles, repeated roles at
different institutions, and short values such as `TBA`. Exact duplicate pairs
are suppressed. Legacy extraction remains the fallback for unstructured pages.

Validation: four extraction tests and ten website affiliation tests passed;
all 371 stored profiles were checked for roles with missing affiliation details,
with zero remaining. See `AFFILIATION_AUDIT_2026-09-13.md` in the workspace root.
Backup: `backups/affiliation_pairs_fix_20260913_120935/`.

Workspace-relative sources:

- Raw full-history database: `scopus_pipeline/output/scopus_full_history.sqlite3`
- Count audit: `scopus_pipeline/output/pre_2004_audit_20260911.csv`
- Profile comparison: `scopus_pipeline/output/full_history_profile_comparison.csv`
- Validation report: `scopus_pipeline/output/full_history_validation.json`
- Exact public exclusions: `scopus_pipeline/publication_link_exclusions.csv`
- Collection/refresh commands: `scopus_pipeline/README.md`

Both public table and connection exporters apply the same exact publication-link
exclusions. Do not remove raw records or implement a replacement date cutoff.
Collection may require the University of Calgary network/VPN. The website
consumes local exports and makes no live Scopus requests.

## Validation and rollback

The change passed 14 pipeline tests and 34 relevant website tests, database
integrity and foreign-key checks, reconciliation with all 312 API counts,
year/keyword aggregate checks, and validation of all 295 connection payloads.
Browser checks covered both profile routes, earlier publication spans, filtering
back to the original period, coverage labels, and a mobile profile.

Full pre-change backup:
`publication_history_backup_20260911_183930/` in the workspace root.
It includes the v4.6 site, pipeline source, original database, and handoff.
The original `scopus_2004_2026.sqlite3` remains available.

The earlier research-label changes remain in place: researcher-declared wording
is preserved, standardized labels are shown separately, duplicates are suppressed,
and standalone `Ph` and `Interests` are excluded from public research labels.
