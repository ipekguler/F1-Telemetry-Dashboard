# 🏎️ F1 Telemetry Data Streaming & Visualization Pipeline

This project creates a real-time data pipeline for streaming, processing, and visualizing [OpenF1](https://openf1.org/) Formula 1 telemetry data using **PyFlink**, **PostgreSQL**, **Redpanda**, **BigQuery**, and **Looker**.

It ingests live F1 telemetry into Kafka topics, processes and joins the data using PyFlink, sinks it into **PostgreSQL** and syncs it to **Google BigQuery** to generate a real-time dashboard.

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
| `f1-laps`        | Lap-by-lap timing data per driver                                          |
| `f1-position`    | Real-time driver position data                                             |
| `f1-drivers`     | Static driver metadata (name, team, color)                                 |
| `f1-race_control`| Race control data                                                          |

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
| st_speed       | INTEGER     | Speed Trap data                             |
| position       | INTEGER     | Driver's race position                      |
| name_acronym   | STRING      | Driver acronym (e.g., VER, HAM)             |
| team_name      | STRING      | Team name                                   |
| team_colour    | STRING      | Team’s official color code                  |

### `race_control`
Race control messages (yellow flag, SC, etc.)

| Column         | Type        | Description                                 |
|----------------|-------------|---------------------------------------------|
| session_key    | INTEGER     | Unique identifier for session               |
| date           | TIMESTAMP   | Timestamp of the message                    |
| category       | STRING      | Category of control message                 |
| flag           | STRING      | Race control flag (e.g. SC, RED, etc.)      |
| message        | STRING      | Control message text                        |

---

## How It Works

### Redpanda
1. **Data Ingested to Topics**: Extracts data from API services and sends them to `f1-laps`, `f1-position`, `f1-drivers`, `f1-race_control` topics

### Flink:
1. **Read from Redpanda topics**: Creates data sources for `f1-laps`, `f1-position`, `f1-drivers`, `f1-race_control`
2. **Join & Enrich Data**: Combines real-time laps with driver and position data
3. **Output**: Inserts data to PostgreSQL

### PostgreSQL
Stores enriched driver lap data and race control data.  

Used as a source for syncing into BigQuery with a custom sync script.

---

## BigQuery Sync Script (Python)

A Python script that continuously syncs new data from PostgreSQL to BigQuery. Bigquery tables are cleared when a new session begins and populated with new session data.

## Looker Dashboard

See "looker" folder for a snapshot of the live dashboard.

## Setup

### 1. Clone Repo

```
$ git clone https://github.com/ipekguler/f1-telemetry-dashboard.git
$ cd f1-telemetry-dashboard
```

### 2. Configure GCP Credentials

Make sure your service account credentials are in gcp-credentials folder and you have the required permissions.

### 3. Create GCP Resources

Use Terraform to provision Cloud resources for the porject. You need to have Terraform set up.

```
$ cd terraform
$ terraform init
$ terraform apply
```

4. Run Services with Docker

Run the pipeline with docker-compose.

```
$ cd ..
$ docker-compose up
```