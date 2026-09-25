"""Temporary KPI and selected-recognition profile design explorations."""

import streamlit as st

from utils.page_config import BLANK_PAGE_ICON
from utils.profile_summary_exploration import render_profile_summary_exploration
from utils.components import inject_custom_css, render_public_sidebar_navigation


st.set_page_config(
    page_title="Profile Summary Explorations – HBI",
    page_icon=BLANK_PAGE_ICON,
    layout="wide",
)
inject_custom_css()
render_public_sidebar_navigation()

try:
    approach = int(st.query_params.get("approach", "1"))
except (TypeError, ValueError):
    approach = 1

render_profile_summary_exploration(approach)
