import os
import sys

import duckdb
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import load_config

st.set_page_config(
    page_title="US Choropleth",
    page_icon="🗺️",
    layout="wide",
)

cfg = load_config()

with st.sidebar:
    st.markdown("### Data sources")
    nppes_csv_path = st.text_input(
        "NPPES CSV",
        value=cfg["nppes_csv_path"],
        help="Path to the NPPES npidata_pfile_*.csv. Update in ⚙️ Settings to persist.",
    )
    if nppes_csv_path and not os.path.exists(nppes_csv_path):
        st.error("File not found", icon="❌")
    elif nppes_csv_path:
        st.success(f"{os.path.getsize(nppes_csv_path)/1e9:.1f} GB", icon="✅")

    include_territories = st.checkbox("Include US territories", value=False)
    color_metric = st.selectbox(
        "Colour map by",
        ["provider_count", "total_claims", "total_paid"],
        format_func=lambda x: {"provider_count": "Provider count", "total_claims": "Total claims", "total_paid": "Total paid ($)"}[x],
    )

st.title("🗺️ Provider Distribution by State")
st.caption("NPPES provider locations joined to Medicaid claims. Providers are matched on NPI.")

VALID_US_STATES_DC = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
}
US_TERRITORIES = {"PR", "GU", "VI", "AS", "MP"}


@st.cache_resource(show_spinner=False)
def get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect("medicaid_app.duckdb")
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA enable_progress_bar=false")
    return con


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@st.cache_data(show_spinner=False)
def load_nppes_state_rollup(csv_path: str):
    final_columns = [
        "NPI",
        "Entity Type Code",
        "Provider Last Name (Legal Name)",
        "Provider First Name",
        "Provider Credential Text",
        "Provider First Line Business Mailing Address",
        "Provider Business Mailing Address City Name",
        "Provider Business Mailing Address State Name",
        "Provider Business Mailing Address Postal Code",
        "Provider Business Mailing Address Country Code (If outside U.S.)",
        "Provider Business Mailing Address Telephone Number",
        "Provider First Line Business Practice Location Address",
        "Provider Business Practice Location Address City Name",
        "Provider Business Practice Location Address State Name",
        "Provider Business Practice Location Address Postal Code",
        "Provider Business Practice Location Address Country Code (If outside U.S.)",
        "Provider Business Practice Location Address Telephone Number",
        "Provider Enumeration Date",
        "Last Update Date",
        "Provider Sex Code",
        "Healthcare Provider Taxonomy Code_1",
        "Provider License Number_1",
        "Provider License Number State Code_1",
        "Healthcare Provider Primary Taxonomy Switch_1",
        "Is Sole Proprietor",
    ]
    cols_sql = ", ".join([f'"{c}"' for c in final_columns])
    con = get_connection()
    query = f"""
        WITH provider_info AS (
            SELECT {cols_sql}
            FROM read_csv_auto({sql_literal(csv_path)}, all_varchar=1)
        )
        SELECT
            UPPER(TRIM(p."Provider Business Practice Location Address State Name")) AS state,
            COUNT(DISTINCT p.NPI)         AS provider_count,
            COALESCE(SUM(m.TOTAL_CLAIMS), 0) AS total_claims,
            COALESCE(SUM(m.TOTAL_PAID),   0) AS total_paid
        FROM provider_info AS p
        LEFT JOIN medicaid AS m
          ON p.NPI = CAST(m.BILLING_PROVIDER_NPI_NUM AS VARCHAR)
        WHERE p."Provider Business Practice Location Address State Name" IS NOT NULL
          AND LENGTH(TRIM(p."Provider Business Practice Location Address State Name")) = 2
        GROUP BY 1
        ORDER BY 2 DESC
    """
    return con.execute(query).df()


# ── Guard ──────────────────────────────────────────────────────────────────────
if not nppes_csv_path:
    st.info("Set the NPPES CSV path in the sidebar or **⚙️ Settings** to load the map.")
    st.stop()

if not os.path.exists(nppes_csv_path):
    st.error(
        f"NPPES CSV not found: `{nppes_csv_path}`\n\n"
        "Update the path in **⚙️ Settings** or the sidebar above."
    )
    st.stop()

# Check that medicaid view exists (need Overview page loaded first or parquet direct)
con = get_connection()
try:
    con.execute("SELECT 1 FROM medicaid LIMIT 1")
except Exception:
    parquet_path = cfg["parquet_path"]
    if os.path.exists(parquet_path):
        con.execute(f"CREATE OR REPLACE VIEW medicaid AS SELECT * FROM read_parquet({sql_literal(parquet_path)})")
    else:
        st.warning(
            "Medicaid data not loaded yet. Open **📊 Medicaid Overview** first, "
            "or set your parquet path in **⚙️ Settings**."
        )
        st.stop()

with st.spinner("Loading NPPES state rollup… (this may take a minute on first load)"):
    by_state = load_nppes_state_rollup(nppes_csv_path)

allowed_codes = set(VALID_US_STATES_DC)
if include_territories:
    allowed_codes |= US_TERRITORIES

map_df = by_state[by_state["state"].isin(allowed_codes)].copy()
excluded_df = by_state[~by_state["state"].isin(allowed_codes)].copy()

# ── Choropleth ─────────────────────────────────────────────────────────────────
color_labels = {
    "provider_count": "Provider count",
    "total_claims": "Total claims",
    "total_paid": "Total paid ($)",
}
fig_map = px.choropleth(
    map_df,
    locations="state",
    locationmode="USA-states",
    scope="usa",
    color=color_metric,
    hover_data={
        "state": True,
        "provider_count": ":,",
        "total_claims": ":,",
        "total_paid": ":,.0f",
    },
    color_continuous_scale="Blues",
    labels={color_metric: color_labels[color_metric]},
    title=f"NPPES Providers by State — {color_labels[color_metric]}",
)
fig_map.update_layout(
    margin={"l": 0, "r": 0, "t": 50, "b": 0},
    coloraxis_colorbar=dict(title=color_labels[color_metric]),
)
st.plotly_chart(fig_map, use_container_width=True)

st.caption(f"Mapped: {len(map_df)} state codes | Excluded: {len(excluded_df)} non-US/invalid codes")

# ── Data table ────────────────────────────────────────────────────────────────
st.markdown("### State breakdown")
st.dataframe(
    map_df.sort_values(color_metric, ascending=False).style.format(
        {"provider_count": "{:,}", "total_claims": "{:,}", "total_paid": "${:,.0f}"}
    ),
    use_container_width=True,
)

with st.expander("Excluded location codes"):
    st.dataframe(excluded_df, use_container_width=True)
