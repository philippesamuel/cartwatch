from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_name: str
    short_name: str
    quantity: float
    unit: str  # kg, L, piece, m — must match units seed data
    unit_price: float  # price per SI unit
    total_price: float
    discount: float | None = None
    tax_rate: float | None = None  # 0.07 or 0.19


class ExtractedReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    store_name: str
    store_address: str | None = None
    store_city: str | None = None
    purchased_at: datetime
    currency: str = "EUR"
    subtotal: float | None = None
    tax_total: float | None = None
    total: float
    payment_method: str | None = None
    line_items: list[ExtractedLineItem]
