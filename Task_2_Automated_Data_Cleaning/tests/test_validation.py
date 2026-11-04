"""
Tests for Module 8: Data Validation (DataValidator)
"""

import pandas as pd
import pytest
from src.validator import DataValidator


def test_validation_rules_segregation():
    """Test validation of required fields, ranges, unique keys, and regex patterns."""
    data = {
        "customer_id": [101, 102, 103, 104, 105, 105],  # 105 duplicate PK
        "customer_name": ["Alice", "", "Charlie", "David", "Eve", "Eve2"],  # idx 1 missing name
        "age": [25, 30, -5, 150, 40, 42],  # idx 2 negative, idx 3 > 100
        "salary": [50000.0, 60000.0, 70000.0, -100.0, 80000.0, 90000.0],  # idx 3 negative
        "email": [
            "alice@example.com",
            "bob@example.com",
            "charlie@example.com",
            "david@example.com",
            "bad-email",  # idx 4 bad regex
            "eve2@example.com",
        ],
    }
    df = pd.DataFrame(data)

    rules = {
        "primary_key": "customer_id",
        "required_columns": ["customer_id", "customer_name"],
        "numeric_ranges": {
            "age": {"min": 18, "max": 100},
            "salary": {"min": 0, "max": 1000000},
        },
        "regex_patterns": {
            "email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        },
    }

    validator = DataValidator(validation_rules=rules)
    valid_df, quarantined_df, summary = validator.validate(df)

    # Record 0 (Alice) should be valid
    assert len(valid_df) == 1
    assert valid_df.iloc[0]["customer_name"] == "Alice"

    # 5 records quarantined
    assert len(quarantined_df) == 5
    assert "rejection_reasons" in quarantined_df.columns

    # Verify rejection reasons recorded
    reasons_text = " ".join(quarantined_df["rejection_reasons"].tolist())
    assert "Missing mandatory field 'customer_name'" in reasons_text
    assert "below minimum threshold" in reasons_text
    assert "exceeds maximum threshold" in reasons_text
    assert "Duplicate primary key" in reasons_text
    assert "does not match pattern" in reasons_text
