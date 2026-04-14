import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import load_config, save_config

st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ Settings")
st.caption("Configure file paths for all data sources. Changes are saved to `.medicaid_config.json` in the project root.")

cfg = load_config()

st.markdown("### Data Paths")

col1, col2 = st.columns(2)

with col1:
    parquet_path = st.text_input(
        "Medicaid parquet file",
        value=cfg["parquet_path"],
        help="Path to the main Medicaid provider spending parquet file.",
    )
    parquet_ok = os.path.exists(parquet_path)
    if parquet_path:
        if parquet_ok:
            st.success(f"Found ({os.path.getsize(parquet_path) / 1e9:.1f} GB)", icon="✅")
        else:
            st.error("File not found", icon="❌")

with col2:
    nppes_csv_path = st.text_input(
        "NPPES provider CSV",
        value=cfg["nppes_csv_path"],
        help="Path to the NPPES Data Dissemination CSV (npidata_pfile_*.csv). Required for the Choropleth page.",
    )
    if nppes_csv_path:
        if os.path.exists(nppes_csv_path):
            st.success(f"Found ({os.path.getsize(nppes_csv_path) / 1e9:.1f} GB)", icon="✅")
        else:
            st.error("File not found", icon="❌")

col3, col4 = st.columns(2)

with col3:
    hcpcs_csv_path = st.text_input(
        "HCPCS codes CSV (optional)",
        value=cfg["hcpcs_csv_path"],
        help="Path to CMS HCPCS reference CSV. Used by the cleaning notebook to enrich HCPCS codes with descriptions.",
        placeholder="Leave blank to skip HCPCS enrichment",
    )
    if hcpcs_csv_path:
        if os.path.exists(hcpcs_csv_path):
            st.success("Found", icon="✅")
        else:
            st.error("File not found", icon="❌")
    else:
        st.info("Optional — descriptions will be NULL if not provided", icon="ℹ️")

with col4:
    exports_dir = st.text_input(
        "Exports directory",
        value=cfg["exports_dir"],
        help="Directory where cleaned parquet exports from the notebooks are saved.",
    )
    if exports_dir:
        if os.path.isdir(exports_dir):
            files = [f for f in os.listdir(exports_dir) if f.endswith(".parquet")]
            st.success(f"Exists — {len(files)} parquet file(s) found", icon="✅")
        else:
            st.warning("Directory does not exist yet (it will be created when you run notebook 02)", icon="⚠️")

st.divider()

if st.button("💾 Save settings", type="primary"):
    save_config(
        {
            "parquet_path": parquet_path,
            "nppes_csv_path": nppes_csv_path,
            "hcpcs_csv_path": hcpcs_csv_path,
            "exports_dir": exports_dir,
        }
    )
    st.success("Settings saved to `.medicaid_config.json`", icon="✅")
    st.rerun()

st.divider()
st.markdown(
    """
    **Where to get the data files**

    | File | Source |
    |------|--------|
    | Medicaid parquet | CMS Medicaid data export |
    | NPPES CSV (`npidata_pfile_*.csv`) | [CMS NPPES Downloads](https://download.cms.gov/nppes/NPI_Files.html) |
    | HCPCS codes CSV | [CMS HCPCS Reference Files](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system) — download the "HCPCS Annual Update" ZIP and extract the CSV |
    """
)
