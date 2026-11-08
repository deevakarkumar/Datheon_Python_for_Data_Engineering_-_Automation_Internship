"""
Configuration Module
--------------------
Centralized application settings, file paths, and database configurations.
"""

from pathlib import Path
import os

# Project root directory
BASE_DIR = Path(__file__).resolve().parent

# Data directory and datasets
DATA_DIR = BASE_DIR / "data"
STUDENTS_CSV = DATA_DIR / "students.csv"
STUDENTS_UPDATED_CSV = DATA_DIR / "students_updated.csv"
REJECTED_RECORDS_CSV = DATA_DIR / "rejected_records.csv"

# Database directory and SQLite file
DATABASE_DIR = BASE_DIR / "database"
DEFAULT_DB_FILE = DATABASE_DIR / "database.db"
DEFAULT_DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE.as_posix()}")

# Logging settings
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "ingestion.log"
LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(name)s] - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Table and Ingestion Settings
TABLE_NAME = "students"
PRIMARY_KEY_COLUMN = "student_id"
REQUIRED_COLUMNS = [
    "student_id",
    "student_name",
    "email",
    "course",
    "marks",
    "enrollment_date",
]

DEFAULT_BATCH_SIZE = 50
EMAIL_REGEX_PATTERN = r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$"
MIN_MARKS = 0.0
MAX_MARKS = 100.0
