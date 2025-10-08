# components/plots_metrics_tab.py

import streamlit as st
import pypsa
import pandas as pd
import plotly.express as px
import io

from .utils import get_pypsa_component_dfs, _get_available_ts_variables_for_network
from .constants import NO_SNAPSHOTS_WARNING

# Helper to check if a Series is likely cumulative (predominantly non-decreasing, non-negative)
def is_likely_cumulative(series: pd.Series) -> bool:
    if series.empty:
        return False
    if (series < 0).sum() / len(series) > 0.1:
        return False
    diffs = series.diff().dropna()
    if diffs.empty:
        return False
    return (diffs >= 0).sum() / len(diffs) > 0.9


@st.cache_data
def discover_timeseries_components(_network_hash: str, _network: pypsa.Network) -> dict:
    """
    Introspects the network to find components with time-series data and their variables.
    """
    # This calls _get_available_ts_variables_for_network from utils.py
    return _get_available_ts_variables_for_network(_network)


@st.cache_data
def process_and_plot_data(_network_hash: str, _network: pypsa.Network, component_type: str, variable: str,
                          subset: tuple, aggregation: str, frequency: str, apply_diff: bool):
    """
    The core function to fetch, transform, and plot the data.
    """
    if not component_type or not variable:
        return None, None, "Please select a component and a variable."

    df_raw_for_plot = get_pypsa_component_dfs(_network, component_type, time_series=True, target_attribute=variable)
    
    if df_raw_for_plot.empty:
        return None, None, f"Time-series data for variable '{variable}' not found or is empty for component '{component_type}'."

    df = df_raw_for_plot.copy()

    if apply_diff:
        df = df.diff().fillna(0)
    
    # In Plots & Metrics, we let user decide if .diff() is applied.
    # We generally don't clip here as negative values (e.g., storage discharge)
    # might be valid raw data that the user wants to inspect.
    if df.sum().sum() == 0 and df.shape[1] > 0:
         return pd.DataFrame(), None, "Data seems to be all zeros or constant. Check source data or 'Apply .diff()' option."


    if subset:
        valid_subset = [item for item in subset if item in df.columns]
        if not valid_subset:
            return None, None, "Selected subset is not available in the data."
        df = df[valid_subset]
    
    plot_title = f"{variable} for {component_type}"
    plot_df = pd.DataFrame()

    if aggregation == "Per Component":
        if df.shape[1] > 50:
            st.warning(f"Displaying over 50 individual components. The plot may be cluttered.")
        plot_df = df
    elif aggregation == "Total Sum":
        plot_df[f"Total {variable}"] = df.sum(axis=1)
    elif aggregation == "Group by Carrier":
        static_df = get_pypsa_component_dfs(_network, component_type, time_series=False)
        if 'carrier' not in static_df.columns:
            return None, None, f"Cannot group by carrier: '{component_type}' components do not have a 'carrier' attribute."
        
        carrier_map = static_df['carrier']
        filtered_carrier_map = carrier_map[carrier_map.index.isin(df.columns)]

        if filtered_carrier_map.empty:
            return None, None, f"No components with 'carrier' attribute found in the filtered data for {component_type}."

        plot_df = df.groupby(filtered_carrier_map, axis=1).sum()
        plot_title = f"Sum of {variable} by Carrier"

        carriers_to_plot = plot_df.columns[plot_df.abs().sum() > 1e-6]
        plot_df = plot_df[carriers_to_plot]

    if frequency != "Original":
        if not isinstance(plot_df.index, pd.DatetimeIndex):
            return None, None, "Data index is not datetime, cannot resample. Ensure your time-series has a proper DatetimeIndex."
        freq_map = {"Hourly": "H", "Daily": "D", "Monthly": "M"}
        resample_freq = freq_map.get(frequency)
        if resample_freq:
            plot_df = plot_df.resample(resample_freq).mean()
            plot_title += f" ({frequency} Average)"

    if plot_df.empty or plot_df.isnull().all().all():
        return plot_df, None, "No data available for the selected options."
    
    fig = px.area(plot_df, title=plot_title, labels={"value": variable}) if aggregation == "Group by Carrier" else px.line(plot_df, title=plot_title, labels={"value": variable})
    fig.update_layout(xaxis_title="Snapshot", legend_title_text=component_type if aggregation != "Group by Carrier" else "Carrier")
    
    return plot_df, fig, None

def render_plots_metrics_tab(network: pypsa.Network):
    """
    Renders the Plots & Metrics tab.
    """
    st.header("Plots & Metrics")
    st.write("Explore detailed time-series data for various network components.")

    try:
        network_hash = pd.util.hash_pandas_object(network.buses, index=True).sum()
    except Exception:
        network_hash = hash(network.name if hasattr(network, 'name') else id(network))

    available_components = discover_timeseries_components(network_hash, network)

    if not available_components:
        st.warning(NO_SNAPSHOTS_WARNING + " (No time-series data found after introspection).")
        st.info("Ensure your `.nc` file was exported with time-series data for generators, loads, lines, storage units, or buses.")
        return

    st.markdown("#### Plot Configuration")
    c1, c2 = st.columns(2)
    with c1:
        selected_comp = st.selectbox("1. Select Component Type", options=list(available_components.keys()))
    with c2:
        var_options = available_components.get(selected_comp, [])
        if not var_options:
            st.warning(f"No time-series variables found for {selected_comp}.")
            return
        selected_var = st.selectbox("2. Select Variable", options=var_options)

    agg_options = ["Per Component", "Total Sum"]
    if 'carrier' in get_pypsa_component_dfs(network, selected_comp, False).columns:
        agg_options.append("Group by Carrier")
    selected_agg = st.radio("3. Select Aggregation Mode", options=agg_options, horizontal=True)

    subset_options = []
    if selected_agg == "Per Component":
        component_variable_df = get_pypsa_component_dfs(network, selected_comp, time_series=True, target_attribute=selected_var)
        if not component_variable_df.empty:
            subset_options = sorted(list(component_variable_df.columns.unique()))
    
    selected_subset = tuple()
    if subset_options:
        selected_subset = st.multiselect("4. Filter Components (optional)", options=subset_options)
    
    selected_freq = st.selectbox("5. Select Time Resolution", options=["Original", "Hourly", "Daily", "Monthly"])

    # --- New Toggle for .diff() ---
    apply_diff_option = False
    # Only offer this option for power/flow-like variables which might be cumulative
    if selected_var in ['p', 'q', 'p0', 'p1']:
        st.info("Raw data for power/flow variables may be cumulative. Use the toggle below for instantaneous values.")
        apply_diff_option = st.checkbox("Apply `.diff().fillna(0)` for instantaneous values", value=True,
                                        help="Converts cumulative power/flow data to instantaneous values per time interval. Disable if your data is already instantaneous or represents state values (e.g., SOC).")
    else:
        st.info("`.diff()` option not typically applicable to this variable type (e.g., marginal_price, SOC) and is disabled.")


    st.markdown("---")
    with st.spinner("Processing data and generating plot..."):
        subset_tuple = tuple(sorted(selected_subset))

        final_df, fig, error_message = process_and_plot_data(
            network_hash, network, selected_comp, selected_var,
            subset_tuple, selected_agg, selected_freq, apply_diff_option # Pass new argument
        )

        if error_message:
            st.warning(error_message)
        elif fig:
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Data Summary & Export")
            if not final_df.empty:
                st.dataframe(final_df.describe().T.style.format("{:,.2f}"))

                csv_bytes = final_df.to_csv().encode('utf-8')
                
                st.download_button(
                    label="📥 Download Data (CSV)",
                    data=csv_bytes,
                    file_name=f"{selected_comp}_{selected_var}_data.csv",
                    mime="text/csv",
                )
            else:
                st.info("No data to summarize or export.")
        else:
            st.info("No data to display for the selected options.")