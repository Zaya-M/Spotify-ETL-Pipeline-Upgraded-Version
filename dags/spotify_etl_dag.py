# ============================================================
# File: dags/spotify_etl_dag.py
# Description: Airflow DAG Definition - Orchestrates the full ETL process
# Deployment: Must be placed in Airflow's dags/ directory for auto-discovery
# Note: Defines task orchestration and dependencies; logic resides in src/
#
# DAG Task Flow:
#
# check_api_health
#       ↓
# extract_play_history ──→ quality_check ──→ transform_load_dwd
#       ↓                                            ↓
# extract_track_details ──────────────────→ aggregate_dws
#       ↓                                            ↓
# extract_artist_details ─────────────────→ build_ads
#
# ============================================================

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import date

import pandas as pd

# ============================================================
# DAG Configuration
# ============================================================
default_args = {
    "owner": "zaya",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ============================================================
# DAG Definition
# ============================================================
with DAG(
    dag_id="spotify_etl_pipeline",
    default_args=default_args,
    description="Spotify Music Data Warehouse ETL Pipeline",
    # schedule_interval="0 8 * * *",  # Daily at 08:00 UTC+8
    schedule_interval=None,
    catchup=False,
    tags=["spotify", "etl", "data-warehouse"],
) as dag:

    # ============================================================
    # Task 1: API Connectivity Check
    # ============================================================
    def check_api_health_fn(**context):
        from src.extract.spotify_client import SpotifyExtractor
        from src.utils.logger import get_logger

        logger = get_logger("check_api_health")
        extractor = SpotifyExtractor()

        try:
            user = extractor.sp.current_user()
            logger.info(f"API Connection Successful. User: {user['display_name']}")
        except Exception as e:
            raise Exception(f"Spotify API Connection Failed: {e}")

        logger.info("API Health Check Passed")

    check_api = PythonOperator(
        task_id="check_api_health",
        python_callable=check_api_health_fn,
    )

    # ============================================================
    # Task 2: Incremental Play History Extraction (ODS)
    # ============================================================
    def extract_plays_fn(**context):
        from src.extract.spotify_client import SpotifyExtractor
        from src.load.db_writer import DBWriter
        from src.utils.logger import get_logger

        logger = get_logger("extract_plays")
        extractor = SpotifyExtractor()
        writer = DBWriter()

        plays = extractor.fetch_recent_plays(limit=50)
        if not plays:
            return 0

        df = pd.DataFrame(plays)
        df["etl_date"] = date.today()

        writer.write_ods(df, "ods_play_history")

        track_ids = list(df["track_id"].unique())
        context["ti"].xcom_push(key="track_ids", value=track_ids)

        return len(plays)

    extract_plays = PythonOperator(
        task_id="extract_play_history",
        python_callable=extract_plays_fn,
    )

    # ============================================================
    # Task 3: Data Quality Check
    # ============================================================
    def quality_check_fn(**context):
        from src.utils.db_conn import DBConnection
        from src.utils.logger import get_logger
        import pandas as pd

        logger = get_logger("quality_check")
        engine = DBConnection.get_engine()
        today = date.today()

        # Check for data presence in ODS for the current period
        df = pd.read_sql(
            f"""
            SELECT *
            FROM ods_play_history
            WHERE DATE(played_at) = '{today}'
            """,
            engine,
        )

        if df.empty:
            raise Exception("Quality Check Failed: No data found for the current date.")

        logger.info(f"Quality Check Passed. Record count: {len(df)}")

    quality_check = PythonOperator(
        task_id="quality_check",
        python_callable=quality_check_fn,
    )

    # ============================================================
    # Task 4: Track Metadata Extraction
    # ============================================================
    def extract_tracks_fn(**context):
        from src.extract.spotify_client import SpotifyExtractor
        from src.load.db_writer import DBWriter
        from src.utils.logger import get_logger

        logger = get_logger("extract_tracks")
        track_ids = context["ti"].xcom_pull(
            task_ids="extract_play_history", key="track_ids"
        )

        if not track_ids:
            return

        extractor = SpotifyExtractor()
        writer = DBWriter()

        details = extractor.fetch_track_details(track_ids)
        df = pd.DataFrame(details)
        df["etl_date"] = date.today()

        writer.write_ods(df, "ods_track_detail")

        artist_ids = []
        for d in details:
            artist_ids.extend(d.get("artist_ids", []))

        context["ti"].xcom_push(key="artist_ids", value=list(set(artist_ids)))

    extract_tracks = PythonOperator(
        task_id="extract_track_details",
        python_callable=extract_tracks_fn,
    )

    # ============================================================
    # Task 5: Artist Metadata Extraction
    # ============================================================
    def extract_artists_fn(**context):
        from src.extract.spotify_client import SpotifyExtractor
        from src.load.db_writer import DBWriter
        from src.utils.logger import get_logger

        logger = get_logger("extract_artists")
        artist_ids = context["ti"].xcom_pull(
            task_ids="extract_track_details", key="artist_ids"
        )

        if not artist_ids:
            return

        extractor = SpotifyExtractor()
        writer = DBWriter()

        artists = extractor.fetch_artist_details(artist_ids)
        df = pd.DataFrame(artists)
        df["etl_date"] = date.today()

        writer.write_ods(df, "ods_artist_detail")

    extract_artists = PythonOperator(
        task_id="extract_artist_details",
        python_callable=extract_artists_fn,
    )

    # ============================================================
    # Task 6: Transformation & Loading (ODS → DWD)
    # ============================================================
    def transform_load_dwd_fn(**context):
        from src.transform.cleaner import DataCleaner
        from src.load.db_writer import DBWriter
        from src.utils.db_conn import DBConnection
        import pandas as pd

        cleaner = DataCleaner()
        writer = DBWriter()
        engine = DBConnection.get_engine()
        today = date.today()

        ods_plays = pd.read_sql(
            f"SELECT * FROM ods_play_history WHERE DATE(played_at) = '{today}'", engine
        )
        ods_artists = pd.read_sql(
            f"SELECT * FROM ods_artist_detail WHERE etl_date = '{today}'", engine
        )

        # Persistence to DWD layer
        dwd_plays = cleaner.clean_play_records(ods_plays.to_dict("records"))
        writer.write_dwd(dwd_plays, "dwd_play_record")

        dwd_track_artist = cleaner.split_track_artists(ods_plays.to_dict("records"))
        writer.write_dwd(dwd_track_artist, "dwd_track_artist")

        dwd_artists = cleaner.clean_artists(ods_artists.to_dict("records"))
        writer.write_dwd(dwd_artists, "dwd_artist")

    transform_dwd = PythonOperator(
        task_id="transform_load_dwd",
        python_callable=transform_load_dwd_fn,
    )

    # ============================================================
    # Task 7: Data Aggregation (DWS)
    # ============================================================
    def aggregate_dws_fn(**context):
        from src.load.db_writer import DBWriter

        writer = DBWriter()
        today = date.today()

        dws_daily = writer.build_dws_daily_stats(str(today))
        writer.write_dws(dws_daily, "dws_daily_play_stats")

        dws_artist = writer.build_dws_artist_stats(str(today))
        writer.write_dws(dws_artist, "dws_artist_daily_stats")

    aggregate_dws = PythonOperator(
        task_id="aggregate_dws",
        python_callable=aggregate_dws_fn,
    )

    # ============================================================
    # Task 8: Application Data Store (ADS) Generation
    # ============================================================
    def build_ads_fn(**context):
        from src.load.db_writer import DBWriter
        from src.utils.logger import get_logger

        logger = get_logger("build_ads")
        writer = DBWriter()

        # Build application-level metrics (e.g., Top Artists last 30 days)
        ads_top = writer.build_ads_top_artists(days=30)
        writer.write_ads(ads_top, "ads_top_artists_30d")

        logger.info("ADS layer generation completed")

    build_ads = PythonOperator(
        task_id="build_ads",
        python_callable=build_ads_fn,
    )

    # ============================================================
    # Task Dependencies
    # ============================================================
    check_api >> extract_plays
    extract_plays >> [quality_check, extract_tracks]
    extract_tracks >> extract_artists
    [quality_check, extract_artists] >> transform_dwd
    transform_dwd >> aggregate_dws >> build_ads
