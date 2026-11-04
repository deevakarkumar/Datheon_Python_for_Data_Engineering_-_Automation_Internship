"""
Tests for Module 7: Schema Transformation (SchemaTransformer)
"""

import pandas as pd
import pytest
from src.schema_transformer import SchemaTransformer


def test_snake_case_conversion():
    """Test string conversion to snake_case."""
    assert SchemaTransformer.to_snake_case(" Cust_ID ") == "cust_id"
    assert SchemaTransformer.to_snake_case("Annual Income ") == "annual_income"
    assert SchemaTransformer.to_snake_case("Phone-Number") == "phone_number"
    assert SchemaTransformer.to_snake_case("CustomerName") == "customer_name"
    assert SchemaTransformer.to_snake_case("Active Status") == "active_status"


def test_schema_transformer_full():
    """Test standardization, renaming, casting, and ordering."""
    data = {
        " Cust_ID ": ["101", "102"],
        "Customer Name": [" Alice ", " Bob "],
        "Active Status": ["yes", "0"],
        "Extra_Col": [1, 2],
    }
    df = pd.DataFrame(data)

    schema = {
        "customer_id": "Int64",
        "customer_name": "string",
        "is_active": "boolean",
    }
    rename_mapping = {
        "cust_id": "customer_id",
        "customer_name": "customer_name",
        "active_status": "is_active",
    }
    target_order = ["customer_id", "customer_name", "is_active", "extra_col"]

    transformer = SchemaTransformer(
        schema=schema,
        rename_mapping=rename_mapping,
        standardize_names=True,
        target_column_order=target_order,
    )

    df_trans, audit = transformer.transform(df)

    assert list(df_trans.columns) == target_order
    assert str(df_trans["customer_id"].dtype) == "Int64"
    assert str(df_trans["customer_name"].dtype) == "string"
    assert str(df_trans["is_active"].dtype) == "boolean"
    assert df_trans["is_active"].iloc[0] == True
    assert df_trans["is_active"].iloc[1] == False
