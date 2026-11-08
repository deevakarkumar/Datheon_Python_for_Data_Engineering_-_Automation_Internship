"""
Data Validation Module
----------------------
Validates incoming CSV data against schema rules, integrity constraints,
and business rules. Isolates rejected records with explicit failure reasons.
"""

from pathlib import Path
import re
from typing import List, Optional, Tuple
import pandas as pd

from config import (
    EMAIL_REGEX_PATTERN,
    MAX_MARKS,
    MIN_MARKS,
    PRIMARY_KEY_COLUMN,
    REJECTED_RECORDS_CSV,
    REQUIRED_COLUMNS,
)
from src.db_connection import get_logger

logger = get_logger("DataValidator")


class ValidationError(Exception):
    """Custom exception raised when structural dataset validation fails."""
    pass


class DataValidator:
    """
    Validates DataFrames and segregates valid records from quarantined records.
    """

    def __init__(
        self,
        required_columns: Optional[List[str]] = None,
        email_regex: Optional[str] = None,
        min_marks: float = MIN_MARKS,
        max_marks: float = MAX_MARKS,
    ):
        self.required_columns = required_columns or REQUIRED_COLUMNS
        self.email_regex = re.compile(email_regex or EMAIL_REGEX_PATTERN)
        self.min_marks = min_marks
        self.max_marks = max_marks

    def validate_structure(self, df: pd.DataFrame) -> None:
        """
        Validate table boundaries and presence of required columns.
        """
        if df.empty:
            raise ValidationError("CSV dataset is empty (0 records).")

        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            raise ValidationError(f"Missing mandatory column(s): {', '.join(missing_cols)}")

    def validate(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Perform row-level validation and quarantine invalid records.

        Returns:
            Tuple of (valid_records_df, rejected_records_df)
        """
        self.validate_structure(df)
        logger.info("Executing row-level validation across %d records...", len(df))

        working_df = df.copy()
        rejection_reasons: List[Optional[str]] = []
        seen_ids = set()

        # Date validation regex (YYYY-MM-DD)
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        for idx, row in working_df.iterrows():
            errors = []

            # 1. Primary key presence and uniqueness check within batch
            pk_val = row.get(PRIMARY_KEY_COLUMN)
            if pd.isna(pk_val) or str(pk_val).strip() == "":
                errors.append("Missing primary key 'student_id'")
            else:
                pk_str = str(pk_val).strip()
                if pk_str in seen_ids:
                    errors.append(f"Duplicate primary key '{pk_str}' within batch")
                else:
                    seen_ids.add(pk_str)

            # 2. Check missing mandatory fields
            for col in self.required_columns:
                val = row.get(col)
                if pd.isna(val) or (isinstance(val, str) and val.strip() == ""):
                    if f"Missing mandatory field '{col}'" not in errors:
                        errors.append(f"Missing mandatory field '{col}'")

            # 3. Email syntax validation
            email_val = row.get("email")
            if pd.notna(email_val) and isinstance(email_val, str) and email_val.strip():
                if not self.email_regex.match(email_val.strip()):
                    errors.append(f"Invalid email syntax: '{email_val}'")

            # 4. Marks numeric type and range validation
            marks_val = row.get("marks")
            if pd.notna(marks_val):
                try:
                    num_marks = float(marks_val)
                    if num_marks < self.min_marks or num_marks > self.max_marks:
                        errors.append(f"Marks {num_marks} out of allowed range [{self.min_marks}, {self.max_marks}]")
                except (ValueError, TypeError):
                    errors.append(f"Non-numeric marks value: '{marks_val}'")

            # 5. Enrollment date format validation
            date_val = row.get("enrollment_date")
            if pd.notna(date_val) and isinstance(date_val, str) and date_val.strip():
                if not date_pattern.match(date_val.strip()):
                    errors.append(f"Enrollment date '{date_val}' does not match ISO format YYYY-MM-DD")

            if errors:
                rejection_reasons.append("; ".join(errors))
            else:
                rejection_reasons.append(None)

        working_df["rejection_reason"] = rejection_reasons

        valid_mask = working_df["rejection_reason"].isna()
        valid_df = working_df[valid_mask].drop(columns=["rejection_reason"]).copy()
        rejected_df = working_df[~valid_mask].copy()

        # Type cast valid records
        if not valid_df.empty:
            valid_df[PRIMARY_KEY_COLUMN] = valid_df[PRIMARY_KEY_COLUMN].astype(str).str.strip()
            valid_df["student_name"] = valid_df["student_name"].astype(str).str.strip()
            valid_df["email"] = valid_df["email"].astype(str).str.strip()
            valid_df["course"] = valid_df["course"].astype(str).str.strip()
            valid_df["marks"] = valid_df["marks"].astype(float)
            valid_df["enrollment_date"] = valid_df["enrollment_date"].astype(str).str.strip()

        logger.info(
            "Validation completed: %d valid records, %d quarantined records.",
            len(valid_df),
            len(rejected_df),
        )
        return valid_df, rejected_df

    def save_rejected(self, rejected_df: pd.DataFrame, output_path: Optional[Path] = None) -> Path:
        """
        Persist quarantined invalid records to CSV for auditability.
        """
        target_path = output_path or REJECTED_RECORDS_CSV
        target_path.parent.mkdir(parents=True, exist_ok=True)
        rejected_df.to_csv(target_path, index=False, encoding="utf-8")
        logger.info("Saved %d quarantined record(s) to %s", len(rejected_df), target_path)
        return target_path
