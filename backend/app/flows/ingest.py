from postgrest.exceptions import APIError
from prefect import flow, get_run_logger, task
from storage3.exceptions import StorageApiError

from app.core.config import settings
from app.core.supabase import get_supabase
from app.ingestion.extractor import extract_pdf_text
from app.ingestion.gmail import (
    fetch_emails,
    fetch_label_id,
    fetch_raw_email,
    get_gmail_service,
)

LABEL = settings.gmail_label


@task
def fetch_receipts(access_token: str) -> list[dict]:
    logger = get_run_logger()
    service = get_gmail_service(access_token)
    label_id = fetch_label_id(service, label_name=LABEL)
    if not label_id:
        logger.warning(f"Label '{LABEL}' not found in Gmail")
        return []
    emails = fetch_emails(service, label_id)
    logger.info(f"Found {len(emails)} emails with label {LABEL}")
    return emails


@task
def process_email(access_token: str, user_id: str, message_id: str) -> str | None:
    logger = get_run_logger()
    supabase = get_supabase()
    service = get_gmail_service(access_token)
    raw = fetch_raw_email(service, message_id)

    if not raw.text:
        logger.warning(f"No text extracted from email {message_id}")
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
                return None
            raise
        pdf_urls.append(path)

    # extract text from PDFs if no text/html body
    pdf_text = "\n\n".join(extract_pdf_text(b) for b in raw.pdf_attachments)

    # store raw source in supabase
    receipt_source = {
        "user_id": user_id,
        "receipt_id": None,  # linked after extraction
        "source_type": "email",
        "external_id": message_id,
        "raw_text": raw.text or pdf_text or None,
        "raw_html": raw.html,
        "pdf_urls": pdf_urls or None,
    }
    try:
        supabase.table("receipt_sources").insert(receipt_source).execute()
    except APIError as e:
        if e.code == "23505":
            logger.info(f"Email {message_id} already ingested, skipping")
            return None
        raise
    logger.info(f"Stored raw source for email {message_id}")
    return message_id


# ty: ignore[no-matching-overload]
@flow(name="ingest-receipts")
def ingest_receipts(user_id: str, access_token: str) -> list[str]:
    emails = fetch_receipts(access_token)  # ty: ignore[no-matching-overload]

    processed = []
    for email in emails:
        result = process_email(access_token, user_id, email["id"])  # ty: ignore[no-matching-overload]

        if result:
            processed.append(result)
    return processed
