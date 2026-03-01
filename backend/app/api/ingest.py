from fastapi import APIRouter, Header

from app.flows.ingest import ingest_receipts

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/receipts")
async def trigger_ingestion(
    x_supabase_user_id: str = Header(...),
    x_google_access_token: str = Header(...),
):
    processed = ingest_receipts(  # ty: ignore[no-matching-overload]
        user_id=x_supabase_user_id,
        access_token=x_google_access_token,
    )
    return {"processed": len(processed), "message_ids": processed}
