"""
CSV Pipeline: Profiler → Cleaner → Validator
Processes raw uploaded CSV data into clean, typed records for Supabase.
Emits live progress steps (yielded as server-sent events by the router).
"""
import pandas as pd
import numpy as np
import re
import uuid
from datetime import datetime, date
from io import StringIO, BytesIO
from typing import Generator, AsyncGenerator
from models.schemas import DataSource, PipelineStep


# ─── Known column name aliases (maps raw headers → canonical names) ──────────
COLUMN_ALIASES = {
    # Date
    "date": "date", "transaction date": "date", "bill date": "date",
    "invoice date": "date", "dt": "date", "दिनांक": "date",
    # Item
    "item": "item_name", "item name": "item_name", "product": "item_name",
    "commodity": "item_name", "goods": "item_name", "वस्तु": "item_name",
    "பொருள்": "item_name", "వస్తువు": "item_name",
    # Quantity
    "qty": "quantity", "quantity": "quantity", "units": "quantity",
    "amount (kg)": "quantity", "मात्रा": "quantity",
    # Unit
    "unit": "unit", "uom": "unit", "measure": "unit",
    # Price
    "price": "selling_price_per_unit", "rate": "selling_price_per_unit",
    "selling price": "selling_price_per_unit", "unit price": "selling_price_per_unit",
    "price/kg": "selling_price_per_unit", "मूल्य": "selling_price_per_unit",
    # Total
    "total": "total_amount", "total amount": "total_amount",
    "amount": "total_amount", "value": "total_amount", "कुल": "total_amount",
    # Category
    "category": "category", "type": "category", "group": "category",
    "श्रेणी": "category",
    # Transaction type
    "transaction type": "transaction_type", "txn type": "transaction_type",
    "type": "transaction_type",
}

CATEGORY_INFER_RULES = {
    r"(onion|tomato|potato|carrot|garlic|ginger|spinach|cabbage|cauliflower|brinjal|bean|pea|chilli|coriander|mint|vegetable|sabzi|bhaji)": "vegetables",
    r"(rice|wheat|dal|pulse|lentil|maize|jowar|bajra|grain|flour|atta|besan|maida|चावल|गेहूं|दाल)": "grains_pulses",
    r"(milk|curd|paneer|ghee|butter|cheese|dairy|दूध|पनीर|மோர்)": "dairy",
    r"(saree|shirt|cotton|silk|fabric|garment|kurti|denim|jeans|tshirt|cloth|textile|linen|suit|dress|shorts)": "textiles",
    r"(mobile|phone|charger|cable|earphones|screen|battery|laptop|repair|switch|board|bulb|wire|electronics)": "electronics",
    r"(cement|steel|paint|pipe|rod|iron|hardware|tool|screw|nail|hammer|wrench|plywood)": "hardware",
    r"(oil|soap|detergent|shampoo|toothpaste|cosmetic|personal care|biscuit|tea|coffee|snack|fmcg|kirana)": "fmcg",
    r"(sugar|jaggery|salt|spice|masala|turmeric|cumin|pepper|chana|namak|गुड़)": "spices_staples",
    r"(expense|rent|electricity|water|labour|transport|miscellaneous|खर्च)": "expenses",
}


def infer_category(item_name: str) -> str:
    item_lower = str(item_name).lower()
    for pattern, category in CATEGORY_INFER_RULES.items():
        if re.search(pattern, item_lower, re.IGNORECASE):
            return category
    return "other"


def parse_date_flexible(val) -> datetime | None:
    if pd.isna(val):
        return None
    val = str(val).strip()
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%b-%Y", "%d %b %Y", "%B %d, %Y", "%d.%m.%Y",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(val, dayfirst=True).to_pydatetime()
    except Exception:
        return None


def normalize_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Map raw column headers to canonical names. Returns renamed df and list of detected issues."""
    issues = []
    rename_map = {}
    original_cols = [c.lower().strip() for c in df.columns]
    
    for orig_col, orig_col_lower in zip(df.columns, original_cols):
        if orig_col_lower in COLUMN_ALIASES:
            rename_map[orig_col] = COLUMN_ALIASES[orig_col_lower]
        else:
            issues.append(f"Unknown column '{orig_col}' — keeping as-is")
    
    return df.rename(columns=rename_map), issues


def run_pipeline(
    file_bytes: bytes,
    business_id: str,
    source: DataSource = DataSource.CSV,
) -> Generator[PipelineStep, None, dict]:
    """
    Synchronous generator that yields PipelineStep progress events.
    Final return value (via StopIteration.value) is the pipeline result dict.
    """
    results = {
        "rows_total": 0,
        "rows_cleaned": 0,
        "rows_flagged": 0,
        "transactions": [],
        "inventory_updates": [],
        "errors": [],
    }

    # ── STEP 1: Load ──────────────────────────────────────────────────────────
    yield PipelineStep(step="load", status="running", message="Reading CSV file...")
    try:
        df = pd.read_csv(BytesIO(file_bytes), encoding="utf-8", on_bad_lines="skip")
        if df.empty:
            # try latin-1
            df = pd.read_csv(BytesIO(file_bytes), encoding="latin-1", on_bad_lines="skip")
        results["rows_total"] = len(df)
        yield PipelineStep(
            step="load", status="done",
            message=f"Loaded {len(df)} rows, {len(df.columns)} columns",
            detail=f"Columns detected: {', '.join(df.columns.tolist()[:8])}"
        )
    except Exception as e:
        yield PipelineStep(step="load", status="error", message=f"Failed to read CSV: {e}")
        return results

    # ── STEP 2: Profile ───────────────────────────────────────────────────────
    yield PipelineStep(step="profile", status="running", message="Profiling column types and data quality...")
    df, col_issues = normalize_column_names(df)
    
    null_report = df.isnull().sum()
    high_null_cols = [col for col in df.columns if null_report[col] > len(df) * 0.5]
    date_cols_raw = [c for c in df.columns if "date" in c.lower() or c == "date"]
    
    detail = f"Mapped {len(df.columns)} columns. High-null columns: {high_null_cols or 'none'}. Issues: {col_issues[:3] or 'none'}"
    yield PipelineStep(step="profile", status="done", message="Profile complete", detail=detail)

    # ── STEP 3: Clean ─────────────────────────────────────────────────────────
    yield PipelineStep(step="clean", status="running", message="Cleaning data — fixing dates, nulls, types, encoding...")
    
    date_formats_found = set()
    
    # Parse dates
    if "date" in df.columns:
        def _parse_date(v):
            parsed = parse_date_flexible(v)
            if parsed is None:
                return None
            # detect what format was used
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    datetime.strptime(str(v).strip(), fmt)
                    date_formats_found.add(fmt)
                except:
                    pass
            return parsed
        df["date"] = df["date"].apply(_parse_date)

    # Clean numeric columns
    for col in ["quantity", "selling_price_per_unit", "total_amount"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[₹$,\s]", "", regex=True)
                .str.replace(r"[^\d.]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill missing unit
    if "unit" not in df.columns:
        df["unit"] = "kg"
    df["unit"] = df["unit"].fillna("kg").str.lower().str.strip()

    # Fill missing category via inference
    if "category" not in df.columns:
        df["category"] = df.get("item_name", pd.Series(["other"] * len(df))).apply(infer_category)
    else:
        df["category"] = df.apply(
            lambda r: infer_category(r.get("item_name", "")) if pd.isna(r["category"]) else r["category"],
            axis=1,
        )

    # Infer total if missing
    if "total_amount" not in df.columns:
        if "quantity" in df.columns and "selling_price_per_unit" in df.columns:
            df["total_amount"] = df["quantity"] * df["selling_price_per_unit"]

    # Infer selling price if missing
    if "selling_price_per_unit" not in df.columns:
        if "quantity" in df.columns and "total_amount" in df.columns:
            df["selling_price_per_unit"] = df["total_amount"] / df["quantity"].replace(0, np.nan)

    # Default transaction type and canonical normalization
    if "transaction_type" not in df.columns:
        df["transaction_type"] = "sale"
    else:
        df["transaction_type"] = df["transaction_type"].fillna("sale").astype(str).str.lower().str.strip()
        df["transaction_type"] = df["transaction_type"].apply(
            lambda x: "sale" if x in ["sales", "sale", "sell", "sold", "credit", "income", "bill", "invoice", "cr"]
            else ("expense" if x in ["expense", "expenses", "purchase", "purchases", "buy", "debit", "cost", "dr"] else x)
        )

    yield PipelineStep(
        step="clean", status="done",
        message=f"Cleaning done. Found {len(date_formats_found)} date formats, normalized all.",
        detail=f"Date formats: {list(date_formats_found) or ['consistent']}"
    )

    # ── STEP 4: Validate ──────────────────────────────────────────────────────
    yield PipelineStep(step="validate", status="running", message="Validating rows and flagging anomalies...")
    
    flagged_rows = []
    valid_rows = []
    
    for idx, row in df.iterrows():
        flags = []
        
        # Missing critical fields
        if pd.isna(row.get("date")):
            flags.append("Missing/unparseable date")
        if pd.isna(row.get("item_name", None)) or str(row.get("item_name", "")).strip() == "":
            flags.append("Missing item name")
        if pd.isna(row.get("quantity", None)) or row.get("quantity", 0) <= 0:
            flags.append("Invalid quantity")
        if pd.isna(row.get("selling_price_per_unit", None)) or row.get("selling_price_per_unit", 0) < 0:
            flags.append("Invalid price")

        row_dict = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "date": row.get("date", datetime.now()).isoformat() if not pd.isna(row.get("date", None)) else datetime.now().isoformat(),
            "item_name": str(row.get("item_name", "Unknown")).strip(),
            "category": str(row.get("category", "other")),
            "quantity": float(row.get("quantity", 0) or 0),
            "unit": str(row.get("unit", "kg")),
            "selling_price_per_unit": float(row.get("selling_price_per_unit", 0) or 0),
            "total_amount": float(row.get("total_amount", 0) or 0),
            "transaction_type": str(row.get("transaction_type", "sale")),
            "source": source.value,
            "raw_row_index": int(idx),
            "flagged": len(flags) > 0,
            "flag_reason": "; ".join(flags) if flags else None,
        }

        if flags:
            flagged_rows.append(row_dict)
        else:
            valid_rows.append(row_dict)

    results["rows_cleaned"] = len(valid_rows)
    results["rows_flagged"] = len(flagged_rows)
    results["transactions"] = valid_rows + flagged_rows  # insert all, just flagged ones are marked

    yield PipelineStep(
        step="validate", status="done",
        message=f"Validation complete: {len(valid_rows)} clean, {len(flagged_rows)} flagged",
        detail=f"Flagged rows will be visible in Reports for manual review"
    )

    # ── STEP 5: Write to Supabase (handled by router) ─────────────────────────
    yield PipelineStep(
        step="write", status="done",
        message=f"Ready to write {len(valid_rows) + len(flagged_rows)} rows to database",
    )

    return results


def generate_cleaned_csv(transactions: list[dict]) -> bytes:
    """Convert cleaned transaction dicts back to CSV bytes for download."""
    df = pd.DataFrame(transactions)
    cols = ["date", "item_name", "category", "quantity", "unit",
            "selling_price_per_unit", "total_amount", "transaction_type", "flagged", "flag_reason"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].to_csv(index=False).encode("utf-8")
