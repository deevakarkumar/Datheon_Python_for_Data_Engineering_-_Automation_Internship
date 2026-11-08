"""
Tests for Upsert Engine, Batch Processing, and Transaction Management
---------------------------------------------------------------------
"""

from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import text

from src.db_connection import DatabaseManager
from src.ingestion import IngestionPipeline
from src.schema import Student, init_db
from src.upsert import UpsertEngine
from src.verification import DatabaseVerifier


@pytest.fixture
def temp_engine_db(tmp_path: Path):
    """Fixture providing a fresh isolated database with initialized schema."""
    db_file = tmp_path / "test_upsert.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    manager = DatabaseManager(db_url)
    init_db(manager.engine)
    return manager


def test_new_records_insertion(temp_engine_db):
    """Test that all novel records are inserted cleanly into the database."""
    engine = UpsertEngine(temp_engine_db, batch_size=10)
    data = pd.DataFrame([
        {
            "student_id": "STU101",
            "student_name": "Charlie Brown",
            "email": "charlie@university.edu",
            "course": "AI",
            "marks": 95.0,
            "enrollment_date": "2024-01-01",
        },
        {
            "student_id": "STU102",
            "student_name": "Diana Prince",
            "email": "diana@university.edu",
            "course": "Cybersecurity",
            "marks": 89.0,
            "enrollment_date": "2024-01-02",
        },
    ])

    result = engine.upsert(data, rejected_count=0)

    assert result.new_records_inserted == 2
    assert result.existing_records_updated == 0
    assert result.unchanged_records == 0
    assert result.rejected_records == 0

    verifier = DatabaseVerifier(temp_engine_db)
    assert verifier.count_records() == 2


def test_existing_record_update(temp_engine_db):
    """Test updating existing records when fields are modified."""
    engine = UpsertEngine(temp_engine_db, batch_size=10)
    initial_data = pd.DataFrame([
        {
            "student_id": "STU101",
            "student_name": "Charlie Brown",
            "email": "charlie@university.edu",
            "course": "AI",
            "marks": 80.0,
            "enrollment_date": "2024-01-01",
        }
    ])
    engine.upsert(initial_data)

    # Modified data (marks changed from 80.0 to 92.0 and course to Data Science)
    updated_data = pd.DataFrame([
        {
            "student_id": "STU101",
            "student_name": "Charlie Brown",
            "email": "charlie@university.edu",
            "course": "Data Science",
            "marks": 92.0,
            "enrollment_date": "2024-01-01",
        }
    ])

    result = engine.upsert(updated_data)

    assert result.new_records_inserted == 0
    assert result.existing_records_updated == 1
    assert result.unchanged_records == 0

    # Verify database contents
    verifier = DatabaseVerifier(temp_engine_db)
    records = verifier.fetch_records(limit=1)
    assert records[0]["marks"] == 92.0
    assert records[0]["course"] == "Data Science"


def test_unchanged_record_preservation(temp_engine_db):
    """Test that unchanged records are detected and preserved without unnecessary writes."""
    engine = UpsertEngine(temp_engine_db, batch_size=10)
    data = pd.DataFrame([
        {
            "student_id": "STU101",
            "student_name": "Charlie Brown",
            "email": "charlie@university.edu",
            "course": "AI",
            "marks": 85.0,
            "enrollment_date": "2024-01-01",
        }
    ])

    # Run 1: Insert
    res1 = engine.upsert(data)
    assert res1.new_records_inserted == 1

    # Run 2: Ingest identical data
    res2 = engine.upsert(data)
    assert res2.new_records_inserted == 0
    assert res2.existing_records_updated == 0
    assert res2.unchanged_records == 1

    verifier = DatabaseVerifier(temp_engine_db)
    assert verifier.count_records() == 1


def test_batch_processing_and_duplicate_prevention(temp_engine_db):
    """Test multi-batch upsert processing across small batch sizes."""
    engine = UpsertEngine(temp_engine_db, batch_size=2)
    records = [
        {"student_id": f"STU{i:03d}", "student_name": f"Student {i}", "email": f"s{i}@univ.edu", "course": "CS", "marks": 75.0, "enrollment_date": "2024-01-01"}
        for i in range(1, 6)
    ]
    df = pd.DataFrame(records)

    res = engine.upsert(df)
    assert res.new_records_inserted == 5
    assert res.batches_processed == 3  # 5 records with batch size 2 = 3 batches

    # Re-running with same batch size
    res_repeat = engine.upsert(df)
    assert res_repeat.new_records_inserted == 0
    assert res_repeat.unchanged_records == 5

    verifier = DatabaseVerifier(temp_engine_db)
    assert verifier.count_records() == 5


def test_transaction_rollback_on_failure(temp_engine_db, monkeypatch):
    """Test that any unexpected exception triggers a transaction rollback, preventing partial writes."""
    engine = UpsertEngine(temp_engine_db, batch_size=5)

    df = pd.DataFrame([
        {
            "student_id": "STU501",
            "student_name": "Rollback Test",
            "email": "rollback@univ.edu",
            "course": "CS",
            "marks": 90.0,
            "enrollment_date": "2024-01-01",
        }
    ])

    # Monkeypatch session.bulk_save_objects to throw an exception
    def broken_save(self, objs):
        raise RuntimeError("Simulated Database Disk I/O Failure")

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "bulk_save_objects", broken_save)

    with pytest.raises(RuntimeError, match="Simulated Database Disk I/O Failure"):
        engine.upsert(df)

    # Check that database has 0 records (rolled back cleanly)
    verifier = DatabaseVerifier(temp_engine_db)
    assert verifier.count_records() == 0


def test_end_to_end_pipeline(tmp_path: Path):
    """Test full pipeline execution from CSV file ingestion to report generation."""
    db_file = tmp_path / "pipeline_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    manager = DatabaseManager(db_url)
    pipeline = IngestionPipeline(db_manager=manager, batch_size=20)

    # Create test CSV with 3 valid and 1 invalid record
    csv_file = tmp_path / "test_students.csv"
    csv_data = pd.DataFrame([
        {"student_id": "STU001", "student_name": "Student One", "email": "s1@univ.edu", "course": "CS", "marks": 85.0, "enrollment_date": "2024-01-01"},
        {"student_id": "STU002", "student_name": "Student Two", "email": "s2@univ.edu", "course": "AI", "marks": 90.0, "enrollment_date": "2024-01-02"},
        {"student_id": "STU003", "student_name": "Student Three", "email": "s3@univ.edu", "course": "DS", "marks": 95.0, "enrollment_date": "2024-01-03"},
        {"student_id": "STU999", "student_name": "Invalid Marks", "email": "s999@univ.edu", "course": "DS", "marks": -5.0, "enrollment_date": "2024-01-03"},
    ])
    csv_data.to_csv(csv_file, index=False)

    rejected_file = tmp_path / "rejected.csv"
    result = pipeline.run(csv_file, rejected_output_path=rejected_file, print_report=False)

    assert result.total_records_read == 4
    assert result.new_records_inserted == 3
    assert result.rejected_records == 1
    assert rejected_file.exists()

    verifier = DatabaseVerifier(manager)
    assert verifier.count_records() == 3
