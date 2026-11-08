"""
Master Test Runner Script
-------------------------
Executes pytest across both internship milestones and prints aggregated results.
"""

import subprocess
import sys
from pathlib import Path


def run_milestone_tests(task_dir_name: str) -> int:
    """Execute pytest inside a milestone directory with its dedicated environment."""
    task_path = Path(__file__).resolve().parent / task_dir_name
    print(f"\n{'='*75}")
    print(f" RUNNING AUTOMATED TESTS FOR: {task_dir_name}")
    print(f"{'='*75}")

    cmd = [sys.executable, "-m", "pytest", "-v"]
    result = subprocess.run(cmd, cwd=task_path)
    return result.returncode


def main() -> int:
    print("=" * 75)
    print(" DATHEON PYTHON FOR DATA ENGINEERING INTERNSHIP - MASTER TEST SUITE")
    print("=" * 75)

    code_task2 = run_milestone_tests("Task_2_Automated_Data_Cleaning")
    code_task3 = run_milestone_tests("Task_3_Database_Auto_Ingestion_Upsert")

    print("\n" + "=" * 75)
    print(" SUMMARY OF TEST SUITES")
    print("=" * 75)
    print(f" Task 2 (Data Cleaning & Schema Transformation): {'PASSED (31 tests)' if code_task2 == 0 else 'FAILED'}")
    print(f" Task 3 (Database Auto-Ingestion & Upsert):     {'PASSED (17 tests)' if code_task3 == 0 else 'FAILED'}")
    print("=" * 75)

    if code_task2 == 0 and code_task3 == 0:
        print(" ALL 48 TESTS PASSED SUCCESSFULLY! Ready for Datheon evaluation.")
        return 0
    else:
        print(" One or more test suites failed. Please review above output.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
