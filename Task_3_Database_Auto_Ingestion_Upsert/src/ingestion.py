"""
Pipeline Ingestion Orchestration Module
---------------------------------------
Coordinates CSV file loading, pre-validation checks, schema enforcement,
and transaction-managed upsert pipeline execution.
"""

from pathlib import Path
from typing import Optional, Union
import pandas as pd

from config import DEFAULT_BATCH_SIZE, REJECTED_RECORDS_CSV
from src.db_connection import DatabaseManager, get_logger
from src.reporting import IngestionReporter
from src.schema import init_db
from src.upsert import UpsertEngine, UpsertResult
from src.validation import DataValidator, ValidationError

logger = get_logger("IngestionPipeline")


class IngestionPipeline:
    """
    Main orchestrator for the automated database ingestion and upsert engine.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.db_manager = db_manager or DatabaseManager()
        self.batch_size = batch_size
        self.validator = DataValidator()
        self.upsert_engine = UpsertEngine(self.db_manager, batch_size=self.batch_size)

    def load_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Safely load CSV file into a Pandas DataFrame with validation checks.
        """
        path = Path(file_path)
        logger.info("Initiating ingestion for CSV file: %s", path)

        if not path.exists():
            raise FileNotFoundError(f"Input CSV file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a valid file: {path}")

        if path.stat().st_size == 0:
            raise ValidationError(f"Input file is completely empty (0 bytes): {path}")

        # Try multi-encoding loading
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        df: Optional[pd.DataFrame] = None
        last_error = None

        for enc in encodings:
            try:
                df = pd.read_csv(path, encoding=enc, dtype=str)
                logger.info("Successfully read %s using encoding '%s' (%d rows).", path.name, enc, len(df))
                break
            except UnicodeDecodeError as err:
                last_error = err
                continue

        if df is None:
            raise ValidationError(f"Failed to read CSV with supported encodings. Last error: {last_error}")

        return df

    def run(
        self,
        file_path: Union[str, Path],
        rejected_output_path: Optional[Path] = None,
        print_report: bool = True,
    ) -> UpsertResult:
        """
        Execute end-to-end ingestion and upsert lifecycle.

        Steps:
        1. Ensure database and schema are initialized.
        2. Ingest and parse raw CSV file.
        3. Validate records and isolate quarantined rows.
        4. Persist rejected rows to rejected_records.csv if violations exist.
        5. Execute batched upsert with atomic transactions.
        6. Compile and render execution report.
        """
        # Step 1: Ensure database schema exists
        init_db(self.db_manager.engine)

        # Step 2: Load CSV
        raw_df = self.load_csv(file_path)

        # Step 3: Validate and split
        valid_df, rejected_df = self.validator.validate(raw_df)

        # Step 4: Save quarantined records if any exist
        if not rejected_df.empty:
            out_path = rejected_output_path or REJECTED_RECORDS_CSV
            self.validator.save_rejected(rejected_df, out_path)

        # Step 5: Upsert valid records
        result = self.upsert_engine.upsert(valid_df, rejected_count=len(rejected_df))

        # Step 6: Render report
        if print_report:
            IngestionReporter.print_terminal_report(
                result=result,
                db_status="SUCCESS",
                execution_status="COMPLETED",
            )

        return result
