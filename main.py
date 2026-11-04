"""
Command Line Interface (CLI) Entry Point
----------------------------------------
User-facing execution script for the Datheon Automated Data Cleaning &
Schema Transformation project.
"""

from pathlib import Path
import argparse
import logging
import sys

from src.loader import DataLoader, DataLoaderError
from src.pipeline import DataCleaningPipeline, setup_logger
from src.profiler import DataProfiler


def build_parser() -> argparse.ArgumentParser:
    """
    Construct the command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Datheon Automated Data Cleaning & Schema Transformation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input data/raw/sample_messy_data.csv
  python main.py --input data/raw/sample_messy_data.csv --profile-only
  python main.py -i data/raw/sample_messy_data.csv -c config/schema_config.json -o data/output --verbose
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="data/raw/sample_messy_data.csv",
        help="Path to the input raw CSV file (default: data/raw/sample_messy_data.csv)",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config/schema_config.json",
        help="Path to the JSON schema and rules configuration file (default: config/schema_config.json)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="data/output",
        help="Directory to save generated outputs, reports, and logs (default: data/output)",
    )

    parser.add_argument(
        "-p",
        "--profile-only",
        action="store_true",
        help="Inspect and profile the dataset without running cleaning and transformation",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed DEBUG level logging output in terminal",
    )

    return parser


def print_banner() -> None:
    """Print application startup banner."""
    print("""
========================================================================
    DATHEON AUTOMATED DATA CLEANING & SCHEMA TRANSFORMATION ENGINE    
    Python for Data Engineering & Automation Internship Project        
========================================================================
""")


def main() -> int:
    """
    Main execution routine.
    """
    if sys.platform.startswith("win") and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args()

    print_banner()

    input_path = Path(args.input)
    config_path = Path(args.config)
    output_dir = Path(args.output)
    log_level = logging.DEBUG if args.verbose else logging.INFO

    # Check input file existence
    if not input_path.exists():
        print(f"[ERROR] Input CSV dataset file not found: {input_path}")
        return 1

    # Check config existence
    if not config_path.exists():
        print(f"[ERROR] Configuration file not found: {config_path}")
        return 1

    # Mode 1: Profiling Only
    if args.profile_only:
        print(f"[*] Running dataset inspection on: {input_path.name}...\n")
        try:
            loader = DataLoader(input_path)
            df_raw, meta = loader.load()
            profiler = DataProfiler(df_raw)
            print(profiler.generate_summary_text())
            print("\n[+] Profiling completed successfully.")
            return 0
        except DataLoaderError as err:
            print(f"[ERROR] Loading failed: {err}")
            return 1
        except Exception as err:
            print(f"[ERROR] Unexpected profiling error: {err}")
            return 1

    # Mode 2: Full Cleaning & Transformation Pipeline
    print(f"[*] Initializing cleaning pipeline with config '{config_path.name}'...")
    print(f"[*] Target Output Directory: {output_dir.resolve()}\n")

    try:
        pipeline = DataCleaningPipeline(config_path=config_path, output_dir=output_dir)
        # Apply terminal log level
        pipeline.logger.setLevel(log_level)

        summary = pipeline.run(input_path)

        # Pretty print execution highlights
        print("\n" + "=" * 70)
        print("                   EXECUTION HIGHLIGHTS")
        print("=" * 70)
        print(f"  Status                  : {summary['processing_status']}")
        print(f"  Duration                : {summary['execution_duration_seconds']}s")
        print(f"  Raw Records Ingested    : {summary['original_record_count']}")
        print(f"  Duplicates Purged       : {summary['duplicates_removed_count']}")
        print(f"  Missing Values Imputed  : {summary['missing_values_handled_count']}")
        print(f"  Valid Clean Records     : {summary['final_clean_record_count']}")
        print(f"  Quarantined Records     : {summary['quarantined_record_count']}")
        print(f"  Validation Pass Rate    : {summary['validation_summary']['pass_rate_percentage']}%")
        print("-" * 70)
        print("Generated Output Artifacts:")
        print(f"  1. Clean Data CSV       : {summary['output_files']['cleaned_data']}")
        print(f"  2. Quarantined CSV      : {summary['output_files']['quarantined_records']}")
        print(f"  3. JSON Validation      : {summary['output_files']['validation_report']}")
        print(f"  4. HTML Visual Summary  : {summary['output_files']['html_summary']}")
        print(f"  5. Execution Log        : {summary['output_files']['log_file']}")
        print("=" * 70)
        print("\n[+] Pipeline executed and completed successfully!\n")
        return 0

    except DataLoaderError as err:
        print(f"\n[FATAL ERROR] Dataset ingestion failed: {err}")
        return 1
    except Exception as err:
        print(f"\n[FATAL ERROR] Pipeline execution encountered an unhandled exception: {err}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
