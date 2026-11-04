"""
ETL Pipeline Orchestration Module
---------------------------------
Coordinates end-to-end data ingestion, profiling, currency/date normalization,
missingness imputation, duplicate removal, schema transformation, validation,
and export management with robust rotating logging.
"""

from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import logging
import sys
import pandas as pd

from src.currency import CurrencyNormalizer
from src.dates import DateNormalizer
from src.duplicates import DuplicateHandler
from src.loader import DataLoader, DataLoaderError
from src.missing_values import MissingValueHandler
from src.profiler import DataProfiler
from src.reporter import QualityReporter
from src.schema_transformer import SchemaTransformer
from src.validator import DataValidator


def setup_logger(
    log_file_path: Optional[Union[str, Path]] = None,
    log_level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure pipeline-wide logger with both console and rotating file outputs.

    Args:
        log_file_path: Path to log file on disk. If provided, uses RotatingFileHandler.
        log_level: Python logging level (default: logging.INFO).

    Returns:
        Configured root logger for DataCleaningPipeline.
    """
    logger = logging.getLogger("DataCleaningPipeline")
    logger.setLevel(log_level)
    logger.propagate = False

    # Clear existing handlers to avoid duplicates during repeated runs
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ensure stdout handles UTF-8 (e.g., currency symbols ₹) gracefully on Windows consoles
    if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler
    if log_file_path:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB max file size
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class DataCleaningPipeline:
    """
    End-to-end automated cleaning and schema transformation engine.
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the DataCleaningPipeline with a JSON configuration file.

        Args:
            config_path: Path to schema_config.json.
            output_dir: Directory where artifacts and reports will be saved.
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.output_dir = Path(output_dir) if output_dir else Path("data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging inside output directory as well as central logs/
        self.log_file = self.output_dir / "cleaning.log"
        self.logger = setup_logger(self.log_file)
        self.logger.info("Initialized DataCleaningPipeline with config: %s", self.config_path.name)

    def run(self, input_file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Execute the full automated data cleaning and schema transformation pipeline.

        Args:
            input_file_path: Path to the raw CSV file.

        Returns:
            Dictionary containing comprehensive pipeline execution summary and file paths.
        """
        execution_start = datetime.now()
        input_path = Path(input_file_path)

        self.logger.info("=" * 70)
        self.logger.info("STARTING DATA CLEANING PIPELINE FOR: %s", input_path.name)
        self.logger.info("=" * 70)

        # -------------------------------------------------------------
        # Step 1: Ingestion & Loading
        # -------------------------------------------------------------
        loader = DataLoader(input_path)
        df_raw, load_meta = loader.load()
        initial_row_count = len(df_raw)

        # -------------------------------------------------------------
        # Step 2: Initial Profiling
        # -------------------------------------------------------------
        profiler = DataProfiler(df_raw)
        initial_profile = profiler.profile()

        # -------------------------------------------------------------
        # Step 3: Column Name Normalization & Renaming
        # -------------------------------------------------------------
        transformer = SchemaTransformer(
            schema=self.config.get("schema", {}),
            rename_mapping=self.config.get("rename_mapping", {}),
            standardize_names=self.config.get("standardize_column_names", True),
            target_column_order=self.config.get("target_column_order", []),
        )

        df_work, std_headers = transformer.standardize_headers(df_raw)
        df_work, renamed_cols = transformer.apply_rename_mapping(df_work)

        # -------------------------------------------------------------
        # Step 4: Currency Normalization
        # -------------------------------------------------------------
        currency_config = self.config.get("currency_columns", {})
        currency_audit: Dict[str, Any] = {}

        for col, c_settings in currency_config.items():
            if col in df_work.columns:
                normalizer = CurrencyNormalizer(
                    default_currency=c_settings.get("default_currency", "INR"),
                    target_currency=c_settings.get("target_currency", "INR"),
                    remove_symbols=c_settings.get("remove_symbols", True),
                )
                df_work[col], c_stats = normalizer.normalize_series(df_work[col])
                currency_audit[col] = c_stats

        # -------------------------------------------------------------
        # Step 5: Date Normalization
        # -------------------------------------------------------------
        date_config = self.config.get("date_columns", {})
        date_audit: Dict[str, Any] = {}

        for col, d_settings in date_config.items():
            if col in df_work.columns:
                date_normalizer = DateNormalizer(
                    day_first=d_settings.get("day_first", True),
                    target_format=d_settings.get("target_format", "%Y-%m-%d"),
                )
                df_work[col], d_stats = date_normalizer.normalize_series(df_work[col])
                date_audit[col] = d_stats

        # -------------------------------------------------------------
        # Step 6: Missing Value Handling
        # -------------------------------------------------------------
        missing_handler = MissingValueHandler(
            strategies=self.config.get("missing_value_strategies", {}),
            drop_empty_threshold=self.config.get("drop_columns_threshold", 0.90),
        )
        df_work, missing_audit = missing_handler.handle(df_work)

        # -------------------------------------------------------------
        # Step 7: Duplicate Detection and Removal
        # -------------------------------------------------------------
        dup_rules = self.config.get("duplicate_rules", {})
        dup_handler = DuplicateHandler(
            subset=dup_rules.get("subset"),
            keep=dup_rules.get("keep", "first"),
        )
        df_work, dup_audit = dup_handler.process(df_work)

        # -------------------------------------------------------------
        # Step 8: Final Schema Casting & Column Ordering
        # -------------------------------------------------------------
        df_work, type_changes = transformer.cast_types(df_work)
        df_work = transformer.enforce_ordering(df_work)

        schema_audit = {
            "standardized_headers": std_headers,
            "renamed_columns": renamed_cols,
            "type_changes": type_changes,
            "final_column_order": list(df_work.columns),
        }

        # -------------------------------------------------------------
        # Step 9: Data Validation & Quarantine Segregation
        # -------------------------------------------------------------
        validator = DataValidator(validation_rules=self.config.get("validation_rules", {}))
        valid_df, quarantined_df, validation_summary = validator.validate(df_work)

        # -------------------------------------------------------------
        # Step 10: Artifact Export Management
        # -------------------------------------------------------------
        cleaned_path = self.output_dir / "cleaned_data.csv"
        quarantined_path = self.output_dir / "invalid_records.csv"
        json_report_path = self.output_dir / "validation_report.json"
        html_report_path = self.output_dir / "cleaning_summary.html"

        valid_df.to_csv(cleaned_path, index=False, encoding="utf-8")
        quarantined_df.to_csv(quarantined_path, index=False, encoding="utf-8")

        execution_end = datetime.now()
        duration_sec = round((execution_end - execution_start).total_seconds(), 3)

        # Assemble Master Metrics
        metrics_payload: Dict[str, Any] = {
            "project_name": self.config.get("project_name", "Automated Data Cleaning"),
            "input_file": str(input_path),
            "execution_timestamp": execution_start.isoformat(),
            "execution_duration_seconds": duration_sec,
            "processing_status": "SUCCESS",
            "original_record_count": initial_row_count,
            "final_clean_record_count": len(valid_df),
            "quarantined_record_count": len(quarantined_df),
            "duplicates_removed_count": dup_audit.get("total_duplicates_removed", 0),
            "missing_values_handled_count": missing_audit.get("total_imputed_cells", 0),
            "profiling_initial": initial_profile,
            "currency_normalization_audit": currency_audit,
            "date_normalization_audit": date_audit,
            "missing_values_audit": missing_audit,
            "duplicate_audit": dup_audit,
            "schema_audit": schema_audit,
            "validation_summary": validation_summary,
            "output_files": {
                "cleaned_data": str(cleaned_path),
                "quarantined_records": str(quarantined_path),
                "validation_report": str(json_report_path),
                "html_summary": str(html_report_path),
                "log_file": str(self.log_file),
            },
        }

        # -------------------------------------------------------------
        # Step 11: Generate JSON & HTML Reports
        # -------------------------------------------------------------
        reporter = QualityReporter(metrics_payload)
        reporter.generate_json_report(json_report_path)
        reporter.generate_html_report(html_report_path)

        self.logger.info("=" * 70)
        self.logger.info("PIPELINE COMPLETED SUCCESSFULLY IN %.2f SECONDS", duration_sec)
        self.logger.info("Cleaned records saved to:     %s", cleaned_path)
        self.logger.info("Quarantined records saved to: %s", quarantined_path)
        self.logger.info("Validation report saved to:   %s", json_report_path)
        self.logger.info("HTML summary saved to:         %s", html_report_path)
        self.logger.info("=" * 70)

        return metrics_payload
