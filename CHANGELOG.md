# Changelog

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
