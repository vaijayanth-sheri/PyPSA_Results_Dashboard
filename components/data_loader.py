# components/data_loader.py

import streamlit as st
import pypsa
import pandas as pd
import io
import tempfile
import os
from .constants import (
    MAX_FILE_SIZE_MB, FILE_SIZE_WARNING_MESSAGE,
    PYPSA_LOAD_ERROR_MESSAGE
)

@st.cache_resource
def load_pypsa_network(file_content: bytes, file_hash: str) -> pypsa.Network:
    """
    Loads a PyPSA network from file content by writing it to a temporary file.
    Caches the network object.
    """
    temp_file_path = None
    st.session_state.file_error = False # Reset error state for this load attempt
    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        n = pypsa.Network(temp_file_path)
        return n
    except Exception as e:
        st.error(f"{PYPSA_LOAD_ERROR_MESSAGE}\nDetailed error: {e}")
        st.session_state.file_error = True
        return None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def render_file_uploader(uploader_key: str = "main_file_uploader") -> pypsa.Network:
    """
    Renders the file uploader and handles loading.
    Returns the loaded PyPSA network object or None.
    """
    uploaded_file = st.file_uploader(
        "Drag and drop your .nc results file here, or click to browse",
        type="nc",
        key=uploader_key
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue()
        file_size_mb = len(file_content) / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            st.warning(FILE_SIZE_WARNING_MESSAGE)

        file_hash = uploaded_file.file_id
        
        network = load_pypsa_network(file_content, file_hash)

        if network:
            st.success("File loaded successfully!")
        
        return network
    else:
        st.info("Please upload a PyPSA `.nc` file to begin.")
        return None

def render_comparison_file_uploader(uploader_key: str = "comparison_file_uploader") -> dict[str, pypsa.Network]:
    """
    Renders a multi-file uploader for the comparison tab.
    Returns a dictionary of loaded PyPSA network objects.
    """
    uploaded_files = st.file_uploader(
        "Upload 2-3 PyPSA .nc files for comparison",
        type="nc",
        accept_multiple_files=True,
        key=uploader_key
    )

    loaded_networks = st.session_state.get('comparison_networks', {})
    
    if uploaded_files:
        for uf in uploaded_files:
            if uf.name not in loaded_networks:
                file_content = uf.getvalue()
                file_hash = uf.file_id
                with st.spinner(f"Loading {uf.name}..."):
                    network_obj = load_pypsa_network(file_content, file_hash)
                if network_obj:
                    loaded_networks[uf.name] = network_obj

    st.session_state.comparison_networks = loaded_networks

    return st.session_state.comparison_networks