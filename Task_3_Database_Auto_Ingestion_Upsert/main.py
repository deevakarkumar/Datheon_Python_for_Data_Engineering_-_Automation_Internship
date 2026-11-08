"""
Relational Database Auto-Ingestion & Upsert Engine
CLI Entry Point
-------------------------------------------------
User-facing command line interface providing subcommands for database initialization,
automated CSV ingestion & upsert, database verification, and execution reporting.
"""

import argparse
from pathlib import Path
import sys

# Clean formatting powered by pandas to_string
import pandas as pd

from config import DEFAULT_BATCH_SIZE, DEFAULT_DB_URL, STUDENTS_CSV, STUDENTS_UPDATED_CSV
from src.db_connection import DatabaseManager, get_logger
from src.ingestion import IngestionPipeline
from src.schema import init_db
from src.verification import DatabaseVerifier

logger = get_logger("CLI")


def print_banner() -> None:
    """Print ASCII application header."""
    print("""
========================================================================
     RELATIONAL DATABASE AUTO-INGESTION & UPSERT ENGINE
     Python for Data Engineering & Automation Internship Project
========================================================================
""")


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize database tables and schema constraints."""
    db_manager = DatabaseManager(args.db_url)
    print(f"[*] Initializing database schema at: {db_manager.db_url}")
    try:
        init_db(db_manager.engine)
        print("[+] Database initialized successfully.")
        return 0
    except Exception as exc:
        print(f"[-] Database initialization failed: {exc}", file=sys.stderr)
        return 1


def cmd_ingest(args: argparse.Namespace) -> int:
    """Execute CSV ingestion with automated validation, batch processing, and upsert."""
    input_file = Path(args.file)
    db_manager = DatabaseManager(args.db_url)
    pipeline = IngestionPipeline(db_manager=db_manager, batch_size=args.batch_size)

    print(f"[*] Ingesting CSV: {input_file}")
    print(f"[*] Batch size: {args.batch_size}")
    try:
        result = pipeline.run(
            file_path=input_file,
            print_report=True,
        )
        return 0
    except Exception as exc:
        print(f"[-] Ingestion failed: {exc}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Run data integrity and constraint verification checks."""
    db_manager = DatabaseManager(args.db_url)
    verifier = DatabaseVerifier(db_manager)

    print("[*] Running database verification and integrity audit...")
    summary = verifier.get_summary()

    print("\n========================================")
    print("      DATABASE INTEGRITY SUMMARY")
    print("========================================")
    print(f"Target Table:             {summary['table_name']}")
    print(f"Total Database Records:   {summary['total_records']}")
    print(f"Duplicate Primary Keys:   {summary['duplicate_primary_keys']}")
    print(f"Duplicate Email Accounts: {summary['duplicate_emails']}")
    print(f"SQLite PRAGMA Integrity:  {summary['sqlite_integrity_check']}")
    print(f"Overall Database Health:  {summary['database_health']}")
    print("========================================\n")

    return 0 if summary["database_health"] == "HEALTHY" else 1


def cmd_report(args: argparse.Namespace) -> int:
    """Display current database summary and inspect recent records."""
    db_manager = DatabaseManager(args.db_url)
    verifier = DatabaseVerifier(db_manager)

    summary = verifier.get_summary()
    total = summary["total_records"]

    print("\n========================================")
    print("       DATABASE STATUS REPORT")
    print("========================================")
    print(f"Database URL:             {db_manager._mask_db_url(db_manager.db_url)}")
    print(f"Active Records in DB:     {total}")
    print(f"Integrity Status:         {summary['database_health']}")
    print("========================================\n")

    if total > 0:
        limit = args.limit
        records = verifier.fetch_records(limit=limit)
        df = pd.DataFrame(records)
        print(f"--- Sample Database Records (Showing first {len(df)} of {total}) ---")
        print(df.to_string(index=False))
        print("\n")
    else:
        print("[!] No records found in database. Run 'ingest' command first.")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Relational Database Auto-Ingestion & Upsert Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py init
  python main.py ingest --file data/students.csv
  python main.py ingest --file data/students_updated.csv
  python main.py verify
  python main.py report --limit 10
        """,
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=DEFAULT_DB_URL,
        help=f"Database connection URL (default: {DEFAULT_DB_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # init
    parser_init = subparsers.add_parser("init", help="Initialize database tables and schema constraints")
    parser_init.set_defaults(func=cmd_init)

    # ingest
    parser_ingest = subparsers.add_parser("ingest", help="Ingest and upsert records from a CSV file")
    parser_ingest.add_argument(
        "--file",
        "-f",
        type=str,
        default=str(STUDENTS_CSV),
        help="Path to CSV data file (default: data/students.csv)",
    )
    parser_ingest.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of records processed per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser_ingest.set_defaults(func=cmd_ingest)

    # verify
    parser_verify = subparsers.add_parser("verify", help="Verify database integrity and primary key uniqueness")
    parser_verify.set_defaults(func=cmd_verify)

    # report
    parser_report = subparsers.add_parser("report", help="Generate database report and inspect records")
    parser_report.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Number of student records to display (default: 10)",
    )
    parser_report.set_defaults(func=cmd_report)

    return parser


def main() -> int:
    """Main CLI execution flow."""
    # Ensure UTF-8 output on Windows consoles
    if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print_banner()
    parser = build_parser()
    args = parser.parse_args()

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
