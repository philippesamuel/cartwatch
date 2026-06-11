from prefect import flow, get_run_logger, task
from storage3.exceptions import StorageApiError

from core.config import get_gmail_settings, get_supabase_settings
from core.supabase import get_supabase
from ingestion.receipts.extractor import extract_pdf_text
from ingestion.receipts.gmail import (
    fetch_emails,
    fetch_label_id,
    fetch_raw_email,
    get_gmail_service,
)


@task
def fetch_receipts() -> list[dict]:
    settings = get_gmail_settings()
    LABEL = settings.gmail_label

    logger = get_run_logger()
    service = get_gmail_service()
    label_id = fetch_label_id(service, label_name=LABEL)
    if not label_id:
        logger.warning(f"Label '{LABEL}' not found in Gmail")
        return []
    emails = fetch_emails(service, label_id)
    logger.info(f"Found {len(emails)} emails with label {LABEL}")
    return emails


@task
def process_email(user_id: str, message_id: str) -> str | None:
    logger = get_run_logger()
    supabase = get_supabase()
    service = get_gmail_service()
    raw = fetch_raw_email(service, message_id)

    if raw.content_is_empty():
        logger.warning(f"No content extracted from email {message_id}")
        return None

    # upload PDFs to Supabase Storage, collect URLs
    pdf_urls: list[str] = []
    for i, pdf_bytes in enumerate(raw.pdf_attachments):
        path = f"{user_id}/{message_id}/{i}.pdf"
        try:
            supabase.storage.from_("receipts").upload(
                path,
                pdf_bytes,
                file_options={"content-type": "application/pdf"},
            )
        except StorageApiError as e:
            if e.status == "409":
                logger.info(f"PDF {path} already ingested")
            else:
                raise
        pdf_urls.append(path)

    # extract text from PDFs if no text/html body
    pdf_text = "\n\n".join(extract_pdf_text(b) for b in raw.pdf_attachments)

    # store raw source in supabase
    receipt_source = {
        "user_id": user_id,
        "source_type": "email",
        "external_id": message_id,
        "raw_text": raw.text or pdf_text or None,
        "raw_html": raw.html,
        "pdf_urls": pdf_urls or None,
    }
    existing = (
        supabase.table("receipt_sources")
        .select("id")
        .eq("external_id", message_id)
        .maybe_single()
        .execute()
    )
    if existing.data:
        logger.debug(receipt_source)
        logger.info(f"Email {message_id} already ingested. Upserting")
        receipt_source["id"] = existing.data["id"]
        supabase.table("receipt_sources").upsert(receipt_source).execute()
    else:
        logger.info(f"Inserting e-mail {message_id} ...")
        supabase.table("receipt_sources").insert(receipt_source).execute()
    logger.info(f"Stored raw source for email {message_id}")
    return message_id


# ty: ignore[no-matching-overload]
@flow(name="ingest-receipts")
def ingest_receipts() -> list[str]:
    settings = get_supabase_settings()
    user_id=settings.supabase_user_id
    emails = fetch_receipts()  # ty: ignore[no-matching-overload]

    processed = []
    for email in emails:
        result = process_email(user_id, email["id"])  # ty: ignore[no-matching-overload]

        if result:
            processed.append(result)
    return processed
