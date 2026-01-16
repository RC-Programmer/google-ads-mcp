#!/usr/bin/env python
# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utilities used by the MCP server."""

from typing import Any
import logging
import os
import importlib.resources

import proto
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.ads.googleads.util import get_nested_attr
from google.oauth2.credentials import Credentials

from ads_mcp.mcp_header_interceptor import MCPHeaderInterceptor

# filename for generated field information used by search
_GAQL_FILENAME = "gaql_resources.json"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Read-only scope for Google Ads API.
_READ_ONLY_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


def _create_credentials() -> Credentials:
    """Returns OAuth credentials from environment variables."""
    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing OAuth credentials. Set GOOGLE_ADS_CLIENT_ID, "
            "GOOGLE_ADS_CLIENT_SECRET, and GOOGLE_ADS_REFRESH_TOKEN."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[_READ_ONLY_ADS_SCOPE],
    )
    return credentials


def _get_developer_token() -> str:
    """Returns the developer token from the environment variable GOOGLE_ADS_DEVELOPER_TOKEN."""
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if dev_token is None:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set.")
    return dev_token


def _get_login_customer_id() -> str:
    """Returns login customer id, if set, from the environment variable GOOGLE_ADS_LOGIN_CUSTOMER_ID."""
    return os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")


def _get_googleads_client() -> GoogleAdsClient:
    client = GoogleAdsClient(
        credentials=_create_credentials(),
        developer_token=_get_developer_token(),
        login_customer_id=_get_login_customer_id(),
    )
    return client


_googleads_client = _get_googleads_client()


def get_googleads_service(serviceName: str) -> GoogleAdsServiceClient:
    return _googleads_client.get_service(
        serviceName, interceptors=[MCPHeaderInterceptor()]
    )


def get_googleads_type(typeName: str):
    return _googleads_client.get_type(typeName)


def _is_repeated_container(value: Any) -> bool:
    # protobuf repeated containers don't serialize, but behave like lists
    t = type(value).__name__
    return t in ("RepeatedCompositeContainer", "RepeatedScalarContainer")


def format_output_value(value: Any) -> Any:
    """
    Converts Google Ads API (proto / proto-plus) values into JSON-serializable types.

    - Enums -> enum name
    - Repeated containers -> list
    - Proto messages:
        - If they have `.text` (ex: AdTextAsset), return that text
        - else try `.to_dict()`
        - else fallback to `str(value)`
    """
    if value is None:
        return None

    # Enums -> "ENUM_NAME"
    if isinstance(value, proto.Enum):
        return value.name

    # Repeated containers / lists -> list of serialized items
    if isinstance(value, (list, tuple)) or _is_repeated_container(value):
        return [format_output_value(v) for v in list(value)]

    # Proto messages (AdTextAsset, etc.)
    if isinstance(value, proto.Message):
        # If you want JUST the text for RSA assets:
        if hasattr(value, "text"):
            return getattr(value, "text")

        # Otherwise, fall back to a dict (best-effort)
        if hasattr(value, "to_dict"):
            d = value.to_dict()
            if isinstance(d, dict):
                return {k: format_output_value(v) for k, v in d.items()}
            return format_output_value(d)

        # Last resort: stringify
        return str(value)

    # Plain scalars
    return value


def format_output_row(row: proto.Message, attributes):
    return {attr: format_output_value(get_nested_attr(row, attr)) for attr in attributes}


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path
