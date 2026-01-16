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

from typing import Any
from collections.abc import Mapping, Sequence
import importlib.resources
import logging
import os

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


def _get_login_customer_id() -> str | None:
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
    return _googleads_client.get_service(serviceName, interceptors=[MCPHeaderInterceptor()])


def get_googleads_type(typeName: str):
    return _googleads_client.get_type(typeName)


def _flatten_text_assets(value: Any) -> Any:
    """
    Convert AdTextAsset-ish objects to plain strings.
    Accepts:
      - list[dict] with {'text': ...}
      - list[proto.Message] that become dicts
      - dict with {'text': ...}
    """
    if isinstance(value, Mapping):
        if "text" in value and isinstance(value.get("text"), str):
            return value["text"]
        return value

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        out: list[Any] = []
        for item in value:
            if isinstance(item, Mapping) and "text" in item and isinstance(item.get("text"), str):
                out.append(item["text"])
            else:
                out.append(item)
        return out

    return value


def _to_plain(value: Any, *, attr_path: str | None = None) -> Any:
    """
    Recursively convert protobuf / proto-plus objects into JSON-serializable Python types.

    Special-case:
      - RSA headlines/descriptions -> list[str] (just the 'text' field)
    """
    # Enums
    if isinstance(value, proto.Enum):
        return value.name

    # Protobuf / proto-plus Messages
    if isinstance(value, proto.Message):
        as_dict = MessageToDict(
            value,
            preserving_proto_field_name=True,
            including_default_value_fields=False,
            use_integers_for_enums=False,
        )
        # If we're serializing a text asset itself, compress to text
        if isinstance(as_dict, dict) and "text" in as_dict and isinstance(as_dict.get("text"), str):
            return as_dict["text"]
        return as_dict

    # Repeated containers / lists / tuples
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_plain(v, attr_path=attr_path) for v in value]

    # Dicts
    if isinstance(value, Mapping):
        return {k: _to_plain(v, attr_path=attr_path) for k, v in value.items()}

    return value


def format_output_value(value: Any, attr_path: str | None = None) -> Any:
    """
    Converts Google Ads API field values into JSON-serializable types.

    Key behavior:
      - Enums -> string names
      - Messages -> dict
      - Repeated values -> list
      - RSA headlines/descriptions -> list[str] (text only)
    """
    plain = _to_plain(value, attr_path=attr_path)

    # Only flatten to plain text list for specific RSA fields requested by you.
    if attr_path and (
        attr_path.endswith(".responsive_search_ad.headlines")
        or attr_path.endswith(".responsive_search_ad.descriptions")
    ):
        return _flatten_text_assets(plain)

    return plain


def format_output_row(row: proto.Message, attributes):
    return {attr: format_output_value(get_nested_attr(row, attr), attr) for attr in attributes}


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path
