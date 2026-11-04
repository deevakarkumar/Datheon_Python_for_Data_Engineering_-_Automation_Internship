"""
Missing Value Handling Module
-----------------------------
Provides deterministic and configurable imputation strategies for numerical,
categorical, and date features, alongside empty-column pruning and critical field tracking.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.MissingValues")


class MissingValueHandler:
    """
    Applies configurable imputation strategies across heterogeneous columns,
    logging all transformations for audit integrity.
    """

    def __init__(
        self,
        strategies: Optional[Dict[str, Any]] = None,
        drop_empty_threshold: float = 0.90,
    ):
        """
        Initialize MissingValueHandler.

        Args:
            strategies: Imputation strategy mapping containing:
                - 'numerical': {col: {'strategy': 'mean'|'median'|'custom', 'fill_value': ...}}
                - 'categorical': {col: {'strategy': 'mode'|'custom', 'fill_value': ...}}
                - 'critical_columns': [list of columns where missingness cannot be imputed]
            drop_empty_threshold: Drop columns with null percentage >= this value (0.0 - 1.0).
        """
        self.strategies = strategies or {}
        self.drop_empty_threshold = drop_empty_threshold

    def clean_empty_strings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert empty strings, whitespace-only strings, and text 'nan'/'null' to real NaN.
        """
        df_clean = df.copy()
        for col in df_clean.columns:
            if df_clean[col].dtype == "object" or pd.api.types.is_string_dtype(df_clean[col]):
                df_clean[col] = (
                    df_clean[col]
                    .astype(str)
                    .str.strip()
                    .replace({"": np.nan, "nan": np.nan, "NaN": np.nan, "None": np.nan, "null": np.nan, "<NA>": np.nan})
                )
        return df_clean

    def drop_sparse_columns(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Drop columns exceeding the drop_empty_threshold.

        Returns:
            Tuple of (pruned_dataframe, dropped_columns_list)
        """
        total_rows = len(df)
        if total_rows == 0:
            return df, []

        dropped_cols: List[str] = []
        df_pruned = df.copy()

        for col in df.columns:
            missing_ratio = df[col].isna().sum() / total_rows
            if missing_ratio >= self.drop_empty_threshold:
                dropped_cols.append(str(col))
                df_pruned = df_pruned.drop(columns=[col])
                logger.info(
                    "Dropping column '%s': missing ratio %.2f exceeds threshold %.2f",
                    col,
                    missing_ratio,
                    self.drop_empty_threshold,
                )

        return df_pruned, dropped_cols

    def handle(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute missing value imputation pipeline.

        Returns:
            Tuple of (imputed_dataframe, audit_report_dict)
        """
        # Step 1: Standardize whitespace into np.nan
        df_work = self.clean_empty_strings(df)

        # Step 2: Prune sparse / empty columns
        df_work, dropped_cols = self.drop_sparse_columns(df_work)

        operations: List[Dict[str, Any]] = []
        total_imputed = 0

        # Numerical Imputations
        num_rules = self.strategies.get("numerical", {})
        for col, rule in num_rules.items():
            if col in df_work.columns:
                series = pd.to_numeric(df_work[col], errors="coerce")
                missing_count = int(series.isna().sum())
                if missing_count > 0:
                    strategy = rule.get("strategy", "median").lower()
                    impute_value: Optional[float] = None

                    if strategy == "mean":
                        impute_value = float(series.mean()) if not series.empty else 0.0
                    elif strategy == "median":
                        impute_value = float(series.median()) if not series.empty else 0.0
                    elif strategy == "custom":
                        impute_value = float(rule.get("fill_value", 0.0))
                    else:
                        logger.warning("Unknown numerical strategy '%s' for '%s'", strategy, col)

                    if impute_value is not None:
                        df_work[col] = series.fillna(round(impute_value, 2))
                        total_imputed += missing_count
                        op = {
                            "column": col,
                            "type": "numerical",
                            "strategy": strategy,
                            "fill_value": round(impute_value, 2),
                            "records_imputed": missing_count,
                        }
                        operations.append(op)
                        logger.info("Imputed %d missing values in '%s' with %s=%.2f", missing_count, col, strategy, impute_value)

        # Categorical Imputations
        cat_rules = self.strategies.get("categorical", {})
        for col, rule in cat_rules.items():
            if col in df_work.columns:
                series = df_work[col]
                missing_count = int(series.isna().sum())
                if missing_count > 0:
                    strategy = rule.get("strategy", "mode").lower()
                    impute_value = None

                    if strategy == "mode":
                        mode_vals = series.dropna().mode()
                        impute_value = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
                    elif strategy == "custom":
                        impute_value = rule.get("fill_value", "Unknown")

                    if impute_value is not None:
                        df_work[col] = series.fillna(impute_value)
                        total_imputed += missing_count
                        op = {
                            "column": col,
                            "type": "categorical",
                            "strategy": strategy,
                            "fill_value": str(impute_value),
                            "records_imputed": missing_count,
                        }
                        operations.append(op)
                        logger.info("Imputed %d missing values in '%s' with %s='%s'", missing_count, col, strategy, impute_value)

        critical_columns = self.strategies.get("critical_columns", [])
        critical_missing_counts = {}
        for col in critical_columns:
            if col in df_work.columns:
                crit_missing = int(df_work[col].isna().sum())
                critical_missing_counts[col] = crit_missing

        report: Dict[str, Any] = {
            "dropped_columns": dropped_cols,
            "imputation_operations": operations,
            "total_imputed_cells": total_imputed,
            "critical_missing_counts": critical_missing_counts,
        }

        return df_work, report
