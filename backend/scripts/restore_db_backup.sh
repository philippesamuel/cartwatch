#!/usr/bin/env bash
set -euo pipefail

dump_file=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../db_backups"
mkdir -p "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"   # resolve to absolute path

docker run --rm -v "$BACKUP_DIR:/db_backups" \
  postgres:17 pg_restore\
  --clean \
  --if-exists \
  --no-acl \
  --no-owner \
  -d postgresql://postgres.${SUPABASE_PROJECT_ID}:${SUPABASE_DB_PASSWORD}@aws-1-eu-central-1.pooler.supabase.com:5432/postgres \
  $dump_file \
