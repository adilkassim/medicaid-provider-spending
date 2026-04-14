import os
import sys

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import load_config

st.set_page_config(
    page_title="Medicaid Overview",
    page_icon="📊",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="metric-container"] {
        background: #f7fbff;
        border: 1px solid #d0e8f9;
        border-radius: 8px;
        padding: 0.8rem 1rem;
    }
    [data-testid="metric-container"] label { color: #555; font-size: 0.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar — path override ───────────────────────────────────────────────────
cfg = load_config()
with st.sidebar:
    st.markdown("### Data source")
    parquet_path = st.text_input(
        "Medicaid parquet",
        value=cfg["parquet_path"],
        help="Override the path saved in Settings.",
    )
    if not os.path.exists(parquet_path):
        st.error("File not found — update in Settings or above.")
    else:
        st.success(f"{os.path.getsize(parquet_path)/1e9:.1f} GB", icon="✅")

st.title("📊 Medicaid Overview")


# ── DuckDB helpers ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect("medicaid_app.duckdb")
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA enable_progress_bar=false")
    return con


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@st.cache_data(show_spinner=False)
def prepare_data(path: str) -> None:
    con = get_connection()
    con.execute(f"CREATE OR REPLACE VIEW medicaid AS SELECT * FROM read_parquet({sql_literal(path)})")
    con.execute(
        """
        CREATE OR REPLACE TABLE agg_summary AS
        SELECT
            COUNT(*)                                    AS total_rows,
            SUM(TOTAL_PAID)                             AS total_spend,
            SUM(TOTAL_CLAIMS)                           AS total_claims,
            COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM)    AS distinct_billing_npi,
            COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM)  AS distinct_servicing_npi,
            COUNT(DISTINCT HCPCS_CODE)                  AS unique_services
        FROM medicaid
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE agg_year AS
        SELECT
            SUBSTR(CAST(CLAIM_FROM_MONTH AS VARCHAR), 1, 4) AS year,
            SUM(TOTAL_PAID)                                  AS total_paid,
            COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM)         AS distinct_billing_npi,
            COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM)       AS distinct_servicing_npi
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
            SUM(TOTAL_PAID)   AS total_paid
        FROM medicaid
        WHERE HCPCS_CODE IS NOT NULL
        GROUP BY HCPCS_CODE
        """
    )


@st.cache_data(show_spinner=False)
def load_columns(path: str) -> list[str]:
    con = get_connection()
    return (
        con.execute("SELECT column_name FROM (DESCRIBE SELECT * FROM medicaid) ORDER BY column_name")
        .df()["column_name"]
        .tolist()
    )


@st.cache_data(show_spinner=False)
def load_summary(_path: str) -> dict:
    con = get_connection()
    row = con.execute(
        "SELECT total_rows, total_spend, total_claims, distinct_billing_npi, distinct_servicing_npi, unique_services FROM agg_summary"
    ).df().iloc[0]
    return {k: row[k] for k in row.index}


@st.cache_data(show_spinner=False)
def load_spend_by_year(_path: str):
    return get_connection().execute("SELECT * FROM agg_year").df()


@st.cache_data(show_spinner=False)
def load_hcpcs_rollup(_path: str, metric: str, top_n: int):
    if metric not in {"total_claims", "total_paid"}:
        raise ValueError("Invalid metric")
    query = f"SELECT HCPCS_CODE, total_claims, total_paid FROM agg_hcpcs ORDER BY {metric} DESC LIMIT ?"
    return get_connection().execute(query, [top_n]).df()


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_large(n: float) -> str:
    """Human-readable number: 1.09T, 18.8B, 4.2M, etc."""
    abs_n = abs(n)
    if abs_n >= 1e12:
        return f"{n/1e12:.2f}T"
    if abs_n >= 1e9:
        return f"{n/1e9:.2f}B"
    if abs_n >= 1e6:
        return f"{n/1e6:.2f}M"
    if abs_n >= 1e3:
        return f"{n/1e3:.1f}K"
    return f"{n:,.0f}"


# ── Guard ─────────────────────────────────────────────────────────────────────
if not os.path.exists(parquet_path):
    st.error(f"Medicaid parquet not found: `{parquet_path}`\n\nUpdate the path in **⚙️ Settings** or the sidebar.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading overview metrics…"):
    prepare_data(parquet_path)
    columns = load_columns(parquet_path)
    summary = load_summary(parquet_path)
    spend_by_year = load_spend_by_year(parquet_path)

# ── KPI row ───────────────────────────────────────────────────────────────────
m = st.columns(7)
m[0].metric("Total Spend", f"${fmt_large(float(summary['total_spend']))}")
m[1].metric("Total Claims", fmt_large(float(summary["total_claims"])))
m[2].metric("Claim Rows", fmt_large(int(summary["total_rows"])))
m[3].metric("Columns", f"{len(columns):,}")
m[4].metric("Billing Providers", fmt_large(int(summary["distinct_billing_npi"])))
m[5].metric("Servicing Providers", fmt_large(int(summary["distinct_servicing_npi"])))
m[6].metric("Unique HCPCS Codes", fmt_large(int(summary["unique_services"])))

st.divider()

# ── Spend by Year ─────────────────────────────────────────────────────────────
st.markdown("## Spend by Year")
chart_type = st.radio("Chart type", ["Bar", "Line"], horizontal=True)

CHART_COLOR = "#1a6fa8"
if chart_type == "Line":
    fig_year = px.line(
        spend_by_year,
        x="year",
        y="total_paid",
        markers=True,
        labels={"year": "Year", "total_paid": "Total Paid ($)"},
        color_discrete_sequence=[CHART_COLOR],
    )
    fig_year.update_traces(line_width=2.5)
else:
    fig_year = px.bar(
        spend_by_year,
        x="year",
        y="total_paid",
        labels={"year": "Year", "total_paid": "Total Paid ($)"},
        color_discrete_sequence=[CHART_COLOR],
    )

fig_year.update_layout(
    title="Total Medicaid Spend by Year",
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="#eee", tickformat="$.2s"),
    hovermode="x unified",
)
st.plotly_chart(fig_year, use_container_width=True)

# ── Spend + NPI dual-axis ─────────────────────────────────────────────────────
with st.expander("Spend vs distinct provider count by year", expanded=False):
    st.caption("Bar = SUM(TOTAL_PAID). Lines = COUNT(DISTINCT NPI) for billing and servicing provider columns.")
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(
        go.Bar(x=spend_by_year["year"], y=spend_by_year["total_paid"], name="Total Paid", marker_color=CHART_COLOR),
        secondary_y=False,
    )
    fig_dual.add_trace(
        go.Scatter(
            x=spend_by_year["year"],
            y=spend_by_year["distinct_billing_npi"],
            name="Billing NPIs",
            mode="lines+markers",
            line=dict(color="#EF553B"),
        ),
        secondary_y=True,
    )
    fig_dual.add_trace(
        go.Scatter(
            x=spend_by_year["year"],
            y=spend_by_year["distinct_servicing_npi"],
            name="Servicing NPIs",
            mode="lines+markers",
            line=dict(color="#00CC96"),
        ),
        secondary_y=True,
    )
    fig_dual.update_layout(
        title="Total paid vs distinct NPI counts",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig_dual.update_xaxes(title_text="Year", showgrid=False)
    fig_dual.update_yaxes(title_text="Total Paid ($)", tickformat="$.2s", secondary_y=False, gridcolor="#eee")
    fig_dual.update_yaxes(title_text="Distinct NPI count", secondary_y=True, showgrid=False)
    st.plotly_chart(fig_dual, use_container_width=True)

st.divider()

# ── Top HCPCS ─────────────────────────────────────────────────────────────────
st.markdown("## Top HCPCS Codes")
st.caption("HCPCS codes treated as categories. Use log scale when payouts span a wide range.")

ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
with ctrl1:
    top_n = st.slider("Codes to show", min_value=5, max_value=100, value=20, step=5)
with ctrl2:
    metric_map = {
        "Highest payout (TOTAL_PAID)": "total_paid",
        "Most claims (TOTAL_CLAIMS)": "total_claims",
    }
    metric_label = st.selectbox("Rank by", list(metric_map.keys()))
with ctrl3:
    log_scale = st.checkbox("Log scale", value=False)

metric = metric_map[metric_label]

with st.spinner("Loading HCPCS rollup…"):
    hcpcs_df = load_hcpcs_rollup(parquet_path, metric, top_n)

plot_df = hcpcs_df.copy()
plot_df["HCPCS_CODE"] = plot_df["HCPCS_CODE"].astype(str)
plot_df = plot_df.sort_values(metric, ascending=True)

fig_codes = px.bar(
    plot_df,
    x=metric,
    y="HCPCS_CODE",
    orientation="h",
    labels={metric: metric_label, "HCPCS_CODE": "HCPCS code"},
    color_discrete_sequence=[CHART_COLOR],
)
fig_codes.update_layout(
    title=f"Top {top_n} HCPCS codes — {metric_label}",
    yaxis=dict(type="category", categoryorder="array", categoryarray=plot_df["HCPCS_CODE"].tolist()),
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(gridcolor="#eee"),
)
if log_scale:
    axis_type = "symlog" if metric == "total_paid" else "log"
    fig_codes.update_xaxes(type=axis_type, title=f"{metric_label} ({axis_type})")

st.plotly_chart(fig_codes, use_container_width=True)

with st.expander("Raw HCPCS table"):
    st.dataframe(
        hcpcs_df.sort_values(metric, ascending=False).style.format(
            {"total_paid": "${:,.0f}", "total_claims": "{:,.0f}"}
        ),
        use_container_width=True,
    )
