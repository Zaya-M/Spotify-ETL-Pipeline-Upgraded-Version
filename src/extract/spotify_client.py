# ============================================================
# File: src/extract/spotify_client.py
# Description: Spotify API wrapper for data extraction (ETL - Extract Phase)
# Dependencies: spotipy, python-dotenv
# ============================================================

import os
import json
import time
from datetime import datetime, timezone
from typing import Optional
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

from src.utils.logger import get_logger
from src.utils.db_conn import DBConnection
from sqlalchemy import text

load_dotenv()
logger = get_logger(__name__)


class SpotifyExtractor:
    """
    Spotify data extractor responsible for pulling playback history,
    track details, and artist information.
    """

    # Scopes required for Spotify API authentication
    SCOPES = [
        "user-read-recently-played",
        "user-read-currently-playing",
        "user-library-read",
        "playlist-read-private",
    ]

    def __init__(self):
        """
        Initialize Spotify client with OAuth2 authentication.
        """
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

        if not all([client_id, client_secret, redirect_uri]):
            logger.error("Missing Spotify credentials in environment variables.")
            raise ValueError("Missing Spotify Credentials")

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=" ".join(self.SCOPES),
            open_browser=False,
        )

        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("Spotify API client initialized successfully.")

    def get_watermark(self, table_name: str) -> Optional[datetime]:
        """
        Retrieve the last successful extraction timestamp (watermark) from the database.
        """
        engine = DBConnection.get_engine()
        sql = text(
            "SELECT last_run_time FROM ods_etl_watermark WHERE table_name = :table_name"
        )

        try:
            with engine.connect() as conn:
                result = conn.execute(sql, {"table_name": table_name}).fetchone()
                if result and result[0]:
                    logger.info(f"Watermark found: {table_name} -> {result[0]}")
                    return result[0]
                else:
                    logger.info(
                        f"No watermark for {table_name}. Performing full extraction."
                    )
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch watermark: {e}")
            return None

    def update_watermark(
        self,
        table_name: str,
        last_time: datetime,
        records_count: int,
        status: str = "success",
    ):
        """
        Update the ETL watermark in the database upon successful execution.
        """
        engine = DBConnection.get_engine()
        sql = text(
            """
            REPLACE INTO ods_etl_watermark (table_name, last_run_time, status, records_count)
            VALUES (:table_name, :last_time, :status, :records_count)
        """
        )
        try:
            with engine.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "table_name": table_name,
                        "last_time": last_time,
                        "status": status,
                        "records_count": records_count,
                    },
                )
            logger.debug(f"Watermark updated: {table_name} -> {last_time}")
        except Exception as e:
            logger.error(f"Failed to update watermark: {e}")

    def fetch_recent_plays(self, limit: int = 50) -> list[dict]:
        """
        Fetch the user's recently played tracks from Spotify API.
        Implements incremental loading using a watermark.
        """
        logger.info("Starting recent plays extraction...")

        watermark = self.get_watermark("ods_play_history")
        after_timestamp = int(watermark.timestamp() * 1000) if watermark else None

        try:
            results = self.sp.current_user_recently_played(
                limit=limit, after=after_timestamp
            )
            items = results.get("items", [])

            if not items:
                logger.info("No new playback records found.")
                return []

            parsed_data = []
            for item in items:
                track = item["track"]
                played_at_str = item["played_at"]
                # Convert ISO 8601 timestamp to datetime object
                played_at_dt = datetime.fromisoformat(
                    played_at_str.replace("Z", "+00:00")
                )

                parsed_data.append(
                    {
                        "track_id": track["id"],
                        "track_name": track["name"],
                        "artist_ids": json.dumps([a["id"] for a in track["artists"]]),
                        "artist_names": json.dumps(
                            [a["name"] for a in track["artists"]]
                        ),
                        "album_id": track["album"]["id"],
                        "album_name": track["album"]["name"],
                        "duration_ms": track["duration_ms"],
                        "played_at": played_at_dt,
                        "context_type": (
                            item["context"]["type"] if item.get("context") else None
                        ),
                    }
                )

            latest_time = max([d["played_at"] for d in parsed_data])
            self.update_watermark("ods_play_history", latest_time, len(parsed_data))

            logger.info(f"Successfully extracted {len(parsed_data)} playback records.")
            return parsed_data

        except Exception as e:
            logger.error(f"Error during playback history extraction: {e}")
            return []

    def fetch_track_details(self, track_ids: list[str]) -> list[dict]:
        """
        Batch fetch track details (Max 50 IDs per request).
        Handles pagination and basic retry logic for rate limiting.
        """
        logger.info(f"Extracting details for {len(track_ids)} tracks...")

        batches = [track_ids[i : i + 50] for i in range(0, len(track_ids), 50)]
        all_details = []

        for batch in batches:
            retry = 3
            while retry > 0:
                try:
                    response = self.sp.tracks(batch)
                    for t in response["tracks"]:
                        if t:
                            all_details.append(
                                {
                                    "track_id": t["id"],
                                    "popularity": t["popularity"],
                                    "explicit": t["explicit"],
                                    "available_markets_count": len(
                                        t.get("available_markets", [])
                                    ),
                                }
                            )
                    break
                except Exception as e:
                    logger.warning(
                        f"API request failed, retrying... {retry-1} attempts left."
                    )
                    time.sleep(2)
                    retry -= 1

        return all_details

    def fetch_artist_details(self, artist_ids: list[str]) -> list[dict]:
        """
        Batch fetch artist details including genres and follower counts.
        """
        logger.info(f"Extracting details for {len(artist_ids)} artists...")
        batches = [artist_ids[i : i + 50] for i in range(0, len(artist_ids), 50)]
        all_artists = []

        for batch in batches:
            try:
                response = self.sp.artists(batch)
                for a in response["artists"]:
                    if a:
                        all_artists.append(
                            {
                                "artist_id": a["id"],
                                "name": a["name"],
                                "genres": json.dumps(a["genres"]),
                                "popularity": a["popularity"],
                                "followers": a["followers"]["total"],
                            }
                        )
            except Exception as e:
                logger.error(f"Failed to batch fetch artists: {e}")

        return all_artists


if __name__ == "__main__":
    # Test execution for API connectivity
    extractor = SpotifyExtractor()
    plays = extractor.fetch_recent_plays(limit=10)
    print(f"Extracted {len(plays)} records.")
    if plays:
        print("Sample Record:")
        import pprint

        pprint.pprint(plays[0])
