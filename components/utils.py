# components/utils.py

import pypsa
import pandas as pd
import numpy as np
# Removed streamlit import as no more debugging prints in this file

def _get_network_kpis(network: pypsa.Network) -> dict:
    """Calculates a set of KPIs for the network based only on data present in the file."""
    kpis = {}

    kpis['num_buses'] = len(network.buses)
    kpis['num_lines'] = len(network.lines)
    kpis['num_generators'] = len(network.generators)
    kpis['num_storage_units'] = len(network.storage_units)
    kpis['num_snapshots'] = len(network.snapshots) if hasattr(network, 'snapshots') and network.snapshots is not None else 0

    kpis['total_p_nom_generators'] = network.generators['p_nom'].sum() if not network.generators.empty and 'p_nom' in network.generators.columns else 0
    kpis['total_p_nom_storage'] = network.storage_units['p_nom'].sum() if not network.storage_units.empty and 'p_nom' in network.storage_units.columns else 0

    total_generation = 0
    generators_t_p = get_pypsa_component_dfs(network, "Generator", time_series=True, target_attribute='p')
    if generators_t_p is not None and not generators_t_p.empty:
        instantaneous_generation = generators_t_p.diff().fillna(0) # Apply diff for KPIs
        total_generation = instantaneous_generation.sum().sum()

    kpis['total_annual_generation_mwh'] = total_generation
    
    kpis['total_system_cost'] = network.objective if hasattr(network, 'objective') else np.nan

    return kpis


def get_pypsa_component_dfs(network: pypsa.Network, component_type: str, time_series: bool = True, target_attribute: str = None) -> pd.DataFrame:
    """
    Retrieves the DataFrame for a given PyPSA component type.
    This function handles how PyPSA stores DataFrames within its component objects
    and ensures it always returns a standard pandas.DataFrame.
    
    If `target_attribute` is provided (e.g., 'p', 'state_of_charge'), it tries to return
    that specific time-series DataFrame directly.
    """
    component_to_attribute_map = {
        "Generator": "generators",
        "Load": "loads",
        "Line": "lines",
        "Bus": "buses",
        "StorageUnit": "storage_units"
    }
    
    base_attr = component_to_attribute_map.get(component_type)
    if not base_attr:
        return pd.DataFrame()

    pypsa_attr_name = f"{base_attr}_t" if time_series else base_attr
    
    pypsa_obj = getattr(network, pypsa_attr_name, None)
    
    if pypsa_obj is None:
        return pd.DataFrame()

    df = pd.DataFrame() # Initialize an empty DataFrame
    
    if time_series:
        if target_attribute:
            attr_df = getattr(pypsa_obj, target_attribute, None)
            if isinstance(attr_df, pd.DataFrame):
                df = attr_df
            else:
                try:
                    df = pd.DataFrame(attr_df) if attr_df is not None else pd.DataFrame()
                except Exception:
                    df = pd.DataFrame()
        else: # For discovery, without a specific target_attribute, try common ones
            if hasattr(pypsa_obj, 'p') and isinstance(pypsa_obj.p, pd.DataFrame):
                df = pypsa_obj.p
            elif hasattr(pypsa_obj, 'df') and isinstance(pypsa_obj.df, pd.DataFrame): # Fallback some objects use .df
                df = pypsa_obj.df
            else:
                try:
                    df = pd.DataFrame(pypsa_obj)
                except Exception:
                    df = pd.DataFrame()

    else: # Static components
        if isinstance(pypsa_obj, pd.DataFrame):
            df = pypsa_obj
        else:
            try:
                df = pd.DataFrame(pypsa_obj)
            except Exception:
                df = pd.DataFrame()

    # Final validation for time-series data:
    if time_series and not df.empty:
        if not isinstance(df.index, pd.DatetimeIndex):
            return pd.DataFrame()
        if df.columns.empty and df.index.empty:
            return pd.DataFrame()
    elif time_series and df.empty:
        return pd.DataFrame()

    return df

def _get_available_ts_variables_for_network(network: pypsa.Network) -> dict:
    """
    Introspects a single network to find components with time-series data and their variables.
    Returns a dictionary mapping component names to a list of their variables.
    """
    available = {}
    component_names = ["Generator", "Load", "Line", "StorageUnit", "Bus"]
    common_ts_variables = ['p', 'q', 'state_of_charge', 'p0', 'p1', 'marginal_price']

    for comp in component_names:
        found_variables = []
        pypsa_t_obj = getattr(network, f"{comp.lower()}s_t", None)
        
        if pypsa_t_obj is not None:
            for var in common_ts_variables:
                df_for_var = get_pypsa_component_dfs(network, comp, time_series=True, target_attribute=var)
                
                if not df_for_var.empty and isinstance(df_for_var.index, pd.DatetimeIndex):
                    found_variables.append(var)
        
        if found_variables:
            available[comp] = sorted(list(set(found_variables)))

    return available
