# ============================================================
# File: src/load/db_writer.py
# Description: Persists cleansed DataFrames into MySQL layers (Load Phase)
# Core Principle: Idempotency — Ensures re-runs do not produce duplicate data
# Dependencies: pandas, sqlalchemy, pymysql
# ============================================================

import pandas as pd
from sqlalchemy import text
from datetime import datetime
from src.utils.logger import get_logger
from src.utils.db_conn import DBConnection

logger = get_logger(__name__)


def insert_ignore(table, conn, keys, data_iter):
    """
    Custom insertion method for pandas.to_sql to implement INSERT IGNORE syntax.
    """
    columns = ", ".join(keys)
    placeholders = ", ".join(["%s"] * len(keys))
    sql = f"INSERT IGNORE INTO {table.name} ({columns}) VALUES ({placeholders})"
    conn.execute(sql, list(data_iter))


class DBWriter:
    """
    Handles database persistence with support for various write strategies:
    INSERT IGNORE, Overwrite (Delete-Insert), and Full Refresh (Truncate).
    """

    def __init__(self):
        self.engine = DBConnection.get_engine()

    def _write_with_ignore(self, df: pd.DataFrame, table_name: str) -> int:
        """
        Loads data into ODS/DWD layers using INSERT IGNORE to maintain idempotency.

        Args:
            df: Cleaned DataFrame to be loaded.
            table_name: Target MySQL table name.

        Returns:
            int: Number of records processed.
        """
        if df is None or len(df) == 0:
            logger.warning(f"Skip writing to {table_name}: DataFrame is empty.")
            return 0

        try:
            df.to_sql(
                table_name,
                self.engine,
                if_exists="append",
                index=False,
                method=insert_ignore,
            )
            logger.info(
                f"Successfully loaded {len(df)} records into {table_name} (duplicates ignored)."
            )
            return len(df)
        except Exception as e:
            logger.error(f"Failed to load data into {table_name}: {e}")
            return 0

    def write_ods(self, df: pd.DataFrame, table_name: str) -> int:
        return self._write_with_ignore(df, table_name)

    def write_dwd(self, df: pd.DataFrame, table_name: str) -> int:
        return self._write_with_ignore(df, table_name)

    def write_dws(self, df: pd.DataFrame, table_name: str) -> int:
        """
        Loads data into DWS layer using a 'Delete-then-Insert' strategy for a specific date.
        This ensures data freshness for the given T+1 partition without duplication.
        """
        if df is None or len(df) == 0:
            return 0

        today = datetime.now().date()
        with self.engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {table_name} WHERE etl_date = :date"),
                {"date": today},
            )
            df.to_sql(table_name, conn, if_exists="append", index=False)

        logger.info(f"DWS Layer {table_name}: Incremental refresh completed.")
        return len(df)

    def write_ads(self, df: pd.DataFrame, table_name: str) -> int:
        """
        Loads data into ADS layer using a Full Refresh (Truncate & Insert) strategy.
        """
        if df is None or len(df) == 0:
            return 0

        with self.engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            df.to_sql(table_name, conn, if_exists="append", index=False)

        logger.info(f"ADS Layer {table_name}: Full refresh completed.")
        return len(df)

    def build_dws_daily_stats(self, etl_date: str) -> pd.DataFrame:
        """
        Aggregates DWD records into DWS daily statistics via SQL for optimal performance.
        """
        sql = """
        -- Task: Aggregate daily listening metrics from dwd_play_record
        SELECT 
             play_date AS stat_date,
             COUNT(*) AS total_plays,
             COUNT(DISTINCT track_id) AS unique_tracks,
             ROUND(SUM(duration_sec) / 60, 2) AS total_duration_min,
             0 AS avg_popularity, 
             CURDATE() AS etl_date
        FROM dwd_play_record
        WHERE etl_date = %s
        GROUP BY play_date
        """
        return pd.read_sql(sql, self.engine, params=(etl_date,))

    def build_dws_artist_stats(self, etl_date: str) -> pd.DataFrame:
        """
        Aggregates artist-level metrics by joining play records and artist metadata.
        """
        sql = """
        -- Task: Calculate daily artist statistics via table join
        SELECT 
            pr.play_date AS stat_date,
            ta.artist_id,
            ta.artist_name,
            COUNT(*) AS play_count,
            COUNT(DISTINCT pr.track_id) AS unique_track_count,
            ROUND(SUM(pr.duration_sec) / 60, 2) AS total_duration_min,
            %s AS etl_date
        FROM dwd_play_record pr
        JOIN dwd_track_artist ta ON pr.track_id = ta.track_id
        WHERE pr.etl_date = %s
        GROUP BY pr.play_date, ta.artist_id, ta.artist_name
        """
        return pd.read_sql(sql, self.engine, params=(etl_date, etl_date))

    def build_ads_top_artists(self, days: int = 30) -> pd.DataFrame:
        """
        Ranks top artists over the last N days using DWS aggregated data.
        """
        sql = """
        -- Task: Generate Top 20 artist rankings based on play count
        SELECT 
            ROW_NUMBER() OVER (ORDER BY SUM(play_count) DESC) AS rank_no,
            artist_id,
            artist_name,
            SUM(play_count) AS total_play_count,
            SUM(total_duration_min) AS total_duration_min,
            COUNT(DISTINCT stat_date) AS active_days
        FROM dws_artist_daily_stats
        WHERE stat_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY artist_id, artist_name
        ORDER BY total_play_count DESC
        LIMIT 20
        """
        return pd.read_sql(sql, self.engine, params=(days,))
