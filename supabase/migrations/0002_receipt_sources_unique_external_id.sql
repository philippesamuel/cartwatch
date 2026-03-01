-- ============================================================
-- receipt_sources: unique partial index on external_id
-- Prevents duplicate ingestion of the same email/file.
-- Partial: only applies when external_id is not null
-- (manual receipts have no external_id)
-- ============================================================

create unique index receipt_sources_external_id_unique
  on receipt_sources (external_id)
  where external_id is not null;
