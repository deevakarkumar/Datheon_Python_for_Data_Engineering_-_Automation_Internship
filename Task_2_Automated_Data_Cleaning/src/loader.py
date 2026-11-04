"""
Dataset Input and Loading Module
--------------------------------
Handles resilient ingestion of CSV datasets using Pandas, supporting
multi-encoding detection, empty file checks, and structural verification.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Loader")


class DataLoaderError(Exception):
    """Custom exception raised when data loading fails."""
    pass


class DataLoader:
    """
    Robust CSV dataset loader with encoding fallback and structural validation.
    """

    ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]

    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize the DataLoader.

        Args:
            file_path: Path to the CSV file to load.
        """
        self.file_path = Path(file_path)

    def load(self) -> Tuple[pd.DataFrame, Dict[str, Union[int, List[str], str]]]:
        """
        Load the dataset from disk into a Pandas DataFrame.

        Returns:
            Tuple of (DataFrame, metadata_dict)

        Raises:
            DataLoaderError: If the file is missing, empty, or unparseable.
        """
        if not self.file_path.exists():
            msg = f"Dataset file not found at path: {self.file_path}"
            logger.error(msg)
            raise DataLoaderError(msg)

        if not self.file_path.is_file():
            msg = f"Specified path is not a file: {self.file_path}"
            logger.error(msg)
            raise DataLoaderError(msg)

        if self.file_path.stat().st_size == 0:
            msg = f"The dataset file is empty (0 bytes): {self.file_path}"
            logger.error(msg)
            raise DataLoaderError(msg)

        df: Optional[pd.DataFrame] = None
        successful_encoding: Optional[str] = None

        for encoding in self.ENCODINGS_TO_TRY:
            try:
                logger.debug("Attempting to load CSV with encoding '%s'", encoding)
                df = pd.read_csv(self.file_path, encoding=encoding, dtype=str)
                successful_encoding = encoding
                break
            except (UnicodeDecodeError, pd.errors.ParserError) as exc:
                logger.warning("Failed loading with encoding '%s': %s", encoding, exc)
                continue
            except Exception as exc:
                msg = f"Unexpected error while reading CSV: {exc}"
                logger.error(msg)
                raise DataLoaderError(msg) from exc

        if df is None:
            msg = (
                f"Failed to decode '{self.file_path.name}' using supported encodings: "
                f"{', '.join(self.ENCODINGS_TO_TRY)}"
            )
            logger.error(msg)
            raise DataLoaderError(msg)

        if df.empty and len(df.columns) == 0:
            msg = f"Dataset contains no rows or columns: {self.file_path}"
            logger.error(msg)
            raise DataLoaderError(msg)

        logger.info(
            "Successfully loaded '%s' [%d rows x %d cols] using encoding '%s'",
            self.file_path.name,
            df.shape[0],
            df.shape[1],
            successful_encoding,
        )

        metadata: Dict[str, Union[int, List[str], str]] = {
            "file_name": self.file_path.name,
            "row_count": int(df.shape[0]),
            "col_count": int(df.shape[1]),
            "columns": list(df.columns),
            "encoding": successful_encoding or "unknown",
            "file_size_bytes": self.file_path.stat().st_size,
        }

        return df, metadata
