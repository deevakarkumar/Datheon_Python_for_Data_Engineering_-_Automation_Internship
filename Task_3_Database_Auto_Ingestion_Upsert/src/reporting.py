"""
Execution Reporting & Summary Formatting Module
-----------------------------------------------
Formats execution statistics into terminal reports, JSON payloads,
and persistent audit records.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.db_connection import get_logger
from src.upsert import UpsertResult

logger = get_logger("ReportingEngine")


class IngestionReporter:
    """
    Renders standardized execution summaries and audit logs.
    """

    @staticmethod
    def generate_terminal_report(result: UpsertResult, db_status: str = "SUCCESS", execution_status: str = "COMPLETED") -> str:
        """
        Generate the standardized ASCII execution summary report.
        """
        report = f"""
========================================
       DATA INGESTION REPORT
========================================

Total Records Read:       {result.total_records_read:>5}
New Records Inserted:     {result.new_records_inserted:>5}
Existing Records Updated: {result.existing_records_updated:>5}
Unchanged Records:        {result.unchanged_records:>5}
Rejected Records:         {result.rejected_records:>5}

Total Records Processed:  {result.total_records_processed:>5}

Database Status: {db_status}
Execution Status: {execution_status}

========================================
Execution Time: {result.execution_duration_sec:.3f}s | Batches: {result.batches_processed}
========================================
"""
        return report

    @staticmethod
    def print_terminal_report(result: UpsertResult, db_status: str = "SUCCESS", execution_status: str = "COMPLETED") -> None:
        """Print formatted terminal report to standard output."""
        print(IngestionReporter.generate_terminal_report(result, db_status, execution_status))

    @staticmethod
    def export_json_report(result: UpsertResult, output_path: Path, extra_meta: Optional[Dict[str, Any]] = None) -> Path:
        """
        Export machine-readable JSON metrics for pipeline audits.
        """
        payload = result.to_dict()
        payload["timestamp"] = datetime.utcnow().isoformat()
        if extra_meta:
            payload.update(extra_meta)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

        logger.info("Saved JSON execution report to %s", output_path)
        return output_path
