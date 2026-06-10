import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, ConfigDict, Field

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class EmailContent(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str | None = None
    html: str | None = None
    pdf_attachments: tuple[bytes, ...] = ()


class RawEmail(BaseModel):
    message_id: str
    subject: str
    date: str
    content: EmailContent = Field(default_factory=EmailContent)

    @property
    def text(self) -> str | None:
        return self.content.text

    @property
    def html(self) -> str | None:
        return self.content.html

    @property
    def pdf_attachments(self) -> tuple[bytes, ...]:
        return self.content.pdf_attachments

    def content_is_empty(self) -> bool:
        return all(
            (
                self.content.text is None,
                self.content.html is None,
                self.content.pdf_attachments == (),
            )
        )


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

    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Subject":
            subject = h["value"]
        if h["name"] == "Date":
            date = h["value"]

    content = _extract_parts(
        service,
        msg.get("payload", {}),
        message_id,
        content=EmailContent(),
    )
    return RawEmail(
        message_id=message_id,
        subject=subject,
        date=date,
        content=content,
    )


def _extract_parts(
    service,
    payload: dict,
    message_id: str,
    content: EmailContent,
) -> EmailContent:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    updated_content = content

    match mime_type:
        case "text/plain":
            data = body.get("data", "")
            if data:
                updated_content = content.model_copy(
                    update=dict(text=_decode_base64(data)),
                )
        case "text/html":
            data = body.get("data", "")
            if data:
                updated_content = content.model_copy(
                    update=dict(html=_decode_base64(data)),
                )
        case "application/pdf" | "application/octet-stream":
            filename = payload.get("filename", "")
            attachment_id = body.get("attachmentId")
            is_pdf = mime_type == "application/pdf" or filename.endswith(".pdf")
            if is_pdf and attachment_id:
                pdf_bytes = _fetch_pdf_bytes(service, message_id, attachment_id)
                updated_content = content.model_copy(
                    update=dict(
                        pdf_attachments=content.pdf_attachments + (pdf_bytes,)
                        )
                    )
        case _:
            updated_content = content.model_copy()

    for part in payload.get("parts", []):
        updated_content = _extract_parts(
            service,
            part,
            message_id,
            updated_content,
        )

    return updated_content


def _fetch_pdf_bytes(service, message_id: str, attachment_id: str) -> bytes:
    att = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    return base64.urlsafe_b64decode(att["data"])


def _decode_base64(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")