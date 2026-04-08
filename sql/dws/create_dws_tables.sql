-- ============================================================
-- File: sql/dws/create_dws_tables.sql
-- Layer: DWS (Data Warehouse Summary)
-- Purpose: Perform aggregations by time/dimension to produce core metrics.
-- Design Principles:
--   1. One table per analysis theme.
--   2. Aggregated by Day/Week/Month for downstream consumption.
--   3. Daily full refresh for the current partition.
-- ============================================================

-- ============================================================
-- DWS: Daily Playback Statistics
-- ============================================================
CREATE TABLE IF NOT EXISTS dws_daily_play_stats (
    stat_date           DATE        NOT NULL COMMENT 'Statistics date',
    total_plays         INT         COMMENT 'Total play count per day',
    unique_tracks       INT         COMMENT 'Unique tracks played per day',
    unique_artists      INT         COMMENT 'Unique artists played per day',
    total_duration_min  DECIMAL(10,2) COMMENT 'Total duration in minutes',
    avg_popularity      DECIMAL(5,2)  COMMENT 'Average track popularity',
    peak_hour           TINYINT     COMMENT 'Hour with peak playback activity',
    -- ETL Metadata
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (stat_date)
) ENGINE=InnoDB COMMENT='DWS Layer - Daily Playback Summary';


-- ============================================================
-- DWS: Daily Artist Playback Statistics
-- ============================================================
CREATE TABLE IF NOT EXISTS dws_artist_daily_stats (
    stat_date           DATE        NOT NULL,
    artist_id           VARCHAR(50) NOT NULL,
    artist_name         VARCHAR(300),
    play_count          INT         COMMENT 'Total plays per artist per day',
    unique_track_count  INT         COMMENT 'Unique tracks per artist per day',
    total_duration_min  DECIMAL(10,2),
    avg_popularity      DECIMAL(5,2),
    -- ETL Metadata
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (stat_date, artist_id),
    INDEX idx_artist_id (artist_id)
) ENGINE=InnoDB COMMENT='DWS Layer - Daily Artist Stats';


-- ============================================================
-- DWS: Hourly Playback Heatmap Statistics
-- ============================================================
CREATE TABLE IF NOT EXISTS dws_hourly_stats (
    stat_date           DATE        NOT NULL,
    play_hour           TINYINT     NOT NULL COMMENT 'Hour of the day (0-23)',
    play_count          INT         COMMENT 'Playback count per hour',
    unique_tracks       INT         COMMENT 'Unique tracks per hour',
    PRIMARY KEY (stat_date, play_hour)
) ENGINE=InnoDB COMMENT='DWS Layer - Hourly Playback Stats';