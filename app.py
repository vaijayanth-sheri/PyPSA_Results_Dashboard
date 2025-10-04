# app.py

import streamlit as st
import pypsa
import pandas as pd

# Import all necessary components
from components.data_loader import render_file_uploader
from components.overview_tab import render_overview_tab
from components.map_view_tab import render_map_view_tab
from components.plots_metrics_tab import render_plots_metrics_tab
from components.comparison_tab import render_comparison_tab

# --- Streamlit Application ---
st.set_page_config(layout="wide", page_title="PyPSA Results Visualization Dashboard")

st.title("⚡ PyPSA Results Visualization Dashboard")
st.markdown(
    "Welcome to the PyPSA Results Visualization Dashboard. "
    "Use the tabs below to explore your simulation results."
)

# Initialize top-level session state variables
if 'main_network' not in st.session_state:
    st.session_state.main_network = None
if 'main_network_error' not in st.session_state:
    st.session_state.main_network_error = False
if 'comparison_networks' not in st.session_state:
    st.session_state.comparison_networks = {}


# --- Top-Level Tabs ---
results_tab, compare_tab = st.tabs(["📊 Results Visualization", "⚖️ Comparison"])

with results_tab:
    st.markdown("---")
    st.subheader("Upload PyPSA .nc File for Visualization")
    
    st.session_state.main_network = render_file_uploader(uploader_key="main_viz_uploader")
    
    if st.session_state.main_network is None and st.session_state.get('file_error', False):
        st.session_state.main_network_error = True
    else:
        st.session_state.main_network_error = False

    if st.session_state.main_network and not st.session_state.main_network_error:
        network = st.session_state.main_network

        st.markdown("---")
        # Sub-tabs for Results Visualization
        tab1, tab2, tab3 = st.tabs(["Overview", "Map View", "Plots & Metrics"])

        with tab1:
            render_overview_tab(network)
        with tab2:
            render_map_view_tab(network)
        with tab3:
            render_plots_metrics_tab(network)
    elif not st.session_state.main_network_error:
        st.info("Upload a .nc file above to enable the visualization tabs.")


with compare_tab:
    render_comparison_tab()