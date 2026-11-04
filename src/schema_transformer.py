"""
Schema Transformation Module
----------------------------
Standardizes column nomenclature (whitespace trimming and snake_case formatting),
applies custom renaming mappings, safely casts dtypes, enforces column ordering,
and flags schema mismatches.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import re
import numpy as np
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.SchemaTransformer")


class SchemaTransformer:
    """
    Transforms DataFrame structure and types according to an external schema specification.
    """

    def __init__(
        self,
        schema: Optional[Dict[str, str]] = None,
        rename_mapping: Optional[Dict[str, str]] = None,
        standardize_names: bool = True,
        target_column_order: Optional[List[str]] = None,
    ):
        """
        Initialize SchemaTransformer.

        Args:
            schema: Mapping of {column_name: pandas_dtype_string}.
            rename_mapping: Mapping of {old_column_name: new_column_name}.
            standardize_names: If True, automatically strip and convert to snake_case.
            target_column_order: Desired final column sequencing.
        """
        self.schema = schema or {}
        self.rename_mapping = rename_mapping or {}
        self.standardize_names = standardize_names
        self.target_column_order = target_column_order

    @staticmethod
    def to_snake_case(name: str) -> str:
        """
        Convert any raw string to standardized snake_case.

        Examples:
            "Cust_ID " -> "cust_id"
            " Annual Income" -> "annual_income"
            "Phone-Number" -> "phone_number"
            "Active Status" -> "active_status"
        """
        s = str(name).strip()
        # Replace dashes, slashes, periods, spaces with underscores
        s = re.sub(r"[\s\-\.\/]+", "_", s)
        # Handle CamelCase transitions (e.g. customerName -> customer_name)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        # Remove any non-alphanumeric/non-underscore characters
        s = re.sub(r"[^\w]", "", s)
        # Squash multiple underscores and lowercase
        s = re.sub(r"_+", "_", s).strip("_").lower()
        return s

    def standardize_headers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Trim and normalize column names into snake_case.
        """
        new_cols = {}
        for col in df.columns:
            new_cols[col] = self.to_snake_case(col) if self.standardize_names else str(col).strip()
        
        df_renamed = df.rename(columns=new_cols)
        logger.debug("Standardized columns: %s", new_cols)
        return df_renamed, new_cols

    def apply_rename_mapping(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Apply configuration-based column renaming.
        """
        if not self.rename_mapping:
            return df, {}

        # Match columns case-insensitively
        rename_dict = {}
        for col in df.columns:
            cleaned_col = str(col).lower()
            if cleaned_col in self.rename_mapping:
                rename_dict[col] = self.rename_mapping[cleaned_col]

        df_renamed = df.rename(columns=rename_dict)
        if rename_dict:
            logger.info("Applied column renaming: %s", rename_dict)
        return df_renamed, rename_dict

    @staticmethod
    def _convert_boolean_series(series: pd.Series) -> pd.Series:
        """
        Safely convert heterogeneous truthy/falsy strings into nullable boolean dtype.
        """
        mapping = {
            "true": True, "1": True, "yes": True, "y": True, "t": True,
            "false": False, "0": False, "no": False, "n": False, "f": False,
            True: True, False: False, 1: True, 0: False,
        }
        lowered = series.astype(str).str.strip().str.lower()
        mapped = lowered.map(mapping)
        return mapped.astype("boolean")

    def cast_types(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Dict[str, str]]]:
        """
        Safely cast columns into expected target schema types.
        """
        df_casted = df.copy()
        type_changes: Dict[str, Dict[str, str]] = {}

        for col, target_type in self.schema.items():
            if col not in df_casted.columns:
                continue

            orig_dtype = str(df_casted[col].dtype)
            try:
                target_lower = target_type.lower()
                if "int" in target_lower:
                    # Int64 handles NaN gracefully
                    df_casted[col] = pd.to_numeric(df_casted[col], errors="coerce").astype("Int64")
                elif "float" in target_lower:
                    df_casted[col] = pd.to_numeric(df_casted[col], errors="coerce").astype("float64")
                elif "bool" in target_lower:
                    df_casted[col] = self._convert_boolean_series(df_casted[col])
                elif "string" in target_lower or target_lower == "str":
                    df_casted[col] = df_casted[col].astype("string")
                elif "datetime" in target_lower:
                    df_casted[col] = pd.to_datetime(df_casted[col], errors="coerce")
                else:
                    df_casted[col] = df_casted[col].astype(target_type)

                new_dtype = str(df_casted[col].dtype)
                type_changes[col] = {"from": orig_dtype, "to": new_dtype}
                logger.debug("Casted column '%s' from %s to %s", col, orig_dtype, new_dtype)

            except Exception as exc:
                logger.warning("Failed to cast column '%s' to %s: %s", col, target_type, exc)

        return df_casted, type_changes

    def enforce_ordering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder columns according to target_column_order, appending any remaining columns.
        """
        if not self.target_column_order:
            return df

        ordered = [c for c in self.target_column_order if c in df.columns]
        remaining = [c for c in df.columns if c not in ordered]
        final_cols = ordered + remaining
        return df[final_cols]

    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute full schema transformation lifecycle.

        Returns:
            Tuple of (transformed_df, audit_log_dict)
        """
        # Step 1: Standardize header names
        df_std, std_mapping = self.standardize_headers(df)

        # Step 2: Apply custom renaming map
        df_renamed, rename_applied = self.apply_rename_mapping(df_std)

        # Step 3: Check missing vs unexpected columns
        present_cols = set(df_renamed.columns)
        expected_cols = set(self.schema.keys())

        missing_columns = list(expected_cols - present_cols)
        unexpected_columns = list(present_cols - expected_cols)

        if missing_columns:
            logger.warning("Missing expected schema columns: %s", missing_columns)
        if unexpected_columns:
            logger.info("Encountered unconfigured columns in dataset: %s", unexpected_columns)

        # Step 4: Safely cast dtypes
        df_typed, type_changes = self.cast_types(df_renamed)

        # Step 5: Enforce column sequencing
        df_ordered = self.enforce_ordering(df_typed)

        audit: Dict[str, Any] = {
            "standardized_headers": std_mapping,
            "renamed_columns": rename_applied,
            "type_changes": type_changes,
            "missing_expected_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
            "final_column_order": list(df_ordered.columns),
        }

        return df_ordered, audit
