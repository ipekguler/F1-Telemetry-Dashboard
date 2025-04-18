output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.f1_dataset.dataset_id
}

output "driver_laps_table_id" {
  description = "The ID of the driver laps table"
  value       = google_bigquery_table.driver_laps.table_id
}

output "race_control_table_id" {
  description = "The ID of the race control table"
  value       = google_bigquery_table.race_control.table_id
}

output "bigquery_connection_string" {
  description = "Connection string for BigQuery"
  value       = "https://console.cloud.google.com/bigquery?project=${var.project_id}&p=${var.project_id}&d=${google_bigquery_dataset.f1_dataset.dataset_id}"
}

output "dashboard_instructions" {
  value = <<EOF
To create your F1 dashboard:
1. Go to https://lookerstudio.google.com/
2. Create a new report
3. Add BigQuery as a data source
4. Select the f1_data.driver_laps and f1_data.race_control tables
5. Design your dashboard with the visualizations described in the README
EOF
}