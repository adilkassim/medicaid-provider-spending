import streamlit as st

st.set_page_config(
    page_title="Medicaid Provider Spending",
    page_icon="🏥",
    layout="wide",
)

st.markdown(
    """
    <style>
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        color: #1a6fa8;
        margin-bottom: 0.2rem;
    }
    .hero-sub {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .card {
        background: #f7fbff;
        border: 1px solid #d0e8f9;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .card h3 { margin-top: 0; color: #1a6fa8; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="hero-title">🏥 Medicaid Provider Spending</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Interactive analytics dashboard for CMS Medicaid provider-level spending data.</p>',
    unsafe_allow_html=True,
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="card">
        <h3>⚙️ Settings</h3>
        <p>Configure data file paths (Medicaid parquet, NPPES CSV, HCPCS codes, exports directory).
        Start here on first run.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="card">
        <h3>📊 Medicaid Overview</h3>
        <p>High-level KPIs — total spend, claims, provider counts — plus yearly trends
        and top HCPCS procedure codes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="card">
        <h3>🗺️ US Choropleth</h3>
        <p>State-level provider distribution map built from NPPES data joined
        to Medicaid claims. Requires the NPPES CSV.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.markdown(
    """
    **Data sources required**
    | File | Where to get it |
    |------|-----------------|
    | `medicaid-provider-spending.parquet` | CMS Medicaid data export |
    | `npidata_pfile_*.csv` | [NPPES Data Dissemination (CMS)](https://download.cms.gov/nppes/NPI_Files.html) |
    | `hcpcs_codes.csv` *(optional)* | [CMS HCPCS Reference Files](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system) |

    Navigate using the **sidebar** or click the pages above to get started.
    """
)
