terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "enable_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "storage.googleapis.com",
    "dataproc.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service = each.key
}

# Buckets: raw, trusted, refined, artifacts
resource "google_storage_bucket" "raw" {
  name          = "${var.prefix}-raw-${var.project_id}"
  location      = var.region
  force_destroy = true
}
resource "google_storage_bucket" "trusted" {
  name          = "${var.prefix}-trusted-${var.project_id}"
  location      = var.region
  force_destroy = true
}
resource "google_storage_bucket" "refined" {
  name          = "${var.prefix}-refined-${var.project_id}"
  location      = var.region
  force_destroy = true
}
resource "google_storage_bucket" "artifacts" {
  name          = "${var.prefix}-artifacts-${var.project_id}"
  location      = var.region
  force_destroy = true
}

# Service account for pipeline
resource "google_service_account" "pipeline_sa" {
  account_id   = "${var.prefix}-pipeline-sa"
  display_name = "Pipeline service account"
}

# Give SA storage object admin (to write/read GCS)
resource "google_project_iam_member" "sa_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Give SA BigQuery user
resource "google_project_iam_member" "sa_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Cloud SQL (Postgres)
resource "google_sql_database_instance" "covid_db" {
  name             = "${var.prefix}-covid-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_sql_user" "covid_user" {
  name     = var.db_user
  instance = google_sql_database_instance.covid_db.name
  password = var.db_password
}

resource "google_sql_database" "covid_db_schema" {
  name     = "covid_aux"
  instance = google_sql_database_instance.covid_db.name
}

output "raw_bucket" { value = google_storage_bucket.raw.name }
output "trusted_bucket" { value = google_storage_bucket.trusted.name }
output "refined_bucket" { value = google_storage_bucket.refined.name }
output "artifacts_bucket" { value = google_storage_bucket.artifacts.name }
output "pipeline_sa" { value = google_service_account.pipeline_sa.email }
output "cloudsql_instance" { value = google_sql_database_instance.covid_db.connection_name }
