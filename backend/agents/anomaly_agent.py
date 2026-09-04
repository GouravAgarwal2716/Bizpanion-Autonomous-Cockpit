"""
Anomaly Detection Agent
Runs 4 real, computable checks against actual business data.
Each check returns a severity score and structured evidence.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from models.schemas import AlertType, AlertSeverity
from config import settings
import logging

logger = logging.getLogger(__name__)


def compute_severity(deviation_pct: float, thresholds: dict) -> AlertSeverity:
    """Map a deviation percentage to a severity level."""
    if deviation_pct >= thresholds.get("high", 25):
        return AlertSeverity.HIGH
    elif deviation_pct >= thresholds.get("medium", 15):
        return AlertSeverity.MEDIUM
    else:
        return AlertSeverity.LOW


# ── CHECK 1: Underpricing ────────────────────────────────────────────────────

async def check_underpricing(
    transactions: list[dict],
    market_prices: list[dict],
    threshold_pct: float = None,
) -> list[dict]:
    """
    Compare user's actual recorded selling prices against regional market rates.
    Returns list of anomaly dicts for items where user is underpricing.
    """
    threshold = threshold_pct or settings.UNDERPRICING_THRESHOLD_PCT
    findings = []

    if not transactions or not market_prices:
        return findings

    df = pd.DataFrame(transactions)
    df_market = pd.DataFrame(market_prices)

    # Get recent transactions (last 30 days)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    recent = df[df["date"] >= datetime.now() - timedelta(days=30)]
    
    if recent.empty:
        return findings

    # Compute average selling price per item
    avg_prices = (
        recent.groupby("item_name")["selling_price_per_unit"]
        .agg(["mean", "count"])
        .reset_index()
    )
    avg_prices.columns = ["item_name", "avg_price", "txn_count"]
    avg_prices = avg_prices[avg_prices["txn_count"] >= 3]  # need at least 3 transactions

    for _, row in avg_prices.iterrows():
        item = row["item_name"].lower().strip()
        user_price = row["avg_price"]

        # Find matching market price
        market_match = df_market[
            df_market["commodity"].str.lower().str.contains(item[:4], na=False) |
            df_market["commodity"].str.lower().str.contains(item.split()[0] if item else "x", na=False)
        ]
        if market_match.empty:
            continue

        market_price = market_match["modal_price"].iloc[0]
        market_name = market_match.get("market_name", pd.Series(["regional market"])).iloc[0]

        if market_price <= 0 or user_price <= 0:
            continue

        deviation_pct = ((market_price - user_price) / market_price) * 100

        if deviation_pct >= threshold:
            severity = compute_severity(deviation_pct, {"medium": threshold, "high": threshold * 1.5})
            findings.append({
                "alert_type": AlertType.UNDERPRICING.value,
                "severity": severity.value,
                "item_name": row["item_name"],
                "user_price": round(user_price, 2),
                "market_price": round(market_price, 2),
                "market_name": str(market_name),
                "deviation_pct": round(deviation_pct, 1),
                "txn_count": int(row["txn_count"]),
                "potential_revenue_loss_per_unit": round(market_price - user_price, 2),
            })

    return sorted(findings, key=lambda x: x["deviation_pct"], reverse=True)


# ── CHECK 2: Stock Depletion ─────────────────────────────────────────────────

async def check_stock_depletion(
    inventory: list[dict],
    forecast_results: list[dict],
    days_ahead: int = None,
) -> list[dict]:
    """
    Cross-checks forecasted demand against current stock levels.
    Flags items that will run out within `days_ahead` days.
    """
    days = days_ahead or settings.STOCK_DEPLETION_DAYS_AHEAD
    findings = []

    if not inventory:
        return findings

    inventory_map = {item["item_name"].lower(): item for item in inventory}

    for forecast in forecast_results:
        item_key = forecast.get("item_name", "").lower()
        inv = inventory_map.get(item_key)

        if not inv:
            continue

        current_stock = inv.get("current_stock", 0)
        predicted_demand = forecast.get("predicted_demand_7d", 0)
        daily_demand = predicted_demand / 7 if predicted_demand > 0 else 0

        if daily_demand <= 0:
            continue

        days_until_stockout = current_stock / daily_demand

        if days_until_stockout <= days:
            severity_pct = max(0, (days - days_until_stockout) / days * 100)
            severity = compute_severity(severity_pct, {"medium": 40, "high": 70})
            stockout_date = datetime.now() + timedelta(days=days_until_stockout)

            findings.append({
                "alert_type": AlertType.STOCK_DEPLETION.value,
                "severity": severity.value,
                "item_name": inv["item_name"],
                "current_stock": round(current_stock, 2),
                "unit": inv.get("unit", "kg"),
                "daily_demand": round(daily_demand, 2),
                "days_until_stockout": round(days_until_stockout, 1),
                "stockout_date": stockout_date.isoformat(),
                "predicted_demand_7d": round(predicted_demand, 2),
            })

    return sorted(findings, key=lambda x: x["days_until_stockout"])


# ── CHECK 3: Scheme Deadline ─────────────────────────────────────────────────

async def check_scheme_deadlines_alert(urgent_schemes: list[dict]) -> list[dict]:
    """
    Convert urgent scheme matches from RAG into alert format.
    """
    findings = []
    for scheme in urgent_schemes:
        days_remaining = scheme.get("days_remaining", 999)
        severity = AlertSeverity.HIGH if days_remaining <= 3 else (
            AlertSeverity.MEDIUM if days_remaining <= 5 else AlertSeverity.LOW
        )
        findings.append({
            "alert_type": AlertType.SCHEME_DEADLINE.value,
            "severity": severity.value,
            "scheme_name": scheme.get("scheme_name", ""),
            "days_remaining": days_remaining,
            "deadline": scheme.get("deadline", ""),
            "benefit": scheme.get("benefit", ""),
            "apply_url": scheme.get("apply_url", ""),
            "eligibility": scheme.get("eligibility", ""),
        })
    return findings


# ── CHECK 4: Sales Anomaly ────────────────────────────────────────────────────

async def check_sales_anomaly(transactions: list[dict]) -> list[dict]:
    """
    Statistical z-score anomaly detection on recent sales.
    Compares latest period sales against business's own historical average.
    """
    findings = []
    zscore_threshold = settings.SALES_ZSCORE_THRESHOLD

    if not transactions:
        return findings

    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["transaction_type"] == "sale"]
    df = df.dropna(subset=["date", "total_amount"])

    if len(df) < 14:  # Need at least 2 weeks of data
        return findings

    # Aggregate daily sales
    daily = df.groupby(df["date"].dt.date)["total_amount"].sum().reset_index()
    daily.columns = ["date", "daily_total"]
    daily = daily.sort_values("date")

    if len(daily) < 7:
        return findings

    # Rolling 30-day mean and std for baseline
    daily["rolling_mean"] = daily["daily_total"].rolling(window=min(30, len(daily)), min_periods=7).mean()
    daily["rolling_std"] = daily["daily_total"].rolling(window=min(30, len(daily)), min_periods=7).std()

    # Check last 3 days
    recent = daily.tail(3)
    for _, day_row in recent.iterrows():
        mean = day_row["rolling_mean"]
        std = day_row["rolling_std"]

        if pd.isna(mean) or pd.isna(std) or std == 0:
            continue

        zscore = abs((day_row["daily_total"] - mean) / std)

        if zscore >= zscore_threshold:
            direction = "spike" if day_row["daily_total"] > mean else "drop"
            severity_pct = min(100, (zscore - zscore_threshold) / zscore_threshold * 100)
            severity = compute_severity(severity_pct, {"medium": 30, "high": 60})
            pct_change = ((day_row["daily_total"] - mean) / mean * 100)

            findings.append({
                "alert_type": AlertType.SALES_ANOMALY.value,
                "severity": severity.value,
                "date": str(day_row["date"]),
                "daily_sales": round(day_row["daily_total"], 2),
                "historical_avg": round(mean, 2),
                "zscore": round(zscore, 2),
                "direction": direction,
                "pct_change": round(pct_change, 1),
            })

    return findings


# ── AGGREGATE ALL CHECKS ─────────────────────────────────────────────────────

async def run_all_anomaly_checks(
    transactions: list[dict],
    inventory: list[dict],
    market_prices: list[dict],
    forecast_results: list[dict],
    urgent_schemes: list[dict],
    workflow_rules: dict,
) -> list[dict]:
    """Run all 4 anomaly checks and return combined findings."""
    import asyncio

    underpricing, stock, schemes, sales = await asyncio.gather(
        check_underpricing(transactions, market_prices, workflow_rules.get("underpricing_threshold_pct")),
        check_stock_depletion(inventory, forecast_results, workflow_rules.get("stock_depletion_days")),
        check_scheme_deadlines_alert(urgent_schemes),
        check_sales_anomaly(transactions),
    )

    return underpricing + stock + schemes + sales
