# 🏎️ F1 Telemetry Data Streaming & Visualization Pipeline

This project creates a real-time data pipeline for streaming, processing, and visualizing [OpenF1](https://openf1.org/) Formula 1 telemetry data using **PyFlink**, **PostgreSQL**, **Redpanda**, **BigQuery**, and **Looker**.

It ingests live F1 telemetry into Kafka topics, processes and joins the data using PyFlink, and sinks it into **PostgreSQL** and syncs it to **Google BigQuery** to generate a real-time dashboard.

---

## Tools & Technologies

| Tool                | Purpose                                                                 |
|---------------------|-------------------------------------------------------------------------|
| **Redpanda**        | Kafka-compatible streaming platform for ingesting F1 data               |
| **PyFlink**         | Real-time data processing and streaming logic                           |
| **PostgreSQL**      | Intermediate sink for inspection and primary key enforcement            |
| **Google BigQuery** | Cloud-based data warehouse used for analytics & visualization           |
| **Looker Studio**   | Data visualization and dashboarding tool                                |
| **Docker Compose**  | Orchestration of Redpanda, Flink, PostgreSQL                            |
| **Python**          | Orchestrates syncing data from PostgreSQL into BigQuery                 |

---

## Data Topics

This pipeline works with the following Kafka topics:

| Kafka Topic      | Description                                                                |
|------------------|----------------------------------------------------------------------------|
| `f1_laps`        | Lap-by-lap timing data per driver                                          |
| `f1_position`    | Real-time driver position data                                             |
| `f1_drivers`     | Static driver metadata (name, team, color)                                 |
| `f1-race_control`| Session-level metadata (e.g., session start)                               |

---

## BigQuery Tables

BigQuery is used to store and visualize the final enriched results:

### `driver_laps`
Joined and enriched lap data per driver for the latest session.

| Column         | Type        | Description                                 |
|----------------|-------------|---------------------------------------------|
| session_key    | INTEGER     | Unique identifier for session               |
| date_start     | TIMESTAMP   | Timestamp of lap start                      |
| driver_number  | INTEGER     | Driver’s unique number                      |
| lap_duration   | FLOAT       | Duration of lap                             |
| lap_number     | INTEGER     | Lap number                                  |
| st_speed       | INTEGER     | Sector 1 speed                              |
| position       | INTEGER     | Driver's race position                      |
| name_acronym   | STRING      | Driver acronym (e.g., VER, HAM)             |
| team_name      | STRING      | Team name                                   |
| team_colour    | STRING      | Team’s official color                       |

### `race_control`
Official control messages (yellow flag, SC, etc.)

| Column         | Type        | Description                                 |
|----------------|-------------|---------------------------------------------|
| session_key    | INTEGER     | Unique session ID                           |
| date           | TIMESTAMP   | Timestamp of the message                    |
| category       | STRING      | Category of control message                 |
| flag           | STRING      | Race control flag (e.g. SC, RED, etc.)      |
| message        | STRING      | Control message text                        |

---

## How It Works

### 🌀 Streaming Pipeline (Flink):
1. **Read from Redpanda topics**: `f1_laps`, `f1_position`, `f1_drivers`
2. **Join & Enrich Data**: Combine real-time laps with driver and position metadata
3. **Output**:
   - **Upsert to Kafka topic**: `f1-laps-enriched`
   - **Insert to PostgreSQL**: For historical verification
   - **Insert to BigQuery**: For visualization in Looker

### PostgreSQL
Stores enriched lap data and race control data.  

Used as a source for syncing into BigQuery with a custom sync script.

---

## BigQuery Sync Script (Python)

A Python script continuously syncs new data from PostgreSQL to BigQuery.

### Features:
- Tracks the latest synced `id` for each table
- Automatically detects session changes
- Truncates BigQuery tables on startup and on new session
- Batches inserts to BigQuery using `insert_rows_json()`

## Looker Dashboard

Check out Looker folder for a snapshot of the live dashboard

## Setup

### 1. Clone Repo

```
$ git clone https://github.com/ipekguler/f1-telemetry-dashboard.git
$ cd f1-telemetry-dashboard
```

### 2. Configure GCP Credentials

Make sure your service account credentials are in gcp-credentials folder and you have the required permissions.

### 3. Create GCP Resources

```
$ cd terraform
$ terraform init
$ terraform apply
```

4. Run Services with Docker
```
$ cd ..
$ docker-compose up
```