# Insurance Claims AI — Project Memory

## SDLC Stage
**Current:** Stage 9 — Released v0.1.0 ✅
**Completed:** Stage 1–9 (all stages done)
**Remaining:** Stage 10 — Deployment (on explicit `/deploy-cloudrun` command only)

## Project Overview
Agentic Insurance Claims Processing System — 4-stage Gemini pipeline (Document Verification → Fraud Detection → Claim Validation → Decision). HITL triggers when claim amount > $10k OR fraud risk ≥ 0.7.

## Tech Stack
- **Frontend:** Next.js 15 (App Router) + TypeScript + Tailwind (dark mode) — standalone output for Docker
- **Agent Backend:** Python 3.11 + Google ADK + FastAPI
- **Database:** BigQuery (`insurance` dataset)
- **Real-time:** Redis pub/sub → Next.js SSE → Browser EventSource
- **AI Models:** gemini-2.5-flash (doc verify, fraud) · gemini-2.5-pro (validation, decision)
- **CI/CD:** Harness CI/CD → Cloud Run (`harness-pipeline.yaml`)
- **Secrets:** GCP Secret Manager

## BigQuery Write Pattern (CRITICAL)
- `insurance_claims`: DML INSERT (not streaming insert) — required so UPDATE statements see the row immediately
- `human_approval_requests`: DML INSERT (not streaming insert) — same reason; `update_hitl_decision` DML-UPDATEs the same row
- `agent_analyses`: streaming insert OK (append-only, never UPDATEd)
- `audit_log`: streaming insert OK (insert-only by design)

## Key References
- Jira Project: SCRUM | Label: `insurance-claims-ai`
- Jira Tickets: SCRUM-95 to SCRUM-101
- Confluence HLD: Page ID 21430276
- GitHub Repo: https://github.com/sneha2002saji-pixel/insurance-claims-ai
- Release: v0.1.0 tagged and pushed
- Cloud Run Services (not yet deployed): `insurance-agent` · `insurance-web` in us-central1
- GCP Project: upbeat-repeater-477110-q6

## Known Issues / Lessons Learned
- BigQuery DML INSERT must be used for any table that has subsequent DML UPDATEs — streaming inserts go into a buffer not visible to DML for up to 90 min
- `harness-pipeline.yaml` uses `gcp_connector` and `gcp_sa_key` secret references — these must be configured in the Harness account before running the pipeline
- Web Dockerfile uses Next.js standalone output — `next.config.ts` must have `output: "standalone"`
