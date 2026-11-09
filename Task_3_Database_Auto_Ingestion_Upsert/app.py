"""
Relational Database Auto-Ingestion & Upsert Engine
Interactive Streamlit Web Dashboard
-------------------------------------------------
Visual analytics, live database exploration, interactive SQL runner,
and one-click upsert pipeline execution for internship evaluation.
"""

from datetime import datetime
from pathlib import Path
import tempfile
import pandas as pd
from sqlalchemy import text
import streamlit as st

from config import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DB_URL,
    REJECTED_RECORDS_CSV,
    STUDENTS_CSV,
    STUDENTS_UPDATED_CSV,
    TABLE_NAME,
)
from src.db_connection import DatabaseManager
from src.ingestion import IngestionPipeline
from src.schema import init_db
from src.verification import DatabaseVerifier

# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Database Ingestion & Upsert Engine",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .main-header {
            font-size: 2.1rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #4B5563;
            margin-bottom: 1.5rem;
        }
        .stat-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        .status-badge-ok {
            background-color: #DCFCE7;
            color: #166534;
            padding: 0.2rem 0.6rem;
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
st.markdown('<div class="main-header">🗄️ Relational Database Auto-Ingestion & Upsert Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Datheon Python for Data Engineering & Automation Internship &mdash; Milestone 3 Dashboard</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Database Manager Setup
# ---------------------------------------------------------------------------
if "db_manager" not in st.session_state:
    st.session_state["db_manager"] = DatabaseManager(DEFAULT_DB_URL)

db_mgr: DatabaseManager = st.session_state["db_manager"]
verifier = DatabaseVerifier(db_mgr)

# Ensure schema exists
try:
    init_db(db_mgr.engine)
except Exception as e:
    st.error(f"Failed to connect to database: {e}")

# ---------------------------------------------------------------------------
# Sidebar: Controls & Ingestion
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Database Controls")

# Integrity check badge
summary = verifier.get_summary()
health_status = summary.get("database_health", "UNKNOWN")
total_in_db = summary.get("total_records", 0)

if health_status == "HEALTHY":
    st.sidebar.markdown(f"**Database Status:** <span class='status-badge-ok'>● {health_status}</span>", unsafe_allow_html=True)
else:
    st.sidebar.warning(f"Database Status: {health_status}")

st.sidebar.caption(f"Target: `{TABLE_NAME}` table | SQLite 3 Relational Engine")

if st.sidebar.button("🔄 Reset / Re-initialize Schema", use_container_width=True):
    with st.spinner("Re-initializing database schema..."):
        init_db(db_mgr.engine)
        st.sidebar.success("Schema verified & initialized.")

st.sidebar.markdown("---")
st.sidebar.header("📁 Ingestion & Upsert Trigger")

dataset_choice = st.sidebar.radio(
    "Select Source CSV Dataset:",
    [
        "Initial: data/students.csv (105 records)",
        "Updated: data/students_updated.csv (105 records - Upsert Demo)",
        "Upload Custom CSV File",
    ],
    index=1,
)

active_csv_path: Path = STUDENTS_UPDATED_CSV
uploaded_custom = None

if dataset_choice == "Initial: data/students.csv (105 records)":
    active_csv_path = STUDENTS_CSV
elif dataset_choice == "Updated: data/students_updated.csv (105 records - Upsert Demo)":
    active_csv_path = STUDENTS_UPDATED_CSV
else:
    uploaded_custom = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
    if uploaded_custom:
        temp_dir = Path(tempfile.gettempdir()) / "task3_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        active_csv_path = temp_dir / uploaded_custom.name
        with open(active_csv_path, "wb") as f:
            f.write(uploaded_custom.getbuffer())
        st.sidebar.success(f"Loaded: `{uploaded_custom.name}`")
    else:
        st.sidebar.info("Upload a CSV file to test custom ingestion.")

batch_size = st.sidebar.slider("Batch Size (Records per transaction):", min_value=10, max_value=100, value=DEFAULT_BATCH_SIZE, step=10)

run_ingestion_btn = st.sidebar.button("🚀 Run Upsert Pipeline", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Pipeline Execution State
# ---------------------------------------------------------------------------
if "last_ingestion_result" not in st.session_state:
    st.session_state["last_ingestion_result"] = None

if run_ingestion_btn:
    if active_csv_path.exists():
        with st.spinner("Executing batched upsert pipeline..."):
            pipeline = IngestionPipeline(db_manager=db_mgr, batch_size=batch_size)
            try:
                res = pipeline.run(active_csv_path, print_report=False)
                st.session_state["last_ingestion_result"] = res
                st.sidebar.success("✅ Ingestion & Upsert Complete!")
            except Exception as exc:
                st.sidebar.error(f"Pipeline error: {exc}")
    else:
        st.sidebar.error("Selected CSV file does not exist.")

# ---------------------------------------------------------------------------
# Main Dashboard Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📊 1. Execution Summary & Metrics",
    "🗄️ 2. Live Database Explorer",
    "⚠️ 3. Quarantined Records",
    "💻 4. Interactive SQL Console",
    "📜 5. Execution Logs",
])

# ---------------------------------------------------------------------------
# TAB 1: Execution Summary & Metrics
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Automated Ingestion & Upsert Summary")
    st.caption("Real-time metrics calculated dynamically during the pipeline execution.")

    result = st.session_state.get("last_ingestion_result")

    # High-level database summary metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Records in DB", f"{verifier.count_records():,}")
    with m2:
        inserted_val = result.new_records_inserted if result else "—"
        st.metric("New Records Inserted", inserted_val)
    with m3:
        updated_val = result.existing_records_updated if result else "—"
        st.metric("Existing Records Updated", updated_val)
    with m4:
        unchanged_val = result.unchanged_records if result else "—"
        st.metric("Unchanged (0 I/O Writes)", unchanged_val)
    with m5:
        rejected_val = result.rejected_records if result else "—"
        st.metric("Quarantined (Violations)", rejected_val, delta_color="inverse")

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Operational Breakdown")
        if result:
            chart_data = pd.DataFrame([
                {"Category": "New Inserted", "Records": result.new_records_inserted},
                {"Category": "Updated", "Records": result.existing_records_updated},
                {"Category": "Unchanged", "Records": result.unchanged_records},
                {"Category": "Quarantined", "Records": result.rejected_records},
            ])
            st.bar_chart(chart_data.set_index("Category"), color="#2563EB")
        else:
            st.info("Click **'🚀 Run Upsert Pipeline'** in the sidebar to populate execution statistics.")

    with col_right:
        st.markdown("#### Standardized Audit Report")
        if result:
            summary_text = f"""
========================================
       DATA INGESTION REPORT
========================================

Total Records Read:       {result.total_records_read:>5}
New Records Inserted:     {result.new_records_inserted:>5}
Existing Records Updated: {result.existing_records_updated:>5}
Unchanged Records:        {result.unchanged_records:>5}
Rejected Records:         {result.rejected_records:>5}

Total Records Processed:  {result.total_records_processed:>5}

Database Status: SUCCESS
Execution Status: COMPLETED

========================================
Execution Time: {result.execution_duration_sec:.3f}s | Batches: {result.batches_processed}
========================================
"""
            st.code(summary_text, language="text")
        else:
            st.code("""
========================================
       DATA INGESTION REPORT
========================================
(Awaiting pipeline execution...)
========================================
""", language="text")

# ---------------------------------------------------------------------------
# TAB 2: Live Database Explorer
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader(f"Live Relational Database Contents (`{TABLE_NAME}` table)")
    st.caption("Directly queries SQLite `database/database.db` via SQLAlchemy.")

    all_df = verifier.to_dataframe()

    if not all_df.empty:
        # Search & Filters
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_query = st.text_input("🔍 Search by Student ID or Name:", placeholder="e.g. STU001 or Sharma")
        with f2:
            course_list = ["All Courses"] + sorted(all_df["course"].dropna().unique().tolist())
            selected_course = st.selectbox("Filter by Course:", course_list)
        with f3:
            min_score, max_score = st.slider("Filter by Marks Range:", 0.0, 100.0, (0.0, 100.0))

        # Apply filtering
        filtered_df = all_df.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["student_id"].str.contains(search_query, case=False, na=False)
                | filtered_df["student_name"].str.contains(search_query, case=False, na=False)
            ]
        if selected_course != "All Courses":
            filtered_df = filtered_df[filtered_df["course"] == selected_course]
        filtered_df = filtered_df[(filtered_df["marks"] >= min_score) & (filtered_df["marks"] <= max_score)]

        st.markdown(f"**Showing `{len(filtered_df)}` of `{len(all_df)}` records:**")
        st.dataframe(filtered_df, use_container_width=True)

        csv_download = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Current Records (CSV)",
            data=csv_download,
            file_name="students_database_export.csv",
            mime="text/csv",
            type="primary",
        )
    else:
        st.warning("The database is currently empty. Click 'Run Upsert Pipeline' to populate data.")

# ---------------------------------------------------------------------------
# TAB 3: Quarantined Records
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Data Quarantine Protocol: Rejected Records")
    st.caption("Records that violated data quality rules are isolated with explicit failure notes.")

    if REJECTED_RECORDS_CSV.exists():
        rej_df = pd.read_csv(REJECTED_RECORDS_CSV)
        st.markdown(f"**Total Quarantined Violations:** `{len(rej_df)}`")
        st.dataframe(rej_df, use_container_width=True)

        csv_rej = rej_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Quarantined Records (CSV)",
            data=csv_rej,
            file_name="rejected_records.csv",
            mime="text/csv",
        )
    else:
        st.info("No rejected records found. Run ingestion on `students_updated.csv` to inspect quarantined records.")

# ---------------------------------------------------------------------------
# TAB 4: Interactive SQL Console
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Interactive SQL Query Console")
    st.caption("Execute read-only SQL queries directly against the live SQLite relational database.")

    default_query = "SELECT course, COUNT(*) AS student_count, ROUND(AVG(marks), 2) AS avg_marks FROM students GROUP BY course ORDER BY student_count DESC;"
    query_input = st.text_area("Write SQL Query:", value=default_query, height=120)

    q_col1, q_col2, q_col3 = st.columns([1, 1, 3])
    with q_col1:
        execute_query_btn = st.button("⚡ Execute Query", type="primary")

    if execute_query_btn and query_input.strip():
        # Security check: Read-only queries only
        cleaned_q = query_input.strip().upper()
        if not cleaned_q.startswith("SELECT") and not cleaned_q.startswith("WITH") and not cleaned_q.startswith("PRAGMA"):
            st.error("Only SELECT, WITH, and PRAGMA read queries are permitted in this console.")
        else:
            try:
                with db_mgr.engine.connect() as conn:
                    query_result = pd.read_sql_query(text(query_input), con=conn)
                    st.success(f"Query returned `{len(query_result)}` row(s).")
                    st.dataframe(query_result, use_container_width=True)
            except Exception as err:
                st.error(f"SQL Execution Error: {err}")

# ---------------------------------------------------------------------------
# TAB 5: Execution Logs
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Live Rotating Execution Log (`logs/ingestion.log`)")
    st.caption("Logs recorded via Python's `RotatingFileHandler` with millisecond precision.")

    log_file = Path("logs/ingestion.log")
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent_logs = "".join(lines[-100:])
        st.text_area("Latest 100 log lines:", value=recent_logs, height=450)
    else:
        st.info("Log file will be created upon first execution.")
