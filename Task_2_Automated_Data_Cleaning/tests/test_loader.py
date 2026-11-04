"""
Tests for Module 1: Dataset Input and Loading (DataLoader)
"""

from pathlib import Path
import pytest
import pandas as pd
from src.loader import DataLoader, DataLoaderError


def test_loader_success(tmp_path: Path):
    """Test loading a standard valid CSV file."""
    csv_file = tmp_path / "test_valid.csv"
    csv_file.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n", encoding="utf-8")

    loader = DataLoader(csv_file)
    df, meta = loader.load()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "value"]
    assert meta["row_count"] == 2
    assert meta["col_count"] == 3
    assert meta["encoding"] in ["utf-8", "utf-8-sig"]


def test_loader_encoding_fallback(tmp_path: Path):
    """Test fallback to latin1 when reading encoded files with non-UTF-8 characters."""
    csv_file = tmp_path / "test_latin1.csv"
    # Write latin1 encoded text
    with open(csv_file, "wb") as f:
        f.write("id,city\n1,München\n2,São Paulo\n".encode("latin1"))

    loader = DataLoader(csv_file)
    df, meta = loader.load()

    assert len(df) == 2
    assert meta["encoding"] in ["latin1", "cp1252", "iso-8859-1"]


def test_loader_file_not_found():
    """Test DataLoaderError raised for non-existent file."""
    loader = DataLoader("non_existent_directory/file.csv")
    with pytest.raises(DataLoaderError, match="not found"):
        loader.load()


def test_loader_empty_file(tmp_path: Path):
    """Test DataLoaderError raised for 0-byte empty file."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")

    loader = DataLoader(empty_file)
    with pytest.raises(DataLoaderError, match="empty"):
        loader.load()
