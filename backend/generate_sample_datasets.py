"""
Generate 5 authentic multi-sector datasets for instant demo loading.
Sectors: Kirana/Grocery, Dairy/Livestock, Textile/Apparel, Hardware/Electrical, Vegetable/Produce.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
out_dir = Path("sample_data")
out_dir.mkdir(exist_ok=True)

today = datetime(2026, 9, 4)

SECTOR_CONFIGS = {
    "kirana": {
        "filename": "kirana_grocery_sales.csv",
        "items": [
            ("Aashirvaad Atta 5kg", "groceries", "bag", 230, 260, (2, 8)),
            ("Fortune Sunflower Oil 1L", "groceries", "pouch", 125, 145, (3, 12)),
            ("Tata Salt 1kg", "groceries", "pouch", 22, 28, (4, 15)),
            ("Toor Dal 1kg", "groceries", "kg", 135, 160, (2, 10)),
            ("Maggi 70g Noodles", "groceries", "packet", 11, 14, (10, 40)),
            ("Surf Excel 1kg", "groceries", "pouch", 118, 138, (2, 6)),
            ("Tata Tea Premium 500g", "groceries", "box", 240, 275, (1, 5)),
            ("MDH Garam Masala 100g", "groceries", "box", 82, 98, (2, 8)),
            ("Basmati Rice 5kg", "groceries", "bag", 380, 440, (1, 4)),
            ("Sugar M-Grade 1kg", "groceries", "kg", 39, 44, (3, 15)),
        ]
    },
    "dairy": {
        "filename": "dairy_farm_sales.csv",
        "items": [
            ("Fresh Buffalo Milk", "dairy", "litre", 58, 68, (15, 60)),
            ("Pure Cow Milk", "dairy", "litre", 44, 52, (20, 80)),
            ("Malai Paneer Fresh", "dairy", "kg", 310, 370, (2, 10)),
            ("Desi Cow Ghee 1L", "dairy", "jar", 540, 650, (1, 5)),
            ("Fresh Curd / Dahi 500g", "dairy", "tub", 32, 40, (5, 25)),
            ("Khoya / Mawa Fresh", "dairy", "kg", 260, 320, (1, 6)),
            ("Cattle Feed SuperMash 50kg", "dairy", "bag", 1250, 1400, (1, 3)),
            ("Amul Butter 500g", "dairy", "pack", 235, 275, (2, 8)),
        ]
    },
    "textile": {
        "filename": "textile_garments_sales.csv",
        "items": [
            ("Pure Cotton Printed Saree", "textile", "piece", 420, 580, (1, 6)),
            ("Men Stretch Denim Jeans", "textile", "piece", 550, 780, (2, 8)),
            ("Formal Cotton Shirt", "textile", "piece", 360, 520, (2, 7)),
            ("Silk Jacquard Fabric", "textile", "metre", 180, 260, (5, 20)),
            ("Women Rayon Kurti", "textile", "piece", 280, 420, (3, 10)),
            ("Cotton Bed Sheet Double", "textile", "set", 390, 560, (1, 4)),
            ("Polyester Lining Fabric", "textile", "metre", 38, 55, (10, 40)),
            ("Kids Denim Shorts", "textile", "piece", 210, 320, (2, 6)),
        ]
    },
    "hardware": {
        "filename": "hardware_electrical_sales.csv",
        "items": [
            ("TMT Steel Rebar 12mm", "hardware", "kg", 54, 64, (25, 120)),
            ("Havells 2.5mm Copper Wire 90m", "hardware", "coil", 1850, 2200, (1, 4)),
            ("UltraTech Super Cement 50kg", "hardware", "bag", 340, 385, (5, 30)),
            ("Astral PVC Pipe 4-inch 10ft", "hardware", "length", 290, 360, (2, 10)),
            ("Asian Paints Apex Ultima 20L", "hardware", "bucket", 3800, 4450, (1, 3)),
            ("GI Binding Wire 1kg", "hardware", "roll", 72, 90, (4, 15)),
            ("Brass Ball Valve 1-inch", "hardware", "piece", 210, 270, (2, 8)),
            ("Anchor Modular Switch 6A", "hardware", "box", 240, 310, (1, 5)),
        ]
    },
    "vegetables": {
        "filename": "vegetable_vendor_sales.csv",
        "items": [
            ("Hybrid Red Tomatoes", "vegetables", "kg", 18, 26, (10, 50)),
            ("Cold-Storage Agra Potato", "vegetables", "kg", 16, 22, (15, 60)),
            ("Nashik Red Onion", "vegetables", "kg", 24, 32, (12, 55)),
            ("Fresh Green Chillies", "vegetables", "kg", 38, 55, (2, 12)),
            ("Fresh Cauliflower", "vegetables", "piece", 18, 28, (5, 20)),
            ("Lady Finger / Bhindi", "vegetables", "kg", 28, 42, (3, 15)),
            ("Green Peas / Matar", "vegetables", "kg", 45, 65, (4, 18)),
            ("Fresh Ginger / Adrak", "vegetables", "kg", 75, 110, (1, 6)),
        ]
    }
}

def generate_csvs():
    for sector_key, conf in SECTOR_CONFIGS.items():
        file_path = out_dir / conf["filename"]
        rows = []
        
        # 120 transactions spanning 45 days up to today
        for i in range(120):
            days_ago = random.randint(0, 44)
            tx_date = today - timedelta(days=days_ago, hours=random.randint(8, 20), minutes=random.randint(0, 59))
            date_str = tx_date.strftime("%Y-%m-%d %H:%M:%S")

            item_info = random.choice(conf["items"])
            name, cat, unit, buy_price, sell_price, qty_range = item_info
            
            # 85% sales, 15% purchases
            is_purchase = random.random() < 0.15
            ttype = "purchase" if is_purchase else "sales"
            
            qty = random.randint(qty_range[0], qty_range[1])
            if is_purchase:
                qty = qty * random.randint(3, 8)
                rate = buy_price
            else:
                # Add slight price fluctuation
                rate = sell_price + random.choice([-2, -1, 0, 1, 2, 3])
            
            amt = round(qty * rate, 2)
            
            rows.append({
                "date": date_str,
                "item_name": name,
                "category": cat,
                "quantity": qty,
                "unit": unit,
                "selling_price_per_unit": rate,
                "total_amount": amt,
                "transaction_type": ttype,
            })
            
        rows.sort(key=lambda x: x["date"])
        
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "date", "item_name", "category", "quantity", "unit", 
                "selling_price_per_unit", "total_amount", "transaction_type"
            ])
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"[SUCCESS] Generated {file_path} with {len(rows)} records")

if __name__ == "__main__":
    generate_csvs()
