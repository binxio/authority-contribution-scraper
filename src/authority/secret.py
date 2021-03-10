import google.auth
from google.cloud import secretmanager


def get_token():
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform'])
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    response = client.access_secret_version(name=f"projects/{project}/secrets/xke-api-token/versions/latest")
    return response.payload.data.decode('UTF-8')