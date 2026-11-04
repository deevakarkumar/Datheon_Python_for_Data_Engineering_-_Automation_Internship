"""
Date Normalization Module
-------------------------
Normalizes polymorphic date string formats into standard ISO 8601 (YYYY-MM-DD)
dates, resolving ambiguous patterns via configurable day-first settings and
recording unparseable date values.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import re
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Dates")


class DateNormalizer:
    """
    Standardizes varied date representations into YYYY-MM-DD strings.
    """

    DEFAULT_TARGET_FORMAT = "%Y-%m-%d"

    TEXT_FORMATS = (
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
    )

    def __init__(
        self,
        day_first: bool = True,
        year_first: bool = False,
        target_format: str = DEFAULT_TARGET_FORMAT,
    ):
        """
        Initialize DateNormalizer.

        Args:
            day_first: Interpret ambiguous dates (e.g. 01/02/2023) as DD/MM/YYYY if True.
            year_first: Interpret ambiguous dates as YYYY/MM/DD if True.
            target_format: Target strftime output format (default: '%Y-%m-%d').
        """
        self.day_first = day_first
        self.year_first = year_first
        self.target_format = target_format

    def parse_single_date(self, val: Any) -> Optional[datetime]:
        """
        Parse a single date value using deterministic ISO and regex heuristics.
        """
        if pd.isna(val):
            return None

        val_str = str(val).strip()
        if not val_str or val_str.lower() in ("none", "nan", "nat", "null"):
            return None

        # 1. ISO format starting with 4-digit year: YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
        iso_match = re.match(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$", val_str)
        if iso_match:
            y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            try:
                return datetime(y, m, d)
            except ValueError:
                return None

        # 2. Date ending with 4-digit year: DD-MM-YYYY or MM-DD-YYYY
        end_year_match = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})$", val_str)
        if end_year_match:
            p1, p2, y = int(end_year_match.group(1)), int(end_year_match.group(2)), int(end_year_match.group(3))
            d, m = (p1, p2) if self.day_first else (p2, p1)
            try:
                return datetime(y, m, d)
            except ValueError:
                return None

        # 3. Named textual month formats: '01 Oct 2026', '15 Jan 2023'
        for fmt in self.TEXT_FORMATS:
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue

        # 4. Fallback to general parser
        try:
            dt = pd.to_datetime(val_str, dayfirst=self.day_first, errors="raise")
            return dt.to_pydatetime()
        except Exception:
            return None

    def normalize_series(
        self, series: pd.Series
    ) -> Tuple[pd.Series, Dict[str, Any]]:
        """
        Convert a series of date strings into standardized YYYY-MM-DD strings.

        Args:
            series: Input Pandas Series containing date strings.

        Returns:
            Tuple of (normalized_series, audit_metrics_dict)
        """
        total_items = len(series)
        if total_items == 0:
            return series, {
                "total_records": 0,
                "valid_dates": 0,
                "invalid_dates": 0,
                "invalid_samples": [],
            }

        formatted_list: List[Optional[str]] = []
        invalid_samples: List[str] = []
        valid_count = 0
        invalid_count = 0

        for val in series:
            if pd.isna(val) or str(val).strip() in ("", "None", "nan", "NaT"):
                formatted_list.append(None)
                continue

            dt = self.parse_single_date(val)
            if dt is not None:
                formatted_list.append(dt.strftime(self.target_format))
                valid_count += 1
            else:
                formatted_list.append(None)
                invalid_count += 1
                sample_str = str(val).strip()
                if sample_str not in invalid_samples:
                    invalid_samples.append(sample_str)

        formatted_series = pd.Series(formatted_list, index=series.index, dtype="string")

        logger.info(
            "Date normalization for column '%s': %d valid dates, %d invalid dates (samples: %s)",
            series.name,
            valid_count,
            invalid_count,
            invalid_samples[:5],
        )

        metrics: Dict[str, Any] = {
            "column_name": str(series.name),
            "total_records": total_items,
            "valid_dates": valid_count,
            "invalid_dates": invalid_count,
            "invalid_samples": invalid_samples[:10],
            "day_first_used": self.day_first,
            "target_format": self.target_format,
        }

        return formatted_series, metrics
