terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
    google-beta = {
      source = "hashicorp/google-beta"
    }
    local = {
      source = "hashicorp/local"
    }
  }
  required_version = ">= 1.0.11"
}
