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
import datetime
import decimal
import importlib.resources
import logging
import os

import proto
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.util import get_nested_attr
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
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


def _is_repeated_container(value: Any) -> bool:
    """
    Google Ads protobufs frequently return these internal container types:
      - google._upb._message.RepeatedScalarContainer
      - google._upb._message.RepeatedCompositeContainer
    They are iterable but not JSON serializable, so we convert them to lists.
    """
    if value is None:
        return False
    tname = type(value).__name__
    return tname in ("RepeatedScalarContainer", "RepeatedCompositeContainer")


def _message_to_dict(msg: proto.Message) -> dict[str, Any]:
    """
    Best-effort conversion of a proto-plus message into a JSON-serializable dict.
    Only includes fields that are actually set.
    """
    # proto-plus messages wrap a protobuf message in ._pb
    pb = getattr(msg, "_pb", None)
    if pb is None or not hasattr(pb, "ListFields"):
        # Fallback to string if we can't introspect
        return {"_value": str(msg)}

    out: dict[str, Any] = {}
    for field_desc, field_value in pb.ListFields():
        out[field_desc.name] = format_output_value(field_value)
    return out


def format_output_value(value: Any) -> Any:
    """
    Convert Google Ads API return values into JSON-serializable Python objects.

    Special behavior:
    - AdTextAsset (RSA headline/description objects) -> return just the plain `text`
    - Repeated* containers -> plain Python lists
    - proto messages -> dict of set fields (best-effort)
    """
    if value is None:
        return None

    # Enums -> name
    if isinstance(value, proto.Enum):
        return value.name

    # Already-serializable primitives
    if isinstance(value, (str, int, float, bool)):
        return value

    # Common scalars
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)

    # Google protobuf repeated containers (not JSON serializable)
    if _is_repeated_container(value) or isinstance(value, (list, tuple, set)):
        return [format_output_value(v) for v in list(value)]

    # proto-plus messages (includes AdTextAsset, PolicySummaryInfo, etc.)
    if isinstance(value, proto.Message):
        # Make RSA assets readable: headlines/descriptions are AdTextAsset messages.
        # They always have a `text` field; return just that.
        if hasattr(value, "text"):
            txt = getattr(value, "text", None)
            if txt is not None:
                return txt

        # Otherwise convert to dict (only set fields)
        return _message_to_dict(value)

    # Last resort: stringify (keeps server from crashing)
    return str(value)


def format_output_row(row: proto.Message, attributes):
    return {attr: format_output_value(get_nested_attr(row, attr)) for attr in attributes}


def get_gaql_resources_filepath():
    package_root = importlib.resources.files("ads_mcp")
    file_path = package_root.joinpath(_GAQL_FILENAME)
    return file_path
