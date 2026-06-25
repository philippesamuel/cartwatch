#!/usr/bin/env bash
set -euo pipefail

TEMPLATE="$(dirname "$0")/../infra/ecs-pool-base-job-template.json"
PREFECT_API_URL="${PREFECT_API_URL:?PREFECT_API_URL must be set}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"

export PREFECT_API_URL

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

sed "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" "$TEMPLATE" > "$tmp"
prefect work-pool update ecs-pool --base-job-template "$tmp"
