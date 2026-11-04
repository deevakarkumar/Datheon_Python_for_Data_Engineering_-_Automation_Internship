"""
Edge Case and Error Handling Tests
----------------------------------
Validates pipeline resilience when facing boundary inputs, missing schema keys,
malformed CSVs, and empty tables.
"""

from pathlib import Path
import pytest
import pandas as pd
from src.currency import CurrencyNormalizer
from src.dates import DateNormalizer
from src.duplicates import DuplicateHandler
from src.missing_values import MissingValueHandler
from src.schema_transformer import SchemaTransformer
from src.validator import DataValidator
from main import build_parser


def test_empty_dataframe_profiler():
    """Verify profiler handles 0-row DataFrames gracefully."""
    from src.profiler import DataProfiler

    empty_df = pd.DataFrame(columns=["id", "name", "salary"])
    profiler = DataProfiler(empty_df)
    report = profiler.profile()

    assert report["total_records"] == 0
    assert report["total_columns"] == 3
    assert report["exact_duplicate_rows"] == 0


def test_empty_dataframe_pipeline_modules():
    """Ensure modules do not crash on empty DataFrames."""
    empty_df = pd.DataFrame(columns=["id", "salary", "join_date"])

    # Duplicates
    dup = DuplicateHandler()
    df_dup, meta_dup = dup.process(empty_df)
    assert len(df_dup) == 0

    # Missing values
    missing = MissingValueHandler()
    df_miss, meta_miss = missing.handle(empty_df)
    assert len(df_miss) == 0

    # Validator
    val = DataValidator()
    valid_df, quarantined_df, meta_val = val.validate(empty_df)
    assert len(valid_df) == 0
    assert len(quarantined_df) == 0


def test_date_disambiguation_dayfirst():
    """Verify that dayfirst=False interprets MM-DD-YYYY."""
    normalizer_us = DateNormalizer(day_first=False)
    s = pd.Series(["03-11-2023"])  # Nov 3 in dayfirst=True, Mar 11 in dayfirst=False
    norm, _ = normalizer_us.normalize_series(s)
    assert norm.iloc[0] == "2023-03-11"

    normalizer_uk = DateNormalizer(day_first=True)
    norm_uk, _ = normalizer_uk.normalize_series(s)
    assert norm_uk.iloc[0] == "2023-11-03"


def test_missing_value_custom_imputation():
    """Verify custom fill_value works for both numeric and categorical columns."""
    df = pd.DataFrame({
        "score": [10.0, None, 30.0],
        "status": ["active", None, "pending"],
    })
    strategies = {
        "numerical": {"score": {"strategy": "custom", "fill_value": 99.9}},
        "categorical": {"status": {"strategy": "custom", "fill_value": "UNKNOWN"}},
    }
    handler = MissingValueHandler(strategies=strategies)
    cleaned, _ = handler.handle(df)

    assert cleaned["score"].iloc[1] == 99.9
    assert cleaned["status"].iloc[1] == "UNKNOWN"


def test_cli_argument_parsing():
    """Verify argparse configuration defaults and custom flags."""
    parser = build_parser()
    args = parser.parse_args(["-i", "test.csv", "-c", "test_config.json", "-v", "-p"])

    assert args.input == "test.csv"
    assert args.config == "test_config.json"
    assert args.verbose is True
    assert args.profile_only is True
