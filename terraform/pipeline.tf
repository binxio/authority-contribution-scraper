resource "google_cloudbuild_trigger" "push" {
  name = "push-authority-contribution-scraper"
  github {
    owner = "binxio"
    name  = "authority-contribution-scraper"
    push {
      branch = "master"
    }
  }
  filename = "cloudbuild.yaml"
  project  = data.google_project.current.project_id
  provider = google-beta
}

resource "google_cloudbuild_trigger" "tag" {
  name = "tag-authority-contribution-scraper"
  github {
    owner = "binxio"
    name  = "authority-contribution-scraper"
    push {
      tag = ".*"
    }
  }
  filename = "cloudbuild.yaml"
  project  = data.google_project.current.project_id
  provider = google-beta
}


resource "google_project_iam_member" "cloudbuild-editor" {
  role       = "roles/owner"
  member     = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  project    = data.google_project.current.project_id
  depends_on = [google_project_service.cloudbuild]
}

