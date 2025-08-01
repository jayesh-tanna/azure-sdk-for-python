# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import uuid
from typing import (
    Any,
    cast,
    Dict,
    Iterator,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import parse_qs, quote

from azure.core.credentials import AzureSasCredential, AzureNamedKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError
from azure.core.pipeline import Pipeline
from azure.core.pipeline.transport import (  # pylint: disable=non-abstract-transport-import, no-name-in-module
    HttpTransport,
    RequestsTransport,
)
from azure.core.pipeline.policies import (
    AzureSasCredentialPolicy,
    ContentDecodePolicy,
    DistributedTracingPolicy,
    HttpLoggingPolicy,
    ProxyPolicy,
    RedirectPolicy,
    UserAgentPolicy,
)

from .authentication import SharedKeyCredentialPolicy
from .constants import CONNECTION_TIMEOUT, DEFAULT_OAUTH_SCOPE, READ_TIMEOUT, SERVICE_HOST_BASE, STORAGE_OAUTH_SCOPE
from .models import LocationMode, StorageConfiguration
from .policies import (
    ExponentialRetry,
    QueueMessagePolicy,
    StorageBearerTokenCredentialPolicy,
    StorageContentValidation,
    StorageHeadersPolicy,
    StorageHosts,
    StorageLoggingPolicy,
    StorageRequestHook,
    StorageResponseHook,
)
from .request_handlers import serialize_batch_body, _get_batch_request_delimiter
from .response_handlers import PartialBatchErrorException, process_storage_error
from .shared_access_signature import QueryStringConstants
from .._version import VERSION
from .._shared_access_signature import _is_credential_sastoken

if TYPE_CHECKING:
    from azure.core.credentials_async import AsyncTokenCredential
    from azure.core.pipeline.transport import HttpRequest, HttpResponse  # pylint: disable=C4756

_LOGGER = logging.getLogger(__name__)
_SERVICE_PARAMS = {
    "blob": {"primary": "BLOBENDPOINT", "secondary": "BLOBSECONDARYENDPOINT"},
    "queue": {"primary": "QUEUEENDPOINT", "secondary": "QUEUESECONDARYENDPOINT"},
    "file": {"primary": "FILEENDPOINT", "secondary": "FILESECONDARYENDPOINT"},
    "dfs": {"primary": "BLOBENDPOINT", "secondary": "BLOBENDPOINT"},
}


class StorageAccountHostsMixin(object):

    _client: Any
    _hosts: Dict[str, str]

    def __init__(
        self,
        parsed_url: Any,
        service: str,
        credential: Optional[
            Union[
                str,
                Dict[str, str],
                AzureNamedKeyCredential,
                AzureSasCredential,
                "AsyncTokenCredential",
                TokenCredential,
            ]
        ] = None,
        **kwargs: Any,
    ) -> None:
        self._location_mode = kwargs.get("_location_mode", LocationMode.PRIMARY)
        self._hosts = kwargs.get("_hosts", {})
        self.scheme = parsed_url.scheme
        self._is_localhost = False

        if service not in ["blob", "queue", "file-share", "dfs"]:
            raise ValueError(f"Invalid service: {service}")
        service_name = service.split("-")[0]
        account = parsed_url.netloc.split(f".{service_name}.core.")

        self.account_name = account[0] if len(account) > 1 else None
        if (
            not self.account_name
            and parsed_url.netloc.startswith("localhost")
            or parsed_url.netloc.startswith("127.0.0.1")
        ):
            self._is_localhost = True
            self.account_name = parsed_url.path.strip("/")

        self.credential = _format_shared_key_credential(self.account_name, credential)
        if self.scheme.lower() != "https" and hasattr(self.credential, "get_token"):
            raise ValueError("Token credential is only supported with HTTPS.")

        secondary_hostname = ""
        if hasattr(self.credential, "account_name"):
            self.account_name = self.credential.account_name
            secondary_hostname = f"{self.credential.account_name}-secondary.{service_name}.{SERVICE_HOST_BASE}"

        if not self._hosts:
            if len(account) > 1:
                secondary_hostname = parsed_url.netloc.replace(account[0], account[0] + "-secondary")
            if kwargs.get("secondary_hostname"):
                secondary_hostname = kwargs["secondary_hostname"]
            primary_hostname = (parsed_url.netloc + parsed_url.path).rstrip("/")
            self._hosts = {LocationMode.PRIMARY: primary_hostname, LocationMode.SECONDARY: secondary_hostname}

        self._sdk_moniker = f"storage-{service}/{VERSION}"
        self._config, self._pipeline = self._create_pipeline(self.credential, sdk_moniker=self._sdk_moniker, **kwargs)

    @property
    def url(self) -> str:
        """The full endpoint URL to this entity, including SAS token if used.

        This could be either the primary endpoint,
        or the secondary endpoint depending on the current :func:`location_mode`.

        :return: The full endpoint URL to this entity, including SAS token if used.
        :rtype: str
        """
        return self._format_url(self._hosts[self._location_mode])  # type: ignore

    @property
    def primary_endpoint(self) -> str:
        """The full primary endpoint URL.

        :return: The full primary endpoint URL.
        :rtype: str
        """
        return self._format_url(self._hosts[LocationMode.PRIMARY])  # type: ignore

    @property
    def primary_hostname(self) -> str:
        """The hostname of the primary endpoint.

        :return: The hostname of the primary endpoint.
        :rtype: str
        """
        return self._hosts[LocationMode.PRIMARY]

    @property
    def secondary_endpoint(self) -> str:
        """The full secondary endpoint URL if configured.

        If not available a ValueError will be raised. To explicitly specify a secondary hostname, use the optional
        `secondary_hostname` keyword argument on instantiation.

        :return: The full secondary endpoint URL.
        :rtype: str
        :raise ValueError: If no secondary endpoint is configured.
        """
        if not self._hosts[LocationMode.SECONDARY]:
            raise ValueError("No secondary host configured.")
        return self._format_url(self._hosts[LocationMode.SECONDARY])  # type: ignore

    @property
    def secondary_hostname(self) -> Optional[str]:
        """The hostname of the secondary endpoint.

        If not available this will be None. To explicitly specify a secondary hostname, use the optional
        `secondary_hostname` keyword argument on instantiation.

        :return: The hostname of the secondary endpoint, or None if not configured.
        :rtype: Optional[str]
        """
        return self._hosts[LocationMode.SECONDARY]

    @property
    def location_mode(self) -> str:
        """The location mode that the client is currently using.

        By default this will be "primary". Options include "primary" and "secondary".

        :return: The current location mode.
        :rtype: str
        """

        return self._location_mode

    @location_mode.setter
    def location_mode(self, value):
        if self._hosts.get(value):
            self._location_mode = value
            self._client._config.url = self.url  # pylint: disable=protected-access
        else:
            raise ValueError(f"No host URL for location mode: {value}")

    @property
    def api_version(self):
        """The version of the Storage API used for requests.

        :rtype: str
        """
        return self._client._config.version  # pylint: disable=protected-access

    def _format_query_string(
        self,
        sas_token: Optional[str],
        credential: Optional[
            Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", TokenCredential]
        ],
        snapshot: Optional[str] = None,
        share_snapshot: Optional[str] = None,
    ) -> Tuple[
        str, Optional[Union[str, Dict[str, str], "AzureNamedKeyCredential", "AzureSasCredential", TokenCredential]]
    ]:
        query_str = "?"
        if snapshot:
            query_str += f"snapshot={snapshot}&"
        if share_snapshot:
            query_str += f"sharesnapshot={share_snapshot}&"
        if sas_token and isinstance(credential, AzureSasCredential):
            raise ValueError(
                "You cannot use AzureSasCredential when the resource URI also contains a Shared Access Signature."
            )
        if _is_credential_sastoken(credential):
            credential = cast(str, credential)
            query_str += credential.lstrip("?")
            credential = None
        elif sas_token:
            query_str += sas_token
        return query_str.rstrip("?&"), credential

    def _create_pipeline(
        self,
        credential: Optional[
            Union[str, Dict[str, str], AzureNamedKeyCredential, AzureSasCredential, TokenCredential]
        ] = None,
        **kwargs: Any,
    ) -> Tuple[StorageConfiguration, Pipeline]:
        self._credential_policy: Any = None
        if hasattr(credential, "get_token"):
            if kwargs.get("audience"):
                audience = str(kwargs.pop("audience")).rstrip("/") + DEFAULT_OAUTH_SCOPE
            else:
                audience = STORAGE_OAUTH_SCOPE
            self._credential_policy = StorageBearerTokenCredentialPolicy(cast(TokenCredential, credential), audience)
        elif isinstance(credential, SharedKeyCredentialPolicy):
            self._credential_policy = credential
        elif isinstance(credential, AzureSasCredential):
            self._credential_policy = AzureSasCredentialPolicy(credential)
        elif credential is not None:
            raise TypeError(f"Unsupported credential: {type(credential)}")

        config = kwargs.get("_configuration") or create_configuration(**kwargs)
        if kwargs.get("_pipeline"):
            return config, kwargs["_pipeline"]
        transport = kwargs.get("transport")
        kwargs.setdefault("connection_timeout", CONNECTION_TIMEOUT)
        kwargs.setdefault("read_timeout", READ_TIMEOUT)
        if not transport:
            transport = RequestsTransport(**kwargs)
        policies = [
            QueueMessagePolicy(),
            config.proxy_policy,
            config.user_agent_policy,
            StorageContentValidation(),
            ContentDecodePolicy(response_encoding="utf-8"),
            RedirectPolicy(**kwargs),
            StorageHosts(hosts=self._hosts, **kwargs),
            config.retry_policy,
            config.headers_policy,
            StorageRequestHook(**kwargs),
            self._credential_policy,
            config.logging_policy,
            StorageResponseHook(**kwargs),
            DistributedTracingPolicy(**kwargs),
            HttpLoggingPolicy(**kwargs),
        ]
        if kwargs.get("_additional_pipeline_policies"):
            policies = policies + kwargs.get("_additional_pipeline_policies")  # type: ignore
        config.transport = transport  # type: ignore
        return config, Pipeline(transport, policies=policies)

    def _batch_send(self, *reqs: "HttpRequest", **kwargs: Any) -> Iterator["HttpResponse"]:
        """Given a series of request, do a Storage batch call.

        :param HttpRequest reqs: A collection of HttpRequest objects.
        :return: An iterator of HttpResponse objects.
        :rtype: Iterator[HttpResponse]
        """
        # Pop it here, so requests doesn't feel bad about additional kwarg
        raise_on_any_failure = kwargs.pop("raise_on_any_failure", True)
        batch_id = str(uuid.uuid1())

        request = self._client._client.post(  # pylint: disable=protected-access
            url=(
                f"{self.scheme}://{self.primary_hostname}/"
                f"{kwargs.pop('path', '')}?{kwargs.pop('restype', '')}"
                f"comp=batch{kwargs.pop('sas', '')}{kwargs.pop('timeout', '')}"
            ),
            headers={
                "x-ms-version": self.api_version,
                "Content-Type": "multipart/mixed; boundary=" + _get_batch_request_delimiter(batch_id, False, False),
            },
        )

        policies = [StorageHeadersPolicy()]
        if self._credential_policy:
            policies.append(self._credential_policy)

        request.set_multipart_mixed(*reqs, policies=policies, enforce_https=False)

        Pipeline._prepare_multipart_mixed_request(request)  # pylint: disable=protected-access
        body = serialize_batch_body(request.multipart_mixed_info[0], batch_id)
        request.set_bytes_body(body)

        temp = request.multipart_mixed_info
        request.multipart_mixed_info = None
        pipeline_response = self._pipeline.run(request, **kwargs)
        response = pipeline_response.http_response
        request.multipart_mixed_info = temp

        try:
            if response.status_code not in [202]:
                raise HttpResponseError(response=response)
            parts = response.parts()
            if raise_on_any_failure:
                parts = list(response.parts())
                if any(p for p in parts if not 200 <= p.status_code < 300):
                    error = PartialBatchErrorException(
                        message="There is a partial failure in the batch operation.", response=response, parts=parts
                    )
                    raise error
                return iter(parts)
            return parts  # type: ignore [no-any-return]
        except HttpResponseError as error:
            process_storage_error(error)


class TransportWrapper(HttpTransport):
    """Wrapper class that ensures that an inner client created
    by a `get_client` method does not close the outer transport for the parent
    when used in a context manager.
    """

    def __init__(self, transport):
        self._transport = transport

    def send(self, request, **kwargs):
        return self._transport.send(request, **kwargs)

    def open(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


def _format_shared_key_credential(
    account_name: Optional[str],
    credential: Optional[
        Union[str, Dict[str, str], AzureNamedKeyCredential, AzureSasCredential, "AsyncTokenCredential", TokenCredential]
    ] = None,
) -> Any:
    if isinstance(credential, str):
        if not account_name:
            raise ValueError("Unable to determine account name for shared key credential.")
        credential = {"account_name": account_name, "account_key": credential}
    if isinstance(credential, dict):
        if "account_name" not in credential:
            raise ValueError("Shared key credential missing 'account_name")
        if "account_key" not in credential:
            raise ValueError("Shared key credential missing 'account_key")
        return SharedKeyCredentialPolicy(**credential)
    if isinstance(credential, AzureNamedKeyCredential):
        return SharedKeyCredentialPolicy(credential.named_key.name, credential.named_key.key)
    return credential


def parse_connection_str(
    conn_str: str,
    credential: Optional[Union[str, Dict[str, str], AzureNamedKeyCredential, AzureSasCredential, TokenCredential]],
    service: str,
) -> Tuple[
    str,
    Optional[str],
    Optional[Union[str, Dict[str, str], AzureNamedKeyCredential, AzureSasCredential, TokenCredential]],
]:
    conn_str = conn_str.rstrip(";")
    conn_settings_list = [s.split("=", 1) for s in conn_str.split(";")]
    if any(len(tup) != 2 for tup in conn_settings_list):
        raise ValueError("Connection string is either blank or malformed.")
    conn_settings = dict((key.upper(), val) for key, val in conn_settings_list)
    endpoints = _SERVICE_PARAMS[service]
    primary = None
    secondary = None
    if not credential:
        try:
            credential = {"account_name": conn_settings["ACCOUNTNAME"], "account_key": conn_settings["ACCOUNTKEY"]}
        except KeyError:
            credential = conn_settings.get("SHAREDACCESSSIGNATURE")
    if endpoints["primary"] in conn_settings:
        primary = conn_settings[endpoints["primary"]]
        if endpoints["secondary"] in conn_settings:
            secondary = conn_settings[endpoints["secondary"]]
    else:
        if endpoints["secondary"] in conn_settings:
            raise ValueError("Connection string specifies only secondary endpoint.")
        try:
            primary = (
                f"{conn_settings['DEFAULTENDPOINTSPROTOCOL']}://"
                f"{conn_settings['ACCOUNTNAME']}.{service}.{conn_settings['ENDPOINTSUFFIX']}"
            )
            secondary = f"{conn_settings['ACCOUNTNAME']}-secondary." f"{service}.{conn_settings['ENDPOINTSUFFIX']}"
        except KeyError:
            pass

    if not primary:
        try:
            primary = (
                f"https://{conn_settings['ACCOUNTNAME']}."
                f"{service}.{conn_settings.get('ENDPOINTSUFFIX', SERVICE_HOST_BASE)}"
            )
        except KeyError as exc:
            raise ValueError("Connection string missing required connection details.") from exc
    if service == "dfs":
        primary = primary.replace(".blob.", ".dfs.")
        if secondary:
            secondary = secondary.replace(".blob.", ".dfs.")
    return primary, secondary, credential


def create_configuration(**kwargs: Any) -> StorageConfiguration:
    # Backwards compatibility if someone is not passing sdk_moniker
    if not kwargs.get("sdk_moniker"):
        kwargs["sdk_moniker"] = f"storage-{kwargs.pop('storage_sdk')}/{VERSION}"
    config = StorageConfiguration(**kwargs)
    config.headers_policy = StorageHeadersPolicy(**kwargs)
    config.user_agent_policy = UserAgentPolicy(**kwargs)
    config.retry_policy = kwargs.get("retry_policy") or ExponentialRetry(**kwargs)
    config.logging_policy = StorageLoggingPolicy(**kwargs)
    config.proxy_policy = ProxyPolicy(**kwargs)
    return config


def parse_query(query_str: str) -> Tuple[Optional[str], Optional[str]]:
    sas_values = QueryStringConstants.to_list()
    parsed_query = {k: v[0] for k, v in parse_qs(query_str).items()}
    sas_params = [f"{k}={quote(v, safe='')}" for k, v in parsed_query.items() if k in sas_values]
    sas_token = None
    if sas_params:
        sas_token = "&".join(sas_params)

    snapshot = parsed_query.get("snapshot") or parsed_query.get("sharesnapshot")
    return snapshot, sas_token
