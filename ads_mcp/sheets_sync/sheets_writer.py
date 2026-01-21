"""Write data to Google Sheets."""

import os
import json
import logging
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ads_mcp.sheets_sync.config import SPREADSHEET_ID, SHEET_NAME, COLUMN_MAPPINGS

logger = logging.getLogger(__name__)

# Scopes for Google Sheets API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_sheets_service():
    """Create Google Sheets API service using service account credentials."""
    
    # Try to load credentials from environment variable (JSON string)
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    else:
        # Fallback: load from file
        creds_file = os.environ.get(
            "GOOGLE_SHEETS_CREDENTIALS_FILE",
            "credentials/sheets_service_account.json"
        )
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
    
    return build("sheets", "v4", credentials=credentials)


def get_sheet_data() -> tuple[List[List[Any]], List[str]]:
    """Get current sheet data and headers."""
    service = _get_sheets_service()
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'"
    ).execute()
    
    values = result.get("values", [])
    
    if not values:
        return [], []
    
    headers = values[0]
    return values, headers


def find_account_row(values: List[List[Any]], headers: List[str], account_id: str) -> int:
    """Find the row index for a given account ID. Returns -1 if not found."""
    
    # Find ACCOUNT-ID column
    account_col = -1
    for i, header in enumerate(headers):
        h = header.strip().upper().replace(" ", "-")
        if h in ["ACCOUNT-ID", "ACCOUNT_ID", "ACCOUNTID"]:
            account_col = i
            break
    
    if account_col == -1:
        logger.error("Could not find ACCOUNT-ID column")
        return -1
    
    # Normalize search ID (remove dashes)
    search_id = account_id.replace("-", "").strip()
    
    # Search for account (start from row 1, skip header)
    for row_idx, row in enumerate(values[1:], start=1):
        if len(row) > account_col:
            row_id = str(row[account_col]).replace("-", "").replace(".0", "").strip()
            if row_id == search_id:
                return row_idx
    
    return -1


def find_under_management_accounts(values: List[List[Any]], headers: List[str]) -> List[str]:
    """Find all account IDs where 'Under Management' = 'Yes'."""
    
    # Find column indices
    account_col = -1
    mgmt_col = -1
    
    for i, header in enumerate(headers):
        h = header.strip().upper().replace(" ", "-")
        if h in ["ACCOUNT-ID", "ACCOUNT_ID", "ACCOUNTID"]:
            account_col = i
        elif "UNDER" in h and "MANAGEMENT" in h:
            mgmt_col = i
    
    if account_col == -1:
        logger.error("Could not find ACCOUNT-ID column")
        return []
    
    if mgmt_col == -1:
        logger.warning("Could not find 'Under Management' column, returning all accounts")
        # Return all account IDs if no management column
        accounts = []
        for row in values[1:]:
            if len(row) > account_col and row[account_col]:
                acc_id = str(row[account_col]).replace("-", "").replace(".0", "").strip()
                if acc_id:
                    accounts.append(acc_id)
        return accounts
    
    # Find accounts under management
    accounts = []
    for row in values[1:]:
        if len(row) > max(account_col, mgmt_col):
            mgmt_status = str(row[mgmt_col]).strip().lower() if len(row) > mgmt_col else ""
            if mgmt_status == "yes":
                acc_id = str(row[account_col]).replace("-", "").replace(".0", "").strip()
                if acc_id:
                    accounts.append(acc_id)
    
    return accounts


def update_account_row(
    row_index: int,
    headers: List[str],
    metrics: Dict[str, Any]
) -> bool:
    """Update a single row with metrics data."""
    
    service = _get_sheets_service()
    
    # Build the update data
    # We need to map metrics to the correct columns
    updates = []
    
    for col_idx, header in enumerate(headers):
        # Normalize header for matching
        header_clean = header.strip()
        
        # Check if this header is in our mappings
        if header_clean in COLUMN_MAPPINGS:
            metric_key = COLUMN_MAPPINGS[header_clean]
            value = metrics.get(metric_key, "")
            
            # Format the value appropriately
            if value is None:
                value = ""
            elif isinstance(value, float):
                # Keep as number for Sheets
                pass
            
            updates.append({
                "range": f"'{SHEET_NAME}'!{_col_letter(col_idx)}{row_index + 1}",
                "values": [[value]]
            })
    
    if not updates:
        logger.warning(f"No updates to make for row {row_index}")
        return False
    
    # Batch update
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates
    }
    
    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update row {row_index}: {e}")
        return False


def _col_letter(col_idx: int) -> str:
    """Convert column index to letter (0=A, 1=B, ..., 26=AA, etc.)."""
    result = ""
    while col_idx >= 0:
        result = chr(col_idx % 26 + ord('A')) + result
        col_idx = col_idx // 26 - 1
    return result
