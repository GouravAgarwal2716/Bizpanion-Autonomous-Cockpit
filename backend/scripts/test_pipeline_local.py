"""
End-to-end Local Verification Script for Bizpanion.
Tests:
1. CSV Loading & Cleaning Pipeline (Hindi/messy data)
2. Demand Forecasting (Prophet + PyTorch LSTM fallback)
3. 4-Vector Anomaly Detection Engine (Underpricing, Volume Drop, Stock Depletion, Scheme Deadlines)
4. Alert generation & Severity Scoring
5. Tally XML Parsing (Sales vouchers + Stock summary)
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from services.csv_pipeline import run_pipeline, generate_cleaned_csv
from models.schemas import DataSource
from models.forecast_model import ForecastModel
from agents.anomaly_agent import run_all_anomaly_checks
from routers.tally import parse_vouchers, parse_stock


def test_csv_pipeline():
    print("\n--- 1. Testing CSV Pipeline (Messy Ledger with Hindi Headers) ---")
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "priya_kirana_messy_ledger.csv")
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    gen = run_pipeline(file_bytes, "biz-test-001", DataSource.CSV)
    steps = []
    final_result = None
    try:
        while True:
            step = next(gen)
            steps.append(step)
    except StopIteration as e:
        final_result = e.value

    print(f"✅ Pipeline executed {len(steps)} steps successfully.")
    print(f"   - Total rows: {final_result.get('rows_total')}")
    print(f"   - Cleaned rows: {final_result.get('rows_cleaned')}")
    print(f"   - Flagged rows: {final_result.get('rows_flagged')}")
    
    cleaned_bytes = generate_cleaned_csv(final_result.get("transactions", []))
    print(f"   - Generated cleaned CSV: {len(cleaned_bytes)} bytes")
    assert len(final_result.get("transactions", [])) > 0, "No transactions generated!"


def test_forecast_model():
    print("\n--- 2. Testing Demand Forecasting Engine ---")
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "ramesh_vegetable_stall_clean.csv")
    df = pd.read_csv(file_path)
    txns = [{"date": r["Date"], "quantity": r["Quantity"]} for _, r in df.iterrows()]
    
    model = ForecastModel()
    pred = model.predict(txns, days_ahead=7)
    print(f"✅ Forecast generated using model: {pred.get('model')}")
    print(f"   - 7-day predicted demand: {pred.get('predicted_demand_7d')} units")
    print(f"   - Daily predictions: {pred.get('daily_predictions')}")
    print(f"   - Confidence score: {pred.get('confidence')}")
    assert pred.get("predicted_demand_7d") > 0, "Predicted demand must be positive!"


import asyncio

async def test_anomaly_detection():
    print("\n--- 3. Testing 4-Vector Anomaly Detection Engine ---")
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "anomaly_demo_underpricing.csv")
    df = pd.read_csv(file_path)
    # Canonicalize column names for anomaly agent
    txns = []
    for _, r in df.iterrows():
        txns.append({
            "date": r["Date"],
            "item_name": r["Item Name"],
            "category": r["Category"],
            "quantity": r["Quantity"],
            "selling_price_per_unit": r["Selling Price"],
            "total_amount": r["Total Amount"],
            "transaction_type": r["Transaction Type"],
        })

    # Underpricing check: Onion sold at ₹12 vs market modal price ₹18
    market_prices = [
        {"commodity": "Onion", "modal_price": 18.0, "state": "Maharashtra", "market_name": "Lasalgaon"}
    ]
    
    inventory = [
        {"item_name": "Tomato", "current_stock": 10.0, "reorder_level": 25.0, "unit": "kg"}
    ]
    
    forecasts = [
        {"item_name": "Tomato", "predicted_demand_7d": 150.0}
    ]
    
    schemes = [
        {"scheme_name": "PM SVANidhi 3rd Tranche", "days_remaining": 4, "deadline": "2026-09-08"}
    ]
    
    rules = {
        "underpricing_threshold_pct": 15.0,
        "sales_zscore_threshold": 2.0,
        "stock_depletion_days": 7,
        "scheme_deadline_days": 7,
    }

    anomalies = await run_all_anomaly_checks(txns, inventory, market_prices, forecasts, schemes, rules)
    print(f"✅ Anomaly Engine detected {len(anomalies)} real actionable anomalies:")
    for a in anomalies:
        atype = a.get("alert_type")
        sev = a.get("severity", "medium").upper()
        item = a.get("item_name", a.get("scheme_name", "General"))
        print(f"   [{sev}] {atype} for '{item}' (details: {a})")
    assert len(anomalies) >= 2, "Expected at least underpricing and stock/scheme anomalies!"


def test_tally_parser():
    print("\n--- 4. Testing Real Tally Prime XML Parsers ---")
    vouchers_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "tally_export_vouchers.xml")
    with open(vouchers_path, "r", encoding="utf-8") as f:
        vouchers_xml = f.read()
    txns = parse_vouchers(vouchers_xml)
    print(f"✅ Parsed {len(txns)} transactions from Tally voucher export XML")
    
    stock_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "tally_export_stock.xml")
    with open(stock_path, "r", encoding="utf-8") as f:
        stock_xml = f.read()
    stock = parse_stock(stock_xml)
    print(f"✅ Parsed {len(stock)} inventory items from Tally stock summary XML")
    assert len(txns) > 0, "Tally voucher parsing returned 0 transactions!"
    assert len(stock) > 0, "Tally stock parsing returned 0 items!"


if __name__ == "__main__":
    print("=" * 65)
    print("🚀 BIZPANION LOCAL END-TO-END VERIFICATION SUITE")
    print("=" * 65)
    test_csv_pipeline()
    test_forecast_model()
    asyncio.run(test_anomaly_detection())
    test_tally_parser()
    print("\n" + "=" * 65)
    print("🎉 ALL SYSTEMS TESTED AND VERIFIED SUCCESSFULLY!")
    print("=" * 65)
