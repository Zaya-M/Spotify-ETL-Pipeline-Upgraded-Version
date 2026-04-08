# Spotify-ETL-Pipeline-Upgraded-Version

A production-ready Spotify ETL pipeline built with Python, Airflow, and MySQL. This project implements a structured data warehousing approach using ODS, DWD, and ADS layering.

## 📌 Project Overview
This project automates the extraction of "Recently Played" tracks from the Spotify API, processes the data through several quality checks, and loads it into a MySQL data warehouse for further analysis.

## 🛠 Tech Stack
* **Language:** Python 3.x
* **Orchestration:** Apache Airflow
* **Database:** MySQL (Structured with ODS, DWD, ADS layers)
* **Data Handling:** Pandas
* **API:** Spotify Web API (Spotipy)

## 🏗 Data Warehouse Architecture
The pipeline follows a classic three-layer data modeling approach:
* **ODS (Operational Data Store):** Original data landed directly from the API (Raw format).
* **DWD (Data Warehouse Detail):** Cleaned and standardized data (De-duplicated, null values handled).
* **ADS (Application Data Service):** Aggregated metrics for business insights (e.g., top artists, listening trends).

## 🚀 Key Features
* **Incremental Loading:** Only new listening history is processed to save resources.
* **Data Validation:** Includes integrity checks for primary keys and null constraints.
* **Workflow Automation:** Airflow DAGs manage the scheduling and dependency of ETL tasks.

## ⚙️ Setup & Installation
1. Clone the repository.
2. Configure your Spotify API credentials in `config.py`.
3. Set up the Airflow environment and MySQL connection.
4. Trigger the DAG: `spotify_etl_dag`.