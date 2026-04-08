# ============================================================
# File: src/transform/cleaner.py
# Description: Data cleaning and transformation (Transform Phase)
# Input: ODS raw data (List of dictionaries)
# Output: DWD cleaned data (Pandas DataFrame)
# Dependencies: pandas
# ============================================================

import json
import pandas as pd
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)

# CST Offset = UTC + 8 hours
CST_OFFSET = timedelta(hours=8)


class DataCleaner:
    """
    DataCleaner handles the transformation from ODS (Operational Data Store)
    to DWD (Data Warehouse Detail) layer.
    """

    @staticmethod
    def process_genres(genres_list):
        if not genres_list or len(genres_list) == 0:
            return None, "[]"
        main_genre = genres_list[0]
        all_genres = json.dumps(genres_list, ensure_ascii=False)
        return main_genre, all_genres

    def clean_play_records(self, raw_records: list[dict]) -> pd.DataFrame:
        """
        Cleans listening history and transforms ODS format to DWD format.

        Cleaning Rules:
        1. Deduplication based on track_id and played_at.
        2. Filter out records with null track_name or track_id.
        3. Convert duration_ms to duration_sec (rounded to 2 decimal places).
        4. Parse played_at strings into UTC datetime objects.
        5. Convert UTC to CST (UTC+8) and extract time dimensions.
        """
        if not raw_records:
            logger.warning("No raw records found for cleaning.")
            return pd.DataFrame()

        logger.info(f"Starting cleaning process for {len(raw_records)} records...")

        df = pd.DataFrame(raw_records)

        # Statistics of missing values before cleaning
        null_counts = df.isnull().sum().to_dict()
        logger.debug(f"Null value statistics before cleaning: {null_counts}")

        # ---- Deduplication ----
        initial_count = len(df)
        df = df.drop_duplicates(subset=["track_id", "played_at"], keep="first")

        # ---- Filtering ----
        df = df.dropna(subset=["track_id", "track_name"])
        dropped_count = initial_count - len(df)
        if dropped_count > 0:
            logger.info(f"Filtered {dropped_count} invalid/duplicate records.")

        # ---- Unit Conversion ----
        df["duration_sec"] = (df["duration_ms"] / 1000).round(2)

        # ---- Timezone Transformation ----
        # Parse UTC time and convert to CST (Asia/Shanghai)
        df["played_at_utc"] = pd.to_datetime(df["played_at"], utc=True)
        df["played_at_cst"] = df["played_at_utc"].dt.tz_convert("Asia/Shanghai")

        # ---- Feature Engineering: Time Dimensions ----
        df["play_date"] = df["played_at_cst"].dt.date
        df["play_hour"] = df["played_at_cst"].dt.hour
        df["play_weekday"] = df["played_at_cst"].dt.dayofweek + 1  # 1=Monday, 7=Sunday

        # ---- Popularity Constraint ----
        if "popularity" in df.columns:
            df["popularity"] = df["popularity"].clip(0, 100)

        # ---- Schema Alignment ----
        # Select and reorder columns for DWD table schema
        cols = [
            "track_id",
            "track_name",
            "album_id",
            "album_name",
            "duration_sec",
            "popularity",
            "played_at_utc",
            "played_at_cst",
            "play_date",
            "play_hour",
            "play_weekday",
            "context_type",
            "etl_date",
        ]

        df["etl_date"] = datetime.now().date()

        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols]

        logger.info(f"Cleaning completed. {len(df)} records remaining.")
        return df

    def split_track_artists(self, raw_records: list[dict]) -> pd.DataFrame:
        """
        Flattens the artist list into a one-to-many relationship table.
        Example: One track with 3 artists generates 3 separate rows.

        Input: Raw records with artist_ids as JSON strings.
        Output: DataFrame with track-artist mappings (track_id, artist_id, artist_name, artist_order).
        """
        rows = []
        for record in raw_records:
            track_id = record.get("track_id")
            if not track_id:
                continue

            try:
                # Handle both JSON strings and list formats
                ids = record.get("artist_ids")
                names = record.get("artist_names")

                artist_ids = json.loads(ids) if isinstance(ids, str) else ids
                artist_names = json.loads(names) if isinstance(names, str) else names

                # Generate mapping rows with order index starting from 1
                for idx, (a_id, a_name) in enumerate(zip(artist_ids, artist_names), 1):
                    rows.append(
                        {
                            "track_id": track_id,
                            "artist_id": a_id,
                            "artist_name": a_name,
                            "artist_order": idx,
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to parse artist JSON for track {track_id}: {e}")

        return pd.DataFrame(rows).drop_duplicates()

    def clean_artists(self, raw_artists: list[dict]) -> pd.DataFrame:
        """
        Cleans artist metadata.

        Cleaning Rules:
        1. Deduplicate by artist_id.
        2. Extract primary genre and serialize full genre list to JSON.
        3. Filter out records with empty artist names.
        """
        if not raw_artists:
            return pd.DataFrame()

        df = pd.DataFrame(raw_artists)

        # Remove records with missing identifiers and keep the most recent entry
        df = df.dropna(subset=["artist_name", "artist_id"])
        df = df.drop_duplicates(subset=["artist_id"], keep="last")

        # Process genre metadata
        if "genres" in df.columns:
            res = df["genres"].apply(self.process_genres)
            df["main_genre"] = [x[0] for x in res]
            df["all_genres"] = [x[1] for x in res]

        df["etl_date"] = datetime.now().date()

        return df
