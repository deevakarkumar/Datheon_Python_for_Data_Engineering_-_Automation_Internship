"""
Data Validation Module
----------------------
Executes business logic and integrity rules, segregating valid records
from quarantined records, while appending clear rejection diagnostics.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import re
import numpy as np
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Validator")


class DataValidator:
    """
    Validates records against configurable schema integrity and domain constraints,
    quarantining failed rows with human-readable rejection reasons.
    """

    def __init__(self, validation_rules: Optional[Dict[str, Any]] = None):
        """
        Initialize DataValidator.

        Args:
            validation_rules: Mapping defining:
                - 'primary_key': primary identifier column
                - 'required_columns': list of non-nullable mandatory columns
                - 'numeric_ranges': {col: {'min': num, 'max': num}}
                - 'regex_patterns': {col: regex_str}
        """
        self.rules = validation_rules or {}

    def validate(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Validate DataFrame records, splitting into valid and quarantined sets.

        Args:
            df: Transformed Pandas DataFrame.

        Returns:
            Tuple of (valid_df, quarantined_df, validation_summary_dict)
        """
        total_records = len(df)
        if total_records == 0:
            return df, pd.DataFrame(), {"total_records": 0, "valid_count": 0, "invalid_count": 0, "violations": {}}

        # Initialize violation trackers per index
        # We map index -> list of error message strings
        violations: Dict[Any, List[str]] = {idx: [] for idx in df.index}
        violation_counts: Dict[str, int] = {}

        def record_violation(idx: Any, rule_name: str, message: str) -> None:
            violations[idx].append(message)
            violation_counts[rule_name] = violation_counts.get(rule_name, 0) + 1

        # Rule 1: Required columns non-null
        required_cols = self.rules.get("required_columns", [])
        for col in required_cols:
            if col in df.columns:
                series = df[col]
                # Check for null, NaN, pd.NA, or empty whitespace strings
                is_missing = series.isna()
                if series.dtype == "object" or pd.api.types.is_string_dtype(series):
                    is_missing = is_missing | (series.astype(str).str.strip() == "")

                failing_indices = df[is_missing].index
                for idx in failing_indices:
                    record_violation(idx, f"missing_required_{col}", f"Missing mandatory field '{col}'")
            else:
                logger.error("Required column '%s' is completely absent from DataFrame!", col)
                violation_counts[f"missing_column_{col}"] = total_records

        # Rule 2: Primary Key uniqueness
        primary_key = self.rules.get("primary_key")
        if primary_key and primary_key in df.columns:
            pk_series = df[primary_key]
            # Flag non-first duplicates
            dup_mask = pk_series.duplicated(keep="first") & pk_series.notna()
            dup_indices = df[dup_mask].index
            for idx in dup_indices:
                pk_val = df.loc[idx, primary_key]
                record_violation(idx, "duplicate_primary_key", f"Duplicate primary key '{pk_val}' in '{primary_key}'")

        # Rule 3: Numeric Ranges (e.g. age between 18 and 100, salary >= 0)
        numeric_ranges = self.rules.get("numeric_ranges", {})
        for col, bounds in numeric_ranges.items():
            if col in df.columns:
                num_series = pd.to_numeric(df[col], errors="coerce")
                min_val = bounds.get("min")
                max_val = bounds.get("max")

                if min_val is not None:
                    violating_min = df[num_series.notna() & (num_series < min_val)].index
                    for idx in violating_min:
                        actual = df.loc[idx, col]
                        record_violation(
                            idx,
                            f"range_{col}_below_min",
                            f"Value {actual} in '{col}' is below minimum threshold ({min_val})"
                        )

                if max_val is not None:
                    violating_max = df[num_series.notna() & (num_series > max_val)].index
                    for idx in violating_max:
                        actual = df.loc[idx, col]
                        record_violation(
                            idx,
                            f"range_{col}_above_max",
                            f"Value {actual} in '{col}' exceeds maximum threshold ({max_val})"
                        )

        # Rule 4: Regex Patterns (e.g., email format)
        regex_patterns = self.rules.get("regex_patterns", {})
        for col, pattern in regex_patterns.items():
            if col in df.columns:
                compiled = re.compile(pattern)
                str_series = df[col].dropna().astype(str).str.strip()
                for idx, val in str_series.items():
                    if val and not compiled.match(val):
                        record_violation(
                            idx,
                            f"regex_{col}",
                            f"Value '{val}' in '{col}' does not match pattern '{pattern}'"
                        )

        # Segregate valid vs quarantined
        invalid_indices = [idx for idx, msgs in violations.items() if len(msgs) > 0]
        valid_indices = [idx for idx, msgs in violations.items() if len(msgs) == 0]

        valid_df = df.loc[valid_indices].copy().reset_index(drop=True)
        quarantined_df = df.loc[invalid_indices].copy()

        # Add explicit rejection reasons column to quarantined records
        quarantined_df["rejection_reasons"] = [
            "; ".join(violations[idx]) for idx in invalid_indices
        ]
        quarantined_df = quarantined_df.reset_index(drop=True)

        logger.info(
            "Validation completed: %d valid records, %d quarantined records (out of %d total)",
            len(valid_df),
            len(quarantined_df),
            total_records,
        )

        summary: Dict[str, Any] = {
            "total_records_evaluated": total_records,
            "valid_records_count": len(valid_df),
            "quarantined_records_count": len(quarantined_df),
            "pass_rate_percentage": round(len(valid_df) / total_records * 100, 2) if total_records > 0 else 0.0,
            "rule_violation_breakdown": violation_counts,
        }

        return valid_df, quarantined_df, summary
