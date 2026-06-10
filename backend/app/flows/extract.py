import io
from typing import Generator, Iterable, overload

import pdfplumber
from prefect import flow, get_run_logger, task

from app.core.supabase import get_supabase
from app.ingestion.receipts.extractor import extract_receipt
from app.ingestion.receipts.models import ExtractedReceipt


@task
async def fetch_unprocessed_sources() -> list[dict]:
    supabase = get_supabase()
    result = (
        supabase.table("receipt_sources")
        .select("*")
        .is_("receipt_id", "null")
        .execute()
    )
    return result.data


@task
async def extract_and_store(source: dict) -> str | None:
    logger = get_run_logger()
    supabase = get_supabase()

    try:
        pdf_urls = source.get("pdf_urls") or []
        extracted = await extract_receipt(
            text=source.get("raw_text"),
            html=source.get("raw_html"),
            pdf_text=get_pdf_text_from_object_storage(pdf_urls)
        )
    except Exception as e:
        logger.error(f"Extraction failed for source {source['id']}: {e}")
        return None

    # resolve store
    store_id = _resolve_store(supabase, extracted, source["user_id"])

    # insert receipt
    receipt = (
        supabase.table("receipts")
        .insert({
            "user_id": source["user_id"],
            "store_id": store_id,
            "purchased_at": extracted.purchased_at.isoformat(),
            "currency": extracted.currency,
            "subtotal": extracted.subtotal,
            "tax_total": extracted.tax_total,
            "total": extracted.total,
            "payment_method": extracted.payment_method,
        })
        .execute()
    )
    receipt_id = receipt.data[0]["id"]

    # insert line items
    supabase.table("receipt_items").insert([
        {
            "receipt_id": receipt_id,
            "user_id": source["user_id"],
            "raw_name": item.raw_name,
            "short_name": item.short_name,
            "quantity": item.quantity,
            "unit_id": _resolve_unit(supabase, item.unit),
            "unit_price": item.unit_price,
            "total_price": item.total_price,
            "discount": item.discount,
            "tax_rate": item.tax_rate,
        }
        for item in extracted.line_items
    ]).execute()

    # link source back to receipt
    supabase.table("receipt_sources").update(
        {"receipt_id": receipt_id}
    ).eq("id", source["id"]).execute()

    logger.info(f"Extracted receipt {receipt_id} from source {source['id']}")
    return receipt_id


def _resolve_store(supabase, extracted: ExtractedReceipt, user_id: str) -> str | None:
    """Find or create a store by name."""
    result = (
        supabase.table("stores")
        .select("id")
        .eq("user_id", user_id)
        .eq("name", extracted.store_name)
        .execute()
    )
    if result.data:
        return result.data[0]["id"]

    # find chain
    chain = (
        supabase.table("store_chains")
        .select("id")
        .ilike("name", f"%{extracted.store_name}%")
        .execute()
    )
    chain_id = chain.data[0]["id"] if chain.data else None

    new_store = (
        supabase.table("stores")
        .insert({
            "user_id": user_id,
            "name": extracted.store_name,
            "chain_id": chain_id,
            "address": extracted.store_address,
            "city": extracted.store_city,
        })
        .execute()
    )
    return new_store.data[0]["id"]


def _resolve_unit(supabase, unit_symbol: str) -> str | None:
    """Resolve unit symbol to unit id."""
    result = (
        supabase.table("units")
        .select("id")
        .eq("symbol", unit_symbol)
        .execute()
    )
    return result.data[0]["id"] if result.data else None


@flow(name="extract-receipts")
async def extract_receipts() -> list[str]:
    sources = await fetch_unprocessed_sources()  # ty: ignore[no-matching-overload]
    logger = get_run_logger()
    logger.info(f"Found {len(sources)} unprocessed sources")

    results = []
    for source in sources:
        receipt_id = await extract_and_store(source)  # ty: ignore[no-matching-overload]
        if receipt_id:
            results.append(receipt_id)
    return results


def get_pdf_text_from_object_storage(urls: list[str]) -> str:
    pdf_bytes = download_receipts(urls)
    pdf_bytes = (p for p in pdf_bytes if p is not None)
    pdf_text = (get_pdf_text(p) for p in pdf_bytes)
    return "\n---".join(pdf_text)


def download_receipts(urls: Iterable[str]) -> Generator[bytes, None, None]:
    client = get_supabase()
    for url in urls:
        yield (
            client.storage
            .from_("receipts")
            .download(url)
            )

@overload
def get_pdf_text(pdf_bytes: None) -> None: ...
@overload
def get_pdf_text(pdf_bytes: bytes) -> str: ...
def get_pdf_text(pdf_bytes: bytes | None) -> str | None:
    if not pdf_bytes:
        return None
    pdf_bytes_io = io.BytesIO(pdf_bytes)
    with pdfplumber.open(pdf_bytes_io) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)
