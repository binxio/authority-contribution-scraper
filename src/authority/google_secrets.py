import functools
import logging
import re

import gcloud_config_helper
import google.auth
from google.cloud.secretmanager_v1 import SecretManagerServiceClient

from authority.util.singleton import Singleton


class SecretName:
    def __init__(self, name: str, project_id: str):
        """
        represents a Google Secret Manager secret version name. Provides for a human-readable
        version specification and returns a fully qualified name.

        Use:
        >>> SecretName("my-secret", "playground")
        projects/playground/secrets/my-secret/versions/latest
        >>> SecretName("projects/playground/secrets/my-secret/versions/latest", "other-project")
        projects/playground/secrets/my-secret/versions/latest
        >>> SecretName("playground/my-secret/1", "other-project")
        projects/playground/secrets/my-secret/versions/1
        >>> SecretName("my-secret/2", "other-project")
        projects/other-project/secrets/my-secret/versions/2
        >>> SecretName("playground/my-secret/version/more", "project")
        Traceback (most recent call last):
        ...
        ValueError: expected 3 components in secret playground/my-secret/version/more, found 4.

        :param str name: (fully qualified) name of the secret, may include the version
        :param str project_id: The ID of the project where the secret is located. Ignored if included in the name

        :raises ValueError
        """
        simplified_name = (
            name.replace("projects/", "")
            .replace("secrets/", "")
            .replace("versions/", "")
        )
        parts = simplified_name.split("/")
        if len(parts) == 1:
            self.project_id = project_id
            self.secret_id = parts[0]
            self.version = "latest"
        elif len(parts) == 2:
            if re.match(r"(\d+|latest)", parts[1]):
                self.project_id = project_id
                self.secret_id = parts[0]
                self.version = parts[1]
            else:
                self.project_id = parts[0]
                self.secret_id = parts[1]
                self.version = "latest"
        elif len(parts) == 3:
            self.project_id, self.secret_id, self.version = parts
        else:
            raise ValueError(
                f"expected 3 components in secret {simplified_name}, found {len(parts)}."
            )

    def __repr__(self):
        return f"projects/{self.project_id}/secrets/{self.secret_id}/versions/{self.version}"


class SecretManager(metaclass=Singleton):
    def __init__(self, configuration_name: str = ""):
        """
        Wrapper for the Google Secret Manager

        :param str configuration_name: Name of the gcloud configuration to use for credentials
        """
        if gcloud_config_helper.on_path():
            self.credentials = gcloud_config_helper.GCloudCredentials(configuration_name)
            self.project_id = self.credentials.project
        else:
            logging.info("using application default credentials")
            self.credentials, self.project_id = google.auth.default()

        self.client = SecretManagerServiceClient(credentials=self.credentials)

    def get_secret(self, name: str) -> str:
        """
        returns the data of the secret version `name`.

        :param str name: Name of the secret to find

        :return: The data of the secret
        :rtype: :obj:`str`
        """
        secret_name = SecretName(name, self.project_id)
        response = self.client.access_secret_version(name=str(secret_name))
        return response.payload.data.decode("utf-8")
