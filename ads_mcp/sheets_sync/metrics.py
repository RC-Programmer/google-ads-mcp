"""Pull KPI metrics from Google Ads API."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

import ads_mcp.utils as utils

logger = logging.getLogger(__name__)


def _get_date_ranges() -> Dict[str, tuple]:
    """Calculate date ranges for current month, last month, 2 months ago, 1 year ago."""
    today = datetime.now()
    
    if today.day == 1:
        yesterday = today - timedelta(days=1)
        current_start = yesterday.replace(day=1)
        current_end = yesterday
    else:
        yesterday = today - timedelta(days=1)
        current_start = today.replace(day=1)
        current_end = yesterday
    
    last_month_end = current_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    
    two_months_end = last_month_start - timedelta(days=1)
    two_months_start = two_months_end.replace(day=1)
    
    one_year_start = current_start.replace(year=current_start.year - 1)
    if one_year_start.month == 12:
        one_year_end = one_year_start.replace(year=one_year_start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        one_year_end = one_year_start.replace(month=one_year_start.month + 1, day=1) - timedelta(days=1)
    
    two_days_ago = today - timedelta(days=2)
    three_days_ago = today - timedelta(days=3)
    
    return {
        "current": (current_start, current_end),
        "last_month": (last_month_start, last_month_end),
        "two_months_ago": (two_months_start, two_months_end),
        "one_year_ago": (one_year_start, one_year_end),
        "yesterday": (yesterday, yesterday),
        "two_days_ago": (two_days_ago, two_days_ago),
        "three_days_ago": (three_days_ago, three_days_ago),
    }


def _format_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _run_query(customer_id: str, query: str) -> Optional[Dict[str, Any]]:
    try:
        ga_service = utils.get_googleads_service("GoogleAdsService")
        result = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in result:
            for row in batch.results:
                return row
        return None
    except Exception as e:
        logger.error(f"Query failed for {customer_id}: {e}")
        return None


def _extract_metric(row: Any, field: str) -> Any:
    try:
        parts = field.split(".")
        value = row
        for part in parts:
            value = getattr(value, part)
        if "micros" in field:
            return float(value) / 1_000_000
        return value
    except Exception:
        return 0


def get_account_metrics(customer_id: str) -> Dict[str, Any]:
    """Get all KPI metrics for a single account."""
    
    date_ranges = _get_date_ranges()
    metrics = {"customer_id": customer_id}
    
    # Base query fields - only metrics compatible with CUSTOMER resource
    base_fields = """
        metrics.cost_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.conversions,
        metrics.conversions_value,
        metrics.all_conversions,
        metrics.all_conversions_value,
        metrics.ctr,
        metrics.average_cpc,
        metrics.average_cpm,
        metrics.average_cost,
        metrics.interactions,
        metrics.interaction_rate,
        metrics.cost_per_conversion,
        metrics.cost_per_all_conversions,
        metrics.conversions_from_interactions_rate,
        metrics.all_conversions_from_interactions_rate,
        metrics.search_impression_share,
        metrics.search_exact_match_impression_share,
        metrics.search_budget_lost_impression_share,
        metrics.search_rank_lost_impression_share,
        metrics.content_impression_share,
        metrics.content_budget_lost_impression_share,
        metrics.content_rank_lost_impression_share,
        metrics.engagements,
        metrics.engagement_rate,
        metrics.active_view_cpm,
        metrics.active_view_measurability,
        metrics.active_view_measurable_cost_micros,
        metrics.invalid_clicks,
        metrics.invalid_click_rate
    """
    
    period_suffixes = {
        "current": "",
        "last_month": "_last_month",
        "two_months_ago": "_2_months_ago",
        "one_year_ago": "_1_year_ago",
    }
    
    for period, suffix in period_suffixes.items():
        start, end = date_ranges[period]
        query = f"""
            SELECT
                customer.descriptive_name,
                {base_fields}
            FROM customer
            WHERE segments.date >= '{_format_date(start)}'
              AND segments.date <= '{_format_date(end)}'
        """
        
        row = _run_query(customer_id, query)
        if row:
            if period == "current":
                try:
                    metrics["account_name"] = row.customer.descriptive_name
                except:
                    metrics["account_name"] = ""
            
            metrics[f"cost{suffix}"] = _extract_metric(row, "metrics.cost_micros")
            metrics[f"impressions{suffix}"] = _extract_metric(row, "metrics.impressions")
            metrics[f"clicks{suffix}"] = _extract_metric(row, "metrics.clicks")
            metrics[f"conversions{suffix}"] = _extract_metric(row, "metrics.conversions")
            metrics[f"conversion_value{suffix}"] = _extract_metric(row, "metrics.conversions_value")
            metrics[f"all_conversions{suffix}"] = _extract_metric(row, "metrics.all_conversions")
            metrics[f"all_conversion_value{suffix}"] = _extract_metric(row, "metrics.all_conversions_value")
            metrics[f"ctr{suffix}"] = _extract_metric(row, "metrics.ctr")
            metrics[f"average_cpc{suffix}"] = _extract_metric(row, "metrics.average_cpc")
            metrics[f"average_cpm{suffix}"] = _extract_metric(row, "metrics.average_cpm")
            metrics[f"average_cpv{suffix}"] = 0
            metrics[f"average_cost{suffix}"] = _extract_metric(row, "metrics.average_cost")
            metrics[f"interactions{suffix}"] = _extract_metric(row, "metrics.interactions")
            metrics[f"interaction_rate{suffix}"] = _extract_metric(row, "metrics.interaction_rate")
            metrics[f"cost_per_conversion{suffix}"] = _extract_metric(row, "metrics.cost_per_conversion")
            metrics[f"cost_per_all_conversions{suffix}"] = _extract_metric(row, "metrics.cost_per_all_conversions")
            metrics[f"conversion_rate{suffix}"] = _extract_metric(row, "metrics.conversions_from_interactions_rate")
            metrics[f"all_conversion_rate{suffix}"] = _extract_metric(row, "metrics.all_conversions_from_interactions_rate")
            metrics[f"search_impression_share{suffix}"] = _extract_metric(row, "metrics.search_impression_share")
            metrics[f"search_exact_match_impression_share{suffix}"] = _extract_metric(row, "metrics.search_exact_match_impression_share")
            metrics[f"search_budget_lost_impression_share{suffix}"] = _extract_metric(row, "metrics.search_budget_lost_impression_share")
            metrics[f"search_rank_lost_impression_share{suffix}"] = _extract_metric(row, "metrics.search_rank_lost_impression_share")
            metrics[f"absolute_top_impression_percentage{suffix}"] = 0  # Not available on CUSTOMER
            metrics[f"top_impression_percentage{suffix}"] = 0  # Not available on CUSTOMER
            metrics[f"content_impression_share{suffix}"] = _extract_metric(row, "metrics.content_impression_share")
            metrics[f"content_budget_lost_impression_share{suffix}"] = _extract_metric(row, "metrics.content_budget_lost_impression_share")
            metrics[f"content_rank_lost_impression_share{suffix}"] = _extract_metric(row, "metrics.content_rank_lost_impression_share")
            metrics[f"engagements{suffix}"] = _extract_metric(row, "metrics.engagements")
            metrics[f"engagement_rate{suffix}"] = _extract_metric(row, "metrics.engagement_rate")
            metrics[f"active_view_cpm{suffix}"] = _extract_metric(row, "metrics.active_view_cpm")
            metrics[f"active_view_measurability{suffix}"] = _extract_metric(row, "metrics.active_view_measurability")
            metrics[f"active_view_measurable_cost_micros{suffix}"] = _extract_metric(row, "metrics.active_view_measurable_cost_micros")
            metrics[f"invalid_clicks{suffix}"] = _extract_metric(row, "metrics.invalid_clicks")
            metrics[f"invalid_click_rate{suffix}"] = _extract_metric(row, "metrics.invalid_click_rate")
            metrics[f"phone_calls{suffix}"] = 0  # Not available on CUSTOMER
            metrics[f"phone_impressions{suffix}"] = 0  # Not available on CUSTOMER
            metrics[f"phone_through_rate{suffix}"] = 0  # Not available on CUSTOMER
    
    # Yesterday, 2 days ago, 3 days ago spend and conversions
    for period in ["yesterday", "two_days_ago", "three_days_ago"]:
        start, end = date_ranges[period]
        query = f"""
            SELECT metrics.cost_micros, metrics.conversions
            FROM customer
            WHERE segments.date >= '{_format_date(start)}'
              AND segments.date <= '{_format_date(end)}'
        """
        row = _run_query(customer_id, query)
        if row:
            if period == "yesterday":
                metrics["spend_yesterday"] = _extract_metric(row, "metrics.cost_micros")
                metrics["conversions_yesterday"] = _extract_metric(row, "metrics.conversions")
            elif period == "two_days_ago":
                metrics["spend_2_days_ago"] = _extract_metric(row, "metrics.cost_micros")
            elif period == "three_days_ago":
                metrics["spend_3_days_ago"] = _extract_metric(row, "metrics.cost_micros")
    
    metrics["daily_budget"] = _get_total_daily_budget(customer_id)
    metrics["last_updated"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    
    return metrics


def _get_total_daily_budget(customer_id: str) -> float:
    try:
        ga_service = utils.get_googleads_service("GoogleAdsService")
        query = """
            SELECT campaign.id, campaign_budget.amount_micros, campaign_budget.explicitly_shared
            FROM campaign
            WHERE campaign.status = 'ENABLED' AND campaign.serving_status = 'SERVING'
        """
        result = ga_service.search_stream(customer_id=customer_id, query=query)
        total_budget = 0.0
        seen_budgets = set()
        for batch in result:
            for row in batch.results:
                budget_micros = row.campaign_budget.amount_micros
                is_shared = row.campaign_budget.explicitly_shared
                budget_key = budget_micros if is_shared else row.campaign.id
                if budget_key not in seen_budgets:
                    seen_budgets.add(budget_key)
                    total_budget += budget_micros / 1_000_000
        return total_budget
    except Exception as e:
        logger.error(f"Failed to get daily budget for {customer_id}: {e}")
        return 0.0


def get_accessible_customer_ids() -> List[str]:
    try:
        customer_service = utils.get_googleads_service("CustomerService")
        response = customer_service.list_accessible_customers()
        return [rn.replace("customers/", "") for rn in response.resource_names]
    except Exception as e:
        logger.error(f"Failed to get accessible customers: {e}")
        return []
