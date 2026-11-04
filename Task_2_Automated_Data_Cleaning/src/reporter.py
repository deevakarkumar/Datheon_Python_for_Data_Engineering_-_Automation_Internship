"""
Data Quality Reporting Module
-----------------------------
Generates structured JSON validation reports and polished, modern HTML/TXT
summary reports for audit, data governance, and stakeholder review.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json
import logging

logger = logging.getLogger("DataCleaningPipeline.Reporter")


class QualityReporter:
    """
    Assembles pipeline execution metrics into structured JSON and responsive HTML reports.
    """

    def __init__(self, metrics: Dict[str, Any]):
        """
        Initialize QualityReporter.

        Args:
            metrics: Aggregated metrics dictionary collected across all pipeline modules.
        """
        self.metrics = metrics

    def generate_json_report(self, output_path: Union[str, Path]) -> Path:
        """
        Save the complete metrics payload to a JSON report file.

        Args:
            output_path: Destination path for the JSON report.

        Returns:
            Path object to saved file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2, default=str)

        logger.info("Generated JSON validation report at: %s", path)
        return path

    def generate_html_report(self, output_path: Union[str, Path]) -> Path:
        """
        Render a modern, standalone HTML dashboard summarizing data quality operations.

        Args:
            output_path: Destination path for the HTML report.

        Returns:
            Path object to saved HTML file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        m = self.metrics
        status_color = "#10b981" if m.get("processing_status") == "SUCCESS" else "#ef4444"

        # Build violation rows HTML
        violation_rows = ""
        violations = m.get("validation_summary", {}).get("rule_violation_breakdown", {})
        if violations:
            for rule, count in violations.items():
                violation_rows += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">{rule}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold; color: #ef4444;">{count}</td>
                </tr>"""
        else:
            violation_rows = "<tr><td colspan='2' style='padding: 10px; text-align: center; color: #64748b;'>No rule violations recorded.</td></tr>"

        # Build column stats rows
        col_rows = ""
        col_stats = m.get("profiling_initial", {}).get("column_statistics", {})
        type_changes = m.get("schema_audit", {}).get("type_changes", {})

        for col, stats in col_stats.items():
            final_type = type_changes.get(col, {}).get("to", stats.get("inferred_type", "unknown"))
            col_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{col}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{stats.get('missing_count', 0)} ({stats.get('missing_percentage', 0)}%)</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{stats.get('unique_values', 0)}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-family: monospace; color: #6366f1;">{stats.get('inferred_type')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-family: monospace; color: #059669; font-weight: bold;">{final_type}</td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Datheon Data Quality & Transformation Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 26px; }}
        .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }}
        .card-title {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
        .card-val {{ font-size: 28px; font-weight: 800; color: #0f172a; margin-top: 5px; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            margin-bottom: 25px;
        }}
        .section h2 {{
            margin-top: 0;
            font-size: 18px;
            color: #0f172a;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            background-color: #f8fafc;
            text-align: left;
            padding: 12px 10px;
            font-weight: 600;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: bold;
            color: white;
            background-color: {status_color};
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #94a3b8;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>Automated Data Cleaning & Schema Transformation Report</h1>
                    <p>Internship Project | Organization: Datheon | Run Timestamp: {m.get('execution_timestamp')}</p>
                </div>
                <div>
                    <span class="badge">{m.get('processing_status')}</span>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-title">Initial Records</div>
                <div class="card-val">{m.get('original_record_count')}</div>
            </div>
            <div class="card">
                <div class="card-title">Clean Valid Records</div>
                <div class="card-val" style="color: #10b981;">{m.get('final_clean_record_count')}</div>
            </div>
            <div class="card">
                <div class="card-title">Quarantined Records</div>
                <div class="card-val" style="color: #ef4444;">{m.get('quarantined_record_count')}</div>
            </div>
            <div class="card">
                <div class="card-title">Duplicates Purged</div>
                <div class="card-val" style="color: #f59e0b;">{m.get('duplicates_removed_count')}</div>
            </div>
            <div class="card">
                <div class="card-title">Values Imputed</div>
                <div class="card-val" style="color: #6366f1;">{m.get('missing_values_handled_count')}</div>
            </div>
        </div>

        <div class="section">
            <h2>Dataset Column Evolution & Quality</h2>
            <table>
                <thead>
                    <tr>
                        <th>Column Name</th>
                        <th>Initial Missing</th>
                        <th>Unique Values</th>
                        <th>Raw Type</th>
                        <th>Cleaned Type</th>
                    </tr>
                </thead>
                <tbody>
                    {col_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Validation Constraint Violations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Integrity Rule</th>
                        <th style="text-align: right;">Violations Quarantined</th>
                    </tr>
                </thead>
                <tbody>
                    {violation_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Executive Audit Summary</h2>
            <p><strong>Input Dataset:</strong> {m.get('input_file')}</p>
            <p><strong>Cleaned Dataset:</strong> {m.get('output_files', {}).get('cleaned_data')}</p>
            <p><strong>Quarantined Records:</strong> {m.get('output_files', {}).get('quarantined_records')}</p>
            <p><strong>Validation Rate:</strong> {m.get('validation_summary', {}).get('pass_rate_percentage')}%</p>
            <p><strong>Dropped Empty Columns:</strong> {', '.join(m.get('missing_values_audit', {}).get('dropped_columns', [])) or 'None'}</p>
        </div>

        <div class="footer">
            Generated autonomously by Datheon Automated Data Cleaning & Schema Transformation System
        </div>
    </div>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info("Generated HTML visual summary report at: %s", path)
        return path
