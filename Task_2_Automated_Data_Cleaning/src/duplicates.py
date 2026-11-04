"""
Duplicate Detection and Removal Module
--------------------------------------
Identifies and purges exact and subset-based duplicate records,
preserving the first occurrence and tracking removal metrics.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Duplicates")


class DuplicateHandler:
    """
    Handles detection and removal of redundant records based on full rows
    or primary identifier subsets.
    """

    def __init__(self, subset: Optional[List[str]] = None, keep: str = "first"):
        """
        Initialize DuplicateHandler.

        Args:
            subset: Specific column names to consider for identifying duplicates.
                    If None, all columns are considered.
            keep: Which duplicate to retain ('first', 'last', False). Default: 'first'.
        """
        self.subset = subset
        self.keep = keep

    def process(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Remove duplicate rows from DataFrame.

        Args:
            df: Input Pandas DataFrame.

        Returns:
            Tuple of (cleaned_df, duplicate_metrics_dict)
        """
        initial_count = len(df)
        if initial_count == 0:
            return df, {"exact_duplicates_removed": 0, "subset_duplicates_removed": 0, "total_removed": 0}

        # Step 1: Detect and remove full-row exact duplicates
        exact_mask = df.duplicated(keep=self.keep)
        exact_duplicate_count = int(exact_mask.sum())
        df_no_exact = df.loc[~exact_mask].copy()

        # Step 2: If subset specified and valid in columns, check subset duplicates
        subset_duplicate_count = 0
        df_final = df_no_exact

        if self.subset:
            valid_subset = [c for c in self.subset if c in df_no_exact.columns]
            if valid_subset:
                subset_mask = df_no_exact.duplicated(subset=valid_subset, keep=self.keep)
                subset_duplicate_count = int(subset_mask.sum())
                df_final = df_no_exact.loc[~subset_mask].copy()
                logger.info(
                    "Removed %d duplicate records matching subset columns %s",
                    subset_duplicate_count,
                    valid_subset,
                )
            else:
                logger.warning(
                    "Specified duplicate subset %s does not match any DataFrame columns: %s",
                    self.subset,
                    list(df_no_exact.columns),
                )

        total_removed = initial_count - len(df_final)

        logger.info(
            "Duplicate processing complete: %d exact duplicates, %d subset duplicates removed. "
            "Remaining rows: %d (from %d)",
            exact_duplicate_count,
            subset_duplicate_count,
            len(df_final),
            initial_count,
        )

        metrics: Dict[str, Any] = {
            "initial_rows": initial_count,
            "exact_duplicates_removed": exact_duplicate_count,
            "subset_duplicates_removed": subset_duplicate_count,
            "total_duplicates_removed": total_removed,
            "final_rows": len(df_final),
            "subset_columns": self.subset,
        }

        return df_final, metrics
