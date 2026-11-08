"""
Tests for Data Validation Engine
--------------------------------
"""

from pathlib import Path
import pandas as pd
import pytest

from src.validation import DataValidator, ValidationError


@pytest.fixture
def sample_valid_df() -> pd.DataFrame:
    """Fixture providing a clean DataFrame."""
    return pd.DataFrame([
        {
            "student_id": "STU001",
            "student_name": "Alice Smith",
            "email": "alice.smith@university.edu",
            "course": "Computer Science",
            "marks": 92.5,
            "enrollment_date": "2024-01-15",
        },
        {
            "student_id": "STU002",
            "student_name": "Bob Jones",
            "email": "bob.jones@university.edu",
            "course": "Data Science",
            "marks": 85.0,
            "enrollment_date": "2024-02-01",
        },
    ])


def test_validation_valid_data(sample_valid_df):
    """Test that clean records pass validation without quarantine."""
    validator = DataValidator()
    valid_df, rejected_df = validator.validate(sample_valid_df)

    assert len(valid_df) == 2
    assert len(rejected_df) == 0


def test_validation_missing_columns():
    """Test that missing mandatory columns raises ValidationError."""
    invalid_cols_df = pd.DataFrame([{"student_id": "STU001", "marks": 90.0}])
    validator = DataValidator()

    with pytest.raises(ValidationError, match="Missing mandatory column"):
        validator.validate(invalid_cols_df)


def test_validation_empty_dataframe():
    """Test that an empty DataFrame raises ValidationError."""
    validator = DataValidator()
    with pytest.raises(ValidationError, match="empty"):
        validator.validate(pd.DataFrame())


def test_validation_invalid_marks_range():
    """Test that marks < 0 or > 100 are quarantined with explicit reasons."""
    df = pd.DataFrame([
        {
            "student_id": "STU001",
            "student_name": "Negative Student",
            "email": "neg@university.edu",
            "course": "AI",
            "marks": -10.0,
            "enrollment_date": "2024-01-10",
        },
        {
            "student_id": "STU002",
            "student_name": "Over Marks Student",
            "email": "over@university.edu",
            "course": "AI",
            "marks": 105.0,
            "enrollment_date": "2024-01-10",
        },
    ])
    validator = DataValidator()
    valid_df, rejected_df = validator.validate(df)

    assert len(valid_df) == 0
    assert len(rejected_df) == 2
    assert "out of allowed range" in rejected_df.iloc[0]["rejection_reason"]
    assert "out of allowed range" in rejected_df.iloc[1]["rejection_reason"]


def test_validation_invalid_email_regex():
    """Test that ill-formed email strings are flagged and quarantined."""
    df = pd.DataFrame([
        {
            "student_id": "STU001",
            "student_name": "Bad Email Student",
            "email": "not-an-email-at-all",
            "course": "AI",
            "marks": 80.0,
            "enrollment_date": "2024-01-10",
        }
    ])
    validator = DataValidator()
    valid_df, rejected_df = validator.validate(df)

    assert len(valid_df) == 0
    assert len(rejected_df) == 1
    assert "Invalid email syntax" in rejected_df.iloc[0]["rejection_reason"]


def test_validation_missing_values_and_batch_duplicate_pks():
    """Test missing mandatory field detection and intra-batch PK collision handling."""
    df = pd.DataFrame([
        {
            "student_id": "STU001",
            "student_name": "",  # Missing name
            "email": "missing.name@university.edu",
            "course": "CS",
            "marks": 85.0,
            "enrollment_date": "2024-01-10",
        },
        {
            "student_id": "STU002",
            "student_name": "Valid Student",
            "email": "valid@university.edu",
            "course": "CS",
            "marks": 90.0,
            "enrollment_date": "2024-01-10",
        },
        {
            "student_id": "STU002",  # Duplicate primary key in batch
            "student_name": "Duplicate Student",
            "email": "dup@university.edu",
            "course": "CS",
            "marks": 70.0,
            "enrollment_date": "2024-01-10",
        },
    ])
    validator = DataValidator()
    valid_df, rejected_df = validator.validate(df)

    assert len(valid_df) == 1
    assert valid_df.iloc[0]["student_id"] == "STU002"
    assert len(rejected_df) == 2
    reasons = " ".join(rejected_df["rejection_reason"].tolist())
    assert "Missing mandatory field 'student_name'" in reasons
    assert "Duplicate primary key 'STU002' within batch" in reasons


def test_save_rejected_records(tmp_path: Path):
    """Test saving rejected rows to CSV on disk."""
    rejected_df = pd.DataFrame([
        {
            "student_id": "STU999",
            "student_name": "Bad Record",
            "rejection_reason": "Test Failure",
        }
    ])
    out_file = tmp_path / "rejected.csv"
    validator = DataValidator()
    saved_path = validator.save_rejected(rejected_df, out_file)

    assert saved_path.exists()
    loaded = pd.read_csv(saved_path)
    assert len(loaded) == 1
    assert loaded.iloc[0]["rejection_reason"] == "Test Failure"
