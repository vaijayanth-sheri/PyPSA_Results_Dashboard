# components/comparison_tab.py

import streamlit as st
import pypsa
import pandas as pd
import numpy as np
import plotly.express as px
import io

from .data_loader import render_comparison_file_uploader
from .utils import _get_network_kpis, get_pypsa_component_dfs, _get_available_ts_variables_for_network

def render_comparison_tab():
    """
    Renders the Comparison tab content.
    This tab is independent of the main visualization network.
    """
    st.header("Compare Multiple PyPSA Runs")
    st.write("Upload 2-3 PyPSA `.nc` files to compare their key metrics side-by-side.")

    comparison_networks = render_comparison_file_uploader(uploader_key="comparison_networks_uploader")

    if comparison_networks:
        st.subheader("Loaded Networks for Comparison")
        num_loaded = len(comparison_networks)
        comp_cols = st.columns(min(num_loaded, 3)) if num_loaded > 0 else []

        comparison_kpis = {}
        for i, (filename, comp_net) in enumerate(list(comparison_networks.items())):
            if comp_net is not None:
                with comp_cols[i % len(comp_cols)]:
                    st.info(filename)
                    kpis_comp = _get_network_kpis(comp_net)
                    comparison_kpis[filename] = kpis_comp
                    st.write(f"Buses: {kpis_comp.get('num_buses', 'N/A')}")
                    st.write(f"Generators: {kpis_comp.get('num_generators', 'N/A')}")
                    st.write(f"Snapshots: {kpis_comp.get('num_snapshots', 'N/A')}")
                    st.write(f"Total Gen Capacity: {kpis_comp.get('total_p_nom_generators', 0):,.0f} MW")
                    if st.button(f"Unload {filename}", key=f"unload_{filename}"):
                        del st.session_state.comparison_networks[filename]
                        st.experimental_rerun()
            else: # Handle failed load
                with comp_cols[i % len(comp_cols)]:
                    st.error(f"Failed to load {filename}")
                    if st.button(f"Remove", key=f"remove_{filename}"):
                        del st.session_state.comparison_networks[filename]
                        st.experimental_rerun()
        
        if len(comparison_kpis) > 1:
            st.subheader("Comparison Table: Key Metrics")
            metrics_to_show = ['total_system_cost', 'total_p_nom_generators', 'total_annual_generation_mwh']
            metric_names = {
                'total_system_cost': 'Total System Cost',
                'total_p_nom_generators': 'Total Installed Gen. Capacity (MW)',
                'total_annual_generation_mwh': 'Total Generation (MWh)',
            }
            kpi_data = {metric_names[metric]: [comparison_kpis[fname].get(metric, np.nan) for fname in comparison_kpis] for metric in metrics_to_show}
            kpi_df = pd.DataFrame(kpi_data, index=comparison_kpis.keys()).T
            st.dataframe(kpi_df.style.format("{:,.0f}", na_rep="N/A"))

            st.subheader("Delta Visualizations")
            cost_series = kpi_df.loc['Total System Cost']
            if not cost_series.isnull().all() and len(cost_series) > 1:
                base_cost = cost_series.iloc[0]
                delta_costs = (cost_series - base_cost)
                fig_delta = px.bar(delta_costs, title='Delta Total System Cost (vs. First Scenario)', labels={"value": 'Cost Difference'})
                st.plotly_chart(fig_delta, use_container_width=True)

            st.markdown("---")
            st.subheader("Plot Comparison")
            st.write("Generate custom time-series plots for comparing networks.")

            selected_networks_for_plot = st.multiselect(
                "Select Networks to Plot",
                options=list(comparison_networks.keys()),
                default=list(comparison_networks.keys())[:min(2, len(comparison_networks))]
            )

            if not selected_networks_for_plot:
                st.info("Please select at least one network to plot.")
                return

            all_available_components = {}
            for net_name in selected_networks_for_plot:
                net_obj = comparison_networks[net_name]
                if net_obj:
                    # No need for hash, just pass network directly to discovery func
                    components_for_net = _get_available_ts_variables_for_network(net_obj)
                    for comp_type, vars_list in components_for_net.items():
                        if comp_type not in all_available_components:
                            all_available_components[comp_type] = set()
                        all_available_components[comp_type].update(vars_list)
            
            common_component_types = sorted(list(all_available_components.keys()))

            if not common_component_types:
                st.warning("No common time-series data found across selected networks for plotting.")
                return

            c1_plot, c2_plot = st.columns(2)
            with c1_plot:
                selected_comp_plot = st.selectbox("1. Select Component Type", options=common_component_types, key="comp_plot_compare")
            with c2_plot:
                common_vars_for_comp = sorted(list(all_available_components.get(selected_comp_plot, [])))
                if not common_vars_for_comp:
                    st.warning(f"No common time-series variables for {selected_comp_plot} across selected networks.")
                    return
                selected_var_plot = st.selectbox("2. Select Variable", options=common_vars_for_comp, key="var_plot_compare")
            
            agg_options = ["Per Component", "Total Sum"]
            has_carrier_info = False
            for net_name in selected_networks_for_plot:
                net_obj = comparison_networks[net_name]
                if net_obj:
                    static_df_comp = get_pypsa_component_dfs(net_obj, selected_comp_plot, time_series=False)
                    if 'carrier' in static_df_comp.columns and not static_df_comp['carrier'].empty:
                        has_carrier_info = True
                        break
            if has_carrier_info:
                agg_options.append("Group by Carrier")
            
            selected_agg_plot = st.radio("3. Select Aggregation Mode", options=agg_options, horizontal=True, key="agg_plot_compare")

            all_component_ids = set()
            if selected_agg_plot == "Per Component":
                for net_name in selected_networks_for_plot:
                    net_obj = comparison_networks[net_name]
                    if net_obj:
                        df_comp_var = get_pypsa_component_dfs(net_obj, selected_comp_plot, time_series=True, target_attribute=selected_var_plot)
                        if not df_comp_var.empty:
                            all_component_ids.update(df_comp_var.columns.unique())
            
            subset_options_plot = sorted(list(all_component_ids))
            selected_subset_plot = tuple()
            if subset_options_plot:
                selected_subset_plot = st.multiselect("4. Filter Components (optional)", options=subset_options_plot,
                                                     help="Select specific component IDs to display. Leave blank to show all matching IDs across networks.", key="subset_plot_compare")
                selected_subset_plot = tuple(sorted(selected_subset_plot))

            selected_freq_plot = st.selectbox("5. Select Time Resolution", options=["Original", "Hourly", "Daily", "Monthly"], key="freq_plot_compare")

            if st.button("Generate Comparison Plot", key="generate_comp_plot_btn"):
                plot_data_frames = []
                errors_encountered = []

                for net_name in selected_networks_for_plot:
                    net_obj = comparison_networks[net_name]
                    if net_obj:
                        df_raw_for_net = get_pypsa_component_dfs(net_obj, selected_comp_plot, time_series=True, target_attribute=selected_var_plot)
                        
                        if df_raw_for_net.empty:
                            errors_encountered.append(f"No data for '{selected_comp_plot}.{selected_var_plot}' in network '{net_name}'.")
                            continue
                        
                        df_instantaneous = df_raw_for_net.diff().fillna(0)
                        
                        if selected_subset_plot:
                            df_instantaneous = df_instantaneous[[col for col in selected_subset_plot if col in df_instantaneous.columns]]
                            if df_instantaneous.empty:
                                errors_encountered.append(f"No data for selected subset '{selected_subset_plot}' in network '{net_name}'.")
                                continue

                        processed_df = pd.DataFrame()
                        if selected_agg_plot == "Per Component":
                            processed_df = df_instantaneous
                        elif selected_agg_plot == "Total Sum":
                            processed_df[f"Total {selected_var_plot}"] = df_instantaneous.sum(axis=1)
                        elif selected_agg_plot == "Group by Carrier":
                            static_df_for_group = get_pypsa_component_dfs(net_obj, selected_comp_plot, time_series=False)
                            if 'carrier' not in static_df_for_group.columns:
                                errors_encountered.append(f"Cannot group by carrier: '{selected_comp_plot}' components in network '{net_name}' do not have a 'carrier' attribute.")
                                continue
                            carrier_map_for_group = static_df_for_group.carrier[static_df_for_group.index.isin(df_instantaneous.columns)]
                            if carrier_map_for_group.empty:
                                errors_encountered.append(f"No components with 'carrier' info found for grouping in network '{net_name}'.")
                                continue
                            processed_df = df_instantaneous.groupby(carrier_map_for_group, axis=1).sum()
                            carriers_to_plot = processed_df.columns[processed_df.abs().sum() > 1e-6]
                            processed_df = processed_df[carriers_to_plot]
                            if processed_df.empty:
                                errors_encountered.append(f"No significant generation for any carrier after processing instantaneous values in network '{net_name}'.")
                                continue

                        if selected_freq_plot != "Original":
                            if not isinstance(processed_df.index, pd.DatetimeIndex):
                                errors_encountered.append(f"Data index for network '{net_name}' is not datetime, cannot resample.")
                                continue
                            freq_map = {"Hourly": "H", "Daily": "D", "Monthly": "M"}
                            resample_freq = freq_map.get(selected_freq_plot)
                            if resample_freq:
                                processed_df = processed_df.resample(resample_freq).mean()
                        
                        processed_df.columns = [f"{net_name}: {col}" for col in processed_df.columns]
                        plot_data_frames.append(processed_df)
                    else:
                        errors_encountered.append(f"Network '{net_name}' object is None (failed to load).")

                if errors_encountered:
                    for err in errors_encountered:
                        st.warning(err)

                if plot_data_frames:
                    combined_df = pd.concat(plot_data_frames, axis=1, join='outer')
                    combined_df = combined_df.sort_index()
                    
                    if combined_df.empty or combined_df.isnull().all().all():
                        st.warning("Combined data is empty or all NaN after processing. Cannot generate plot.")
                        return

                    # --- FIX: Removed hover_name argument ---
                    if selected_agg_plot == "Group by Carrier":
                        fig_comp = px.area(combined_df, title=f"Comparison of {selected_var_plot} ({selected_agg_plot}) by Carrier",
                                           labels={"value": f"Power ({selected_var_plot})", "index": "Time"})
                    else:
                        fig_comp = px.line(combined_df, title=f"Comparison of {selected_var_plot} ({selected_agg_plot})",
                                           labels={"value": f"Power ({selected_var_plot})", "index": "Time"})

                    fig_comp.update_layout(xaxis_title="Snapshot", yaxis_title=f"Power ({selected_var_plot})")
                    st.plotly_chart(fig_comp, use_container_width=True)
                    
                    st.markdown("#### Comparison Plot Data Export")
                    csv_bytes = combined_df.to_csv().encode('utf-8')
                    st.download_button(
                        label="📥 Download Plot Data (CSV)",
                        data=csv_bytes,
                        file_name=f"comparison_plot_data_{selected_comp_plot}_{selected_var_plot}.csv",
                        mime="text/csv",
                    )

                else:
                    st.info("No data available to generate a comparison plot for the selected networks/options.")
            else:
                st.info("Make your selections and click 'Generate Comparison Plot' to visualize.")

        elif len(st.session_state.comparison_networks) == 1:
            st.info("Upload at least one more file to enable comparison features.")
    else:
        st.info("No networks loaded for comparison.")