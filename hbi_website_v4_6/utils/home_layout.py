"""Welcome layouts and shared scroll-responsive directory banner styles."""

import streamlit as st

from utils.components import portable_static_source


_HBI_LOGO_SRC = portable_static_source("/app/static/images/brand/hbi-logo.png")
_HBI_COMMUNITY_SRC = portable_static_source("/app/static/images/brand/hbi-community.png")


def _render_welcome_styles():
    st.markdown(
        """<style>
        section.stMain {
            scroll-timeline-name: --hbi-home-scroll;
            timeline-scope: --hbi-discovery-visibility;
        }
        .hbi-home-hero {
            --expanded-height: 240px; --compact-height: 76px;
            --expanded-title: 2.65rem; --compact-title: 1.35rem;
            --expanded-padding: 32px 38px; --compact-padding: 12px 24px;
            position:relative; display:flex; align-items:center; justify-content:space-between; gap:24px;
            height:var(--expanded-height); padding:var(--expanded-padding);
            box-sizing:border-box; overflow:hidden; border-radius:30px 30px 48px 30px;
            background:radial-gradient(ellipse at 95% 0%, #ee2945 0%, transparent 55%),
                linear-gradient(120deg, #bb0827, #870018);
            color:white; box-shadow:0 8px 24px rgba(135,0,24,.09);
        }
        .hbi-home-hero-copy { min-width:0; max-width:calc(100% - 285px); }
        .hbi-home-hero h1 {
            color:white !important; font-size:var(--expanded-title); line-height:1.15;
            font-weight:750; letter-spacing:-.035em; margin:0; padding:0;
        }
        .hbi-home-hero .hbi-home-tagline {
            font-size:1.15rem; line-height:1.5; margin:14px 0 0;
            color:white; max-height:80px; overflow:hidden;
        }
        .hbi-home-shortcuts {
            position:absolute; right:24px; top:50%; transform:translateY(-50%); display:flex; gap:6px;
            visibility:hidden; opacity:0;
        }
        .hbi-home-shortcuts a {
            color:white !important; text-decoration:none; font-size:.88rem;
            border:1px solid #ffffff70; border-radius:999px; padding:8px 13px;
            background:#ffffff0a; white-space:nowrap;
        }
        .hbi-home-shortcuts a:hover { background:#ffffff26; }
        .hbi-home-shortcuts a:focus-visible, .hbi-home-directory:focus-visible {
            outline:3px solid #ffbd48; outline-offset:3px;
        }
        .st-key-home_discovery {
            padding:28px 32px 30px; border:1px solid #f0e5e6; border-radius:24px;
            background:linear-gradient(160deg, #fffafa, #fff 65%); margin-top:20px;
            view-timeline-name: --hbi-discovery-visibility;
            view-timeline-axis: block;
            view-timeline-inset: calc(3.5rem + 76px) 0px;
        }
        #home-search { scroll-margin-top:160px; }
        #home-search .hbi-home-invitation { font-size:1.65rem; font-weight:650; line-height:1.3; color:#302428; margin:0 0 8px; }
        .hbi-home-search-hint { font-size:.95rem; color:#62575a; margin:0; }
        .st-key-home_discovery .hbi-home-browse-label {
            display:flex; align-items:center; gap:16px; margin:12px 0 14px;
            font-size:1.05rem; font-weight:700; color:#75676b;
        }
        .hbi-home-browse-label::before, .hbi-home-browse-label::after {
            content:""; height:1px; flex:1; background:#ecdee1;
        }
        a.hbi-home-directory {
            display:block; padding:14px 20px 20px; border:1px solid #eee8e9;
            border-radius:18px; text-align:center; text-decoration:none !important;
            background:white; color:#302428 !important;
            transition:border-color .15s, background .15s;
        }
        a.hbi-home-directory:hover { border-color:#cf0722; background:#fffdfd; }
        .hbi-home-directory-icon { display:flex; align-items:center; justify-content:center; height:112px; }
        .hbi-home-directory-icon img { display:block; object-fit:contain; }
        .hbi-home-directory strong { display:block; font-size:1.13rem; margin:8px 0 5px; }
        .hbi-home-directory-description { display:block; font-size:.9rem; line-height:1.5; color:#63595c; }
        .hbi-home-directory-action { display:block; margin-top:12px; font-size:.85rem; font-weight:650; color:#ad0620; }
        .st-key-home_map_panel {
            padding:24px 32px 30px; margin-top:24px; border:1px solid #f0e5e6;
            border-radius:24px; background:#fff;
        }
        .hbi-home-world { text-align:center; }
        .hbi-home-world img { display:block; width:140px; height:140px; margin:0 auto 8px; }
        .hbi-home-world h2 { font-size:1.65rem; padding:0; margin:0; color:#302428; }
        .hbi-home-world p { color:#62575a; margin:8px 0 18px; font-size:.95rem; }
        .hbi-home-clean-image { filter:contrast(1.12) brightness(1.03); }
        .st-key-home_discovery .hbi-grid { grid-template-columns:repeat(auto-fill, minmax(min(300px, 100%), 1fr)); }
        @supports (animation-timeline: scroll()) {
            div[data-testid="stElementContainer"]:has(.hbi-home-hero) {
                position:sticky !important; top:3.5rem; z-index:900;
            }
            .hbi-home-hero { animation:hbi-home-collapse linear both; }
            .hbi-home-hero h1 { animation:hbi-home-title-collapse linear both; }
            .hbi-home-tagline { animation:hbi-home-detail-collapse linear both; }
            .hbi-home-hero, .hbi-home-hero h1, .hbi-home-tagline {
                animation-timeline:--hbi-home-scroll; animation-range:0px 220px;
            }
        }
        @supports (timeline-scope: --hbi-discovery-visibility) {
            .hbi-home-shortcuts {
                animation:hbi-home-shortcuts-reveal steps(1, end) both;
                animation-timeline:--hbi-discovery-visibility;
                animation-range:exit 99.9% exit 100%;
            }
        }
        @keyframes hbi-home-shortcuts-reveal {
            from { visibility:hidden; opacity:0; }
            to { visibility:visible; opacity:1; }
        }
        @keyframes hbi-home-collapse {
            from { height:var(--expanded-height); padding:var(--expanded-padding); border-radius:30px 30px 48px 30px; }
            to { height:var(--compact-height); padding:var(--compact-padding); border-radius:0 0 20px 20px; }
        }
        @keyframes hbi-home-title-collapse {
            from { font-size:var(--expanded-title); }
            to { font-size:var(--compact-title); letter-spacing:-.01em; }
        }
        @keyframes hbi-home-detail-collapse {
            to { opacity:0; max-height:0; margin:0; }
        }
        @media (max-width:900px) {
            .hbi-home-hero {
                --expanded-height:290px; --compact-height:114px;
                --expanded-title:2.1rem; --compact-title:1.14rem;
                --expanded-padding:26px; --compact-padding:12px 16px;
                flex-direction:column; align-items:flex-start; justify-content:center; gap:14px;
            }
            .hbi-home-shortcuts a { padding:6px 12px; font-size:.82rem; }
            .hbi-home-shortcuts { right:16px; top:auto; bottom:12px; transform:none; }
            .hbi-home-hero-copy { max-width:100%; margin-bottom:44px; }
            .st-key-home_discovery {
                padding:22px 18px;
                view-timeline-inset:calc(3.5rem + 114px) 0px;
            }
            .st-key-home_map_panel { padding:22px 18px; }
            #home-search .hbi-home-invitation { font-size:1.4rem; }
            #home-search { scroll-margin-top:200px; }
        }
        @media (prefers-reduced-motion:reduce) {
            div[data-testid="stElementContainer"]:has(.hbi-home-hero) { position:static !important; }
            .hbi-home-hero, .hbi-home-hero h1, .hbi-home-tagline, .hbi-home-shortcuts { animation:none !important; }
            a.hbi-home-directory { transition:none; }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def render_home_welcome():
    _render_welcome_styles()
    st.markdown(
        '<div class="hbi-home-hero">'
        '<div class="hbi-home-hero-copy">'
        '<h1>Hotchkiss Brain Institute</h1>'
        '<p class="hbi-home-tagline">Discover the people and organizations affiliated with the HBI</p>'
        '</div>'
        '<nav class="hbi-home-shortcuts" aria-label="Directory shortcuts">'
        '<a href="#home-search" target="_self">Search</a>'
        '<a href="/HBI_Members" target="_self">Members</a>'
        '<a href="/HBI_Community" target="_self">Community</a>'
        '</nav></div>',
        unsafe_allow_html=True,
    )


def render_member_directory_welcome():
    _render_welcome_styles()
    st.markdown(
        """<style>
        .hbi-members-hero .hbi-home-hero-copy {
            display:flex; align-items:center; gap:20px; max-width:100%;
        }
        .hbi-member-banner-text { min-width:0; }
        .hbi-members-hero .hbi-home-tagline { max-height:120px; }
        .hbi-member-banner-logo {
            width:112px; height:80px; padding:8px; box-sizing:border-box;
            object-fit:contain; background:white; border-radius:14px; flex-shrink:0;
        }
        .st-key-member_directory_controls {
            margin-top:20px;
        }
        @supports (animation-timeline:scroll()) {
            .hbi-member-banner-logo {
                animation:hbi-member-logo-collapse linear both;
                animation-timeline:--hbi-home-scroll; animation-range:0px 220px;
            }
        }
        @keyframes hbi-member-logo-collapse {
            to { width:48px; height:36px; padding:4px; border-radius:8px; }
        }
        @media (max-width:1100px) {
            .hbi-members-hero {
                --expanded-height:260px; --compact-height:76px;
                --expanded-title:2.1rem; --compact-title:1.14rem;
                --expanded-padding:24px; --compact-padding:12px 16px;
            }
            .hbi-members-hero .hbi-home-hero-copy { gap:14px; margin-bottom:0; }
        }
        @media (prefers-reduced-motion:reduce) {
            .hbi-member-banner-logo { animation:none !important; }
        }
        @media (max-width:480px) {
            .hbi-members-hero { --expanded-title:1.85rem; }
            .hbi-member-banner-logo { width:88px; height:64px; }
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hbi-home-hero hbi-members-hero">'
        '<div class="hbi-home-hero-copy">'
        f'<img class="hbi-member-banner-logo" src="{_HBI_LOGO_SRC}" alt="HBI Members">'
        '<div class="hbi-member-banner-text"><h1>Member Directory</h1>'
        '<p class="hbi-home-tagline">Discover HBI members and their research.</p></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_home_directory_links():
    st.markdown('<p class="hbi-home-browse-label">Or explore a directory</p>', unsafe_allow_html=True)
    members, community = st.columns(2, gap="medium")
    with members:
        st.markdown(
            '<a class="hbi-home-directory" href="/HBI_Members" target="_self">'
            f'<span class="hbi-home-directory-icon"><img src="{_HBI_LOGO_SRC}" '
            'alt="HBI Logo" style="width:112px;height:80px;"></span>'
            '<strong>HBI Members</strong>'
            '<span class="hbi-home-directory-description">Meet our faculty and explore their research.</span>'
            '<span class="hbi-home-directory-action">Browse members →</span></a>',
            unsafe_allow_html=True,
        )
    with community:
        st.markdown(
            '<a class="hbi-home-directory" href="/HBI_Community" target="_self">'
            '<span class="hbi-home-directory-icon"><img class="hbi-home-clean-image" '
            f'src="{_HBI_COMMUNITY_SRC}" alt="HBI Community" '
            'style="width:140px;height:140px;"></span>'
            '<strong>HBI Community</strong>'
            '<span class="hbi-home-directory-description">Discover collaborators, alumni, and our wider community.</span>'
            '<span class="hbi-home-directory-action">Browse community →</span></a>',
            unsafe_allow_html=True,
        )
