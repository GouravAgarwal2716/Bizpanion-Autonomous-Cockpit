"""
Pydantic schemas for all API request/response models.
"""
from __future__ import annotations
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MARATHI = "mr"
    BENGALI = "bn"
    GUJARATI = "gu"


class BusinessType(str, Enum):
    VEGETABLE_VENDOR = "vegetable_vendor"
    GROCERY_STORE = "grocery_store"
    KIRANA_SHOP = "kirana_shop"
    DAIRY_FARMER = "dairy_farmer"
    HANDICRAFT = "handicraft"
    TEXTILE = "textile"
    HARDWARE = "hardware"
    FOOD_PROCESSING = "food_processing"
    OTHER = "other"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertType(str, Enum):
    UNDERPRICING = "underpricing"
    STOCK_DEPLETION = "stock_depletion"
    SCHEME_DEADLINE = "scheme_deadline"
    SALES_ANOMALY = "sales_anomaly"


class DataSource(str, Enum):
    CSV = "csv"
    TALLY = "tally"
    PHOTO_OCR = "photo_ocr"


# ─── Business Profile ─────────────────────────────────────────────────────────

class BusinessProfileCreate(BaseModel):
    user_id: str
    business_name: str
    business_type: BusinessType
    region: str                       # district/state e.g. "Nashik, Maharashtra"
    language: Language = Language.ENGLISH
    whatsapp_number: str              # E.164 format: +91XXXXXXXXXX
    alert_sensitivity: AlertSeverity = AlertSeverity.HIGH  # minimum severity to WhatsApp

class BusinessProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[BusinessType] = None
    region: Optional[str] = None
    language: Optional[Language] = None
    whatsapp_number: Optional[str] = None
    alert_sensitivity: Optional[AlertSeverity] = None

class BusinessProfile(BusinessProfileCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Transactions ──────────────────────────────────────────────────────────────

class Transaction(BaseModel):
    id: Optional[str] = None
    business_id: str
    date: datetime
    item_name: str
    category: str
    quantity: float
    unit: str
    selling_price_per_unit: float
    total_amount: float
    transaction_type: str             # "sale" | "purchase" | "expense"
    source: DataSource
    raw_row_index: Optional[int] = None
    flagged: bool = False
    flag_reason: Optional[str] = None


# ─── Inventory ────────────────────────────────────────────────────────────────

class InventoryItem(BaseModel):
    id: Optional[str] = None
    business_id: str
    item_name: str
    category: str
    current_stock: float
    unit: str
    reorder_level: float
    last_updated: datetime


# ─── Market Prices ────────────────────────────────────────────────────────────

class MarketPrice(BaseModel):
    id: Optional[str] = None
    commodity: str
    variety: str
    market_name: str
    state: str
    district: str
    min_price: float
    max_price: float
    modal_price: float
    date: datetime
    source: str = "agmarknet"


# ─── Alerts ───────────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    business_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str                      # in user's language
    message_en: str                   # always stored in English too
    data_snapshot: Dict[str, Any]     # the numbers that triggered this
    recommended_action: str
    recommended_action_en: str
    whatsapp_sent: bool = False
    audio_url: Optional[str] = None

class Alert(AlertCreate):
    id: str
    created_at: datetime
    acknowledged: bool = False

    class Config:
        from_attributes = True


# ─── Pipeline Status ──────────────────────────────────────────────────────────

class PipelineStep(BaseModel):
    step: str
    status: str                       # "pending" | "running" | "done" | "error"
    message: str
    detail: Optional[str] = None

class PipelineResult(BaseModel):
    upload_id: str
    source: DataSource
    steps: List[PipelineStep]
    rows_total: int = 0
    rows_cleaned: int = 0
    rows_flagged: int = 0
    cleaned_csv_url: Optional[str] = None
    error: Optional[str] = None


# ─── Voice / TTS ──────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    language: Language
    cache_key: Optional[str] = None   # if set, cache and reuse audio


class TTSResponse(BaseModel):
    audio_url: str
    language: Language
    duration_seconds: Optional[float] = None


# ─── Forecast ────────────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    business_id: str
    item_name: str
    days_ahead: int = 7

class ForecastResponse(BaseModel):
    item_name: str
    current_stock: float
    predicted_demand_7d: float
    stockout_risk: bool
    stockout_date: Optional[datetime] = None
    confidence: float


# ─── Agent Pipeline ───────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    business_id: str
    trigger: str = "new_data"         # "new_data" | "scheduled" | "manual"

class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    alerts_generated: int
    whatsapp_sent: int
    duration_seconds: float
