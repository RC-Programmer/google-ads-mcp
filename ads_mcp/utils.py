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

from typing import Any, Dict, List
import proto
import logging
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.oauth2.credentials import Credentials
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict
from ads_mcp.mcp_header_interceptor import MCPHeaderInterceptor
import os
import importlib.resources

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
    return _googleads_client.get_service(serviceName, interceptors=[MCPHeaderInterceptor()])


def get_googleads_type(typeName: str):
    return _googleads_client.get_type(typeName)


def _to_jsonable(value: Any) -> Any:
    """
    Convert protobuf / repeated containers / nested structures into plain JSON-safe
    Python types (dict, list, str, int, float, bool, None).
    """
    if value is None:
        return None

    # Enum -> name (ex: ENABLED)
    if isinstance(value, proto.Enum):
        return value.name

    # Protobuf message -> dict
    if isinstance(value, Message):
        return MessageToDict(
            value,
            preserving_proto_field_name=True,
            including_default_value_fields=False,
            use_integers_for_enums=True,
        )

    # Protobuf repeated containers:
    # google._upb._message.RepeatedScalarContainer / RepeatedCompositeContainer
    # They behave like iterables but are not JSON serializable.
    mod = getattr(value.__class__, "__module__", "")
    name = getattr(value.__class__, "__name__", "")
    if mod.startswith("google.") and "Repeated" in name:
        return [_to_jsonable(v) for v in list(value)]

    # Normal containers
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]

    # Bytes -> decode best-effort
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return str(value)

    # Scalars are already JSON-safe
    return value


def format_output_row(row: proto.Message, attributes: List[str]) -> Dict[str, Any]:
    """
    Return a dict mapping each requested field path to a JSON-safe value.
    """
    out: Dict[str, Any] = {}
    for attr in attributes:
        raw = getattr(row, attr.split(".")[0], None)

        # Fallback: use get_nested_attr for nested paths
        try:
            raw = get_nested_attr(row, attr)
        except Exception:
            raw = None

        out[attr] = _to_jsonable(raw)

    return out


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path
