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

from __future__ import annotations

from typing import Any, Dict
from collections.abc import Mapping, Sequence
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
from google.protobuf.json_format import MessageToDict

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

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[_READ_ONLY_ADS_SCOPE],
    )


def _get_developer_token() -> str:
    """Returns the developer token from GOOGLE_ADS_DEVELOPER_TOKEN."""
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if dev_token is None:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set.")
    return dev_token


def _get_login_customer_id() -> str | None:
    """Returns login customer id, if set, from GOOGLE_ADS_LOGIN_CUSTOMER_ID."""
    return os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")


def _get_googleads_client() -> GoogleAdsClient:
    """Builds a GoogleAdsClient instance with interceptor support."""
    return GoogleAdsClient(
        credentials=_create_credentials(),
        developer_token=_get_developer_token(),
        login_customer_id=_get_login_customer_id(),
    )


_googleads_client = _get_googleads_client()


def get_googleads_service(service_name: str) -> GoogleAdsServiceClient:
    """Returns a Google Ads API service with MCP header interceptor."""
    return _googleads_client.get_service(
        service_name, interceptors=[MCPHeaderInterceptor()]
    )


def get_googleads_type(type_name: str):
    """Returns a Google Ads API message type."""
    return _googleads_client.get_type(type_name)


def safe_get_nested_attr(row: Any, attr: str) -> Any:
    """Safely get a nested attribute (GAQL field path) from a row."""
    try:
        return get_nested_attr(row, attr)
    except Exception:
        return None


def _is_sequence(v: Any) -> bool:
    return isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray))


def format_output_value(value: Any) -> Any:
    """
    Convert Google Ads API values (proto / protobuf) into JSON-safe primitives.

    Key behavior needed here:
    - AdTextAsset (RSA headlines/descriptions) becomes its plain text value.
    - Repeated containers become normal Python lists.
    - Unknown message objects get converted to dict where possible.
    """
    if value is None:
        return None

    # Lists/tuples/repeated fields
    if _is_sequence(value):
        return [format_output_value(v) for v in value]

    # Dict-like
    if isinstance(value, Mapping):
        return {k: format_output_value(v) for k, v in value.items()}

    # proto-plus Enums
    if isinstance(value, proto.Enum):
        return value.name

    # proto-plus Messages (Google Ads commonly returns these)
    if isinstance(value, proto.Message):
        # AdTextAsset and other text-bearing assets
        if hasattr(value, "text"):
            txt = getattr(value, "text", None)
            if isinstance(txt, str):
                return txt

        # Convert to dict via underlying protobuf message if available
        try:
            if hasattr(value, "_pb"):
                return format_output_value(
                    MessageToDict(value._pb, preserving_proto_field_name=True)
                )
        except Exception:
            pass

        # Last resort: stringify
        return str(value)

    # Raw protobuf message
    if hasattr(value, "DESCRIPTOR"):
        try:
            return format_output_value(
                MessageToDict(value, preserving_proto_field_name=True)
            )
        except Exception:
            return str(value)

    # Primitives
    if isinstance(value, (str, int, float, bool)):
        return value

    # Bytes
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")

    # Fallback
    return str(value)


def format_output_row(row: proto.Message, attributes) -> Dict[str, Any]:
    """
    Formats a Google Ads row into a JSON-safe dict based on field mask paths.
    """
    out: Dict[str, Any] = {}
    for attr in attributes:
        raw_val = safe_get_nested_attr(row, attr)
        out[attr] = format_output_value(raw_val)
    return out


def get_gaql_resources_filepath():
    """Returns the packaged path to gaql_resources.json."""
    package_root = importlib.resources.files("ads_mcp")
    return package_root.joinpath(_GAQL_FILENAME)
