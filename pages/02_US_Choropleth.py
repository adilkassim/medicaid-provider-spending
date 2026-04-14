import os

import duckdb
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="US Choropleth",
    page_icon="🗺️",
    layout="wide",
)
st.title("US Choropleth")

default_nppes_csv = "/Users/adilkassim/Downloads/NPPES_Data_Dissemination_February_2026_V2/npidata_pfile_20050523-20260208.csv"
nppes_csv_path = st.sidebar.text_input("NPPES CSV path", value=default_nppes_csv)
include_territories = st.sidebar.checkbox("Include US territories", value=False)

VALID_US_STATES_DC = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}
US_TERRITORIES = {"PR", "GU", "VI", "AS", "MP"}


@st.cache_resource(show_spinner=False)
def get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect("medicaid_app.duckdb")
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA enable_progress_bar=false")
    return con


def sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


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
    csv_literal = sql_literal(csv_path)
    con = get_connection()
    query = f"""
        WITH provider_info AS (
            SELECT {cols_sql}
            FROM read_csv_auto({csv_literal}, all_varchar=1)
        )
        SELECT
            UPPER(TRIM(p."Provider Business Practice Location Address State Name")) AS state,
            COUNT(DISTINCT p.NPI) AS provider_count,
            COALESCE(SUM(m.TOTAL_CLAIMS), 0) AS total_claims,
            COALESCE(SUM(m.TOTAL_PAID), 0) AS total_paid
        FROM provider_info AS p
        LEFT JOIN medicaid AS m
          ON p.NPI = CAST(m.BILLING_PROVIDER_NPI_NUM AS VARCHAR)
        WHERE p."Provider Business Practice Location Address State Name" IS NOT NULL
          AND LENGTH(TRIM(p."Provider Business Practice Location Address State Name")) = 2
        GROUP BY 1
        ORDER BY 2 DESC
    """
    return con.execute(query).df()


if not os.path.exists(nppes_csv_path):
    st.error(f"NPPES CSV file not found: {nppes_csv_path}")
    st.stop()

with st.spinner("Loading NPPES state rollup..."):
    by_state = load_nppes_state_rollup(nppes_csv_path)

allowed_codes = set(VALID_US_STATES_DC)
if include_territories:
    allowed_codes |= US_TERRITORIES

map_df = by_state[by_state["state"].isin(sorted(allowed_codes))].copy()
excluded_df = by_state[~by_state["state"].isin(sorted(allowed_codes))].copy()

fig_map = px.choropleth(
    map_df,
    locations="state",
    locationmode="USA-states",
    scope="usa",
    color="provider_count",
    hover_data={"state": True, "provider_count": ":,", "total_claims": ":,", "total_paid": ":,"},
    color_continuous_scale="Blues",
    title="NPPES Provider Count by State (Filtered to US codes)",
)
fig_map.update_layout(margin={"l": 0, "r": 0, "t": 50, "b": 0})
st.plotly_chart(fig_map, use_container_width=True)
st.caption(
    f"Mapped rows: {len(map_df)} codes | Excluded non-US/invalid codes: {len(excluded_df)}"
)
st.dataframe(map_df, use_container_width=True)

with st.expander("Show excluded location codes"):
    st.dataframe(excluded_df, use_container_width=True)
