"""
Database Connection & Engine Management Module
----------------------------------------------
Provides connection factory, lifecycle management, and logging infrastructure.
"""

from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Generator, Optional, Union
import logging
import sys

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config import DEFAULT_DB_URL, LOG_DATE_FORMAT, LOG_FILE, LOG_FORMAT, LOGS_DIR


def get_logger(name: str = "DatabaseEngine", log_level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a centralized logger with console and rotating file handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False

    if not logger.handlers:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (Rotating 5MB with 3 backups)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class DatabaseManager:
    """
    Manages SQLAlchemy engine lifecycle and database connection transactions.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the DatabaseManager with a database connection string.
        """
        self.db_url = db_url or DEFAULT_DB_URL
        self.logger = get_logger("DatabaseManager")

        # Ensure directory exists for file-based SQLite databases
        if self.db_url.startswith("sqlite:///") and ":memory:" not in self.db_url:
            db_path = Path(self.db_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """
        Lazy-initialize and return the SQLAlchemy engine.
        """
        if self._engine is None:
            connect_args = {}
            if "sqlite" in self.db_url:
                # Enable timeout and multi-thread support for SQLite
                connect_args = {"check_same_thread": False, "timeout": 30}

            self._engine = create_engine(
                self.db_url,
                connect_args=connect_args,
                echo=False,
                future=True,
            )
            self._session_factory = sessionmaker(bind=self._engine, future=True)
            self.logger.info("Initialized SQLAlchemy engine for %s", self._mask_db_url(self.db_url))

        return self._engine

    def test_connection(self) -> bool:
        """
        Verify database connectivity by executing a lightweight ping query.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                is_connected = result == 1
                if is_connected:
                    self.logger.info("Database connection ping successful.")
                return is_connected
        except Exception as exc:
            self.logger.error("Database connection failed: %s", exc)
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        Commits upon clean exit, rolls back on exception.
        """
        if self._session_factory is None:
            _ = self.engine
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            self.logger.error("Transaction rolled back due to error: %s", exc)
            raise
        finally:
            session.close()

    def _mask_db_url(self, url: str) -> str:
        """Mask sensitive credentials in database URLs for secure logging."""
        if "@" in url:
            scheme_user = url.split("@")[0]
            host_db = url.split("@")[1]
            return f"{scheme_user.split(':')[0]}:***@{host_db}"
        return url
