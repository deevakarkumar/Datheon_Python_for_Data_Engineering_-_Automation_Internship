"""
Database Verification & Integrity Checker Module
------------------------------------------------
Provides diagnostic tools to verify table counts, duplicate keys,
schema integrity constraints, and query records for inspection.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from config import PRIMARY_KEY_COLUMN, TABLE_NAME
from src.db_connection import DatabaseManager, get_logger
from src.schema import Student

logger = get_logger("VerificationEngine")


class DatabaseVerifier:
    """
    Verifies database state, checks structural integrity, and retrieves audit samples.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def count_records(self) -> int:
        """Return the total number of records currently stored in the students table."""
        with self.db_manager.get_session() as session:
            count = session.query(func.count(Student.student_id)).scalar()
            return count or 0

    def check_duplicate_primary_keys(self) -> List[Dict[str, Any]]:
        """
        Verify that no primary key collisions exist in the database.
        Returns a list of duplicate IDs if any exist (should always be empty).
        """
        with self.db_manager.get_session() as session:
            duplicates = (
                session.query(Student.student_id, func.count(Student.student_id).label("count"))
                .group_by(Student.student_id)
                .having(func.count(Student.student_id) > 1)
                .all()
            )
            return [{"student_id": d[0], "count": d[1]} for d in duplicates]

    def check_duplicate_emails(self) -> List[Dict[str, Any]]:
        """
        Verify that email uniqueness constraints are fully respected.
        """
        with self.db_manager.get_session() as session:
            duplicates = (
                session.query(Student.email, func.count(Student.email).label("count"))
                .group_by(Student.email)
                .having(func.count(Student.email) > 1)
                .all()
            )
            return [{"email": d[0], "count": d[1]} for d in duplicates]

    def run_sqlite_integrity_check(self) -> str:
        """
        Execute SQLite native PRAGMA integrity_check.
        """
        try:
            with self.db_manager.engine.connect() as conn:
                res = conn.execute(text("PRAGMA integrity_check")).scalar()
                return str(res)
        except Exception as exc:
            logger.warning("Could not run PRAGMA integrity_check: %s", exc)
            return "N/A"

    def get_summary(self) -> Dict[str, Any]:
        """
        Assemble comprehensive health and verification metrics for the database.
        """
        total_records = self.count_records()
        duplicate_pks = self.check_duplicate_primary_keys()
        duplicate_emails = self.check_duplicate_emails()
        integrity_status = self.run_sqlite_integrity_check()

        is_healthy = len(duplicate_pks) == 0 and len(duplicate_emails) == 0 and integrity_status in ("ok", "N/A")

        summary = {
            "table_name": TABLE_NAME,
            "total_records": total_records,
            "duplicate_primary_keys": len(duplicate_pks),
            "duplicate_emails": len(duplicate_emails),
            "sqlite_integrity_check": integrity_status,
            "database_health": "HEALTHY" if is_healthy else "CORRUPTED",
        }

        logger.info("Database verification: %d total records, Health: %s", total_records, summary["database_health"])
        return summary

    def fetch_records(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve a slice of student records for CLI inspection or reporting.
        """
        with self.db_manager.get_session() as session:
            students = (
                session.query(Student)
                .order_by(Student.student_id)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [s.to_dict() for s in students]

    def to_dataframe(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Export current database records into a Pandas DataFrame.
        """
        query = session_query = f"SELECT * FROM {TABLE_NAME} ORDER BY {PRIMARY_KEY_COLUMN}"
        if limit:
            query += f" LIMIT {limit}"
        return pd.read_sql_query(query, con=self.db_manager.engine)
