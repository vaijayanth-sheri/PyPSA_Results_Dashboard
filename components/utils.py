# components/utils.py

import pypsa
import pandas as pd
import numpy as np
import streamlit as st


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
        instantaneous_generation = generators_t_p.diff().fillna(0).clip(lower=0)
        total_generation = instantaneous_generation.sum().sum()

    kpis['total_annual_generation_mwh'] = total_generation
    
    raw_system_cost = network.objective if hasattr(network, 'objective') else np.nan
    
    kpis['system_cost_was_negative'] = False
    if isinstance(raw_system_cost, (int, float)) and not pd.isna(raw_system_cost):
        if raw_system_cost < 0:
            kpis['system_cost_was_negative'] = True
            kpis['total_system_cost'] = 0 # Clip negative costs to 0 for display
        else:
            kpis['total_system_cost'] = raw_system_cost
    else:
        kpis['total_system_cost'] = np.nan # Keep as NaN if not a valid number

    return kpis


def get_pypsa_component_dfs(network: pypsa.Network, component_type: str, time_series: bool = True, target_attribute: str = None) -> pd.DataFrame:
    """
    Retrieves the DataFrame for a given PyPSA component type.
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

    df = pd.DataFrame()
    
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
        else:
            if hasattr(pypsa_obj, 'p') and isinstance(pypsa_obj.p, pd.DataFrame):
                df = pypsa_obj.p
            elif hasattr(pypsa_obj, 'df') and isinstance(pypsa_obj.df, pd.DataFrame):
                df = pypsa_obj.df
            else:
                try:
                    df = pd.DataFrame(pypsa_obj)
                except Exception:
                    df = pd.DataFrame()

    else:
        if isinstance(pypsa_obj, pd.DataFrame):
            df = pypsa_obj
        else:
            try:
                df = pd.DataFrame(pypsa_obj)
            except Exception:
                df = pd.DataFrame()

    if time_series and not df.empty:
        if not isinstance(df.index, pd.DatetimeIndex):
            return pd.DataFrame()
        if df.columns.empty and df.index.empty:
            return pd.DataFrame()
    elif time_series and df.empty:
        return pd.DataFrame()

    return df


@st.cache_data
def _get_available_ts_variables_for_network(_network: pypsa.Network) -> dict: # <--- FIX: Changed network to _network
    """
    Introspects a single network to find components with time-series data and their variables.
    """
    available = {}
    component_names = ["Generator", "Load", "Line", "StorageUnit", "Bus"]
    common_ts_variables = ['p', 'q', 'state_of_charge', 'p0', 'p1', 'marginal_price']

    for comp in component_names:
        found_variables = []
        pypsa_t_obj = getattr(_network, f"{comp.lower()}s_t", None) # <--- Use _network
        
        if pypsa_t_obj is not None:
            for var in common_ts_variables:
                df_for_var = get_pypsa_component_dfs(_network, comp, time_series=True, target_attribute=var) # <--- Use _network
                
                if not df_for_var.empty and isinstance(df_for_var.index, pd.DatetimeIndex):
                    found_variables.append(var)
        
        if found_variables:
            available[comp] = sorted(list(set(found_variables)))

    return available

@st.cache_data
def _calculate_carrier_marginal_costs(_network_hash: str, _network: pypsa.Network) -> pd.Series:
    """
    Calculates the total marginal cost for each generator carrier in a network.
    Assumes generators_t.p is already instantaneous power (or converted via diff).
    """
    marginal_costs_series = pd.Series(dtype=float)
    if not _network.generators.empty and 'carrier' in _network.generators.columns and \
       'marginal_cost' in _network.generators.columns:
        
        generators_t_p = get_pypsa_component_dfs(_network, "Generator", time_series=True, target_attribute='p')
        if generators_t_p.empty:
            return pd.Series(dtype=float)

        instantaneous_generators_t_p = generators_t_p.diff().fillna(0).clip(lower=0)

        generating_generators = instantaneous_generators_t_p.columns[instantaneous_generators_t_p.abs().sum() > 1e-6]
        
        if not generating_generators.empty:
            generator_info = _network.generators.loc[generating_generators, ['carrier', 'marginal_cost']]
            
            costs_per_generator_t = instantaneous_generators_t_p[generating_generators] * generator_info['marginal_cost']
            
            marginal_costs_series = costs_per_generator_t.groupby(generator_info['carrier'], axis=1).sum().sum()
            marginal_costs_series = marginal_costs_series.clip(lower=0)

    return marginal_costs_series