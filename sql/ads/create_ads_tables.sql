-- ============================================================
-- File: sql/ads/create_ads_tables.sql
-- Layer: ADS (Application Data Store)
-- Purpose: Denormalized tables for Metabase visualization and business reporting.
-- Design Principles:
--   1. Denormalized schema for optimal query performance.
--   2. Business-friendly field descriptions.
--   3. Direct mapping to BI charts without complex joins.
-- ============================================================

-- ============================================================
-- ADS: Top Artists Ranking (Last 30 Days)
-- Visualization: Bar Chart - Top 10 Frequently Streamed Artists
-- ============================================================
CREATE TABLE IF NOT EXISTS ads_top_artists_30d (
    rank_no             INT         COMMENT 'Ranking position',
    artist_id           VARCHAR(50),
    artist_name         VARCHAR(300),
    total_play_count    INT         COMMENT 'Total play count in last 30d',
    total_duration_min  DECIMAL(10,2) COMMENT 'Total listening duration (min) in last 30d）',
    unique_track_count  INT         COMMENT 'Count of distinct tracks played',
    main_genre          VARCHAR(100) COMMENT 'Primary music genre',
    -- Metadata
    stat_start_date     DATE        COMMENT 'Statistics start date',
    stat_end_date       DATE        COMMENT 'Statistics end date',
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rank_no)
) ENGINE=InnoDB COMMENT='ADS-Top Artists Ranking (Last 30 Days)';


-- ============================================================
-- ADS: Daily Listening Trends
-- Visualization: Line Chart - Daily Playback Volume Trend
-- ============================================================
CREATE TABLE IF NOT EXISTS ads_daily_trend (
    stat_date           DATE        PRIMARY KEY,
    total_plays         INT         COMMENT 'Total play count per day',
    total_duration_min  DECIMAL(10,2) COMMENT 'Total listening duration (min) per day',
    unique_artists      INT         COMMENT 'Count of distinct artists per day',
    unique_tracks       INT         COMMENT 'Count of distinct tracks per day',
    plays_vs_yesterday  DECIMAL(10,2) COMMENT 'Playback volume growth rate vs yesterday (%)',
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='ADS-Daily Listening Trends';


-- ============================================================
-- ADS: Genre Distribution
-- Visualization: Pie/Donut Chart - Music Taste Distribution
-- ============================================================
CREATE TABLE IF NOT EXISTS ads_genre_distribution (
    main_genre          VARCHAR(100)    NOT NULL,
    play_count          INT             COMMENT 'Total play count per genre',
    play_percentage     DECIMAL(5,2)    COMMENT 'Percentage of total playback volume',
    unique_artists      INT             COMMENT 'Count of distinct artists in genre',
    stat_start_date     DATE,
    stat_end_date       DATE,
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (main_genre)
) ENGINE=InnoDB COMMENT='ADS-Genre Distribution Statistics';


-- ============================================================
-- ADS: Listening Heatmap
-- Visualization: Heatmap - Peak Listening Hours
-- ============================================================
CREATE TABLE IF NOT EXISTS ads_listening_heatmap (
    play_weekday        TINYINT     NOT NULL COMMENT 'Day of week (1-7)',
    play_hour           TINYINT     NOT NULL COMMENT 'Hour of day (0-23)',
    play_count          INT         COMMENT 'Cumulative play count for this period',
    etl_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (play_weekday, play_hour)
) ENGINE=InnoDB COMMENT='ADS-Listening Heatmap Data';
