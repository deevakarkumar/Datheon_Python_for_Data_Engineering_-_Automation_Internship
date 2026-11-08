"""
Data Upsert & Batch Processing Engine Module
--------------------------------------------
Implements high-performance, transaction-safe INSERT OR UPDATE logic,
preserving unchanged records and tracking granular operational metrics.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import DEFAULT_BATCH_SIZE, PRIMARY_KEY_COLUMN, TABLE_NAME
from src.db_connection import DatabaseManager, get_logger
from src.schema import Student

logger = get_logger("UpsertEngine")


@dataclass
class UpsertResult:
    """Dataclass encapsulating granular metrics from an upsert operation."""
    total_records_read: int = 0
    new_records_inserted: int = 0
    existing_records_updated: int = 0
    unchanged_records: int = 0
    rejected_records: int = 0
    batches_processed: int = 0
    execution_duration_sec: float = 0.0

    @property
    def total_records_processed(self) -> int:
        return self.total_records_read

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_records_processed"] = self.total_records_processed
        return data


class UpsertEngine:
    """
    Executes batched, transaction-safe upsert operations against the database.
    """

    def __init__(self, db_manager: DatabaseManager, batch_size: int = DEFAULT_BATCH_SIZE):
        self.db_manager = db_manager
        self.batch_size = max(1, batch_size)

    def upsert(self, valid_df: pd.DataFrame, rejected_count: int = 0) -> UpsertResult:
        """
        Execute batched upsert on validated DataFrame with transaction management.

        Args:
            valid_df: Cleaned and validated DataFrame.
            rejected_count: Number of records quarantined during validation.

        Returns:
            UpsertResult object with dynamically calculated metrics.
        """
        start_time = datetime.now()
        total_read = len(valid_df) + rejected_count

        result = UpsertResult(
            total_records_read=total_read,
            rejected_records=rejected_count,
        )

        if valid_df.empty:
            logger.info("No valid records to upsert.")
            result.execution_duration_sec = round((datetime.now() - start_time).total_seconds(), 3)
            return result

        records = valid_df.to_dict(orient="records")
        total_valid = len(records)
        num_batches = (total_valid + self.batch_size - 1) // self.batch_size

        logger.info(
            "Starting batch upsert: %d valid records across %d batch(es) (batch_size=%d)...",
            total_valid,
            num_batches,
            self.batch_size,
        )

        # Process each batch inside a dedicated transaction scope
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_valid)
            batch = records[start_idx:end_idx]

            self._process_batch(batch, result)
            result.batches_processed += 1

        result.execution_duration_sec = round((datetime.now() - start_time).total_seconds(), 3)
        logger.info(
            "Upsert complete in %.3fs: %d inserted, %d updated, %d unchanged, %d rejected.",
            result.execution_duration_sec,
            result.new_records_inserted,
            result.existing_records_updated,
            result.unchanged_records,
            result.rejected_records,
        )

        return result

    def _process_batch(self, batch: List[Dict[str, Any]], result: UpsertResult) -> None:
        """
        Process a single batch within an isolated transaction.
        Differentiates between new, modified, and unchanged records.
        """
        batch_ids = [str(r[PRIMARY_KEY_COLUMN]) for r in batch]
        now = datetime.utcnow()

        with self.db_manager.get_session() as session:
            # 1. Fetch all existing records in this batch in a single query
            existing_students = (
                session.query(Student)
                .filter(Student.student_id.in_(batch_ids))
                .all()
            )
            existing_map = {s.student_id: s for s in existing_students}

            inserts: List[Student] = []

            for row in batch:
                sid = str(row[PRIMARY_KEY_COLUMN])
                incoming_name = str(row["student_name"]).strip()
                incoming_email = str(row["email"]).strip()
                incoming_course = str(row["course"]).strip()
                incoming_marks = float(row["marks"])
                incoming_date = str(row["enrollment_date"]).strip()

                if sid not in existing_map:
                    # New record -> Insert
                    new_student = Student(
                        student_id=sid,
                        student_name=incoming_name,
                        email=incoming_email,
                        course=incoming_course,
                        marks=incoming_marks,
                        enrollment_date=incoming_date,
                        last_updated=now,
                    )
                    inserts.append(new_student)
                    result.new_records_inserted += 1
                else:
                    existing = existing_map[sid]
                    # Check if any values changed
                    has_changed = (
                        existing.student_name != incoming_name
                        or existing.email != incoming_email
                        or existing.course != incoming_course
                        or abs(existing.marks - incoming_marks) > 1e-5
                        or existing.enrollment_date != incoming_date
                    )

                    if has_changed:
                        # Existing record with modifications -> Update
                        existing.student_name = incoming_name
                        existing.email = incoming_email
                        existing.course = incoming_course
                        existing.marks = incoming_marks
                        existing.enrollment_date = incoming_date
                        existing.last_updated = now
                        result.existing_records_updated += 1
                    else:
                        # Identical values -> Preserve without write
                        result.unchanged_records += 1

            if inserts:
                session.bulk_save_objects(inserts)
