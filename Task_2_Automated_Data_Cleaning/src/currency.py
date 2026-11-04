"""
Currency Normalization Module
-----------------------------
Normalizes diverse international and domestic currency strings into clean
floating-point representations, supporting symbol stripping, accounting brackets,
negative values, and currency code extraction.
"""

from typing import Any, Dict, Optional, Tuple, Union
import logging
import re
import numpy as np
import pandas as pd

logger = logging.getLogger("DataCleaningPipeline.Currency")


class CurrencyNormalizer:
    """
    Parses and standardizes diverse currency formatting variants into numeric values.
    """

    # Comprehensive symbol & text token regex
    CURRENCY_SYMBOLS_PATTERN = r"[₹$€£¥]|(?:INR|Rs\.?|USD|EUR|GBP|AUD|CAD|JPY)"

    def __init__(
        self,
        default_currency: str = "INR",
        target_currency: str = "INR",
        remove_symbols: bool = True,
    ):
        """
        Initialize CurrencyNormalizer.

        Args:
            default_currency: Expected currency if no symbol is detected.
            target_currency: Output currency unit for reporting.
            remove_symbols: Whether to strip symbols and return pure numeric floats.
        """
        self.default_currency = default_currency
        self.target_currency = target_currency
        self.remove_symbols = remove_symbols

    @classmethod
    def clean_currency_string(cls, val: Any) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse a single currency value string into (numeric_value, detected_currency_symbol).

        Examples:
            "₹25,000" -> (25000.0, "₹")
            "Rs. 25,000.50" -> (25000.5, "Rs.")
            "-INR 500" -> (-500.0, "INR")
            "(₹1,200.00)" -> (-1200.0, "₹")
            "invalid_val" -> (None, None)
        """
        if pd.isna(val):
            return None, None

        raw = str(val).strip()
        if not raw:
            return None, None

        # Check for accounting-style negative parentheses, e.g., (1,000) or (₹500)
        is_negative = False
        if raw.startswith("(") and raw.endswith(")"):
            is_negative = True
            raw = raw[1:-1].strip()
        elif "-" in raw:
            is_negative = True
            raw = raw.replace("-", "").strip()

        # Extract currency symbol or token if present
        detected_symbol: Optional[str] = None
        match = re.search(cls.CURRENCY_SYMBOLS_PATTERN, raw, re.IGNORECASE)
        if match:
            detected_symbol = match.group(0).strip()
            # Strip detected token from raw
            raw = re.sub(cls.CURRENCY_SYMBOLS_PATTERN, "", raw, flags=re.IGNORECASE)

        # Remove commas, extra spaces, and apostrophes (used as thousands separator in some locales)
        cleaned = raw.replace(",", "").replace(" ", "").replace("'", "")

        try:
            numeric_val = float(cleaned)
            if is_negative:
                numeric_val = -abs(numeric_val)
            return numeric_val, detected_symbol
        except (ValueError, TypeError):
            logger.debug("Could not parse currency value '%s'", val)
            return None, detected_symbol

    def normalize_series(self, series: pd.Series) -> Tuple[pd.Series, Dict[str, Any]]:
        """
        Normalize an entire Pandas series containing currency values.

        Args:
            series: Series containing raw currency strings.

        Returns:
            Tuple of (numeric_float_series, statistics_dict)
        """
        total_items = len(series)
        results = [self.clean_currency_string(v) for v in series]

        numeric_values = [r[0] for r in results]
        detected_symbols = [r[1] for r in results if r[1] is not None]

        cleaned_series = pd.Series(numeric_values, index=series.index, dtype="float64")

        valid_count = int(cleaned_series.notna().sum())
        invalid_count = total_items - valid_count
        symbols_found = list(set(detected_symbols))

        stats: Dict[str, Any] = {
            "total_records": total_items,
            "valid_normalized": valid_count,
            "unparseable_records": invalid_count,
            "detected_currency_symbols": symbols_found,
            "target_currency": self.target_currency,
        }

        logger.info(
            "Normalized currency series '%s': %d valid values, %d unparseable. Symbols found: %s",
            series.name,
            valid_count,
            invalid_count,
            symbols_found,
        )

        return cleaned_series, stats
