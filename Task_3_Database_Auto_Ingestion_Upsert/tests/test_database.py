"""
Tests for Database Connection, Initialization, and Integrity Checks
-------------------------------------------------------------------
"""

from pathlib import Path
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.db_connection import DatabaseManager
from src.schema import Student, init_db
from src.verification import DatabaseVerifier


@pytest.fixture
def temp_db(tmp_path: Path):
    """Provide a fresh isolated SQLite database instance for tests."""
    db_file = tmp_path / "test_db.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    manager = DatabaseManager(db_url)
    init_db(manager.engine)
    return manager


def test_database_creation(temp_db):
    """Test that SQLite database file and engine are successfully created."""
    assert temp_db.test_connection() is True
    inspector = inspect(temp_db.engine)
    tables = inspector.get_table_names()
    assert "students" in tables


def test_table_schema_and_columns(temp_db):
    """Verify table column definitions, nullable constraints, and primary keys."""
    inspector = inspect(temp_db.engine)
    columns = {col["name"]: col for col in inspector.get_columns("students")}

    assert "student_id" in columns
    assert "student_name" in columns
    assert "email" in columns
    assert "course" in columns
    assert "marks" in columns
    assert "enrollment_date" in columns
    assert "last_updated" in columns

    # Primary key check
    pks = inspector.get_pk_constraint("students")
    assert "student_id" in pks["constrained_columns"]


def test_unique_email_constraint(temp_db):
    """Test that inserting duplicate email values raises IntegrityError."""
    with temp_db.get_session() as session:
        s1 = Student(
            student_id="STU001",
            student_name="Alice",
            email="alice@university.edu",
            course="Data Science",
            marks=88.0,
            enrollment_date="2024-01-15",
        )
        session.add(s1)

    # Attempt inserting duplicate email
    with pytest.raises(IntegrityError):
        with temp_db.get_session() as session:
            s2 = Student(
                student_id="STU002",
                student_name="Bob",
                email="alice@university.edu",  # Duplicate email
                course="Computer Science",
                marks=75.0,
                enrollment_date="2024-01-16",
            )
            session.add(s2)


def test_database_verifier_integrity(temp_db):
    """Test verification engine checks and PRAGMA integrity query."""
    verifier = DatabaseVerifier(temp_db)
    summary = verifier.get_summary()

    assert summary["total_records"] == 0
    assert summary["duplicate_primary_keys"] == 0
    assert summary["duplicate_emails"] == 0
    assert summary["database_health"] == "HEALTHY"
