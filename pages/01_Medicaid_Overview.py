import os

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Medicaid Overview",
    page_icon="💶",
    layout="wide",
)

default_parquet = os.path.expanduser("~/Downloads/medicaid-provider-spending.parquet")
parquet_path = st.sidebar.text_input("Medicaid parquet path", value=default_parquet)


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
def prepare_data(path: str) -> None:
    con = get_connection()
    parquet_literal = sql_literal(path)
    con.execute(
        f"CREATE OR REPLACE VIEW medicaid AS SELECT * FROM read_parquet({parquet_literal})"
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE agg_summary AS
        SELECT
            COUNT(*) AS total_rows,
            SUM(TOTAL_PAID) AS total_spend,
            SUM(TOTAL_CLAIMS) AS total_claims,
            COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM) AS distinct_billing_npi,
            COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM) AS distinct_servicing_npi,
            COUNT(DISTINCT HCPCS_CODE) AS unique_services
        FROM medicaid
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE agg_year AS
        SELECT
            SUBSTR(CAST(CLAIM_FROM_MONTH AS VARCHAR), 1, 4) AS year,
            SUM(TOTAL_PAID) AS total_paid,
            COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM) AS distinct_billing_npi,
            COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM) AS distinct_servicing_npi
        FROM medicaid
        GROUP BY 1
        ORDER BY 1
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE agg_hcpcs AS
        SELECT
            HCPCS_CODE,
            SUM(TOTAL_CLAIMS) AS total_claims,
            SUM(TOTAL_PAID) AS total_paid
        FROM medicaid
        WHERE HCPCS_CODE IS NOT NULL
        GROUP BY HCPCS_CODE
        """
    )


@st.cache_data(show_spinner=False)
def load_columns(path: str) -> list[str]:
    con = get_connection()
    cols_df = con.execute(
        """
        SELECT column_name
        FROM (DESCRIBE SELECT * FROM medicaid)
        ORDER BY column_name
        """,
    ).df()
    return cols_df["column_name"].tolist()


@st.cache_data(show_spinner=False)
def load_summary(_: str) -> dict:
    con = get_connection()
    summary_df = con.execute(
        """
        SELECT
            total_rows,
            total_spend,
            total_claims,
            distinct_billing_npi,
            distinct_servicing_npi,
            unique_services
        FROM agg_summary
        """
    ).df()
    row = summary_df.iloc[0]
    return {
        "total_rows": int(row["total_rows"]),
        "total_spend": float(row["total_spend"]),
        "total_claims": float(row["total_claims"]),
        "distinct_billing_npi": int(row["distinct_billing_npi"]),
        "distinct_servicing_npi": int(row["distinct_servicing_npi"]),
        "unique_services": int(row["unique_services"]),
    }


@st.cache_data(show_spinner=False)
def load_spend_by_year(_: str):
    con = get_connection()
    return con.execute("SELECT * FROM agg_year").df()


@st.cache_data(show_spinner=False)
def load_hcpcs_rollup(_: str, metric: str, top_n: int):
    if metric not in {"total_claims", "total_paid"}:
        raise ValueError("Invalid metric")

    con = get_connection()
    query = f"""
        SELECT
            HCPCS_CODE,
            total_claims,
            total_paid
        FROM agg_hcpcs
        ORDER BY {metric} DESC
        LIMIT ?
    """
    return con.execute(query, [top_n]).df()


if not os.path.exists(parquet_path):
    st.error(f"File not found: {parquet_path}")
    st.stop()

with st.spinner("Loading overview metrics..."):
    prepare_data(parquet_path)
    columns = load_columns(parquet_path)
    summary = load_summary(parquet_path)
    spend_by_year = load_spend_by_year(parquet_path)

metrics = st.columns(7)
metrics[0].metric("Total Spend", f"${float(summary['total_spend']):,.0f}")
metrics[1].metric("Total Rows", f"{int(summary['total_rows']):,}")
metrics[2].metric("Total Columns", f"{len(columns):,}")
metrics[3].metric(
    "Distinct BILLING_PROVIDER_NPI_NUM", f"{int(summary['distinct_billing_npi']):,}"
)
metrics[4].metric(
    "Distinct SERVICING_PROVIDER_NPI_NUM", f"{int(summary['distinct_servicing_npi']):,}"
)
metrics[5].metric("Unique HCPCS codes", f"{int(summary['unique_services']):,}")
metrics[6].metric("Total Claims", f"{float(summary['total_claims']):,.0f}")

st.markdown("## Provider Spend by Year")
chart_type = st.radio("Chart type", options=["Bar", "Line"], horizontal=True)
if chart_type == "Line":
    fig_year = px.line(
        spend_by_year,
        x="year",
        y="total_paid",
        markers=True,
        title="Total Medicaid Spend by Year",
        labels={"year": "Year", "total_paid": "Total Paid ($)"},
    )
else:
    fig_year = px.bar(
        spend_by_year,
        x="year",
        y="total_paid",
        title="Total Medicaid Spend by Year",
        labels={"year": "Year", "total_paid": "Total Paid ($)"},
    )
st.plotly_chart(fig_year, use_container_width=True)

st.markdown("### Total payments by year (billing NPI on claim rows)")
st.caption(
    "TOTAL_PAID summed by year. Lines show COUNT(DISTINCT …) per year for the two NPI columns on the file."
)
fig_billing = make_subplots(specs=[[{"secondary_y": True}]])
fig_billing.add_trace(
    go.Bar(
        x=spend_by_year["year"],
        y=spend_by_year["total_paid"],
        name="SUM(TOTAL_PAID)",
        marker_color="#636EFA",
    ),
    secondary_y=False,
)
fig_billing.add_trace(
    go.Scatter(
        x=spend_by_year["year"],
        y=spend_by_year["distinct_billing_npi"],
        name="COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM)",
        mode="lines+markers",
        line=dict(color="#EF553B"),
    ),
    secondary_y=True,
)
fig_billing.add_trace(
    go.Scatter(
        x=spend_by_year["year"],
        y=spend_by_year["distinct_servicing_npi"],
        name="COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM)",
        mode="lines+markers",
        line=dict(color="#00CC96"),
    ),
    secondary_y=True,
)
fig_billing.update_layout(
    title="Total paid by year vs distinct NPI counts (billing / servicing)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
)
fig_billing.update_xaxes(title_text="Year")
fig_billing.update_yaxes(title_text="Total paid ($)", secondary_y=False)
fig_billing.update_yaxes(
    title_text="Count distinct NPI (billing & servicing)",
    secondary_y=True,
)
st.plotly_chart(fig_billing, use_container_width=True)

st.markdown("## Top HCPCS codes")
st.caption(
    "HCPCS codes are plotted as **categories** (not numbers). Use a log scale if payouts span a wide range."
)
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
with ctrl1:
    top_n = st.slider("Top codes to show", min_value=5, max_value=100, value=15, step=5)
with ctrl2:
    metric_map = {
        "Most claims (TOTAL_CLAIMS)": "total_claims",
        "Highest payout (TOTAL_PAID)": "total_paid",
    }
    metric_label = st.selectbox("Rank by", list(metric_map.keys()))
with ctrl3:
    log_scale = st.checkbox("Log scale (value axis)", value=False)
metric = metric_map[metric_label]

with st.spinner("Loading HCPCS rollup..."):
    hcpcs_df = load_hcpcs_rollup(parquet_path, metric, top_n)

# Plotly treats numeric-looking codes (e.g. 99213) as continuous unless they are strings.
plot_df = hcpcs_df.copy()
plot_df["HCPCS_CODE"] = plot_df["HCPCS_CODE"].astype(str)
# Horizontal bars: ascending metric puts the largest bar at the top of the chart.
plot_df = plot_df.sort_values(metric, ascending=True)

fig_codes = px.bar(
    plot_df,
    x=metric,
    y="HCPCS_CODE",
    orientation="h",
    title=f"Top {top_n} HCPCS codes — {metric_label}",
    labels={metric: metric_label, "HCPCS_CODE": "HCPCS code"},
)
fig_codes.update_layout(
    yaxis=dict(
        type="category",
        categoryorder="array",
        categoryarray=plot_df["HCPCS_CODE"].tolist(),
    )
)
fig_codes.update_xaxes(title=metric_label)
if log_scale:
    if metric == "total_paid":
        # Reversals can be negative; symlog handles signed values better than log.
        fig_codes.update_xaxes(type="symlog", title=f"{metric_label} (symlog)")
    else:
        fig_codes.update_xaxes(type="log", title=f"{metric_label} (log)")
st.plotly_chart(fig_codes, use_container_width=True)
st.dataframe(hcpcs_df.sort_values(metric, ascending=False), use_container_width=True)
