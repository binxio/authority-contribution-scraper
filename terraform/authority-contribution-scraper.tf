resource "google_cloud_run_service" "authority-contribution-scraper" {
  name     = "authority-contribution-scraper"
  location = "europe-west4"

  template {
    spec {
      container_concurrency = 1
      service_account_name  = google_service_account.authority-contribution-scraper.email
      containers {
        image = "eu.gcr.io/binxio-mgmt/authority-contribution-scraper:0.1.3"
      }
    }
  }
  project    = data.google_project.current.project_id
  provider   = google
  depends_on = [google_project_service.run]
  timeouts {
    create = "10m"
  }
}

resource "google_service_account" "authority-contribution-scraper-invoker" {
  account_id   = "authority-cntrbtn-scrpr-invkr"
  display_name = "Authority Contribution scraper invoker"
}

resource "google_project_iam_member" "authority-contribution-scraper-invoker" {
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.authority-contribution-scraper-invoker.email}"
  project = var.project
}


resource "google_cloud_scheduler_job" "authority-contribution-scraper" {
  name             = "authority-contribution-scraper"
  description      = "Authority Contribution scraper"
  schedule         = "1 * * * *"
  time_zone        = "Europe/Amsterdam"
  attempt_deadline = "320s"
  region           = "europe-west1"

  http_target {
    http_method = "GET"
    uri         = google_cloud_run_service.authority-contribution-scraper.status[0].url
    oidc_token {
      service_account_email = google_service_account.authority-contribution-scraper-invoker.email
    }
  }
  depends_on = [google_project_iam_member.cloudscheduler_iam_service_account_user]
}

resource "google_service_account" "authority-contribution-scraper" {
  display_name = "binx.io authority contribution scraper"
  account_id   = "authority-contribution-scraper"
  project      = data.google_project.current.project_id
}

resource "google_project_iam_member" "authority-contribution-scraper-bigquery-dataEditor" {
  project = data.google_project.current.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.authority-contribution-scraper.email}"
}

resource "google_project_iam_member" "authority-contribution-scraper-bigquery-jobUser" {
  project = data.google_project.current.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.authority-contribution-scraper.email}"
}

resource "google_project_iam_member" "cloudscheduler_iam_service_account_user" {
  project    = data.google_project.current.project_id
  role       = "roles/iam.serviceAccountUser"
  member     = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
  depends_on = [google_project_service.cloudscheduler]
}

