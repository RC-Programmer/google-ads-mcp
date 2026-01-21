"""Main entry point for Google Sheets sync job."""

import logging
import requests
from datetime import datetime
from typing import List

from ads_mcp.sheets_sync.config import DISCORD_WEBHOOK_URL
from ads_mcp.sheets_sync.metrics import get_account_metrics
from ads_mcp.sheets_sync.sheets_writer import (
    get_sheet_data,
    find_account_row,
    find_under_management_accounts,
    update_account_row,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def send_discord_notification(title: str, message: str, color: int = 3066993):
    """Send a notification to Discord."""
    if not DISCORD_WEBHOOK_URL:
        return
    
    timestamp = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
    
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color,
            "footer": {"text": f"KPI Hub | {timestamp} CT"}
        }]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")


def send_discord_error(error_message: str, account_name: str = None):
    """Send error notification to Discord."""
    description = f"**Error:** {error_message}"
    if account_name:
        description = f"**Account:** {account_name}\n{description}"
    
    send_discord_notification(
        title="🚨 Sheets Sync Error",
        message=description,
        color=15158332  # Red
    )


def send_discord_summary(success_count: int, error_count: int, errors: List[str]):
    """Send summary notification to Discord."""
    description = f"✅ **Processed:** {success_count}\n❌ **Errors:** {error_count}"
    
    if errors:
        description += "\n\n**Error Details:**\n"
        for err in errors[:10]:  # Limit to 10 errors
            description += f"• {err}\n"
    
    color = 16776960 if error_count > 0 else 3066993  # Yellow if errors, green if success
    emoji = "⚠️" if error_count > 0 else "✅"
    
    send_discord_notification(
        title=f"{emoji} Sheets Sync Complete",
        message=description,
        color=color
    )


def run_sync():
    """Main sync function - pull data from Google Ads and write to Sheets."""
    logger.info("=" * 50)
    logger.info("Starting Google Sheets sync")
    logger.info("=" * 50)
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    try:
        # Get current sheet data
        logger.info("Fetching sheet data...")
        values, headers = get_sheet_data()
        
        if not values:
            raise Exception("Sheet is empty or could not be read")
        
        logger.info(f"Found {len(values) - 1} rows in sheet")
        
        # Find accounts to process
        account_ids = find_under_management_accounts(values, headers)
        logger.info(f"Found {len(account_ids)} accounts under management")
        
        if not account_ids:
            logger.warning("No accounts to process")
            return
        
        # Process each account
        for account_id in account_ids:
            try:
                logger.info(f"Processing account: {account_id}")
                
                # Find row for this account
                row_index = find_account_row(values, headers, account_id)
                
                if row_index == -1:
                    logger.warning(f"Account {account_id} not found in sheet, skipping")
                    continue
                
                # Get metrics from Google Ads
                metrics = get_account_metrics(account_id)
                
                if not metrics:
                    raise Exception("No metrics returned")
                
                # Update the row
                success = update_account_row(row_index, headers, metrics)
                
                if success:
                    success_count += 1
                    logger.info(f"✓ Successfully updated account {account_id}")
                else:
                    raise Exception("Failed to update row")
                
            except Exception as e:
                error_count += 1
                error_msg = f"{account_id}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"✗ Error processing {account_id}: {e}")
                send_discord_error(str(e), account_id)
        
    except Exception as e:
        logger.error(f"Fatal error during sync: {e}")
        send_discord_error(f"Fatal error: {str(e)}")
        raise
    
    # Send summary
    logger.info("=" * 50)
    logger.info(f"Sync complete. Success: {success_count}, Errors: {error_count}")
    logger.info("=" * 50)
    
    send_discord_summary(success_count, error_count, error_messages)


if __name__ == "__main__":
    run_sync()
