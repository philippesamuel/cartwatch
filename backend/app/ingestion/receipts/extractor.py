import io

import pdfplumber
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider

from app.core.config import settings
from app.ingestion.receipts.models import ExtractedReceipt


def extract_pdf_text(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def build_agent() -> Agent[None, ExtractedReceipt]:
    model = MistralModel(
        "mistral-small-latest",
        provider=MistralProvider(
            api_key=settings.mistral_api_key.get_secret_value(),
            base_url=settings.mistral_base_url
        )
        )
    return Agent(
        model,
        output_type=ExtractedReceipt,
        system_prompt="""You are a receipt extraction assistant.
Extract structured data from grocery receipt text or HTML.
Rules:
- Convert all quantities to SI base units (kg, L, piece, m)
- unit_price must be price per SI unit (e.g. 1.29 EUR/kg)
- purchased_at must be ISO 8601 with timezone (assume Europe/Berlin if not specified)
- short_name should be a concise product name in English (e.g. "whole milk", "eggs")
- If a field is not present in the receipt, omit it
- total must always be present
""",
    )


_agent = build_agent()


async def extract_receipt(
    text: str | None, 
    html: str | None,
    pdf_text: str | None
    ) -> ExtractedReceipt:    
    sections = {
        "pdf_text": pdf_text,
        "html": html,
        "text": text,
    }
    present = {
        k: v 
        for k, v in sections.items() 
        if ((v is not None) and (v.strip() != ""))
        }

    if not present:
        raise ValueError("No content to extract from")

    content = "\n".join(f"<{k}>{v}</{k}>" for k, v in present.items())
    result = await _agent.run(content)
    return result.output