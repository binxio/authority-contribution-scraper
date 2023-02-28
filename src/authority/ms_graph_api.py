import asyncio
import functools
import typing

import requests
from azure.identity import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
from msgraph import GraphRequestAdapter, GraphServiceClient
from msgraph.generated.users.users_request_builder import UsersRequestBuilder

from authority.model.user import User


class MSGraphAPI:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.client_credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
        # noinspection PyTypeChecker
        auth_provider = AzureIdentityAuthenticationProvider(self.client_credential)
        self.adapter = GraphRequestAdapter(auth_provider)
        self.app_client = GraphServiceClient(self.adapter)

    @functools.lru_cache(maxsize=1000)
    def get_user_by_display_name(self, display_name: str) -> typing.Optional[User]:
        """
        Find a user using the MS Graph API by their display name

        :param str display_name: The display_name of the user to find

        :return: A user if found
        :rtype: :obj:`User`
        """

        query_params = {
            "$select": ",".join(["displayName", "id", "mail", "department", "companyName"]),
            "$search": f"\"displayName:{display_name}\"",
            "$top": 1,
            "$orderby": ",".join(["displayName"]),
        }
        headers = {
          "ConsistencyLevel": "eventual",
        }

        request = self._prepare_request(method="get", resource_path="users", query_params=query_params, headers=headers)
        with requests.Session() as session:
            response = session.send(request=request)
        response.raise_for_status()
        users = response.json()

        return User.from_dict(**users['value'][0]) if users.get("value") else None

    @functools.lru_cache(maxsize=1000)
    def get_user_by_id(self, user_id: str) -> typing.Optional[User]:
        """
        Lookup a user using the MS Graph API by their ID or email address

        :param str user_id: ID or email address of the user to lookup

        :return: A user if found
        :rtype: User
        """
        query_params = {
            "$select": ",".join(["displayName", "id", "mail", "department", "companyName"]),
        }

        request = self._prepare_request(
            method="get",
            resource_path=f"users/{user_id}",
            query_params=query_params,
        )
        with requests.Session() as session:
            response = session.send(request=request)
        response.raise_for_status()
        user = response.json()
        return User.from_dict(**user) if user.get("id") else None

    def _prepare_request(
            self,
            method: str,
            resource_path: str,
            query_params: dict,
            headers: dict = None,
    ):
        if headers is None:
            headers = {}
        access_token = self.client_credential.get_token('https://graph.microsoft.com/.default').token
        request = requests.PreparedRequest()
        request.prepare_method(method=method)
        request.prepare_url(url=f"https://graph.microsoft.com/v1.0/{resource_path}", params=query_params)
        request.prepare_headers(headers={
            "Authorization": f"Bearer {access_token}",
            **headers,
        })
        return request


if __name__ == "__main__":
    import os
    ms_graph_api = MSGraphAPI(
        client_id=os.getenv(
            "MS_GRAPH_CLIENT_ID",
        ),
        tenant_id=os.getenv(
            "MS_GRAPH_TENANT_ID",
        ),
        client_secret=os.getenv(
            "MS_GRAPH_CLIENT_SECRET",
        ),
    )
    user = ms_graph_api.get_user_by_id("koen.vanzuijlen@xebia.com")
    print(user)