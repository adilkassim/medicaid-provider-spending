# medicaid-provider-spending

Analysis of Medicaid provider spending data using DuckDB and Polars, with optional HCPCS code enrichment and provider-level metrics.

## Project Structure

```
.
├── app.py                   # Streamlit home / landing page
├── config.py                # Shared config utility (reads/writes .medicaid_config.json)
├── pages/
│   ├── 00_Settings.py       # Configure all data file paths
│   ├── 01_Medicaid_Overview.py  # KPIs, yearly spend, top HCPCS codes
│   └── 02_US_Choropleth.py  # State-level provider map (requires NPPES CSV)
├── notebooks/
│   ├── 01_eda.ipynb         # Exploratory data analysis
│   ├── 02_cleaning.ipynb    # Data cleaning, enrichment & parquet exports
│   └── 03_analysis.ipynb    # Analysis & visualisations from exported data
├── exports/                 # Parquet files written by notebook 02
└── requirements.txt
```

## Streamlit Dashboard

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

### 3. Configure data paths (Settings page)

On first run, open **⚙️ Settings** in the sidebar and set the paths to your data files. Clicking **Save settings** writes them to `.medicaid_config.json` at the project root — all pages and notebooks pick this up automatically.

| Setting | Description |
|---------|-------------|
| **Medicaid parquet** | Main CMS Medicaid provider spending file |
| **NPPES CSV** | `npidata_pfile_*.csv` from the NPPES Data Dissemination download |
| **HCPCS CSV** *(optional)* | CMS HCPCS reference file — enables procedure descriptions in the cleaning notebook |
| **Exports directory** | Where notebook 02 writes its cleaned parquet outputs (default: `./exports/`) |

### 4. Pages

| Page | Description |
|------|-------------|
| **📊 Medicaid Overview** | High-level KPIs (total spend, claims, provider counts), yearly trend charts, and top HCPCS code rankings |
| **🗺️ US Choropleth** | State-level choropleth of provider distribution, colourable by provider count, total claims, or total paid. Requires the NPPES CSV |

## Notebooks

Run notebooks in order:

1. **`01_eda.ipynb`** — Explore the raw parquet: schema, row counts, spend distribution, top HCPCS codes, yearly trends.
2. **`02_cleaning.ipynb`** — Joins NPPES provider info and (optionally) HCPCS descriptions, filters malformed codes, derives metrics, and exports three parquet files to the exports directory:
   - `by_state_month.parquet`
   - `by_hcpcs_month.parquet`
   - `top_providers.parquet`
3. **`03_analysis.ipynb`** — Loads the exported parquets to answer key questions: spending trends, top states, costliest procedures, top providers, and anomaly detection.

Paths in the notebooks are read automatically from `.medicaid_config.json` (set via the Settings page).

## Data Sources

| File | Where to get it |
|------|-----------------|
| `medicaid-provider-spending.parquet` | CMS Medicaid data export |
| `npidata_pfile_*.csv` | [CMS NPPES Downloads](https://download.cms.gov/nppes/NPI_Files.html) |
| HCPCS codes CSV *(optional)* | [CMS HCPCS Reference Files](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system) — download the annual update ZIP and extract the CSV |

## Tech Stack

- **DuckDB** — fast in-process SQL over parquet files
- **Polars** — DataFrame operations in the notebooks
- **Streamlit** — interactive dashboard
- **Plotly** — charts and choropleth maps
