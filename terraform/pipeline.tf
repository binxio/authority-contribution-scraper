resource "google_cloudbuild_trigger" "build" {
  name = "build-authority-contribution-scraper"
  github {
    owner = "binxio"
    name  = "authority-contribution-scraper"
    push {
      branch = "main"
    }
  }
  ignored_files = ["terraform/**"]
  filename      = "cloudbuild/build.yaml"
  project       = data.google_project.current.project_id
  provider      = google-beta
}

resource "google_cloudbuild_trigger" "release" {
  name = "release-authority-contribution-scraper"
  github {
    owner = "binxio"
    name  = "authority-contribution-scraper"
    push {
      tag = ".*"
    }
  }
  filename = "cloudbuild/release.yaml"
  project  = data.google_project.current.project_id
  provider = google-beta
}

resource "google_cloudbuild_trigger" "deploy" {
  name = "deploy-authority-contribution-scraper"
  github {
    owner = "binxio"
    name  = "authority-contribution-scraper"
    push {
      branch = "main"
    }
  }
  included_files = ["terraform/**"]
  filename       = "cloudbuild/deploy.yaml"

  substitutions = {
    _GIT_REPOSITORY_URL = "git@github.com:binxio/authority-contribution-scraper.git"
  }

  project  = data.google_project.current.project_id
  provider = google-beta
}

resource "google_project_iam_member" "cloudbuild-editor" {
  role       = "roles/owner"
  member     = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  project    = data.google_project.current.project_id
  depends_on = [google_project_service.cloudbuild]
}


resource "google_secret_manager_secret" "cloudbuild" {
  for_each  = toset(["cloudbuild-private-key"])
  secret_id = each.value
  replication {
    user_managed {
      replicas {
        location = var.region
      }
      replicas {
        location = var.replica_region
      }
    }
  }
}

resource "google_secret_manager_secret_iam_member" "cloudbuild" {
  for_each  = google_secret_manager_secret.cloudbuild
  member    = format("serviceAccount:%s@cloudbuild.gserviceaccount.com", data.google_project.current.number)
  role      = "roles/secretmanager.secretAccessor"
  secret_id = each.value.secret_id
}

resource "tls_private_key" "cloudbuild" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "google_secret_manager_secret_version" "cloudbuild-private-key" {
  secret      = google_secret_manager_secret.cloudbuild["cloudbuild-private-key"].id
  secret_data = tls_private_key.cloudbuild.private_key_pem
}

output "cloudbuild-public-key" {
  value = tls_private_key.cloudbuild.public_key_openssh
}
