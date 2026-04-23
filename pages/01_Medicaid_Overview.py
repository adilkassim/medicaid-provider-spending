import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Medicaid Overview",
    page_icon="💶",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _csv(name: str) -> str:
    return os.path.join(DATA_DIR, name)


@st.cache_data(show_spinner=False)
def load_summary() -> dict:
    df = pd.read_csv(_csv("summary_stats.csv"), index_col=0)
    row = df.iloc[0]
    return {
        "total_rows": int(row["total_rows"]),
        "total_spend": float(row["total_spend"]),
        "total_claims": float(row["total_claims"]),
        "distinct_billing_npi": int(row["distinct_billing_npi"]),
        "distinct_servicing_npi": int(row["distinct_servicing_npi"]),
        "unique_services": int(row["unique_services"]),
    }

@st.cache_data(show_spinner=False)
def load_spend_by_month() -> pd.DataFrame:
    df = pd.read_csv(_csv("per_month.csv"), index_col=0)
    df["CLAIM_FROM_MONTH"] = df["CLAIM_FROM_MONTH"].astype(str)
    df.rename(columns={"CLAIM_FROM_MONTH": "date"}, inplace=True)

    return df

@st.cache_data(show_spinner=False)
def load_columns() -> list[str]:
    df = pd.read_csv(_csv("columns.csv"), index_col=0)
    return df["column_name"].tolist()


@st.cache_data(show_spinner=False)
def load_spend_by_year():
    return pd.read_csv(_csv("agg_year.csv"), index_col=0)


@st.cache_data(show_spinner=False)
def load_hcpcs_rollup(metric: str, top_n: int):
    if metric not in {"total_claims", "total_paid"}:
        raise ValueError("Invalid metric")
    df = pd.read_csv(_csv("hcpcs.csv"), index_col=0)
    return df.nlargest(top_n, metric)[["HCPCS_CODE", "total_claims", "total_paid"]]


st.title("Medicaid Spending")

required = ["summary_stats.csv", "agg_year.csv", "hcpcs.csv", "columns.csv"]
missing = [f for f in required if not os.path.exists(_csv(f))]
if missing:
    st.error(f"Missing data files: {missing}. Run page_1_data.py first.")
    st.stop()

with st.spinner("Loading overview metrics..."):
    summary = load_summary()
    columns = load_columns()
    spend_by_month = load_spend_by_month()
    spend_by_year = load_spend_by_year()

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
st.caption("Click a year bar to see the monthly breakdown.")

col_year, col_month = st.columns(2)

with col_year:
    fig_by_year = px.bar(
        spend_by_year,
        x="year",
        y="total_paid",
        title="Total Spend by Year",
        labels={"year": "Year", "total_paid": "Total Paid ($)"},
        color_discrete_sequence=["#636EFA"],
    )
    fig_by_year.add_hline(
        y=spend_by_year["total_paid"].mean(),
        line=dict(color="red", dash="dash", width=1),
        annotation_text=f"Avg: ${spend_by_year['total_paid'].mean() / 1e9:.1f}B",
        annotation_position="top left",
    )
    fig_by_year.update_layout(clickmode="event+select")
    year_event = st.plotly_chart(fig_by_year, use_container_width=True, on_select="rerun", selection_mode="points")

selected_year = None
if year_event and year_event.selection and year_event.selection.points:
    selected_year = str(year_event.selection.points[0]["x"])

with col_month:
    if selected_year:
        month_df = spend_by_month[spend_by_month["date"].str.startswith(selected_year)].sort_values("date")
        month_dates = month_df["date"].tolist()
        month_billions = month_df["total_paid"] / 1e9
        avg = month_billions.mean()

        chart_type = st.radio("Chart type", ["Bar", "Line"], horizontal=True, key="month_chart_type")

        if chart_type == "Bar":
            fig_month = px.bar(
                month_df,
                x="date",
                y="total_paid",
                title=f"Monthly Spend — {selected_year}",
                labels={"date": "Month", "total_paid": "Total Paid ($)"},
                color_discrete_sequence=["#636EFA"],
            )
            fig_month.add_hline(
                y=month_df["total_paid"].mean(),
                line=dict(color="red", dash="dash", width=1),
                annotation_text=f"Avg: ${avg:.1f}B",
                annotation_position="top right",
            )
        else:
            fig_month = go.Figure()
            fig_month.add_trace(go.Scatter(
                x=month_dates,
                y=month_billions,
                mode="lines+markers",
                fill="tozeroy",
                fillcolor="rgba(99, 110, 250, 0.3)",
                line=dict(color="#636EFA"),
                name="Total Paid",
            ))
            fig_month.add_hline(
                y=avg,
                line=dict(color="red", dash="dash", width=1),
                annotation_text=f"Avg: ${avg:.1f}B",
                annotation_position="top right",
            )
            fig_month.update_layout(
                title=f"Monthly Spend — {selected_year}",
                xaxis=dict(tickangle=45),
                yaxis=dict(title="Total Paid (Billions $)"),
            )

        st.plotly_chart(fig_month, use_container_width=True)
    else:
        st.info("Click a year on the left to see monthly breakdown.")

st.markdown("### Distinct NPI counts by year")
st.caption("Lines show COUNT(DISTINCT …) per year for the two NPI columns on the file.")
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
    hcpcs_df = load_hcpcs_rollup(metric, top_n)

plot_df = hcpcs_df.copy()
plot_df["HCPCS_CODE"] = plot_df["HCPCS_CODE"].astype(str)
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
        fig_codes.update_xaxes(type="symlog", title=f"{metric_label} (symlog)")
    else:
        fig_codes.update_xaxes(type="log", title=f"{metric_label} (log)")
st.plotly_chart(fig_codes, use_container_width=True)
st.dataframe(hcpcs_df.sort_values(metric, ascending=False), use_container_width=True)
