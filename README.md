# medicaid-provider-spending

Analysis of Medicaid provider spending data using DuckDB and Polars, with HCPCS code enrichment and provider-level metrics.

## Streamlit Dashboard

This project includes a simple Streamlit app at `app.py` that reads the raw Medicaid parquet directly and shows:

- Overview metrics (total spend, rows, columns, providers, services, claims)
- Spend by year chart
- Top HCPCS code chart with metric toggles

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Run the app

```bash
streamlit run app.py
```

### 3) Data inputs

In the app sidebar, set the path to your Medicaid parquet file.
Default path:

- `~/Downloads/medicaid-provider-spending.parquet`

