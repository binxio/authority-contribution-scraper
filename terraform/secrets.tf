
resource "google_kms_key_ring" "terraform" {
  name       = "terraform"
  location   = "europe"
  project    = data.google_project.current.project_id
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
  filename        = "encrypt.sh"
  file_permission = "0755"
  content         = <<EOF
#!/bin/sh
gcloud kms encrypt \
   --key ${trimprefix(data.google_kms_crypto_key_version.terraform.id, "//cloudkms.googleapis.com/v1/")} \
   --location ${google_kms_key_ring.terraform.location} \
   --plaintext-file - \
   --ciphertext-file - \
    | base64
EOF
}
