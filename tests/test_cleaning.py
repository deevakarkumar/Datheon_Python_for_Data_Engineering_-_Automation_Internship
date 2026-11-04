"""
Tests for Module 3 (Missing Values) and Module 4 (Duplicates)
"""

import numpy as np
import pandas as pd
import pytest
from src.duplicates import DuplicateHandler
from src.missing_values import MissingValueHandler


def test_missing_values_imputation():
    """Test numerical mean/median imputation and categorical mode imputation."""
    data = {
        "age": [20, 30, np.nan, 40],
        "salary": [10000.0, np.nan, 30000.0, 50000.0],
        "city": ["Mumbai", "Delhi", np.nan, "Mumbai"],
        "empty_col": [np.nan, np.nan, np.nan, np.nan],
    }
    df = pd.DataFrame(data)

    strategies = {
        "numerical": {
            "age": {"strategy": "median"},
            "salary": {"strategy": "mean"},
        },
        "categorical": {
            "city": {"strategy": "mode"},
        },
    }

    handler = MissingValueHandler(strategies=strategies, drop_empty_threshold=0.90)
    df_imputed, audit = handler.handle(df)

    # Empty column dropped
    assert "empty_col" not in df_imputed.columns
    assert "empty_col" in audit["dropped_columns"]

    # Age median of [20, 30, 40] is 30.0
    assert df_imputed["age"].iloc[2] == 30.0

    # Salary mean of [10000, 30000, 50000] is 30000.0
    assert df_imputed["salary"].iloc[1] == 30000.0

    # City mode of [Mumbai, Delhi, Mumbai] is Mumbai
    assert df_imputed["city"].iloc[2] == "Mumbai"


def test_duplicate_handler_exact_and_subset():
    """Test exact duplicate elimination and subset-based primary key deduplication."""
    data = {
        "customer_id": [101, 102, 101, 103, 101],
        "name": ["Alice", "Bob", "Alice", "Charlie", "Alice Altered"],
        "age": [25, 30, 25, 35, 25],
    }
    df = pd.DataFrame(data)

    # Row 0 and Row 2 are exact duplicates
    # Row 4 shares customer_id 101 with row 0
    handler = DuplicateHandler(subset=["customer_id"], keep="first")
    df_clean, metrics = handler.process(df)

    assert len(df_clean) == 3
    assert list(df_clean["customer_id"]) == [101, 102, 103]
    assert metrics["exact_duplicates_removed"] == 1
    assert metrics["subset_duplicates_removed"] == 1
    assert metrics["total_duplicates_removed"] == 2
