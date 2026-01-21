"""Configuration for Google Sheets sync."""

# Google Sheet settings
SPREADSHEET_ID = "1QHQzY8razWXJHSdj2TE5EpayidyLBCi94QjFLQBN6OI"
SHEET_NAME = "GOOGLE DATA"

# Discord webhook for notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1449129401064100091/mwhW59cwQOV4yIRCmKi1pENP-0Nb2ZDHy55402uVTmby01sQbFxfPY6yN7IpLqBFS0uL"

# Column header mappings (header name -> metrics key)
# These map your sheet headers to the GAQL field names
COLUMN_MAPPINGS = {
    # Account info
    "ACCOUNT-ID": "customer_id",
    "Account Name": "account_name",
    "Last Updated": "last_updated",
    
    # Budget
    "Current Daily Budget (Total)": "daily_budget",
    
    # Spend columns
    "Spend (Yesterday)": "spend_yesterday",
    "Spend (2 Days Ago)": "spend_2_days_ago",
    "Spend (3 Days Ago)": "spend_3_days_ago",
    "Total Spend": "cost",
    "Total Spend (Last Month)": "cost_last_month",
    "Total Spend (2 Months Ago)": "cost_2_months_ago",
    "Total Spend (1 Year Ago)": "cost_1_year_ago",
    
    # CPA
    "CPA": "cost_per_conversion",
    "CPA (Last Month)": "cost_per_conversion_last_month",
    "CPA (2 Months Ago)": "cost_per_conversion_2_months_ago",
    "CPA (1 Year Ago)": "cost_per_conversion_1_year_ago",
    
    # Conversions
    "Conversions": "conversions",
    "Conversions (Yesterday)": "conversions_yesterday",
    "Conversions (Last Month)": "conversions_last_month",
    "Conversions (2 Months Ago)": "conversions_2_months_ago",
    "Conversions (1 Year Ago)": "conversions_1_year_ago",
    
    # Cost Per All Conversions
    "Cost Per All Conversions": "cost_per_all_conversions",
    "Cost Per All Conversions (Last Month)": "cost_per_all_conversions_last_month",
    "Cost Per All Conversions (2 Months Ago)": "cost_per_all_conversions_2_months_ago",
    "Cost Per All Conversions (1 Year Ago)": "cost_per_all_conversions_1_year_ago",
    
    # Conversion Rate
    "Conversion Rate": "conversion_rate",
    "Conversion Rate (Last Month)": "conversion_rate_last_month",
    "Conversion Rate (2 Months Ago)": "conversion_rate_2_months_ago",
    "Conversion Rate (1 Year Ago)": "conversion_rate_1_year_ago",
    
    # Conversion Value
    "Conversion Value": "conversion_value",
    "Conversion Value (Last Month)": "conversion_value_last_month",
    "Conversion Value (2 Months Ago)": "conversion_value_2_months_ago",
    "Conversion Value (1 Year Ago)": "conversion_value_1_year_ago",
    
    # All Conversions
    "All Conversions": "all_conversions",
    "All Conversions (Last Month)": "all_conversions_last_month",
    "All Conversions (2 Months Ago)": "all_conversions_2_months_ago",
    "All Conversions (1 Year Ago)": "all_conversions_1_year_ago",
    
    # All Conversion Rate
    "All Conversion Rate": "all_conversion_rate",
    "All Conversion Rate (Last Month)": "all_conversion_rate_last_month",
    "All Conversion Rate (2 Months Ago)": "all_conversion_rate_2_months_ago",
    "All Conversion Rate (1 Year Ago)": "all_conversion_rate_1_year_ago",
    
    # All Conversion Value
    "All Conversion Value": "all_conversion_value",
    "All Conversion Value (Last Month)": "all_conversion_value_last_month",
    "All Conversion Value (2 Months Ago)": "all_conversion_value_2_months_ago",
    "All Conversion Value (1 Year Ago)": "all_conversion_value_1_year_ago",
    
    # Clicks
    "Clicks": "clicks",
    "Clicks (Last Month)": "clicks_last_month",
    "Clicks (2 Months Ago)": "clicks_2_months_ago",
    "Clicks (1 Year Ago)": "clicks_1_year_ago",
    
    # Interactions
    "Interactions": "interactions",
    "Interactions (Last Month)": "interactions_last_month",
    "Interactions (2 Months Ago)": "interactions_2_months_ago",
    "Interactions (1 Year Ago)": "interactions_1_year_ago",
    
    # Interaction Rate
    "Interaction Rate": "interaction_rate",
    "Interaction Rate (Last Month)": "interaction_rate_last_month",
    "Interaction Rate (2 Months Ago)": "interaction_rate_2_months_ago",
    "Interaction Rate (1 Year Ago)": "interaction_rate_1_year_ago",
    
    # Impressions
    "Impressions": "impressions",
    "Impressions (Last Month)": "impressions_last_month",
    "Impressions (2 Months Ago)": "impressions_2_months_ago",
    "Impressions (1 Year Ago)": "impressions_1_year_ago",
    
    # CTR
    "CTR": "ctr",
    "CTR (Last Month)": "ctr_last_month",
    "CTR (2 Months Ago)": "ctr_2_months_ago",
    "CTR (1 Year Ago)": "ctr_1_year_ago",
    
    # Avg CPC
    "Avg. CPC": "average_cpc",
    "Avg. CPC (Last Month)": "average_cpc_last_month",
    "Avg. CPC (2 Months Ago)": "average_cpc_2_months_ago",
    "Avg. CPC (1 Year Ago)": "average_cpc_1_year_ago",
    
    # Search Impression Share
    "Search Impression Share": "search_impression_share",
    "Search Impression Share (Last Month)": "search_impression_share_last_month",
    "Search Impression Share (2 Months Ago)": "search_impression_share_2_months_ago",
    "Search Impression Share (1 Year Ago)": "search_impression_share_1_year_ago",
    
    # Search Exact Match IS
    "Search Exact Match IS": "search_exact_match_impression_share",
    "Search Exact Match IS (Last Month)": "search_exact_match_impression_share_last_month",
    "Search Exact Match IS (2 Months Ago)": "search_exact_match_impression_share_2_months_ago",
    "Search Exact Match IS (1 Year Ago)": "search_exact_match_impression_share_1_year_ago",
    
    # Search Lost IS: Budget
    "Search Lost IS: Budget": "search_budget_lost_impression_share",
    "Search Lost IS: Budget (Last Month)": "search_budget_lost_impression_share_last_month",
    "Search Lost IS: Budget (2 Months Ago)": "search_budget_lost_impression_share_2_months_ago",
    "Search Lost IS: Budget (1 Year Ago)": "search_budget_lost_impression_share_1_year_ago",
    
    # Search Lost IS: Rank
    "Search Lost IS: Rank": "search_rank_lost_impression_share",
    "Search Lost IS: Rank (Last Month)": "search_rank_lost_impression_share_last_month",
    "Search Lost IS: Rank (2 Months Ago)": "search_rank_lost_impression_share_2_months_ago",
    "Search Lost IS: Rank (1 Year Ago)": "search_rank_lost_impression_share_1_year_ago",
    
    # Impr. (Abs. Top) %
    "Impr. (Abs. Top) %": "absolute_top_impression_percentage",
    "Impr. (Abs. Top) % (Last Month)": "absolute_top_impression_percentage_last_month",
    "Impr. (Abs. Top) % (2 Months Ago)": "absolute_top_impression_percentage_2_months_ago",
    "Impr. (Abs. Top) % (1 Year Ago)": "absolute_top_impression_percentage_1_year_ago",
    
    # Top Impression %
    "Top Impression %": "top_impression_percentage",
    "Top Impression % (Last Month)": "top_impression_percentage_last_month",
    "Top Impression % (2 Months Ago)": "top_impression_percentage_2_months_ago",
    "Top Impression % (1 Year Ago)": "top_impression_percentage_1_year_ago",
    
    # Content Impression Share
    "Content Impression Share": "content_impression_share",
    "Content Budget Lost Impression Share": "content_budget_lost_impression_share",
    "Content Rank Lost Impression Share": "content_rank_lost_impression_share",
    
    # Engagements
    "Engagements": "engagements",
    "Engagements (Last Month)": "engagements_last_month",
    "Engagements (2 Months Ago)": "engagements_2_months_ago",
    "Engagements (1 Year Ago)": "engagements_1_year_ago",
    
    # Engagement Rate
    "Engagement Rate": "engagement_rate",
    "Engagement Rate (Last Month)": "engagement_rate_last_month",
    "Engagement Rate (2 Months Ago)": "engagement_rate_2_months_ago",
    "Engagement Rate (1 Year Ago)": "engagement_rate_1_year_ago",
    
    # Average CPM
    "Average CPM": "average_cpm",
    "Average CPM (Last Month)": "average_cpm_last_month",
    "Average CPM (2 Months Ago)": "average_cpm_2_months_ago",
    "Average CPM (1 Year Ago)": "average_cpm_1_year_ago",
    
    # Average CPV
    "Average CPV": "average_cpv",
    "Average CPV (Last Month)": "average_cpv_last_month",
    "Average CPV (2 Months Ago)": "average_cpv_2_months_ago",
    "Average CPV (1 Year Ago)": "average_cpv_1_year_ago",
    
    # Average Cost
    "Average Cost": "average_cost",
    "Average Cost (Last Month)": "average_cost_last_month",
    "Average Cost (2 Months Ago)": "average_cost_2_months_ago",
    "Average Cost (1 Year Ago)": "average_cost_1_year_ago",
    
    # ActiveView CPM
    "ActiveView CPM (Avg)": "active_view_cpm",
    "ActiveView CPM (Avg) (Last Month)": "active_view_cpm_last_month",
    "ActiveView CPM (Avg) (2 Months Ago)": "active_view_cpm_2_months_ago",
    "ActiveView CPM (Avg) (1 Year Ago)": "active_view_cpm_1_year_ago",
    
    # Measurable Rate
    "Measurable Rate": "active_view_measurability",
    "Measurable Rate (Last Month)": "active_view_measurability_last_month",
    "Measurable Rate (2 Months Ago)": "active_view_measurability_2_months_ago",
    "Measurable Rate (1 Year Ago)": "active_view_measurability_1_year_ago",
    
    # Measurable Cost
    "Measurable Cost": "active_view_measurable_cost_micros",
    "Measurable Cost (Last Month)": "active_view_measurable_cost_micros_last_month",
    "Measurable Cost (2 Months Ago)": "active_view_measurable_cost_micros_2_months_ago",
    "Measurable Cost (1 Year Ago)": "active_view_measurable_cost_micros_1_year_ago",
    
    # Invalid Clicks
    "Invalid Clicks": "invalid_clicks",
    "Invalid Clicks (Last Month)": "invalid_clicks_last_month",
    "Invalid Clicks (2 Months Ago)": "invalid_clicks_2_months_ago",
    "Invalid Clicks (1 Year Ago)": "invalid_clicks_1_year_ago",
    
    # Invalid Click Rate
    "Invalid Click Rate": "invalid_click_rate",
    "Invalid Click Rate (Last Month)": "invalid_click_rate_last_month",
    "Invalid Click Rate (2 Months Ago)": "invalid_click_rate_2_months_ago",
    "Invalid Click Rate (1 Year Ago)": "invalid_click_rate_1_year_ago",
    
    # Phone Calls
    "Phone Calls": "phone_calls",
    "Phone Calls (Last Month)": "phone_calls_last_month",
    "Phone Calls (2 Months Ago)": "phone_calls_2_months_ago",
    "Phone Calls (1 Year Ago)": "phone_calls_1_year_ago",
    
    # Phone Impressions
    "Phone Impressions": "phone_impressions",
    "Phone Impressions (Last Month)": "phone_impressions_last_month",
    "Phone Impressions (2 Months Ago)": "phone_impressions_2_months_ago",
    "Phone Impressions (1 Year Ago)": "phone_impressions_1_year_ago",
    
    # Phone Through Rate
    "Phone Through Rate": "phone_through_rate",
    "Phone Through Rate (Last Month)": "phone_through_rate_last_month",
    "Phone Through Rate (2 Months Ago)": "phone_through_rate_2_months_ago",
    "Phone Through Rate (1 Year Ago)": "phone_through_rate_1_year_ago",
}
