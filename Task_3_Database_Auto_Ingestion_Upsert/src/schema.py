"""
Database Schema & Table Definition Module
-----------------------------------------
Defines relational models, constraints, and table initialization routines.
"""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    inspect,
)
from sqlalchemy.orm import declarative_base

from config import TABLE_NAME
from src.db_connection import get_logger

Base = declarative_base()
metadata = MetaData()

logger = get_logger("SchemaManager")


class Student(Base):
    """
    SQLAlchemy ORM Model representing the 'students' relational table.
    """

    __tablename__ = TABLE_NAME

    student_id = Column(String(20), primary_key=True, index=True, doc="Unique student identifier (Primary Key)")
    student_name = Column(String(100), nullable=False, doc="Full name of student")
    email = Column(String(120), nullable=False, unique=True, index=True, doc="Unique student email address")
    course = Column(String(100), nullable=False, doc="Enrolled academic course/program")
    marks = Column(Float, nullable=False, doc="Academic grade or percentage (0.0 - 100.0)")
    enrollment_date = Column(String(10), nullable=False, doc="Date of admission (ISO format YYYY-MM-DD)")
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Timestamp tracking initial creation or most recent upsert",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model attributes to a standard dictionary representation."""
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "email": self.email,
            "course": self.course,
            "marks": self.marks,
            "enrollment_date": self.enrollment_date,
            "last_updated": self.last_updated.strftime("%Y-%m-%d %H:%M:%S") if self.last_updated else None,
        }

    def __repr__(self) -> str:
        return f"<Student(id='{self.student_id}', name='{self.student_name}', course='{self.course}', marks={self.marks})>"


def init_db(engine) -> bool:
    """
    Automatically initialize database tables if they do not exist.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        True if initialization was successful.
    """
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if TABLE_NAME in existing_tables:
            logger.info("Table '%s' already exists in database.", TABLE_NAME)
        else:
            logger.info("Table '%s' not found. Creating database schema...", TABLE_NAME)
            Base.metadata.create_all(engine)
            logger.info("Successfully created table '%s'.", TABLE_NAME)

        return True
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)
        raise
