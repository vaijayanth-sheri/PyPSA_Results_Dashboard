# components/overview_tab.py

import streamlit as st
import pypsa
import pandas as pd
import plotly.express as px
import io

from .utils import _get_network_kpis, get_pypsa_component_dfs
from .pdf_report import generate_pdf_report
from .constants import (
    MISSING_LOAD_DATA_MESSAGE, MISSING_GENERATION_DATA_MESSAGE,
    NO_SNAPSHOTS_WARNING
)

def render_overview_tab(network: pypsa.Network):
    """
    Renders the Overview tab content.
    """
    st.header("Overview")
    st.write("This tab provides a summary of the loaded PyPSA network and key performance indicators.")

    kpis = _get_network_kpis(network)

    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Number of Buses", kpis.get('num_buses', 'N/A'))
        st.metric("Number of Lines", kpis.get('num_lines', 'N/A'))
        st.metric("Total Gen Capacity (p_nom)", f"{kpis.get('total_p_nom_generators', 0):,.0f} MW" if kpis.get('total_p_nom_generators', 0) > 0 else "N/A")
    with col2:
        st.metric("Number of Generators", kpis.get('num_generators', 'N/A'))
        st.metric("Number of Storage Units", kpis.get('num_storage_units', 'N/A'))
        st.metric("Total Storage Capacity (p_nom)", f"{kpis.get('total_p_nom_storage', 0):,.0f} MW" if kpis.get('total_p_nom_storage', 0) > 0 else "N/A")
    with col3:
        st.metric("Number of Snapshots", kpis.get('num_snapshots', 'N/A'))
        st.metric("Total Generation", f"{kpis.get('total_annual_generation_mwh', 0):,.0f} MWh" if kpis.get('total_annual_generation_mwh', 0) > 0 else "N/A")
        total_cost = kpis.get('total_system_cost', 'N/A')
        st.metric("Total System Cost", f"{total_cost:,.0f}" if isinstance(total_cost, (int, float)) and not pd.isna(total_cost) else "N/A")

    st.subheader("Load vs. Generation Curve")
    if kpis.get('num_snapshots', 0) == 0:
        st.warning(NO_SNAPSHOTS_WARNING)
    else:
        loads_t_p = get_pypsa_component_dfs(network, "Load", time_series=True, target_attribute='p')
        generators_t_p = get_pypsa_component_dfs(network, "Generator", time_series=True, target_attribute='p')

        if not loads_t_p.empty and not generators_t_p.empty:
            instantaneous_load = loads_t_p.diff().fillna(0).sum(axis=1)
            instantaneous_generation = generators_t_p.diff().fillna(0).sum(axis=1)

            df_plot = pd.DataFrame({
                'Load': instantaneous_load,
                'Generation': instantaneous_generation
            })

            fig = px.line(df_plot, title='System Load vs. Total Generation',
                          labels={"value": "Power (MW/MWh)", "index": "Time"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            if loads_t_p.empty:
                st.warning(MISSING_LOAD_DATA_MESSAGE)
            if generators_t_p.empty:
                st.warning(MISSING_GENERATION_DATA_MESSAGE)
            if loads_t_p.empty or generators_t_p.empty:
                st.warning("One of Load or Generation data is missing, so cannot plot Load vs. Generation.")

    st.subheader("Generation by Carrier (Stacked Area)")
    if kpis.get('num_snapshots', 0) == 0:
        st.warning(NO_SNAPSHOTS_WARNING)
    else:
        generators_t_p_all = get_pypsa_component_dfs(network, "Generator", time_series=True, target_attribute='p')
        generators_static_df = get_pypsa_component_dfs(network, "Generator", time_series=False)

        if not generators_t_p_all.empty and not generators_static_df.empty and 'carrier' in generators_static_df.columns:
            
            existing_generators_in_ts = generators_t_p_all.columns.unique()
            filtered_generators_static = generators_static_df[generators_static_df.index.isin(existing_generators_in_ts)]

            if not filtered_generators_static.empty and 'carrier' in filtered_generators_static.columns:
                instantaneous_generators_t_p = generators_t_p_all.diff().fillna(0)
                
                carrier_map = filtered_generators_static.carrier[filtered_generators_static.index.isin(instantaneous_generators_t_p.columns)]
                
                if carrier_map.empty:
                    st.info("No active generators with carrier information to group by after filtering.")
                    return

                gen_by_carrier = instantaneous_generators_t_p.groupby(carrier_map, axis=1).sum()
                
                # --- FIX: Filter out carriers that are entirely zero across all time steps ---
                # This ensures that Plotly doesn't draw outlines for non-contributing carriers.
                # Only keep columns where the sum of absolute values is greater than a small epsilon
                carriers_to_plot = gen_by_carrier.columns[gen_by_carrier.abs().sum() > 1e-6]
                
                gen_by_carrier_active = gen_by_carrier[carriers_to_plot]
                
                if not gen_by_carrier_active.empty:
                    fig_carrier = px.area(gen_by_carrier_active, title='Total Generation by Carrier',
                                          labels={"value": "Power (MW/MWh)", "index": "Time"})
                    st.plotly_chart(fig_carrier, use_container_width=True)
                else:
                    st.info("No significant generation found for any carrier after processing instantaneous values.")
            else:
                st.warning("Generator carrier information is missing or does not align with active generators in time-series data.")
        else:
            st.warning("Generation time-series data or static generator carrier information is missing.")

    st.markdown("---")
    st.subheader("Report Export")
    if st.button("Generate PDF Report", key="overview_pdf_export_btn"):
        with st.spinner("Generating PDF report..."):
            pdf_bytes = generate_pdf_report(network)
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name="pypsa_dashboard_report.pdf",
                mime="application/pdf"
            )
        st.success("PDF report generated!")