"""HBI — Landing Page."""

import math

import pandas as pd
import pydeck as pdk
import streamlit as st
from st_keyup import st_keyup
from utils.page_config import BLANK_PAGE_ICON

from utils.components import (
    inject_custom_css,
    render_public_sidebar_navigation,
    render_card_grid,
    render_card_html,
    render_community_card_html,
    UCALGARY_RED,
    COMMUNITY_TEAL,
    render_disclaimer,
    render_profile_help_badge_html,
)
from utils.data_loader import build_directory_data, load_members
from utils.linkedin_data_loader import (
    build_community_directory_data, load_community_map_data, load_community_location_audit,
)
from utils.profile_search import search_community_profiles, search_member_profiles
from utils.home_layout import render_home_welcome, render_home_directory_links

st.set_page_config(
    page_title="HBI – Hotchkiss Brain Institute",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# st.page_link and st.switch_page require st.navigation() to be configured in
# Streamlit 1.36+. The home page is represented as a function stub so that
# selecting "Home" does not re-execute this file (which causes recursion).
_on_home = False


def _home_page_stub():
    global _on_home
    _on_home = True


_home_page = st.Page(_home_page_stub, title="Home", default=True)
_members_page = st.Page("pages/1_HBI_Members.py", title="Members")
_community_page = st.Page("pages/2_HBI_Community.py", title="Community")
_areas_of_research_page = st.Page(
    "pages/8_Areas_of_Expertise_2.py",
    title="Areas of Research",
    url_path="Areas_of_Research",
)
_publication_keywords_page = st.Page(
    "pages/7_Scopus_Keywords.py",
    title="Research Keywords from Publications",
    url_path="Research_Keywords_from_Publications",
    visibility="hidden",
)
_organizations_page = st.Page("pages/5_Organizations.py", title="Organizations")

_pg = st.navigation(
    [
        _home_page,
        _members_page,
        _community_page,
        _areas_of_research_page,
        _organizations_page,
        _publication_keywords_page,
        st.Page(
            "pages/10_Research_Terms.py",
            title="Research Terms and Areas of Interest",
            url_path="Research_Terms_and_Areas_of_Interest",
            visibility="hidden",
        ),
        st.Page(
            "pages/1_Member_Profile.py",
            title="Member Profile",
            url_path="Member_Profile",
            visibility="hidden",
        ),
        st.Page(
            "pages/4_Community_Profile.py",
            title="Community Profile",
            url_path="Community_Profile",
            visibility="hidden",
        ),
        st.Page(
            "pages/6_Search_Results.py",
            title="Search Results",
            url_path="Search_Results",
            visibility="hidden",
        ),
        st.Page(
            "pages/9_Profile_Summary_Examples.py",
            title="Profile Summary Explorations",
            url_path="Profile_Summary_Examples",
            visibility="hidden",
        ),
    ],
    position="hidden",
)
_pg.run()

if not _on_home:
    st.stop()

inject_custom_css()
render_public_sidebar_navigation("home")

# Home-only styles also track discovery visibility for the banner shortcuts.
render_home_welcome()

with st.container(key="home_discovery"):
    st.markdown(
        '<div id="home-search">'
        '<p class="hbi-home-invitation">Who or what would you like to discover?</p>'
        '<p class="hbi-home-search-hint">Find people, research interests, and connections across HBI.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    _query = st_keyup(
        "Search",
        label_visibility="collapsed",
        placeholder="Search by name, research area, organization, or keyword…",
        key="home_search_query",
        debounce=0,
    )
    _search_results = st.container()
    render_home_directory_links()

with _search_results:
    if _query.strip():
        _member_hits = search_member_profiles(_query)
        _community_hits = search_community_profiles(_query)
        _member_matches = _member_hits.head(6).merge(
            build_directory_data(), on="member_id", how="inner"
        )
        _community_matches = _community_hits.head(6).merge(
            build_community_directory_data(), on="profile_id", how="inner"
        )
        st.caption(
            f"{len(_member_hits)} HBI member results · "
            f"{len(_community_hits)} community results"
        )
        _member_column, _community_column = st.columns(2, gap="large")

        with _member_column:
            st.markdown("##### HBI Members")
            if _member_matches.empty:
                st.markdown(
                    '<div class="hbi-related-empty">No members were found.</div>',
                    unsafe_allow_html=True,
                )
            else:
                _member_cards = []
                for _, row in _member_matches.iterrows():
                    _photo_path = row.get("photo_path", "")
                    _photo_url = (
                        f"/app/static/images/member/{_photo_path}"
                        if _photo_path and pd.notna(_photo_path)
                        else None
                    )
                    _member_cards.append(
                        render_card_html(
                            name=str(row.get("name") or ""),
                            title=str(row.get("title") or ""),
                            department=str(row.get("department") or ""),
                            areas=row.get("research_areas_list") or [],
                            member_id=str(row.get("member_id") or ""),
                            photo_url=_photo_url,
                            declared_areas=row.get("researcher_declared_areas_list") or [],
                        )
                    )
                st.markdown(render_card_grid(_member_cards), unsafe_allow_html=True)

        with _community_column:
            st.markdown("##### HBI Community Members")
            if _community_matches.empty:
                st.markdown(
                    '<div class="hbi-related-empty">No members were found.</div>',
                    unsafe_allow_html=True,
                )
            else:
                _community_cards = []
                for _, row in _community_matches.iterrows():
                    _photo_path = row.get("photo_path", "")
                    _photo_url = (
                        f"/app/static/images/community/{_photo_path}"
                        if _photo_path and pd.notna(_photo_path)
                        else None
                    )
                    _community_cards.append(
                        render_community_card_html(
                            name=str(row.get("full_name") or ""),
                            current_title=str(row.get("current_title") or ""),
                            current_company=str(row.get("current_company") or ""),
                            location=str(row.get("location") or ""),
                            tags=row.get("research_tags_list") or [],
                            profile_id=str(row.get("profile_id") or ""),
                            photo_url=_photo_url,
                            declared_areas=row.get("researcher_declared_areas_list") or [],
                        )
                    )
                st.markdown(render_card_grid(_community_cards), unsafe_allow_html=True)
        if _member_hits.empty and _community_hits.empty:
            st.info("No profiles match your search yet.")
        elif st.button("View all search results", type="primary"):
            st.session_state["global_search_query"] = _query.strip()
            st.switch_page("pages/6_Search_Results.py")

# ── Community Map ─────────────────────────────────────────────────────────────
with st.container(key="home_map_panel"):
    st.markdown(
        '<div class="hbi-home-world">'
        '<img class="hbi-home-clean-image" src="/app/static/images/brand/hbi-world.png" alt="HBI World">'
        '<h2>Where is our community?</h2>'
        '<p>Explore the people and places connected through HBI.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    _HBI_MAP_HELP = (
        "HBI Members are counted from the UCalgary member directory and grouped at the "
        "University of Calgary affiliation hub in Canada. This marker does not establish "
        "each person's current city, country of residence, or nationality."
    )
    _COMMUNITY_MAP_HELP = (
        "Locations come from the saved LinkedIn profile location field in the latest "
        "published extraction for each person. They are not refreshed live and may be "
        "out of date. We do not infer a location from employment or education history. "
        "Only locations that can be resolved are mapped; missing or uncertain entries are excluded."
    )
    _MAP_PLACE_HELP = (
        "Saved profile location text is cleaned and matched to the GeoNames geographic "
        "reference using city, region, and country. Spelling variants are grouped together. "
        "Markers represent approximate city or metropolitan locations, not street addresses."
    )
    _MAP_COUNTRY_HELP = (
        "This counts distinct normalized countries/regions among mapped Community profiles. "
        "Countries come from resolving their saved LinkedIn location text against GeoNames. "
        "They do not represent nationality, publication collaborations, or a verified current "
        "residence. Unmapped profiles and the separate HBI affiliation hub are excluded."
    )
    st.markdown(
        "<style>.hbi-map-metrics{position:relative;}"
        ".hbi-map-metrics .hbi-profile-help{position:static;}"
        ".hbi-map-metrics .hbi-profile-help-text{left:0;right:auto;max-width:100%;}"
        "</style>", unsafe_allow_html=True,
    )
    _map_hbi_control, _map_community_control, _map_details_control = st.columns(3)
    with _map_details_control:
        _show_map_details = st.toggle("Show map details", value=False, key="home_show_map_details")
    with _map_hbi_control:
        _show_hbi = st.checkbox("HBI Members", value=True, key="map_show_hbi", help=_HBI_MAP_HELP if _show_map_details else None)
    with _map_community_control:
        _show_community = st.checkbox("Community profiles", value=True, key="map_show_community", help=_COMMUNITY_MAP_HELP if _show_map_details else None)

    # University of Calgary — HBI home base
    _UCALGARY_LAT = 51.0784
    _UCALGARY_LON = -114.1348
    _BASE_RADIUS  = 4_000    # metres per single profile
    _MAX_RADIUS   = 30_000   # cap — keeps Calgary from filling Alberta when zoomed in

    try:
        _community_df = load_community_map_data()
        _location_audit = load_community_location_audit()
        _members_df   = load_members()
        _hbi_count    = int(_members_df["member_id"].nunique())
        _community_total = int(_location_audit["profile_id"].nunique())
        _unmapped = int(_location_audit["status"].ne("mapped").sum())

        if (_show_hbi or _show_community) and (_hbi_count or not _community_df.empty):
            _total_community = int(_community_df["count"].sum())
            _cities          = int(_community_df["location_id"].nunique())
            _countries       = int(_community_df["country"].nunique())

            if _show_map_details:
                # Stats strip
                _map_stats = []
                if _show_hbi:
                    _map_stats.append(
                        f'<span style="color:{UCALGARY_RED};font-weight:700;">{_hbi_count}</span> HBI members '
                        + render_profile_help_badge_html(_HBI_MAP_HELP, "About HBI member locations")
                    )
                if _show_community:
                    _map_stats.extend([
                        f'<span style="color:{COMMUNITY_TEAL};font-weight:700;">{_total_community:,} of {_community_total:,}</span> community profiles mapped '
                        + render_profile_help_badge_html(_COMMUNITY_MAP_HELP, "About community profile locations"),
                        f'<span style="color:{COMMUNITY_TEAL};font-weight:700;">{_cities}</span> mapped locations '
                        + render_profile_help_badge_html(_MAP_PLACE_HELP, "About mapped locations"),
                        f'<span style="color:{COMMUNITY_TEAL};font-weight:700;">{_countries}</span> countries/regions '
                        + render_profile_help_badge_html(_MAP_COUNTRY_HELP, "About map countries and regions"),
                    ])
                st.markdown(
                    '<p class="hbi-map-metrics" style="color:#666;font-size:0.95rem;margin-top:-6px;">'
                    + ' &nbsp;·&nbsp; '.join(_map_stats) + '</p>', unsafe_allow_html=True,
                )
                if _show_hbi:
                    st.caption("The HBI marker represents University of Calgary affiliation, not individual current locations.")
                if _show_community:
                    st.caption(f"{_unmapped:,} community profiles have missing or unverified locations.")
                    with st.expander("Location coverage"):
                        _status_counts = _location_audit["status"].value_counts()
                        st.write(
                            f"Missing: {int(_status_counts.get('missing', 0))} · "
                            f"Non-location text: {int(_status_counts.get('invalid', 0))} · "
                            f"Needs verification: {int(_status_counts.get('unresolved', 0))}"
                        )
                        st.download_button(
                            "Download location review", _location_audit.to_csv(index=False).encode("utf-8-sig"),
                            file_name="community_location_review.csv", mime="text/csv",
                        )

            # Sqrt-scale bubble radius
            _community_df = _community_df.copy()
            _community_df["radius"] = _community_df["count"].apply(
                lambda c: min(_MAX_RADIUS, _BASE_RADIUS * math.sqrt(c))
            )

            # Arc data: one row per community city, source = UCalgary
            _arc_df = _community_df.copy()
            _arc_df["src_lat"]   = _UCALGARY_LAT
            _arc_df["src_lon"]   = _UCALGARY_LON
            _arc_df["arc_width"] = _arc_df["count"].apply(
                lambda c: max(1, min(6, int(math.sqrt(c))))
            )

            # UCalgary hub bubble (HBI members)
            _hub_df = pd.DataFrame([{
                "lat":     _UCALGARY_LAT,
                "lon":     _UCALGARY_LON,
                "count":   _hbi_count,
                "city":    "University of Calgary",
                "country": "Canada — HBI Members",
                "precision": "Affiliation hub; individual locations not verified",
                "radius":  min(_MAX_RADIUS, _BASE_RADIUS * math.sqrt(_hbi_count)),
            }])

            # Layer 1 — arc connections (UCalgary → community cities)
            _arc_layer = pdk.Layer(
                "ArcLayer",
                id="arc_layer",
                data=_arc_df,
                get_source_position=["src_lon", "src_lat"],
                get_target_position=["lon", "lat"],
                get_width="arc_width",
                get_source_color=[207, 7, 34, 140],    # UCALGARY_RED
                get_target_color=[51, 113, 109, 200],  # Dark green COMMUNITY_TEAL
                pickable=True,
                auto_highlight=True,
            )

            # Layer 2 — community city bubbles (teal)
            _scatter_community = pdk.Layer(
                "ScatterplotLayer",
                id="community_layer",
                data=_community_df,
                get_position=["lon", "lat"],
                get_radius="radius",
                get_fill_color=[51, 113, 109, 185],
                get_line_color=[36, 90, 85, 235],
                radius_min_pixels=5,
                radius_max_pixels=50,
                line_width_min_pixels=1,
                pickable=True,
            )

            # Layer 3 — UCalgary hub bubble (red)
            _scatter_hbi = pdk.Layer(
                "ScatterplotLayer",
                id="hbi_layer",
                data=_hub_df,
                get_position=["lon", "lat"],
                get_radius="radius",
                get_fill_color=[207, 7, 34, 200],
                get_line_color=[207, 7, 34, 255],
                radius_min_pixels=7,
                radius_max_pixels=60,
                line_width_min_pixels=2,
                pickable=True,
            )

            _view = pdk.ViewState(
                latitude=48.0,
                longitude=-85.0,
                zoom=2.5,
                pitch=30,
            )

            _tooltip = {
                "html": "<b>{city}</b><br/>{country}<br/>{count} profile(s)<br/>{precision}",
                "style": {
                    "backgroundColor": "#1A1A2E",
                    "color": "white",
                    "fontSize": "13px",
                    "padding": "8px 12px",
                    "borderRadius": "6px",
                },
            }

            _visible_layers = []
            if _show_hbi and _show_community:
                _visible_layers.append(_arc_layer)
            if _show_community:
                _visible_layers.append(_scatter_community)
            if _show_hbi:
                _visible_layers.append(_scatter_hbi)
            _map_event = st.pydeck_chart(
                pdk.Deck(
                    layers=_visible_layers,
                    initial_view_state=_view,
                    tooltip=_tooltip,
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                ),
                on_select="rerun",
                selection_mode="single-object",
                key=f"community_map_{int(_show_hbi)}_{int(_show_community)}",
                use_container_width=True,
                height=500,
            )

            # Handle bubble clicks — navigate to the relevant profiles page
            try:
                _sel = _map_event.selection.objects
                if _show_community and _sel.get("community_layer"):
                    _clicked_location = _sel["community_layer"][0].get("location_id", "")
                    if _clicked_location:
                        st.session_state["community_map_location_id"] = _clicked_location
                        st.session_state["comm_location"] = ""
                        st.switch_page("pages/2_HBI_Community.py")
                elif _show_hbi and _sel.get("hbi_layer"):
                    st.switch_page("pages/1_HBI_Members.py")
            except AttributeError:
                pass  # no selection yet

            if _show_map_details:
                # Legend
                _legend = []
                for _enabled, _color, _label in [
                    (_show_hbi, UCALGARY_RED, "University of Calgary affiliation hub"),
                    (_show_community, COMMUNITY_TEAL, "Community Profiles"),
                ]:
                    if _enabled:
                        _legend.append(
                            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                            f'background:{_color};margin-right:5px;vertical-align:middle;"></span>{_label}</span>'
                        )
                if _show_hbi and _show_community:
                    _legend.append('<span style="color:#aaa;">Lines connect from the HBI hub to each community location</span>')
                st.markdown(
                    '<div style="display:flex;flex-wrap:wrap;gap:24px;margin-top:6px;font-size:0.85rem;color:#555;">'
                    + ''.join(_legend) + '</div>', unsafe_allow_html=True,
                )
                if _show_community:
                    st.caption(
                        "Based on stored LinkedIn locations, not live tracking · City and metropolitan markers are approximate · "
                        "Bubble size = number of profiles · Geographic reference: [GeoNames](https://www.geonames.org/), "
                        "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)"
                    )
        elif not _show_hbi and not _show_community:
            st.info("Select HBI Members, Community profiles, or both to display the map.")
        else:
            st.info("No location data available.")
    except Exception as _map_err:
        st.caption(f"Map unavailable: {_map_err}")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
render_disclaimer()
