
resource "google_kms_key_ring" "terraform" {
  name     = "terraform"
  location = "europe"
  project  = data.google_project.current.project_id
  depends_on = [google_project_service.cloudkms]
}

resource "google_kms_crypto_key" "terraform" {
  name     = "encrypt"
  key_ring = google_kms_key_ring.terraform.id
  purpose  = "ENCRYPT_DECRYPT"
}

data "google_kms_crypto_key_version" "terraform" {
  crypto_key = google_kms_crypto_key.terraform.id
}

resource "local_file" "encrypt_sh" {
  filename = "encrypt.sh"
  file_permission = "0755"
  content  = <<EOF
#!/bin/sh
gcloud kms encrypt \
   --key ${trimprefix(data.google_kms_crypto_key_version.terraform.id, "//cloudkms.googleapis.com/v1/")} \
   --location ${google_kms_key_ring.terraform.location} \
   --plaintext-file - \
   --ciphertext-file - \
    | base64
EOF
}

resource "google_secret_manager_secret" "xke_api_token" {
  secret_id = "xke-api-token"
  replication {
    user_managed {
      replicas {
        location = "europe-west1"
      }
      replicas {
        location = "europe-west3"
      }
    }
  }
  project = data.google_project.current.project_id
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "xke_api_token" {
  secret = google_secret_manager_secret.xke_api_token.id
  secret_data = data.google_kms_secret.xke_api_token.plaintext
}

data "google_kms_secret" "xke_api_token" {
  crypto_key = google_kms_crypto_key.terraform.id
  ciphertext = "CiQAQ881WqBCvyOOxWMAIdlb9K7OxRT0cKAAvHoaAQKMep/x89ESUQBOAh2qphxJcHbV95EsUDEJuUD/Wki6GY21QuewAZX+1gdlJB7nNaIuZBrvGOQWBC/otx45DCADLKIqruQitrYvxgbVI67P05zWbYH1nDIn9w=="
}

