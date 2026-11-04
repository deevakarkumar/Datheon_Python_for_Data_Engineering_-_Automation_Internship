"""
Integration Tests for End-to-End Pipeline
"""

from pathlib import Path
import json
import pandas as pd
import pytest
from src.pipeline import DataCleaningPipeline


def test_pipeline_end_to_end(tmp_path: Path):
    """Test entire pipeline execution producing all 5 required artifacts."""
    # Create small messy CSV
    csv_file = tmp_path / "messy.csv"
    csv_content = """Cust_ID , Customer Name, Age,Email_Address ,Annual Income ,Join_Date,City ,Active Status,Notes
1001,John Doe,28,john@example.com,"₹50,000",2023-01-15,Mumbai,true,
1002,Jane Smith,32,jane@example.com,"Rs. 60,000",15-02-2023,Delhi,1,
1001,John Doe,28,john@example.com,"₹50,000",2023-01-15,Mumbai,true,
1003,,24,bad_email,"-₹10,000",99/99/9999,Pune,0,
"""
    csv_file.write_text(csv_content, encoding="utf-8")

    # Config
    config_file = Path("config/schema_config.json")
    output_dir = tmp_path / "output"

    pipeline = DataCleaningPipeline(config_path=config_file, output_dir=output_dir)
    summary = pipeline.run(csv_file)

    assert summary["processing_status"] == "SUCCESS"
    assert summary["original_record_count"] == 4
    assert summary["duplicates_removed_count"] == 1

    # Check that all 5 artifact files were created on disk
    cleaned_file = output_dir / "cleaned_data.csv"
    quarantined_file = output_dir / "invalid_records.csv"
    json_report = output_dir / "validation_report.json"
    html_report = output_dir / "cleaning_summary.html"
    log_file = output_dir / "cleaning.log"

    assert cleaned_file.exists()
    assert quarantined_file.exists()
    assert json_report.exists()
    assert html_report.exists()
    assert log_file.exists()

    # Verify JSON content
    with open(json_report, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["processing_status"] == "SUCCESS"
        assert "validation_summary" in data

    # Verify valid records
    df_clean = pd.read_csv(cleaned_file)
    assert len(df_clean) >= 1
    assert "customer_id" in df_clean.columns
    assert "salary" in df_clean.columns
