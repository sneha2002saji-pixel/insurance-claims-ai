#!/usr/bin/env bash
# Run this script after: gcloud auth login && gcloud auth application-default login
# Usage: bash infra/bq-schemas/provision.sh
set -euo pipefail

PROJECT="upbeat-repeater-477110-q6"
DATASET="insurance"
REGION="us-central1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PATH="/c/google-cloud-sdk/bin:$PATH"

echo "=== Creating BigQuery dataset ==="
bq mk --dataset --location=US "${PROJECT}:${DATASET}" || echo "Dataset already exists — skipping"

echo "=== Creating BigQuery tables ==="
bq mk --table "${PROJECT}:${DATASET}.insurance_claims"        "${SCRIPT_DIR}/insurance_claims.json"        || echo "Table insurance_claims already exists"
bq mk --table "${PROJECT}:${DATASET}.agent_analyses"          "${SCRIPT_DIR}/agent_analyses.json"          || echo "Table agent_analyses already exists"
bq mk --table "${PROJECT}:${DATASET}.audit_log"               "${SCRIPT_DIR}/audit_log.json"               || echo "Table audit_log already exists"
bq mk --table "${PROJECT}:${DATASET}.human_approval_requests" "${SCRIPT_DIR}/human_approval_requests.json" || echo "Table human_approval_requests already exists"

echo "=== Seeding 3 test claims ==="
bq query --use_legacy_sql=false --project_id="${PROJECT}" \
"INSERT INTO \`${PROJECT}.${DATASET}.insurance_claims\`
  (id, claim_type, claimant_name, policy_number, amount, incident_description, document_refs, status, created_at, updated_at)
VALUES
  ('claim-001', 'AUTO',     'John Smith',     'AUTO-2024-001',   3000.00, 'Minor rear-end collision at traffic light. Vehicle has dented bumper and broken tail light.',                                                  NULL, 'pending', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
  ('claim-002', 'HEALTH',   'Sarah Johnson',  'HEALTH-2024-042', 15000.00, 'Emergency appendectomy surgery including 3-day hospital stay and post-operative care.',                                                        NULL, 'pending', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
  ('claim-003', 'PROPERTY', 'Mike Chen',      'PROP-2024-017',   8000.00, 'Basement flooding due to storm. Electronics and furniture damaged. Third claim this year.',                                                      NULL, 'pending', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());"

echo "=== Creating GCS bucket ==="
gsutil mb -p "${PROJECT}" -l "${REGION}" "gs://insurance-mock-documents" || echo "Bucket already exists — skipping"

echo "=== Creating Artifact Registry repository ==="
gcloud artifacts repositories create insurance-claims \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT}" || echo "Repository already exists — skipping"

echo "=== Done! ==="
echo "Verify BQ tables: bq ls ${PROJECT}:${DATASET}"
echo "Verify seed data: bq query --use_legacy_sql=false 'SELECT id, claim_type, amount, status FROM \`${PROJECT}.${DATASET}.insurance_claims\`'"
