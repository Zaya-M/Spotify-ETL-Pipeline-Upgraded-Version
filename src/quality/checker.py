# ============================================================
# File: src/quality/checker.py
# Description: Data Quality Validation (Pre-transformation)
# Purpose: Detect issues early and alert, preventing "dirty data" from entering the warehouse.
# ============================================================

import os
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Thresholds loaded from environment variables
MAX_NULL_RATE = float(os.getenv("MAX_NULL_RATE", "0.05"))
MAX_DUPLICATE_RATE = float(os.getenv("MAX_DUPLICATE_RATE", "0.01"))


class DataQualityChecker:
    """
    Validates data integrity before writing to DWD.
    Logs warnings if quality checks fail against defined thresholds.
    """

    def __init__(self):
        self.check_results = []

    def _record_result(
        self, check_name: str, column: str, value: float, threshold: float, passed: bool
    ):
        """Internal helper to log and store validation results."""
        result = {
            "check": check_name,
            "column": column,
            "value": value,
            "threshold": threshold,
            "passed": passed,
        }
        self.check_results.append(result)
        if not passed:
            logger.warning(
                f"[DQ Alert] {check_name} failed for {column}! "
                f"Value: {value:.2%}, Threshold: {threshold:.2%}"
            )

    def check_null_rate(
        self, df: pd.DataFrame, column: str, threshold: float = MAX_NULL_RATE
    ) -> bool:
        """Checks if the null value ratio exceeds the allowed threshold."""
        null_count = df[column].isnull().sum()
        null_rate = null_count / len(df)
        passed = null_rate <= threshold

        self._record_result("null_rate", column, null_rate, threshold, passed)
        return passed

    def check_duplicate_rate(
        self,
        df: pd.DataFrame,
        key_columns: list[str],
        threshold: float = MAX_DUPLICATE_RATE,
    ) -> bool:
        """
        Checks the duplication rate of primary keys.
        :param key_columns: List of columns defining a unique record.
        """
        if len(df) == 0:
            return True

        duplicate_count = df.duplicated(subset=key_columns).sum()
        duplicate_rate = duplicate_count / len(df)
        passed = duplicate_rate <= threshold

        col_name = "+".join(key_columns)
        self._record_result(
            "duplicate_rate", col_name, duplicate_rate, threshold, passed
        )
        return passed

    def check_value_range(
        self, df: pd.DataFrame, column: str, min_val, max_val
    ) -> bool:
        """Validates if numeric values fall within a logical range (e.g., popularity 0-100)."""
        out_of_range_count = len(df[(df[column] < min_val) | (df[column] > max_val)])
        out_rate = out_of_range_count / len(df)

        # Alert if more than 1% of data is out of range
        passed = out_rate <= 0.01
        self._record_result("value_range", column, out_rate, 0.01, passed)
        return passed

    def check_row_count(self, df: pd.DataFrame, min_rows: int = 1) -> bool:
        """Ensures the dataset is not empty to prevent ingestion of null sets."""
        passed = len(df) >= min_rows

        if not passed:
            logger.error(
                f"[DQ Fatal] Dataset is empty or contains fewer than {min_rows} rows!"
            )

        self.check_results.append(
            {
                "check": "row_count",
                "column": "all",
                "value": float(len(df)),
                "threshold": float(min_rows),
                "passed": passed,
            }
        )
        return passed

    def run_all_checks(self, df: pd.DataFrame, dataset_name: str) -> bool:
        """Executes a full suite of data quality validations for the playback dataset."""
        self.check_results = []

        logger.info(f"Starting DQ checks for [{dataset_name}] with {len(df)} records")

        results = [
            self.check_row_count(df, min_rows=1),
            self.check_null_rate(df, "track_id"),
            self.check_null_rate(df, "track_name"),
            self.check_null_rate(df, "played_at_utc"),
            self.check_duplicate_rate(df, ["track_id", "played_at_utc"]),
            self.check_value_range(df, "popularity", 0, 100),
        ]

        total = len(results)
        passed_count = sum(1 for r in results if r)
        failed_count = total - passed_count

        if failed_count > 0:
            logger.warning(
                f"❌ DQ Check Completed: {total} tests, {passed_count} passed, {failed_count} alerts!"
            )
        else:
            logger.info(f"✅ DQ Check Passed: All {total} tests cleared.")
        return all(results)
