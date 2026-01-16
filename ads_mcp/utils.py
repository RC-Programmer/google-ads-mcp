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
import proto
import logging
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.ads.googleads.util import get_nested_attr
from google.oauth2.credentials import Credentials
from ads_mcp.mcp_header_interceptor import MCPHeaderInterceptor
import os
import importlib.resources

# filename for generated field information used by search
_GAQL_FILENAME = "gaql_resources.json"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Read-only scope for Analytics Admin API and Analytics Data API.
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
    # Handles google._upb._message.RepeatedScalarContainer / RepeatedCompositeContainer
    # without importing their classes directly.
    tname = type(value).__name__
    return tname.startswith("Repeated") or tname.endswith("Container")


def _walk_jsonable(value: Any) -> Any:
    # Make anything JSON-serializable, preferring plain strings for asset objects.
    if value is None:
        return None

    if isinstance(value, proto.Enum):
        return value.name

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _walk_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)) or _is_repeated_container(value):
        return [_walk_jsonable(v) for v in list(value)]

    # Proto-plus messages (Google Ads API objects, including AdTextAsset)
    if isinstance(value, proto.Message):
        # If it looks like an AdTextAsset (or similar) return plain text only.
        if hasattr(value, "text"):
            try:
                txt = getattr(value, "text")
                if isinstance(txt, str):
                    return txt
            except Exception:
                pass

        # Otherwise convert to dict and recursively sanitize it.
        try:
            as_dict = value.to_dict()
            return _walk_jsonable(as_dict)
        except Exception:
            # Last resort: string representation
            return str(value)

    # Catch-all: iterables that aren't strings/bytes (some protobuf containers)
    try:
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            return [_walk_jsonable(v) for v in list(value)]
    except Exception:
        pass

    return str(value)


def format_output_value(value: Any) -> Any:
    return _walk_jsonable(value)


def format_output_row(row: proto.Message, attributes):
    return {attr: format_output_value(get_nested_attr(row, attr)) for attr in attributes}


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path
