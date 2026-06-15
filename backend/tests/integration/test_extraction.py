# backend/tests/integration/test_extraction.py
import pytest

from flows.extract import extract_receipts


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_receipts():
    result = await extract_receipts()
    print(f"Extracted {len(result)} receipts: {result}")
    assert isinstance(result, list)
