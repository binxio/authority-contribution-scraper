resource "google_cloudbuild_trigger" "cicd" {
  name = "cicd-deploy"
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

resource "google_project_iam_member" "cloudbuild-editor" {
  role       = "roles/owner"
  member     = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  project    = data.google_project.current.project_id
  depends_on = [google_project_service.cloudbuild]
}

