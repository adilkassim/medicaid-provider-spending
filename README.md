# medicaid-provider-spending

Analysis of Medicaid provider spending data using DuckDB and Polars, with HCPCS code enrichment and provider-level metrics.

## Streamlit Dashboard

This project includes a simple Streamlit app at `/pages` that reads the raw Medicaid parquet directly and shows:

- Overview metrics (total spend, rows, columns, providers, services, claims)
- Spend by year chart
- Top HCPCS code chart with metric toggles
- Spend by State and Provider Type charts

For now only the first page is implemented, but I plan to add more pages with different analyses and visualizations in the future. The app is designed to be simple and easy to use, with a focus on providing insights into the Medicaid provider spending data.

## Setup

### 1) Install dependencies

```bash
pip install -r requirements.txt
```
### 2) Download the data
```bash
run page_1_data.py
```
Assuming you already have the raw parquet file downloaded, this will read the raw data, do some basic cleaning and preprocessing, and save the cleaned data to `data/`. For now it saves multiple csv files, but I plan to switch to a single csv file per page in the future. 


### 3) Run the app

```bash
streamlit run pages/01_Medicaid_Overview.py
```
For now the app only has one page, but I plan to add more pages with different analyses and visualizations.

