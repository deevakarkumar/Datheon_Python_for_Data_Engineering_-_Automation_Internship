"""
Tests for Module 6: Date Normalization (DateNormalizer)
"""

import pandas as pd
import pytest
from src.dates import DateNormalizer


def test_date_normalizer_various_formats():
    """Test normalizing heterogeneous valid date representations to YYYY-MM-DD."""
    dates = pd.Series([
        "2026-10-01",
        "01-10-2026",
        "2026/10/01",
        "01 Oct 2026",
        "15 Jan 2023",
        "20-11-2022",
    ])
    normalizer = DateNormalizer(day_first=True, target_format="%Y-%m-%d")
    normalized, metrics = normalizer.normalize_series(dates)

    assert normalized.iloc[0] == "2026-10-01"
    assert normalized.iloc[1] == "2026-10-01"
    assert normalized.iloc[2] == "2026-10-01"
    assert normalized.iloc[3] == "2026-10-01"
    assert normalized.iloc[4] == "2023-01-15"
    assert normalized.iloc[5] == "2022-11-20"
    assert metrics["valid_dates"] == 6
    assert metrics["invalid_dates"] == 0


def test_date_normalizer_invalid_dates():
    """Test detection and handling of unparseable date strings."""
    dates = pd.Series(["99/99/9999", "not_a_date", "2026-02-31", "2023-05-10", ""])
    normalizer = DateNormalizer(day_first=True)
    normalized, metrics = normalizer.normalize_series(dates)

    assert pd.isna(normalized.iloc[0])
    assert pd.isna(normalized.iloc[1])
    assert pd.isna(normalized.iloc[2])
    assert normalized.iloc[3] == "2023-05-10"
    assert metrics["valid_dates"] == 1
    assert metrics["invalid_dates"] == 3  # 99/99/9999, not_a_date, 2026-02-31
    assert "99/99/9999" in metrics["invalid_samples"]
