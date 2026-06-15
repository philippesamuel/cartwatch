from fastapi import APIRouter

from flows.ingest import ingest_receipts

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/receipts")
async def trigger_ingestion():
    processed = ingest_receipts()
    return {"processed": len(processed), "message_ids": processed}
