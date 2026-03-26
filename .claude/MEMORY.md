# Insurance Claims AI — Project Memory

## SDLC Stage
**Current:** Stage 5 — Testing (in progress)
**Completed:** Stage 1 — Requirements, Stage 2 — Architecture, Stage 3 — Infrastructure, Stage 4 — Development (copied + adapted from LoanScreen AI)

## Project Overview
Agentic Insurance Claims Processing System — 4-stage Gemini pipeline (Document Verification → Fraud Detection → Claim Validation → Decision). HITL triggers when claim amount > $10k OR fraud risk ≥ 0.7.

## Tech Stack
- **Frontend:** Next.js 15 (App Router) + TypeScript + shadcn/ui + Tailwind (dark mode)
- **Agent Backend:** Python 3.11 + Google ADK + FastAPI
- **Database:** BigQuery (`insurance` dataset)
- **Real-time:** Redis pub/sub → Next.js SSE → Browser EventSource
- **AI Models:** gemini-2.5-flash (doc verify, fraud) · gemini-2.5-pro (validation, decision)
- **CI/CD:** Harness CI/CD → Cloud Run
- **Secrets:** GCP Secret Manager

## BigQuery Tables
- `insurance_claims` — main claims table
- `agent_analyses` — per-agent analysis results
- `audit_log` — insert-only audit trail
- `human_approval_requests` — HITL queue

## Seed Data (3 claims)
1. Auto claim $3k — auto-approve scenario
2. Health claim $15k — HITL trigger scenario
3. Property claim $8k — fraud-rejection scenario

## Key References
- Jira Project: SCRUM | Label: `insurance-claims-ai`
- Jira Tickets: SCRUM-95 (Submit Claim), SCRUM-96 (Pipeline), SCRUM-97 (SSE Feed), SCRUM-98 (HITL), SCRUM-99 (Dashboard), SCRUM-100 (Fraud Detection), SCRUM-101 (Multi-type)
- Confluence HLD: Page ID 21430276 — https://bfsi-na-ai-engineering.atlassian.net/wiki/spaces/SCRUM1/pages/21430276
- GitHub Repo: https://github.com/sneha2002saji-pixel/insurance-claims-ai
- Cloud Run Services: `insurance-agent` · `insurance-web` in us-central1
- GCP Project: upbeat-repeater-477110-q6

## Agent Pipeline
```
DocumentVerificationAgent (Flash)
  → FraudDetectionAgent (Flash)
    → ClaimValidationAgent (Pro)
      → DecisionAgent (Pro)
           └─[amount > $10k OR fraud ≥ 0.7]─→ ADK Interrupt → HITL
```

## State Machine
`pending → under_review → agent_approved / awaiting_human_approval / rejected / partial_settlement → settled`

## Known Issues / Lessons Learned
- See ~/.claude/projects memory for LoanScreen deployment lessons (SHORT_SHA, Artifact Registry, BQ column names)
