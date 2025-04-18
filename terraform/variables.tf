variable "project_id" {
  description = "GCP Project ID"
  default = "formula1-dashboard"
  type        = string
}

variable "region" {
  description = "GCP Region"
  default     = "us-central1"
  type        = string
}

variable "zone" {
  description = "GCP Zone"
  default     = "us-central1-a"
  type        = string
}

variable "bigquery_location" {
  description = "BigQuery Dataset Location"
  default     = "US"
  type        = string
}

variable "temp_bucket_name" {
  description = "Name of the GCS bucket for temporary data"
  default     = "temp-bucket"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  default     = "dev"
  type        = string
}

variable "dashboard_name" {
  description = "Name of the Looker Studio dashboard"
  default     = "F1 Racing Dashboard"
  type        = string
}