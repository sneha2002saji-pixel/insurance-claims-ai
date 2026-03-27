# Insurance Claims AI

Agentic insurance claims processing platform. A 4-stage Gemini pipeline autonomously processes Auto, Health, and Property claims. High-value claims (>$10k) or high fraud risk (≥0.7) trigger a human-in-the-loop review pause.

## Architecture

```
DocumentVerificationAgent (Flash)
  → FraudDetectionAgent (Flash)
    → ClaimValidationAgent (Pro)
      → DecisionAgent (Pro)
           └─[amount > $10k OR fraud ≥ 0.7]─→ HITL → await human resume
```

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind (dark mode) |
| Agent Backend | Python 3.11 + Google ADK + FastAPI |
| Database | BigQuery (`insurance` dataset) |
| Real-time | Redis pub/sub → Next.js SSE → Browser EventSource |
| AI Models | `gemini-2.5-flash` (doc verify, fraud) · `gemini-2.5-pro` (validation, decision) |
| CI/CD | Harness CI/CD → Cloud Run |
| Secrets | GCP Secret Manager |

## Monorepo Layout

```
insurance-claims-ai/
├── apps/
│   ├── agent/          # Python FastAPI + Google ADK service
│   └── web/            # Next.js 15 dashboard
├── packages/
│   └── shared-types/   # Shared TypeScript types
├── infra/
│   ├── terraform/      # GCP infrastructure (BigQuery, IAM, secrets)
│   └── bq-schemas/     # BigQuery table schemas + provision script
├── mock-data/          # Seed claim JSON files
└── harness-pipeline.yaml
```

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker (for Redis)
- GCP credentials: `gcloud auth application-default login`

### Environment variables

**`apps/agent/.env`** (copy from `.env.example`):
```
GCP_PROJECT_ID=upbeat-repeater-477110-q6
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=http://localhost:3000
```

**`apps/web/.env.local`**:
```
AGENT_SERVICE_URL=http://localhost:8000
```

### Start services

```bash
# 1. Redis
docker run -d -p 6379:6379 redis:7-alpine

# 2. Agent backend
cd apps/agent
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn main:app --reload --port 8000

# 3. Web frontend (new terminal)
npm install          # from repo root
cd apps/web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Running Tests

```bash
# Python tests (from apps/agent/)
pytest tests/ -v --cov=. --cov-report=term-missing

# TypeScript type check (from apps/web/)
npx tsc --noEmit

# Next.js build
npm run build
```

## BigQuery Setup

```bash
cd infra/bq-schemas
chmod +x provision.sh
./provision.sh
```

This creates the `insurance` dataset, all 4 tables, seeds 3 test claims, creates the GCS bucket, and sets up the Artifact Registry repo.

## Pages

| Page | Route | Description |
|---|---|---|
| Dashboard | `/` | Claims list with status badges |
| Claim Detail | `/claims/[id]` | Live AI pipeline feed + status timeline |
| Submit Claim | `/claims/new` | New claim form (Auto / Health / Property) |
| HITL Review | `/review/[id]` | Human adjuster decision interface |

## CI/CD

Builds and deploys both services via Harness CI/CD (`harness-pipeline.yaml`):

1. Build & push agent Docker image → Artifact Registry
2. Build & push web Docker image → Artifact Registry
3. Deploy `insurance-agent` Cloud Run service
4. Deploy `insurance-web` Cloud Run service (injects agent URL automatically)

See `harness-pipeline.yaml` for full pipeline configuration.

## GCP Resources

- **Project:** `upbeat-repeater-477110-q6`
- **Region:** `us-central1`
- **Cloud Run:** `insurance-agent` · `insurance-web`
- **BigQuery dataset:** `insurance`
- **Artifact Registry:** `us-central1-docker.pkg.dev/upbeat-repeater-477110-q6/insurance-claims-ai`

## Claim Status Flow

```
pending → under_review → agent_approved
                       → awaiting_human_approval → approved / rejected / partial_settlement
                       → rejected
                       → partial_settlement
```

HITL is triggered when **claim amount > $10,000** OR **fraud score ≥ 0.7**.
