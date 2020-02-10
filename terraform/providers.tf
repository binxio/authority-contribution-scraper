terraform {
  required_version = ">= 0.12"
    backend "gcs" {
      bucket = "binxio-mgmt-terraform-state"
      prefix = "authority"
   }
}

provider "google" {
  project = var.project
  region  = var.region
}

provider "google-beta" {
  project = var.project
  region  = var.region
}

data "google_project" "current" {
  provider = google-beta
}

resource "google_storage_bucket" "terraform_state" {
  name = "binxio-mgmt-terraform-state"
  versioning {
    enabled = true
  }
  project = data.google_project.current.project_id
}

