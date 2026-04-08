-- ============================================================
-- File: sql/ods/create_ods_tables.sql
-- Layer: ODS (Operational Data Store)
-- Purpose: To store raw data ingested from Spotify API in its original format
-- Design Principles:
--   1. No business transformations; field names match API response
--   2. All fields allow NULL for data integrity and missing values
--   3. Include 'etl_date' to track ingestion lineage
--   4. Use REPLACE INTO for idempotency during data re-runs
-- Execution: MySQL / DBeaver
-- ============================================================

-- Initialize Database
CREATE DATABASE IF NOT EXISTS spotify_dw
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE spotify_dw;

-- ============================================================
-- ODS Layer: Raw Playback History
-- Mapping: Spotify API /me/player/recently-played
-- ============================================================
CREATE TABLE IF NOT EXISTS ods_play_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id        VARCHAR(50)     COMMENT 'Spotify unique track ID',
    track_name      VARCHAR(500)    COMMENT 'Track name',
    artist_ids      VARCHAR(500)    COMMENT 'Artist IDs (JSON string)',
    artist_names    VARCHAR(500)    COMMENT 'Artist names (JSON string)',
    album_id        VARCHAR(50)     COMMENT 'Album ID',
    album_name      VARCHAR(500)    COMMENT 'Album name',
    duration_ms     INT             COMMENT 'Duration in milliseconds',
    popularity      INT             COMMENT 'Popularity score (0-100)',
    played_at       DATETIME        COMMENT 'Playback timestamp (UTC)',
    context_type    VARCHAR(50)     COMMENT 'Context: album/artist/playlist',
    context_uri     VARCHAR(200)    COMMENT 'Context URI',
    -- ETL Metadata
    etl_date        DATE            COMMENT 'ETL processing date',
    etl_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Ingestion timestamp',
    -- Unique constraint to prevent duplicate playback records
    UNIQUE KEY uk_track_played (track_id, played_at),
    -- Performance Indexes
    INDEX idx_etl_date (etl_date),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB COMMENT='ODS - Spotify Raw Playback History';


-- ============================================================
-- ODS Layer: Raw Track Details
-- Mapping: Spotify API /tracks/{id}
-- ============================================================
CREATE TABLE IF NOT EXISTS ods_track_detail (
    track_id            VARCHAR(50)     PRIMARY KEY COMMENT 'Spotify unique track ID',
    track_name          VARCHAR(500)    COMMENT 'Track name',
    artist_ids          VARCHAR(500)    COMMENT 'Artist IDs (JSON)',
    artist_names        VARCHAR(500)    COMMENT 'Artist names (JSON)',
    album_id            VARCHAR(50)     COMMENT 'Album ID',
    album_name          VARCHAR(500)    COMMENT 'Album name',
    album_release_date  VARCHAR(20)     COMMENT 'Release date string',
    duration_ms         INT             COMMENT 'Duration in milliseconds',
    explicit            TINYINT(1)      COMMENT 'Contains explicit content (0/1)',
    popularity          INT             COMMENT 'Popularity score (0-100)',
    preview_url         VARCHAR(500)    COMMENT '30s audio preview URL',
    -- ETL Metadata
    etl_date            DATE,
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_etl_date (etl_date)
) ENGINE=InnoDB COMMENT='ODS - Spotify Raw Track Details';


-- ============================================================
-- ODS Layer: Raw Artist Details
-- Mapping: Spotify API /artists/{id}
-- ============================================================
CREATE TABLE IF NOT EXISTS ods_artist_detail (
    artist_id       VARCHAR(50)     PRIMARY KEY COMMENT 'Spotify unique artist ID',
    artist_name     VARCHAR(300)    COMMENT 'Artist name',
    genres          VARCHAR(1000)   COMMENT 'Genres (JSON)',
    popularity      INT             COMMENT 'Artist popularity score (0-100)',
    followers_total INT             COMMENT 'Total followers count',
    -- ETL Metadata
    etl_date        DATE,
    etl_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_etl_date (etl_date)
) ENGINE=InnoDB COMMENT='ODS - Spotify Raw Artist Details';


-- ============================================================
-- ODS Layer: ETL Watermark
-- Purpose: Tracks incremental ingestion progress
-- ============================================================
CREATE TABLE IF NOT EXISTS ods_etl_watermark (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    table_name      VARCHAR(100)    NOT NULL COMMENT 'Target table name',
    last_run_time   DATETIME        COMMENT 'Max timestamp processed in previous run',
    last_run_date   DATE            COMMENT 'Max date processed in previous run',
    status          VARCHAR(20)     COMMENT 'success / failed / running',
    records_count   INT             COMMENT 'Record count for current run',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_table (table_name)
) ENGINE=InnoDB COMMENT='ETL Watermark - Tracks incremental loading state';