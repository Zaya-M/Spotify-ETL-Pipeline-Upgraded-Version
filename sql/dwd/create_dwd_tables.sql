-- ============================================================
-- File: sql/dwd/create_dwd_tables.sql
-- Layer: DWD (Data Warehouse Detail)
-- Purpose: Cleanse and standardize ODS data into structured detail records.
-- Design Principles:
--   1. Strict data typing to prevent data corruption.
--   2. Unified naming convention (snake_case).
--   3. Convert all timestamps to Beijing Time (UTC+8).
--   4. Flatten JSON arrays into individual records (one artist per row).
-- ============================================================

-- ============================================================
-- Table: dwd_play_record
-- Description: Cleansed playback history details.
-- ============================================================
CREATE TABLE IF NOT EXISTS dwd_play_record (
    play_id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id        VARCHAR(50)     NOT NULL COMMENT 'Track ID',
    track_name      VARCHAR(500)    NOT NULL COMMENT 'Track name (non-nullable)',
    album_id        VARCHAR(50)     COMMENT 'Album ID',
    album_name      VARCHAR(500)    COMMENT 'Album name',
    duration_sec    DECIMAL(10,2)   COMMENT 'Duration in seconds (converted from ms)',
    popularity      TINYINT         COMMENT 'Popularity score (0-100)',
    played_at_utc   DATETIME        COMMENT 'Playback time (UTC)',
    played_at_cst   DATETIME        COMMENT 'Playback time (CST/UTC+8)',
    play_date       DATE            COMMENT 'Playback date (CST)',
    play_hour       TINYINT         COMMENT 'Playback hour (0-23)',
    play_weekday    TINYINT         COMMENT 'Day of the week (1=Mon, 7=Sun)',
    context_type    VARCHAR(50)     COMMENT 'Playback context/scenario',
    -- ETL Metadata
    etl_date        DATE            NOT NULL,
    UNIQUE KEY uk_track_played (track_id, played_at_utc),
    INDEX idx_play_date (play_date),
    INDEX idx_track_id (track_id)
) ENGINE=InnoDB COMMENT='DWD - Cleansed Playback Records';


-- ============================================================
-- Table: dwd_track_artist
-- Description: Bridge table for Track and Artist (One-to-Many).
-- Grain: Flattened from artist_ids JSON array to one row per artist.
-- ============================================================
CREATE TABLE IF NOT EXISTS dwd_track_artist (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id        VARCHAR(50)     NOT NULL,
    artist_id       VARCHAR(50)     NOT NULL,
    artist_name     VARCHAR(300)    NOT NULL,
    artist_order    TINYINT         COMMENT 'Position in artist list (1st is usually primary)',
    -- ETL Metadata
    etl_date        DATE            NOT NULL,
    UNIQUE KEY uk_track_artist (track_id, artist_id),
    INDEX idx_artist_id (artist_id),
    INDEX idx_track_id (track_id)
) ENGINE=InnoDB COMMENT='DWD - Track-Artist Relationship';


-- ============================================================
-- Table: dwd_artist
-- Description: Cleansed artist profile details.
-- ============================================================
CREATE TABLE IF NOT EXISTS dwd_artist (
    artist_id       VARCHAR(50)     PRIMARY KEY,
    artist_name     VARCHAR(300)    NOT NULL,
    popularity      TINYINT,
    followers_total INT,
    main_genre      VARCHAR(100)    COMMENT 'Primary genre (extracted from first element)',
    all_genres      VARCHAR(1000)   COMMENT 'All genres in JSON format',
    -- ETL Metadata
    etl_date        DATE            NOT NULL,
    etl_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='DWD - Artist Dimension';