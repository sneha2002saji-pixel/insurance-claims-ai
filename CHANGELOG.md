# Changelog

## [0.1.1] - 2026-03-30

### Fixed
- DELETE endpoint restricted to `pending` claims only — prevents orphaning in-flight pipeline tasks
- SSE stream: `yield_events()` applies per-message `asyncio.wait_for` timeout (300 s)
- Pipeline audit log `previous_status` now reflects actual status on retry path
- HITL `trigger_reason` derived from Python conditions, not LLM output
- Conservative `fraud_score=0.5` fallback on LLM parse failure
- CORS `allow_headers` tightened to explicit allowlist
- `CreateClaimRequest` fields enforce `max_length`/`max_items` constraints
- Web: `/api/claims/[id]/approve` validates `decision` before forwarding
- Web: GET `/api/claims/[id]` returns 502 for non-404 upstream errors
- Web: retry button restricted to `pending` claims; advisory banner for `under_review`
- Web: `under_review` removed from deletable statuses; inline delete error

## [0.1.0] - 2026-03-27

### Added
- 4-stage Gemini agent pipeline: Document Verification → Fraud Detection → Claim Validation → Decision
- HITL escalation for claims >$10k or fraud score ≥0.7
- Real-time agent thinking feed via Redis pub/sub → SSE → browser EventSource
- Next.js 15 dark-mode dashboard with 4 pages (Dashboard, Claim Detail, Submit, HITL Review)
- Support for Auto, Health, and Property claim types
- BigQuery storage for claims, agent analyses, audit log, and HITL requests
- Dockerfiles for both agent (Python/FastAPI) and web (Next.js) services
- Harness CI/CD pipeline for build + deploy to Cloud Run
- Terraform infrastructure for GCP resources (BigQuery, IAM, Secret Manager)
- 58 Python unit tests with ≥80% coverage
