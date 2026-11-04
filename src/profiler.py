"""
Data Inspection and Profiling Module
------------------------------------
Performs comprehensive statistical and structural profiling of datasets
prior to data cleaning and transformations.
"""

from typing import Any, Dict, List, Optional
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Profiler")


class DataProfiler:
    """
    Automated inspector for tabular datasets, identifying missingness,
    uniqueness, duplicates, data types, and numerical outliers.
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize the DataProfiler.

        Args:
            df: Input Pandas DataFrame to inspect.
        """
        self.df = df.copy()

    def profile(self) -> Dict[str, Any]:
        """
        Execute profiling and return a detailed diagnostic dictionary.

        Returns:
            Dictionary containing dataset metrics and column-level statistics.
        """
        total_rows = len(self.df)
        total_cols = len(self.df.columns)
        exact_duplicates = int(self.df.duplicated().sum())

        logger.info(
            "Profiling dataset: %d rows, %d columns, %d duplicate rows found",
            total_rows,
            total_cols,
            exact_duplicates,
        )

        column_profiles: Dict[str, Dict[str, Any]] = {}
        empty_columns: List[str] = []

        for col in self.df.columns:
            series = self.df[col]
            # Consider whitespace-only string values as null for accurate profiling
            is_str = series.dtype == "object" or pd.api.types.is_string_dtype(series)
            if is_str:
                cleaned_series = series.astype(str).str.strip().replace({"": np.nan, "None": np.nan, "nan": np.nan})
            else:
                cleaned_series = series

            missing_count = int(cleaned_series.isna().sum())
            missing_pct = round((missing_count / total_rows * 100), 2) if total_rows > 0 else 0.0
            unique_count = int(cleaned_series.nunique(dropna=True))

            if missing_count == total_rows and total_rows > 0:
                empty_columns.append(str(col))

            col_stat: Dict[str, Any] = {
                "inferred_type": str(series.dtype),
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "unique_values": unique_count,
            }

            column_profiles[str(col)] = col_stat

        outliers = self._detect_outliers()

        report: Dict[str, Any] = {
            "total_records": total_rows,
            "total_columns": total_cols,
            "exact_duplicate_rows": exact_duplicates,
            "empty_columns": empty_columns,
            "column_statistics": column_profiles,
            "numerical_outliers": outliers,
        }

        return report

    def _detect_outliers(self) -> Dict[str, Dict[str, Any]]:
        """
        Identify numerical outliers using the Interquartile Range (IQR) rule.

        Returns:
            Dictionary mapping numerical columns to outlier metrics and boundaries.
        """
        outlier_report: Dict[str, Dict[str, Any]] = {}

        for col in self.df.columns:
            # Try converting to numeric to detect outliers even if stored as object strings
            numeric_series = pd.to_numeric(self.df[col], errors="coerce").dropna()
            if len(numeric_series) >= 10:  # Meaningful sample for IQR
                q1 = float(numeric_series.quantile(0.25))
                q3 = float(numeric_series.quantile(0.75))
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                outliers = numeric_series[
                    (numeric_series < lower_bound) | (numeric_series > upper_bound)
                ]
                outlier_count = int(len(outliers))

                if outlier_count > 0:
                    outlier_report[str(col)] = {
                        "q1": round(q1, 2),
                        "q3": round(q3, 2),
                        "iqr": round(iqr, 2),
                        "lower_bound": round(lower_bound, 2),
                        "upper_bound": round(upper_bound, 2),
                        "outlier_count": outlier_count,
                        "sample_outliers": [round(float(v), 2) for v in outliers.head(5).tolist()],
                    }

        return outlier_report

    def generate_summary_text(self) -> str:
        """
        Render a concise, human-readable terminal summary of the profiling findings.

        Returns:
            Formatted string report.
        """
        profile = self.profile()
        lines = [
            "=" * 60,
            "             DATASET PROFILING SUMMARY             ",
            "=" * 60,
            f"Total Records     : {profile['total_records']}",
            f"Total Columns     : {profile['total_columns']}",
            f"Exact Duplicates  : {profile['exact_duplicate_rows']}",
            f"Empty Columns     : {', '.join(profile['empty_columns']) if profile['empty_columns'] else 'None'}",
            "-" * 60,
            f"{'Column Name':<25} {'Missing':<10} {'Unique':<10} {'Dtype':<10}",
            "-" * 60,
        ]

        for col, stats in profile["column_statistics"].items():
            col_name = (col[:22] + "...") if len(col) > 25 else col
            missing_info = f"{stats['missing_count']} ({stats['missing_percentage']}%)"
            lines.append(
                f"{col_name:<25} {missing_info:<10} {stats['unique_values']:<10} {stats['inferred_type']:<10}"
            )

        if profile["numerical_outliers"]:
            lines.append("-" * 60)
            lines.append("Detected Numerical Outliers (IQR Method):")
            for col, o_info in profile["numerical_outliers"].items():
                lines.append(
                    f"  - {col}: {o_info['outlier_count']} outliers "
                    f"[Bounds: {o_info['lower_bound']} to {o_info['upper_bound']}], "
                    f"Sample: {o_info['sample_outliers']}"
                )

        lines.append("=" * 60)
        return "\n".join(lines)
