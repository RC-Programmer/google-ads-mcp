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

from typing import Any, Dict, List, Optional
import logging
import os
import importlib.resources
from collections.abc import Sequence

import proto
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
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
    """Returns the developer token from env var GOOGLE_ADS_DEVELOPER_TOKEN."""
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if dev_token is None:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set.")
    return dev_token


def _get_login_customer_id() -> Optional[str]:
    """Returns login customer id from env var GOOGLE_ADS_LOGIN_CUSTOMER_ID (optional)."""
    return os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")


def _get_googleads_client() -> GoogleAdsClient:
    return GoogleAdsClient(
        credentials=_create_credentials(),
        developer_token=_get_developer_token(),
        login_customer_id=_get_login_customer_id(),
    )


_googleads_client = _get_googleads_client()


def get_googleads_service(service_name: str) -> GoogleAdsServiceClient:
    return _googleads_client.get_service(service_name, interceptors=[MCPHeaderInterceptor()])


def get_googleads_type(type_name: str):
    return _googleads_client.get_type(type_name)


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    return package_root.joinpath(_GAQL_FILENAME)


def _safe_get_nested_attr(obj: Any, path: str) -> Any:
    """
    Safely traverses nested protobuf fields using a dotted path.

    Important: GA protobufs often use `type_` in Python for fields named `type`.
    GAQL uses `.type`, so we map `type` -> `type_` during traversal.
    """
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None

        # Map GAQL "type" field to python protobuf "type_"
        if part == "type":
            part = "type_"

        try:
            cur = getattr(cur, part)
        except Exception:
            return None

    return cur


def _proto_to_python(value: Any) -> Any:
    """
    Convert protobuf / proto-plus objects (including repeated containers) into
    JSON-serializable Python primitives.
    """
    if value is None:
        return None

    # proto-plus Enum -> name
    if isinstance(value, proto.Enum):
        return value.name

    # proto-plus Message OR protobuf Message -> dict
    if isinstance(value, proto.Message):
        return MessageToDict(
            value,
            preserving_proto_field_name=True,
            including_default_value_fields=False,
            use_integers_for_enums=False,
        )

    # Repeated containers (scalar or message)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        out: List[Any] = []
        for item in value:
            out.append(_proto_to_python(item))
        return out

    # Fallback for other objects (ints, floats, strings, bools, etc.)
    return value


def format_output_value(value: Any) -> Any:
    return _proto_to_python(value)


def format_output_row(row: proto.Message, attributes: List[str]) -> Dict[str, Any]:
    """
    Formats a GoogleAdsRow into a flat dict keyed by the GAQL field paths.
    """
    output: Dict[str, Any] = {}
    for attr in attributes:
        raw = _safe_get_nested_attr(row, attr)
        output[attr] = format_output_value(raw)
    return output
