"""
Datheon Automated Data Cleaning & Schema Transformation Engine
==============================================================
Interactive Streamlit Web Application for visualizing, inspecting,
and running the end-to-end data engineering pipeline.
"""

from pathlib import Path
import json
import tempfile
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.loader import DataLoader
from src.profiler import DataProfiler
from src.pipeline import DataCleaningPipeline

# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Data Cleaning & Quality Pipeline",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0.2rem;
        }
        .sub-title {
            font-size: 1.05rem;
            color: #4B5563;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        .badge-success {
            background-color: #DCFCE7;
            color: #166534;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .badge-warning {
            background-color: #FEF3C7;
            color: #92400E;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .badge-danger {
            background-color: #FEE2E2;
            color: #991B1B;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header Section
# ---------------------------------------------------------------------------
st.markdown('<div class="main-title">⚡ Automated Data Cleaning & Schema Transformation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Production-grade ETL pipeline: Multi-encoding ingestion, IQR outlier profiling, polymorphic date/currency normalization, data quarantine protocol, and audit reporting.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar: Ingestion & Controls
# ---------------------------------------------------------------------------
st.sidebar.header("📁 Data Ingestion")

sample_file_path = Path("data/raw/sample_messy_data.csv")
default_config_path = Path("config/schema_config.json")

data_source = st.sidebar.radio(
    "Choose Dataset Source:",
    ["Use Provided Messy Dataset (120 rows)", "Upload Custom CSV File"],
    index=0,
)

uploaded_file = None
active_input_path: Path = sample_file_path

if data_source == "Upload Custom CSV File":
    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
    if uploaded_file is not None:
        # Save uploaded file to a temporary location
        temp_dir = Path(tempfile.gettempdir()) / "pipeline_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        active_input_path = temp_dir / uploaded_file.name
        with open(active_input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"Uploaded: `{uploaded_file.name}`")
    else:
        st.sidebar.info("Upload a CSV file to begin, or switch back to the sample dataset.")
else:
    active_input_path = sample_file_path
    if active_input_path.exists():
        st.sidebar.success("Using `data/raw/sample_messy_data.csv`")
    else:
        st.sidebar.error("Sample dataset not found at `data/raw/sample_messy_data.csv`")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuration")
st.sidebar.caption(f"Active schema rules: `{default_config_path.name}`")

run_pipeline_btn = st.sidebar.button("🚀 Run Full ETL Pipeline", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Data Loading & Diagnostic Profiling
# ---------------------------------------------------------------------------
if active_input_path.exists():
    try:
        loader = DataLoader(active_input_path)
        raw_df, load_metadata = loader.load()
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        st.stop()
else:
    st.warning("Please provide a valid CSV file to proceed.")
    st.stop()

# ---------------------------------------------------------------------------
# Pipeline Execution State Management
# ---------------------------------------------------------------------------
if "pipeline_results" not in st.session_state:
    st.session_state["pipeline_results"] = None

if run_pipeline_btn:
    with st.spinner("Executing Data Cleaning & Quarantine Pipeline..."):
        try:
            pipeline = DataCleaningPipeline(
                config_path=default_config_path,
                output_dir=Path("data/output"),
            )
            results = pipeline.run(active_input_path)
            st.session_state["pipeline_results"] = results
            st.sidebar.success("✅ Pipeline completed successfully!")
        except Exception as e:
            st.sidebar.error(f"Pipeline failed: {e}")

# ---------------------------------------------------------------------------
# Main Display Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "🔍 1. Raw Data & Profiling",
    "⚙️ 2. Step-by-Step Architecture",
    "🛡️ 3. Clean vs. Quarantined Results",
    "📊 4. Executive HTML Report",
    "📜 5. Schema & Rules Config",
])

# ---------------------------------------------------------------------------
# TAB 1: Raw Data & Profiling
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Raw Data Inspection & Boundary Profiling")
    st.caption("Inspecting the raw file before applying any transformations or mutations.")

    # High-level metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Ingested Rows", f"{len(raw_df):,}")
    with col2:
        st.metric("Total Columns", len(raw_df.columns))
    with col3:
        st.metric("Detected Encoding", load_metadata.get("encoding", "utf-8"))
    with col4:
        st.metric("File Size", f"{load_metadata.get('file_size_bytes', 0) / 1024:.1f} KB")

    st.markdown("#### Raw Input Preview")
    st.dataframe(raw_df.head(15), use_container_width=True)

    # Profiling Analysis
    profiler = DataProfiler(raw_df)
    profile_data = profiler.profile()

    st.markdown("---")
    st.subheader("Automated Quality Diagnostics (Pre-Cleaning)")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown("##### Missing Values by Column")
        missing_dict = profile_data.get("missing_values", {})
        if missing_dict:
            missing_df = pd.DataFrame(list(missing_dict.items()), columns=["Column", "Null Count"])
            missing_df["Missing %"] = (missing_df["Null Count"] / len(raw_df)) * 100
            missing_df = missing_df.sort_values(by="Null Count", ascending=False)
            st.dataframe(missing_df.style.format({"Missing %": "{:.1f}%"}), use_container_width=True)
        else:
            st.info("No missing values detected.")

    with p_col2:
        st.markdown("##### Statistical Outlier Detection (IQR Method)")
        outliers_dict = profile_data.get("numerical_outliers_iqr", {})
        if outliers_dict:
            outlier_rows = []
            for col_name, o_info in outliers_dict.items():
                outlier_rows.append({
                    "Column": col_name,
                    "Outlier Count": o_info.get("count", 0),
                    "Lower Bound": round(o_info.get("lower_bound", 0), 2),
                    "Upper Bound": round(o_info.get("upper_bound", 2), 2),
                })
            outlier_df = pd.DataFrame(outlier_rows)
            st.dataframe(outlier_df, use_container_width=True)
        else:
            st.info("No numerical outliers detected via IQR.")

# ---------------------------------------------------------------------------
# TAB 2: Step-by-Step Architecture
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Pipeline Engineering: How Each Module Works")
    st.write(
        """
        The pipeline does not use hardcoded scripts. Instead, it executes an orchestrated sequence 
        of decoupled, single-responsibility modules:
        """
    )

    steps = [
        {
            "num": "01",
            "name": "Multi-Encoding DataLoader (`src/loader.py`)",
            "desc": "Safely reads files by trying UTF-8, Latin-1, and CP1252 encodings. Validates file boundaries and checks for 0-byte empty files.",
            "example": "Handles BOM characters and mixed Windows/Unix line endings seamlessly.",
        },
        {
            "num": "02",
            "name": "Pre-Cleaning DataProfiler (`src/profiler.py`)",
            "desc": "Computes cardinalities, null percentages, exact duplicates, and numerical outliers using the Interquartile Range (IQR = Q3 - Q1).",
            "example": "Identifies negative ages (e.g. -4) or extreme salaries before any row is altered.",
        },
        {
            "num": "03",
            "name": "Header Normalizer (`src/schema_transformer.py`)",
            "desc": "Converts arbitrary column strings to uniform snake_case, strips leading/trailing whitespaces, and applies custom alias mappings.",
            "example": "' Cust_ID ' ➔ 'cust_id' ➔ 'customer_id' | 'Annual Income ' ➔ 'salary'",
        },
        {
            "num": "04",
            "name": "Robust Currency Normalizer (`src/currency.py`)",
            "desc": "Vectorized regex engine stripping currency symbols (₹, $, €, Rs., INR), accounting parentheses (1,500), and standardizing to float64.",
            "example": "'₹61,793' ➔ 61793.0 | 'Rs 87,730.50' ➔ 87730.5 | '(₹1,500)' ➔ -1500.0",
        },
        {
            "num": "05",
            "name": "Polymorphic Date Normalizer (`src/dates.py`)",
            "desc": "Multi-format date engine with configurable day_first disambiguation converting varied date strings to ISO YYYY-MM-DD.",
            "example": "'15 Jan 2023' ➔ '2023-01-15' | '2021/08/01' ➔ '2021-08-01' | '99/99/9999' ➔ None",
        },
        {
            "num": "06",
            "name": "Missing Value Handler (`src/missing_values.py`)",
            "desc": "Drops columns exceeding a missingness threshold (e.g., >90% null). Imputes numerical columns via mean/median and categoricals via mode.",
            "example": "'Notes' column (95% null) automatically pruned; missing salaries imputed with median.",
        },
        {
            "num": "07",
            "name": "Deduplication Engine (`src/duplicates.py`)",
            "desc": "Detects exact full-row duplicates and duplicate primary keys, keeping the first valid occurrence.",
            "example": "Prevents double-submission duplicate customer IDs from distorting metrics.",
        },
        {
            "num": "08",
            "name": "Data Quarantine Protocol (`src/validator.py`)",
            "desc": "The security bouncer: Validates primary key uniqueness, mandatory presence, acceptable numeric ranges, and regex patterns.",
            "example": "Invalid rows routed to invalid_records.csv with explicit reasons instead of being silently dropped.",
        },
    ]

    for step in steps:
        with st.expander(f"**Step {step['num']}: {step['name']}**", expanded=False):
            st.markdown(f"**Function:** {step['desc']}")
            st.markdown(f"**Real-world Transformation:** `{step['example']}`")

# ---------------------------------------------------------------------------
# TAB 3: Clean vs. Quarantined Results
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Data Quarantine Protocol: Valid vs. Quarantined Records")

    results = st.session_state.get("pipeline_results")

    # If pipeline hasn't been run in this session, check if output files already exist on disk
    cleaned_path = Path("data/output/cleaned_data.csv")
    quarantined_path = Path("data/output/invalid_records.csv")

    if results is None and cleaned_path.exists() and quarantined_path.exists():
        # Load existing output
        df_clean = pd.read_csv(cleaned_path)
        df_quarantined = pd.read_csv(quarantined_path)
    elif results is not None:
        df_clean = pd.read_csv(results["output_files"]["cleaned_data"])
        df_quarantined = pd.read_csv(results["output_files"]["quarantined_records"])
    else:
        st.info("👈 Click **'Run Full ETL Pipeline'** in the sidebar to view transformed results.")
        df_clean = None
        df_quarantined = None

    if df_clean is not None and df_quarantined is not None:
        total_records = len(df_clean) + len(df_quarantined)
        clean_rate = (len(df_clean) / total_records) * 100 if total_records > 0 else 0
        quarantine_rate = (len(df_quarantined) / total_records) * 100 if total_records > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Post-Cleaning Records", f"{total_records:,}")
        with m2:
            st.metric("Passed Validation (Clean)", f"{len(df_clean):,}", f"{clean_rate:.1f}%")
        with m3:
            st.metric("Quarantined (Violations)", f"{len(df_quarantined):,}", f"-{quarantine_rate:.1f}%", delta_color="inverse")
        with m4:
            duplicates_removed = results.get("duplicates_removed_count", "N/A") if results else "N/A"
            st.metric("Duplicates Dropped", duplicates_removed)

        st.markdown("---")
        res_tab1, res_tab2 = st.tabs(["✅ Clean Production Data", "⚠️ Quarantined Invalid Records"])

        with res_tab1:
            st.markdown(f"##### Production Ready Dataset (`{len(df_clean)}` valid rows)")
            st.caption("All schema types enforced (`Int64`, `float64`, `boolean`), dates in ISO `YYYY-MM-DD`, headers standardized.")
            st.dataframe(df_clean, use_container_width=True)

            csv_clean_bytes = df_clean.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Clean Data (CSV)",
                data=csv_clean_bytes,
                file_name="cleaned_data.csv",
                mime="text/csv",
                type="primary",
            )

        with res_tab2:
            st.markdown(f"##### Quarantined Records (`{len(df_quarantined)}` invalid rows)")
            st.caption("Rows that violated business rules. Notice the explicit `rejection_reasons` column explaining every failure.")
            st.dataframe(df_quarantined, use_container_width=True)

            csv_quarantine_bytes = df_quarantined.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Quarantined Records (CSV)",
                data=csv_quarantine_bytes,
                file_name="invalid_records.csv",
                mime="text/csv",
            )

# ---------------------------------------------------------------------------
# TAB 4: Executive HTML Report
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Executive Quality Report (HTML Dashboard)")
    st.caption("Auto-generated, self-contained HTML report with responsive metric cards and schema evolution.")

    html_file = Path("data/output/cleaning_summary.html")
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=800, scrolling=True)
    else:
        st.info("HTML summary report will appear here once the pipeline is executed.")

# ---------------------------------------------------------------------------
# TAB 5: Schema & Rules Config
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Decoupled JSON Schema & Business Rules")
    st.caption("The pipeline is 100% configuration-driven. Edit `config/schema_config.json` to process any new CSV with zero code changes.")

    if default_config_path.exists():
        with open(default_config_path, "r", encoding="utf-8") as f:
            config_json = json.load(f)
        st.json(config_json)
    else:
        st.error("Configuration file `config/schema_config.json` not found.")
