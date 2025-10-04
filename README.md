# ⚡ PyPSA Results Visualization Dashboard

This Streamlit application provides an interactive and user-friendly dashboard for visualizing results from PyPSA (Python for Power System Analysis) simulations. Users can upload their `.nc` result files and explore various aspects of their energy system models without needing to write any code.

## ✨ Features

*   **File Upload:** Securely upload PyPSA `.nc` result files. The app handles large files with warnings and robust loading.
*   **Modular Design:** Code is organized into components for maintainability and scalability.
*   **Results Visualization Tab:**
    *   **Overview:** Get a high-level summary of the network, including key metrics like number of buses, lines, generators, storage units, total generation, and system cost. Features plots for:
        *   System Load vs. Total Generation (instantaneous values).
        *   Generation by Carrier (stacked area chart, showing instantaneous contributions for all active carriers).
    *   **Network Map View:** Visualize the network topology on an interactive Folium map, displaying buses, lines, generators, and storage units based on their coordinates. Tooltips provide basic information on hover.
    *   **Plots & Metrics:** A customizable plotting interface allowing users to:
        *   Select component types (Generators, Loads, Lines, Storage Units, Buses).
        *   Choose specific time-series variables (e.g., `p` for power, `state_of_charge`, `marginal_price`).
        *   Apply aggregation modes (per-component, total sum, group by carrier).
        *   Resample data to different frequencies (hourly, daily, monthly).
        *   Filter individual components.
        *   Export the underlying plot data as CSV.
*   **Comparison Tab:**
    *   Upload multiple `.nc` files to compare different simulation scenarios side-by-side.
    *   View a table comparing key numerical metrics across all loaded networks.
    *   **Dynamic Plot Comparison:** Generate custom time-series plots comparing selected variables from multiple networks, with options for component type, variable, aggregation, and frequency.
    *   Unload individual comparison files.
*   **PDF Report Generation:** Generate a basic PDF report summarizing the network overview and key KPIs.
*   **Robust Error Handling:** Clear messages for invalid files, missing data, and environmental issues.

## 🚀 Getting Started

Follow these instructions to set up and run the dashboard locally.

### Prerequisites

*   Python 3.8+

### 1. Clone the Repository

```bash
git clone https://github.com/vaijayanth-sheri/PyPSA_Results_Dashboard.git 
cd PyPSA_Results_Dashboard
```

### 2. Create and Activate a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.
```
python -m venv venv
```
On Windows:
.\venv\Scripts\activate

On macOS/Linux:
source venv/bin/activate

### 3. Install Dependencies
Install all the required Python packages using pip:
```
pip install -r requirements.txt
```
### 4. Run the Streamlit Application
Once all dependencies are installed, you can launch the dashboard:
```
streamlit run app.py
```
This will open the application in your default web browser, usually at http://localhost:8501.

📂 Project Structure
```
pypsa_dashboard/
├── .gitignore             # Files ignored by Git
├── README.md              # This project's README file
├── app.py                 # Main Streamlit application entry point
├── requirements.txt       # Python dependencies
└── components/            # Directory for modular components
    ├── __init__.py        # Makes 'components' a Python package
    ├── comparison_tab.py  # Logic for the Comparison tab
    ├── constants.py       # Global constants and messages
    ├── data_loader.py     # File upload and PyPSA network loading
    ├── map_view_tab.py    # Logic for the Network Map View tab
    ├── overview_tab.py    # Logic for the Overview tab
    ├── pdf_report.py      # PDF generation using ReportLab
    └── utils.py           # Utility functions (KPIs, DataFrame extraction)
```

⚠️ Important Notes

Data Format: The dashboard expects PyPSA .nc result files. Ensure your PyPSA simulations export the necessary time-series data for full functionality.

Time-Series Data: Plots for load, generation, and other time-dependent variables will automatically apply a .diff().fillna(0) operation to convert potentially cumulative PyPSA outputs into instantaneous values for accurate visualization.

Map Coordinates: For the Map View to work, your PyPSA network's buses (and optionally generators, storage_units) must contain x and y coordinate columns.

🤝 Contributing: 
Feel free to fork this repository, open issues, or submit pull requests.
