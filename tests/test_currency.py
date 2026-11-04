"""
Tests for Module 5: Currency Normalization (CurrencyNormalizer)
"""

import pandas as pd
import pytest
from src.currency import CurrencyNormalizer


@pytest.mark.parametrize(
    "input_val,expected_num,expected_sym",
    [
        ("₹25,000", 25000.0, "₹"),
        ("INR 25000", 25000.0, "INR"),
        ("25,000 INR", 25000.0, "INR"),
        ("Rs. 25,000", 25000.0, "Rs."),
        ("Rs 107,926", 107926.0, "Rs"),
        ("95,990.00", 95990.0, None),
        ("₹ 194,680.50", 194680.5, "₹"),
        ("$500.25", 500.25, "$"),
        ("€1,200", 1200.0, "€"),
        ("-₹45,000", -45000.0, "₹"),
        ("Rs. -20,000", -20000.0, "Rs."),
        ("(₹1,500)", -1500.0, "₹"),
    ],
)
def test_clean_currency_string_valid(input_val, expected_num, expected_sym):
    """Test valid currency extraction and parsing."""
    num, sym = CurrencyNormalizer.clean_currency_string(input_val)
    assert num == expected_num
    assert sym == expected_sym


def test_clean_currency_string_invalid():
    """Test handling of invalid non-numeric currency strings."""
    num, sym = CurrencyNormalizer.clean_currency_string("NOT_A_SALARY")
    assert num is None

    num_null, sym_null = CurrencyNormalizer.clean_currency_string(None)
    assert num_null is None
    assert sym_null is None


def test_currency_normalize_series():
    """Test normalizing a Pandas Series containing mixed currency strings."""
    raw_series = pd.Series(["₹25,000", "INR 50,000.50", "corrupt_data", None, "-Rs. 1,000"])
    normalizer = CurrencyNormalizer(target_currency="INR")
    cleaned_series, stats = normalizer.normalize_series(raw_series)

    assert cleaned_series.iloc[0] == 25000.0
    assert cleaned_series.iloc[1] == 50000.5
    assert pd.isna(cleaned_series.iloc[2])
    assert pd.isna(cleaned_series.iloc[3])
    assert cleaned_series.iloc[4] == -1000.0
    assert stats["valid_normalized"] == 3
    assert stats["unparseable_records"] == 2
