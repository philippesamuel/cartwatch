import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class RawEmail(BaseModel):
    message_id: str
    subject: str
    date: str
    html_body: str | None = None
    pdf_attachments: list[bytes] = Field(default_factory=list)


def get_gmail_service(access_token: str):
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds)


def fetch_label_id(service, label_name: str) -> str | None:
    labels = service.users().labels().list(userId="me").execute()
    for label in labels.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]
    return None


def fetch_emails(service, label_id: str) -> list[dict]:
    result = service.users().messages().list(userId="me", labelIds=[label_id]).execute()
    return result.get("messages", [])


def fetch_raw_email(service, message_id: str) -> RawEmail:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    subject = ""
    date = ""
    html_body = None
    pdf_attachments: list[bytes] = []

    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Subject":
            subject = h["value"]
        if h["name"] == "Date":
            date = h["value"]

    html_body, pdf_attachments = _extract_parts(
        service, msg.get("payload", {}), message_id, html_body, pdf_attachments
    )

    return RawEmail(
        message_id=message_id,
        subject=subject,
        date=date,
        html_body=html_body,
        pdf_attachments=pdf_attachments,
    )


def _extract_parts(
    service,
    payload: dict,
    message_id: str,
    html_body: str | None,
    pdf_attachments: list[bytes],
) -> tuple[str | None, list[bytes]]:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime_type == "text/html":
        data = body.get("data", "")
        if data:
            html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    elif mime_type == "application/pdf":
        attachment_id = body.get("attachmentId")
        if attachment_id:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            pdf_data = base64.urlsafe_b64decode(att["data"])
            pdf_attachments.append(pdf_data)

    for part in payload.get("parts", []):
        html_body, pdf_attachments = _extract_parts(
            service, part, message_id, html_body, pdf_attachments
        )

    return html_body, pdf_attachments
