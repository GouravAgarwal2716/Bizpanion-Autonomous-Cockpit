"""
Generate synthetic test CSV files that demonstrate the pipeline's cleaning capabilities.
Creates 3 CSVs: clean data, messy data, and a mixed edge-case file.
Run: python generate_test_data.py
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def rand_date(days_back=90):
    """Random date within last N days."""
    return (datetime.now() - timedelta(days=random.randint(0, days_back))).date()


ITEMS = [
    ("Onion", "vegetables", "kg", 18.0),
    ("Tomato", "vegetables", "kg", 20.0),
    ("Potato", "vegetables", "kg", 12.0),
    ("Garlic", "vegetables", "kg", 120.0),
    ("Green Chilli", "vegetables", "kg", 40.0),
    ("Cauliflower", "vegetables", "nos", 25.0),
    ("Wheat Flour", "grains_pulses", "kg", 28.0),
    ("Rice", "grains_pulses", "kg", 38.0),
    ("Moong Dal", "grains_pulses", "kg", 95.0),
    ("Tur Dal", "grains_pulses", "kg", 110.0),
    ("Groundnut Oil", "fmcg", "litre", 145.0),
    ("Sugar", "spices_staples", "kg", 42.0),
    ("Salt", "spices_staples", "kg", 18.0),
    ("Turmeric Powder", "spices_staples", "kg", 180.0),
    ("Cumin", "spices_staples", "kg", 350.0),
    ("Milk", "dairy", "litre", 52.0),
    ("Banana", "vegetables", "dozen", 30.0),
]


# ── FILE 1: Clean, well-formatted CSV (Ramesh Vegetable Stall) ──────────────

def make_clean_csv():
    rows = []
    for _ in range(200):
        item, category, unit, base_price = random.choice(ITEMS)
        qty = round(random.uniform(2, 50), 2)
        price = round(base_price * random.uniform(0.85, 1.1), 2)
        total = round(qty * price, 2)
        rows.append({
            "Date": rand_date().strftime("%Y-%m-%d"),
            "Item Name": item,
            "Category": category,
            "Quantity": qty,
            "Unit": unit,
            "Selling Price": price,
            "Total Amount": total,
            "Transaction Type": random.choices(["sale", "purchase"], weights=[0.75, 0.25])[0],
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "ramesh_vegetable_stall_clean.csv")
    df.to_csv(path, index=False)
    print(f"✅ Created: {path} ({len(df)} rows)")


# ── FILE 2: Messy real-world CSV (handwritten ledger digitization) ────────────

def make_messy_csv():
    rows = []
    date_formats = [
        lambda d: d.strftime("%d-%m-%Y"),
        lambda d: d.strftime("%d/%m/%Y"),
        lambda d: d.strftime("%Y%m%d"),
        lambda d: d.strftime("%d %b %Y"),
        lambda d: d.strftime("%B %d, %Y"),
    ]
    
    for i in range(300):
        item, category, unit, base_price = random.choice(ITEMS)
        qty = round(random.uniform(1, 100), 2)
        
        # Various messy price formats
        price = base_price * random.uniform(0.7, 1.15)
        price_str_options = [
            f"Rs.{price:.2f}",
            f"₹{price:.0f}",
            f"{price:.2f}",
            f"{price:.1f}",
            f"  {price:.2f}  ",
        ]
        price_str = random.choice(price_str_options)
        
        total = qty * price
        total_str_options = [
            f"₹{total:.2f}",
            f"{total:.0f}",
            f"{total:,.2f}",
            None,  # missing — to be computed
        ]
        total_str = random.choice(total_str_options)
        
        d = rand_date(180)
        date_str = random.choice(date_formats)(d)
        
        row = {
            "दिनांक": date_str,          # Hindi column name
            "वस्तु": item,               # Hindi item name
            "मात्रा": qty,
            "Unit": unit,
            "मूल्य": price_str,
            "कुल": total_str,
        }
        
        # Inject 5% completely missing rows
        if random.random() < 0.05:
            row["वस्तु"] = None
        if random.random() < 0.03:
            row["मात्रा"] = "N/A"
        
        rows.append(row)
    
    # Add a few duplicate rows
    rows.extend(rows[:5])
    
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "priya_kirana_messy_ledger.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")  # BOM for Excel compatibility
    print(f"✅ Created: {path} ({len(df)} rows, intentionally messy)")


# ── FILE 3: Sales anomaly demo CSV (sudden price drop to trigger anomaly) ────

def make_anomaly_demo_csv():
    """
    This CSV has a 35-day history of onion sales at normal price (₹18/kg),
    then the last 5 days at ₹12/kg (33% below Lasalgaon market rate of ₹18/kg).
    This will trigger the underpricing anomaly detection.
    Also has a sales volume drop in the last 3 days to trigger sales anomaly.
    """
    rows = []
    today = datetime.now().date()
    
    # 45 days of normal data
    for days_ago in range(45, 5, -1):
        d = today - timedelta(days=days_ago)
        qty = round(random.uniform(40, 80), 0)
        price = round(random.uniform(16, 20), 2)  # normal range
        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Item Name": "Onion",
            "Category": "vegetables",
            "Quantity": qty,
            "Unit": "kg",
            "Selling Price": price,
            "Total Amount": round(qty * price, 2),
            "Transaction Type": "sale",
        })
        # Also add Tomato
        qty2 = round(random.uniform(20, 50), 0)
        price2 = round(random.uniform(18, 22), 2)
        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Item Name": "Tomato",
            "Category": "vegetables",
            "Quantity": qty2,
            "Unit": "kg",
            "Selling Price": price2,
            "Total Amount": round(qty2 * price2, 2),
            "Transaction Type": "sale",
        })
    
    # Last 5 days: UNDERPRICING — selling onion at ₹12 when market is ₹18+
    for days_ago in range(5, 0, -1):
        d = today - timedelta(days=days_ago)
        qty = round(random.uniform(20, 30), 0)  # also lower volume = sales drop
        price = 12.0  # INTENTIONALLY LOW
        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Item Name": "Onion",
            "Category": "vegetables",
            "Quantity": qty,
            "Unit": "kg",
            "Selling Price": price,
            "Total Amount": round(qty * price, 2),
            "Transaction Type": "sale",
        })

    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "anomaly_demo_underpricing.csv")
    df.to_csv(path, index=False)
    print(f"✅ Created: {path} ({len(df)} rows — will trigger underpricing + sales anomaly alerts)")


# ── FILE 4: Stock depletion demo ─────────────────────────────────────────────

def make_stock_demo_csv():
    """High-velocity sales consuming stock faster than usual."""
    rows = []
    today = datetime.now().date()
    
    # 30 days of normal daily sales + inventory CSV
    for days_ago in range(30, 0, -1):
        d = today - timedelta(days=days_ago)
        # High demand period (festival season effect)
        multiplier = 3.0 if days_ago < 5 else 1.0
        for item, cat, unit, price in ITEMS[:6]:
            qty = round(random.uniform(10, 30) * multiplier, 1)
            rows.append({
                "Date": d.strftime("%d/%m/%Y"),
                "Item Name": item,
                "Category": cat,
                "Quantity": qty,
                "Unit": unit,
                "Selling Price": price,
                "Total Amount": round(qty * price, 2),
                "Transaction Type": "sale",
            })

    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "festival_season_high_demand.csv")
    df.to_csv(path, index=False)
    print(f"✅ Created: {path} ({len(df)} rows — festival demand spike)")


# ── Tally XML synthetic data ──────────────────────────────────────────────────

TALLY_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <DATA>
      <TALLYMESSAGE xmlns:UDF="TallyUDF">
        {vouchers}
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
"""

VOUCHER_TEMPLATE = """
<VOUCHER REMOTEID="{vid}" VCHTYPE="Sales" ACTION="Create">
  <DATE>{date}</DATE>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{num}</VOUCHERNUMBER>
  <PARTYLEDGERNAME>Cash</PARTYLEDGERNAME>
  <INVENTORYENTRIES.LIST>
    <STOCKITEMNAME>{item}</STOCKITEMNAME>
    <ACTUALQTY>{qty} {unit}</ACTUALQTY>
    <RATE>{price}/{unit}</RATE>
    <AMOUNT>{amount}</AMOUNT>
  </INVENTORYENTRIES.LIST>
</VOUCHER>
"""

STOCK_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <TALLYMESSAGE>
        {items}
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
"""

STOCK_ITEM_TEMPLATE = """
<STOCKITEM NAME="{name}">
  <NAME>{name}</NAME>
  <CLOSINGBALANCE>{qty} {unit}</CLOSINGBALANCE>
</STOCKITEM>
"""


def make_tally_xml():
    vouchers = []
    today = datetime.now().date()
    
    for i in range(1, 51):
        d = today - timedelta(days=random.randint(0, 30))
        item, cat, unit, price = random.choice(ITEMS[:10])
        qty = round(random.uniform(5, 50), 2)
        amount = round(qty * price, 2)
        vouchers.append(VOUCHER_TEMPLATE.format(
            vid=f"VCH{i:04d}",
            date=d.strftime("%Y%m%d"),
            num=f"S{i:04d}",
            item=item,
            qty=qty,
            unit=unit,
            price=price,
            amount=amount,
        ))
    
    xml_content = TALLY_XML_TEMPLATE.format(vouchers="".join(vouchers))
    path = os.path.join(OUTPUT_DIR, "tally_export_vouchers.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    # Stock XML
    stock_items = []
    for item, cat, unit, _ in ITEMS:
        qty = round(random.uniform(20, 200), 2)
        stock_items.append(STOCK_ITEM_TEMPLATE.format(name=item, qty=qty, unit=unit))
    
    stock_xml = STOCK_XML_TEMPLATE.format(items="".join(stock_items))
    stock_path = os.path.join(OUTPUT_DIR, "tally_export_stock.xml")
    with open(stock_path, "w", encoding="utf-8") as f:
        f.write(stock_xml)
    
    print(f"✅ Created: {path} (50 vouchers)")
    print(f"✅ Created: {stock_path} ({len(ITEMS)} stock items)")


if __name__ == "__main__":
    make_clean_csv()
    make_messy_csv()
    make_anomaly_demo_csv()
    make_stock_demo_csv()
    make_tally_xml()
    print("\n✅ All test data files generated in ./test_data/")
    print("\nUse for demo:")
    print("  1. Upload 'priya_kirana_messy_ledger.csv' → shows cleaning pipeline")
    print("  2. Upload 'anomaly_demo_underpricing.csv' → triggers WhatsApp alert")
    print("  3. Import 'tally_export_vouchers.xml' → shows Tally integration")
