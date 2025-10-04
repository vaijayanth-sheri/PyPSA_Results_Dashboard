# components/constants.py

# --- File Handling & UI ---
MAX_FILE_SIZE_MB = 500
FILE_SIZE_WARNING_MESSAGE = (
    f"Your file is >{MAX_FILE_SIZE_MB} MB. Visualizations might be slow. "
    "Consider exporting fewer snapshots or aggregating to hourly."
)
PYPSA_LOAD_ERROR_MESSAGE = (
    "Failed to load PyPSA network. This might not be a valid PyPSA .nc file, "
    "or its schema is unsupported by the current PyPSA version. "
    "Please check the file content and PyPSA compatibility. "
    "See detailed error message for more information."
)

# --- Tab Specific Messages ---
MISSING_COORDINATES_MESSAGE = "No bus coordinates detected. Map view is disabled."
MISSING_PLOT_VARIABLES_MESSAGE = (
    "Selected metric isn’t present in this file. Re-export your run with time-series outputs enabled."
)
MISSING_LOAD_DATA_MESSAGE = (
    "Load data (network.loads_t.p) is missing or empty. "
    "Re-export your run with time-series outputs for loads enabled."
)
MISSING_GENERATION_DATA_MESSAGE = (
    "Generation data (network.generators_t.p) is missing or empty. "
    "Re-export your run with time-series outputs for generators enabled."
)
NO_SNAPSHOTS_WARNING = (
    "No time-series data (snapshots) found in the network. "
    "This tab will have limited functionality."
)