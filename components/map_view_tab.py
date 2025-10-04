# components/map_view_tab.py

import streamlit as st
import pypsa
import pandas as pd
import folium
from streamlit_folium import folium_static

from .constants import MISSING_COORDINATES_MESSAGE

def render_map_view_tab(network: pypsa.Network):
    """
    Renders a simple, view-only map of the PyPSA network.
    """
    st.header("Network Map View")
    st.write("A geographic visualization of the network components.")

    if network.buses.empty or "x" not in network.buses.columns or "y" not in network.buses.columns:
        st.warning(MISSING_COORDINATES_MESSAGE)
        return

    valid_buses = network.buses.copy()
    valid_buses['x'] = pd.to_numeric(valid_buses['x'], errors='coerce')
    valid_buses['y'] = pd.to_numeric(valid_buses['y'], errors='coerce')
    valid_buses = valid_buses.dropna(subset=['x', 'y'])

    if valid_buses.empty:
        st.warning(MISSING_COORDINATES_MESSAGE + " No valid numeric bus coordinates found.")
        return

    map_center_lat = valid_buses['y'].mean()
    map_center_lon = valid_buses['x'].mean()
    m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=6)

    for idx, bus in valid_buses.iterrows():
        folium.CircleMarker(
            location=[bus.y, bus.x], radius=5, color="blue", fill=True, fill_color="blue",
            tooltip=f"Bus: {idx}"
        ).add_to(m)

    if not network.lines.empty:
        for idx, line in network.lines.iterrows():
            try:
                bus0_coords = valid_buses.loc[line.bus0]
                bus1_coords = valid_buses.loc[line.bus1]
                folium.PolyLine(
                    locations=[[bus0_coords.y, bus0_coords.x], [bus1_coords.y, bus1_coords.x]],
                    color="grey", weight=2,
                    tooltip=f"Line: {idx}<br>Capacity: {line.get('s_nom', 'N/A'):.2f} MVA"
                ).add_to(m)
            except KeyError:
                pass

    if not network.generators.empty and "x" in network.generators.columns and "y" in network.generators.columns:
        gen_coords = network.generators.copy().dropna(subset=['x', 'y'])
        for idx, gen in gen_coords.iterrows():
            folium.Marker(
                location=[gen.y, gen.x], icon=folium.Icon(color="green", icon="fa-power-off", prefix='fa'),
                tooltip=f"Generator: {idx}<br>Carrier: {gen.get('carrier', 'N/A')}"
            ).add_to(m)
    
    if not network.storage_units.empty and "x" in network.storage_units.columns and "y" in network.storage_units.columns:
        sto_coords = network.storage_units.copy().dropna(subset=['x', 'y'])
        for idx, sto in sto_coords.iterrows():
            folium.Marker(
                location=[sto.y, sto.x], icon=folium.Icon(color="purple", icon="fa-battery-half", prefix='fa'),
                tooltip=f"Storage: {idx}<br>Carrier: {sto.get('carrier', 'N/A')}"
            ).add_to(m)

    folium_static(m, width=1100, height=700)