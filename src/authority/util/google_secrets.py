"""
Module containing a helper for retrieving Google Secret Manager secrets
"""
import dataclasses
import logging
import re
import typing

import gcloud_config_helper
import google.auth
from google.cloud.secretmanager_v1 import SecretManagerServiceClient

from authority.util.singleton import Singleton


@dataclasses.dataclass
class _SecretName:
    """
    represents a Google Secret Manager secret version name. Provides for a human-readable
    version specification and returns a fully qualified name.

    **Use:**

        >>> _SecretName.parse("my-secret", "playground")
        projects/playground/secrets/my-secret/versions/latest
        >>> _SecretName.parse(
        ...     name="projects/playground/secrets/my-secret/versions/latest",
        ...     project_id="other-project",
        ... )
        projects/playground/secrets/my-secret/versions/latest
        >>> _SecretName.parse("playground/my-secret/1", "other-project")
        projects/playground/secrets/my-secret/versions/1
        >>> _SecretName.parse("my-secret/2", "other-project")
        projects/other-project/secrets/my-secret/versions/2
        >>> _SecretName.parse("playground/my-secret/version/more", "project")
        Traceback (most recent call last):
        ...
        ValueError: expected 3 components in secret playground/my-secret/version/more, found 4.
        >>> _SecretName.parse("my-secret")
        Traceback (most recent call last):
        ...
        ValueError: No project_id provided and unable to parse it from my-secret
    """

    project_id: str
    secret_id: str
    version: str

    @classmethod
    def parse(cls, name: str, project_id: typing.Optional[str] = None):
        """
        :param str name: (fully qualified) name of the secret, may include the version
        :param str project_id: The ID of the project where the secret is located. Ignored if
         included in the name

        :raises: :obj:`ValueError`
        """

        simplified_name = (
            name.replace("projects/", "")
            .replace("secrets/", "")
            .replace("versions/", "")
        )
        parts = simplified_name.split("/")

        if len(parts) < 1 or len(parts) > 3:
            raise ValueError(
                f"expected 3 components in secret {simplified_name}, found {len(parts)}."
            )

        secret_id = parts[0]
        version = "latest"

        if len(parts) == 2:
            if re.match(r"(\d+|latest)", parts[1]):
                version = parts[1]
            else:
                project_id = parts[0]
                secret_id = parts[1]
        elif len(parts) == 3:
            project_id, secret_id, version = parts
        if not project_id:
            raise ValueError(
                f"No project_id provided and unable to parse it from {simplified_name}"
            )
        return cls(project_id=project_id, secret_id=secret_id, version=version)

    def __repr__(self):
        return f"projects/{self.project_id}/secrets/{self.secret_id}/versions/{self.version}"


class SecretManager(metaclass=Singleton):
    """
    Wrapper for the Google Secret Manager
    """

    def __init__(self, configuration_name: str = ""):
        """
        :param str configuration_name: Name of the gcloud configuration to use for credentials
        """
        if gcloud_config_helper.on_path():
            self.credentials = gcloud_config_helper.GCloudCredentials(
                configuration_name
            )
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
        secret_name = _SecretName.parse(name=name, project_id=self.project_id)
        response = self.client.access_secret_version(name=str(secret_name))
        return response.payload.data.decode("utf-8")
