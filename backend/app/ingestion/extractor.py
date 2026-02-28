import io

import pdfplumber
from bs4 import BeautifulSoup

from app.ingestion.gmail import RawEmail


def extract_text(email: RawEmail) -> str:
    """Extract clean text from email HTML body or PDF attachments."""
    parts: list[str] = []

    if email.html_body:
        parts.append(_extract_html(email.html_body))

    for pdf_bytes in email.pdf_attachments:
        parts.append(_extract_pdf(pdf_bytes))

    return "\n\n".join(filter(None, parts))


def _extract_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts and styles
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_pdf(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)
