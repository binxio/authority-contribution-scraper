resource "google_bigquery_dataset" "authority" {
  dataset_id = "authority"
  location   = "EU"
  lifecycle {
    ignore_changes = [access]
  }
}


resource "google_bigquery_dataset_iam_member" "authority_contributions_dataEditor" {
  for_each = toset([
    format("serviceAccount:%s", google_service_account.authority-contribution-scraper.email),
  ])
  dataset_id = google_bigquery_dataset.authority.dataset_id
  project    = google_bigquery_dataset.authority.project
  role       = "roles/bigquery.dataEditor"
  member     = each.value
}

resource "google_bigquery_dataset_iam_member" "authority_contributions_dataViewer" {
  for_each = toset([
    "domain:binx.io",
    format("serviceAccount:%s", google_service_account.authority-contribution-scraper.email)
  ])
  dataset_id = google_bigquery_dataset.authority.dataset_id
  project    = google_bigquery_dataset.authority.project
  role       = "roles/bigquery.dataViewer"
  member     = each.value
}

resource "google_project_iam_member" "bigquery_jobuser" {
  for_each = toset([
    "domain:binx.io",
    "domain:gcp.xebia.com",
    format("serviceAccount:%s", google_service_account.authority-contribution-scraper.email)
  ])
  project = google_bigquery_dataset.authority.project
  role    = "roles/bigquery.jobUser"
  member  = each.value
}


resource "google_bigquery_table" "contributions" {
  dataset_id = google_bigquery_dataset.authority.dataset_id
  table_id   = "contributions"

  schema = <<EOF
   [
            {
                "mode": "REQUIRED",
                "name": "guid",
                "type": "STRING",
                "description": "globally unique id identifying the contributions, normally a url"
            },
            {
                "mode": "REQUIRED",
                "name": "author",
                "type": "STRING",
                "description": "full name of the author"
            },
            {
                "mode": "REQUIRED",
                "name": "title",
                "type": "STRING",
                "description": "of the contribution"
            },
            {
                "mode": "REQUIRED",
                "name": "date",
                "type": "DATETIME",
                "description": "of delivery of the contribution"
            },
            {
                "mode": "REQUIRED",
                "name": "type",
                "type": "STRING",
                "description": "type of contribution: currently we have blog, xke and github-pr"
            },
            {
                "mode": "NULLABLE",
                "name": "scraper_id",
                "type": "STRING",
                "description": "id of scraper that found the contribution"
            },
            {
                "mode": "NULLABLE",
                "name": "url",
                "type": "STRING",
                "description": "pointing to the contribution to view"
            }
        ]
EOF
}
