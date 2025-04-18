provider "google" {
  project = var.project_id
  region  = var.region
}

# Create BigQuery dataset
resource "google_bigquery_dataset" "f1_dataset" {
  dataset_id                  = "f1_data"
  friendly_name               = "F1 Racing Data"
  description                 = "Dataset containing F1 racing data from OpenF1 API"
  location                    = "US"
  default_table_expiration_ms = null

  labels = {
    env = "dev"
  }
}

# Create BigQuery table for Driver Laps
resource "google_bigquery_table" "driver_laps" {
  dataset_id = google_bigquery_dataset.f1_dataset.dataset_id
  table_id   = "driver_laps"

  schema = <<EOF
[
  {
    "name": "id",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Unique row identifier"
  },
  {
    "name": "session_key",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Unique identifier for the session"
  },
  {
    "name": "date_start",
    "type": "TIMESTAMP",
    "mode": "NULLABLE",
    "description": "Start time of the lap"
  },
  {
    "name": "driver_number",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Driver number"
  },
  {
    "name": "lap_duration",
    "type": "FLOAT",
    "mode": "NULLABLE",
    "description": "Duration of the lap in seconds"
  },
  {
    "name": "lap_number",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Lap number"
  },
  {
    "name": "st_speed",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "ST speed"
  },
  {
    "name": "position",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Driver's position during the lap"
  },
  {
    "name": "name_acronym",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Driver's acronym"
  },
  {
    "name": "team_name",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Team name"
  },
  {
    "name": "team_colour",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Team color"
  }
]
EOF

  labels = {
    env = "dev"
  }
}

# Create BigQuery table for Race Control
resource "google_bigquery_table" "race_control" {
  dataset_id = google_bigquery_dataset.f1_dataset.dataset_id
  table_id   = "race_control"

  schema = <<EOF
[
  {
    "name": "id",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Unique row identifier"
  },
  {
    "name": "session_key",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Unique identifier for the session"
  },
  {
    "name": "date",
    "type": "TIMESTAMP",
    "mode": "NULLABLE",
    "description": "Date and time of the message"
  },
  {
    "name": "category",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Category of the message"
  },
  {
    "name": "flag",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Flag status"
  },
  {
    "name": "message",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Race control message"
  }
]
EOF

  labels = {
    env = "dev"
  }
}