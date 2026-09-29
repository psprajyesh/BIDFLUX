# BIDFLUX — Technical Approach

**AI-Powered Procurement Compliance Platform — SIH 2026 demo build**

This document fixes the scope, the architecture and — critically — the boundary between
what genuinely runs and what is simulated for the demo.

---

## 1. Honest capability matrix

Nothing in this project is presented as more than it is. Every row below is surfaced in the
UI with a `MOCK` / `DEMO` badge where simulated.

| # | Capability | Status | What actually happens | What would happen in production |
| --- | --- | --- | --- | --- |
| 1 | Verification case CRUD | **REAL** | Full persistence in SQLite via SQLAlchemy | Same |
| 2 | Tender upload + storage | **REAL** | File saved to disk, size/type validated, text read server-side | Same + virus scan, object storage |
| 3 | Requirement extraction (AI) | **MOCK** | Deterministic rule-based extractor reads the tender text for keywords | LLM / NLP call returning a JSON schema, validated with Pydantic |
| 4 | Document OCR / field extraction | **MOCK** | Deterministic field extractor. Reads real text if the file is `.txt`; otherwise uses the declared document type | Tesseract / cloud OCR → LLM JSON extraction with per-field confidence |
| 5 | Confidence scores | **MOCK** | Fixed per-field values (97–99%) from the demo fixture set | Calibrated model confidence per field |
| 6 | Government registry verification (GST / PAN / Udyam) | **MOCK** | Local format + checksum validation + presence check. **No network call, no government API** | Real GSTN / PAN / Udyam portal integration with signed requests |
| 7 | Experience / turnover evaluation | **REAL logic** | Deterministic numeric comparison against thresholds in the database | Same logic, thresholds from the tender |
| 8 | Compliance matrix | **REAL** | Computed from stored requirements + verification results + rules | Same |
| 9 | Risk score | **REAL** | Deterministic weighted rules over compliance exceptions | Calibrated model + learned weights |
| 10 | AI recommendation | **REAL rules, MOCK label** | Rule engine produces `REQUIRES OFFICER REVIEW`. Text is templated | LLM writes the narrative from the risk + compliance inputs |
| 11 | Officer decision | **REAL** | Persisted with officer name, comment, timestamp, verification ID | Identity-signed decision (needs auth — out of scope) |
| 12 | Audit trail | **REAL** | Append-only events written by services as they execute | Same, plus tamper-evident hashing |
| 13 | Evidence chain | **REAL** | Joins the six actual entities for the case | Same + object-store signed URLs |
| 14 | File security | **REAL** | Extension allow-list, size limit, MIME sniff, sanitised filename, random stored name | Same + antivirus + content-disarm |
| 15 | Authentication | **NOT IMPLEMENTED** | Deliberately excluded for the demo | OIDC / state-panchayat SSO, RBAC |
| 16 | Persistent vector store / RAG | **NOT IMPLEMENTED** | Out of scope | pgvector + tender corpus |

**Hard rule for the demo:** the system never auto-approves. `FINAL_DECISION` can only be written
by the officer-decision endpoint, which requires an explicit human action and a comment.

---

## 2. MVP scope

### In scope (built)
- One end-to-end workflow, 9 steps, from tender upload to audit evidence.
- Deterministic SIH demo dataset, one button, `Load SIH Demo Documents`.
- 8 pages behind a sidebar, one shared verification ID.
- REST API with the 12 endpoints listed in §5.
- SQLite + SQLAlchemy models for the 11 required entities.
- Security: env config, file validation, sanitisation, CORS allow-list, Pydantic input validation.
- Pytest suite over the workflow + 5 frontend-facing API smoke checks.
- Production build passes with zero type errors.

### Explicitly out of scope (rejected, not "later")
- Login / auth / roles / JWT.
- Redux, state-management libraries, drag-and-drop upload libraries, charting libraries.
- Microservices, message queues, separate AI service.
- Multi-tenancy, tender publication, reverse auctions, payment.
- Real GST/PAN/Udyam API calls.
- Full-text search, notification service, email.
- Real OCR engine, LLM SDK integration (behind the mock interfaces only).

### Why these cuts
Every one of them adds a failure mode in a live demo without strengthening the story.
The judging criteria for SIH are: does the workflow work, is the data consistent, is the
decision traceable, and is the boundary between real and simulated honest.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser — Next.js 16 App Router + React 19 + TS + Tailwind │
│  server components for read views, client components for    │
│  the interactive workflow                                   │
│      │  fetch  (NEXT_PUBLIC_API_URL)                       │
└──────┼──────────────────────────────────────────────────────┘
       │  JSON / multipart
┌──────▼──────────────────────────────────────────────────────┐
│  FastAPI                                                    │
│  routers/  thin: parse + validate + call service            │
│  services/ all business logic, reused across routers        │
│  ├─ audit.py       append-only event writer (injected)      │
│  ├─ storage.py     file validation + sanitised save         │
│  ├─ extraction.py  MOCK OCR / field extraction (interface)  │
│  ├─ tender.py      MOCK requirement extraction (interface)  │
│  ├─ verification.py format + rule checks (interface)        │
│  ├─ compliance.py  matrix builder                           │
│  ├─ risk.py        weighted risk scoring                    │
│  └─ recommendation.py rule-based recommendation             │
└──────┼──────────────────────────────────────────────────────┘
       │  SQLAlchemy 2.0 (ORM, typed Mapped columns)
┌──────▼──────────────────────────────────────────────────────┐
│  SQLite  — bidflux.db (file), 11 tables                      │
└─────────────────────────────────────────────────────────────┘
```

Layering rule: **routers never contain business logic; services never touch HTTP.**
A single `AuditService` instance is attached to `app.state` and injected into every other
service, so no service writes audit rows by hand and none can forget to.

No microservices, no extra processes. One FastAPI process, one Next.js process.

---

## 4. Database

Engine: SQLAlchemy 2.0 declarative, typed `Mapped[...]` columns, SQLite file DB.
`check_same_thread=False`, WAL off (SQLite default is fine at demo scale).
`PRAGMA foreign_keys=ON` on every connection. Tables created at startup via
`Base.metadata.create_all` — no Alembic for the demo (see §9).

### Entities (11, as required)

| Entity | Table | Key fields | Relations |
| --- | --- | --- | --- |
| `Verification` | `verifications` | `id` (PK, `VER-YYYY-NNNNNN`), `title`, `tenderer`, `status`, `active_tender_id`, `active_bidder_id`, `current_step`, `created_at`, `updated_at` | 1→n everything below |
| `Tender` | `tenders` | `id`, `verification_id` FK, `reference_no` (`TND/2026/001`), `title`, `file_name`, `stored_name`, `file_size`, `content_type`, `raw_text` | 1→n Requirements, 1→1 Bidder |
| `Requirement` | `requirements` | `id`, `tender_id` FK, `code`, `title`, `description`, `category`, `is_mandatory`, `source` (`AI_EXTRACTED`\|`MANUAL`), `confidence`, `sort_order`, `validated_by_officer` | 1→n ComplianceResult |
| `Bidder` | `bidders` | `id`, `verification_id` FK, `name`, `code` | 1→n Document, 1→n ExtractedField |
| `Document` | `documents` | `id`, `bidder_id` FK, `doc_type`, `file_name`, `stored_name`, `file_size`, `content_type`, `status` (`UPLOADED`\|`PROCESSED`\|`REJECTED`), `processing_mode` (`MOCK`\|`RULE`), `processed_at` | 1→n ExtractedField |
| `ExtractedField` | `extracted_fields` | `id`, `document_id` FK, `field_name`, `field_value`, `confidence`, `page_no`, `extraction_mode` | 1→n VerificationResult |
| `VerificationResult` | `verification_results` | `id`, `requirement_id` FK, `extracted_field_id` FK NULL, `status` (`VERIFIED`\|`MISSING`\|`INVALID`\|`MISMATCH`\|`NOT_VERIFIED`), `method` (`FORMAT_CHECK`\|`PRESENCE`\|`THRESHOLD`), `detail`, `source`, `verified_by`, `verified_at` | → ComplianceResult |
| `ComplianceResult` | `compliance_results` | `id`, `verification_id` FK, `requirement_id` FK, `status` (`PASS`\|`FAIL`\|`REVIEW`\|`NOT_APPLICABLE`), `reason`, `evidence_ref`, `computed_at` (unique per verification+requirement) | → RiskAssessment |
| `RiskAssessment` | `risk_assessments` | `id`, `verification_id` FK (unique), `level` (`LOW`\|`MEDIUM`\|`HIGH`\|`CRITICAL`), `score` 0–100, `reasons` (JSON array of strings), `verified_count`, `total_count`, `computed_at` | 1→1 recommendation payload |
| `OfficerDecision` | `officer_decisions` | `id`, `verification_id` FK, `decision` (`APPROVED`\|`REJECTED`\|`CLARIFICATION_REQUESTED`), `comment`, `officer_name`, `officer_id`, `created_at` | — |
| `AuditEvent` | `audit_events` | `id`, `verification_id` FK, `event_type`, `actor` (`SYSTEM`\|`OFFICER`), `stage`, `message`, `metadata` (JSON), `created_at` (append-only, no update path in code) | — |

### Data integrity rules
- `unique(verification_id, requirement_id)` on `compliance_results` → recompute is idempotent.
- `unique(verification_id)` on `risk_assessments` → upsert on recompute.
- Cascade deletes from `Verification` down to `AuditEvent` only via explicit `demo reset`.
- `audit_events` has no `updated_at` and is never mutated after insert.

### Demo fixture — deterministic by design
Tender `TND/2026/001` · *Supply of Medical Equipment* · Bidder `ABC Technologies`.

8 requirements: `GST Registration`, `PAN`, `Udyam Registration`, `OEM Authorization`,
`Minimum Experience`, `Turnover`, `Technical Specification`, `Financial Eligibility`.

5 documents — GST Certificate ✓, PAN ✓, Udyam ✓, Experience ✓, Turnover ✓.
**OEM Authorization is expected but deliberately not submitted** — it is the one gap
(`missing_expected` reports `["OEM Authorization Letter"]`), so the extraction table stops at
the five uploaded files.

Extraction table (fixed values, fixed confidences):

| Field | Value | Source | Confidence |
| --- | --- | --- | --- |
| GSTIN | `37XXXXXXXXXX1Z5` | GST Certificate | 98% |
| PAN | `ABCDE1234F` | PAN Document | 97% |
| Udyam | `UDYAM-AP-XX-XXXXXXX` | Udyam Certificate | 96% |
| Company | `ABC Technologies` | GST Certificate | 99% |

Expected outcome, computed live from the data — **not hard-coded**:
7/8 requirements verified → OEM `MISSING` → compliance `REVIEW` → risk `HIGH`
→ recommendation `REQUIRES OFFICER REVIEW`.

`Load SIH Demo Documents` is idempotent: loading twice resets the case to the same seeded state,
so the demo can be re-run live without duplicating rows.

---

## 5. API

Base: `http://localhost:8000` · prefix `/api` · all JSON unless noted.
(`backend/live_e2e.py` runs the API on `:8123` against a throwaway SQLite file, so the repo's
`bidflux.db` is never part of the live check.)
No auth by design. Error envelope: `{"error": {"code", "message", "detail"}}`.

| # | Method | Path | Purpose |
| --- | --- | --- | --- |
| 1 | `POST` | `/api/verifications` | Create verification case → returns `id` |
| 2 | `GET` | `/api/verifications` | List (supports `?status`, `?risk`, `?q`) |
| 3 | `GET` | `/api/verifications/{id}` | Full case aggregate (tender, bidder, steps, summary) |
| 4 | `POST` | `/api/verifications/{id}/tender` | Upload tender (multipart) → auto-extracts requirements |
| 5 | `GET` | `/api/verifications/{id}/tender` | Tender + extracted requirements |
| 6 | `POST` | `/api/verifications/{id}/documents` | Upload one document (multipart) |
| 7 | `POST` | `/api/verifications/{id}/documents/process` | Run extraction on uploaded docs |
| 8 | `GET` | `/api/verifications/{id}/documents` | Documents + extracted fields |
| 9 | `POST` | `/api/verifications/{id}/verification/run` | Run verification checks |
| 10 | `GET` | `/api/verifications/{id}/verification` | Verification results per requirement |
| 11 | `GET` | `/api/verifications/{id}/compliance` | Compliance matrix (recomputes if missing) |
| 12 | `GET` | `/api/verifications/{id}/risk` | Risk assessment (recomputes if missing) |
| 13 | `GET` | `/api/verifications/{id}/recommendation` | Rule-based recommendation + rationale |
| 14 | `POST` | `/api/verifications/{id}/decision` | Officer decision (requires comment) |
| 15 | `GET` | `/api/verifications/{id}/audit` | Audit trail, newest last |
| 16 | `GET` | `/api/verifications/{id}/evidence` | Evidence chain (6 levels) |
| 17 | `POST` | `/api/demo/load` | Seed deterministic SIH demo case |
| 18 | `POST` | `/api/demo/reset` | Delete all demo data |
| 19 | `GET` | `/api/dashboard` | KPI aggregates for the dashboard |
| 20 | `GET` | `/api/health` | Liveness + version + capability flags |
| 21 | `GET` | `/api/reports/summary` | Aggregate report rows across verifications |

### Reuse rules (no duplicate APIs)
- `GET /compliance`, `/risk`, `/recommendation` **read from the DB**, and recompute only via one
  shared helper when the case is not ready yet. They never run their own logic.
- `POST /verification/run` calls `run_verification`; `/documents/process` calls `process_documents`.
  Nothing in a router duplicates a service.
- Router files stay under ~120 lines each; all business rules live in `services/`.
- One `WorkflowService` computes `current_step` from real state; the frontend stepper reads it
  rather than duplicating the state machine.

---

## 6. Workflow

`current_step` is derived, not stored as truth — it is the first stage whose preconditions are unmet.

| # | Step | Precondition to complete | Writes |
| --- | --- | --- | --- |
| 1 | Tender | A tender file is attached | `Tender`, `Requirement`×8, audit |
| 2 | Requirements | ≥1 requirement extracted | `Requirement` rows (needs officer validation flag) |
| 3 | Documents | ≥1 document uploaded | `Document` rows |
| 4 | Extraction | All uploaded docs `PROCESSED` | `ExtractedField` rows, audit |
| 5 | Verification | A verification result exists per requirement | `VerificationResult` |
| 6 | Compliance | Matrix rows exist | `ComplianceResult`, audit |
| 7 | Risk | Assessment exists | `RiskAssessment`, audit |
| 8 | Review | Officer has opened the review panel | `Verification.status = REVIEW_REQUIRED` |
| 9 | Decision | `OfficerDecision` row exists | `OfficerDecision`, `Verification.status = FINAL_DECISION`, audit |

Status state machine:
`DRAFT → TENDER_UPLOADED → REQUIREMENTS_EXTRACTED → DOCUMENTS_UPLOADED → DOCUMENTS_PROCESSED
→ VERIFICATION_COMPLETE → COMPLIANCE_READY → REVIEW_REQUIRED → FINAL_DECISION`.

`status` is milestone-derived, never the stored source of truth: risk alone leaves a case at
`COMPLIANCE_READY`; generating the recommendation advances it to `REVIEW_REQUIRED`; recording any
officer decision — approved, clarification requested, or rejected — closes the file at
`FINAL_DECISION`. The decision row itself carries the `decision`, comment and officer identity.

### Compliance rule (deterministic, per requirement)

```
verification VERIFIED          → PASS
verification INVALID/MISMATCH  → FAIL
verification MISSING           → REVIEW ("Required document not submitted — officer judgement required.")
verification NOT_VERIFIED      → REVIEW
no result, mandatory req       → REVIEW
no result, optional req        → NOT_APPLICABLE
```

### Risk rule (deterministic, weighted)

| Signal | Weight |
| --- | --- |
| Any compliance `FAIL` | +40 |
| Any compliance `REVIEW` | +35 |
| Missing mandatory document | +20 |
| Verified ratio below 80% | +10 |

Score clamped to 0–100. `≥75 CRITICAL` · `≥50 HIGH` · `≥25 MEDIUM` · else `LOW`.
Demo case: 1 `REVIEW` (+35) + one missing mandatory document (+20) = **55 → HIGH**, with exactly
three reasons generated from the real rows (officer judgement for OEM, evidence incomplete,
officer review required before a decision).

### Recommendation rule
Any `FAIL`/`CRITICAL`/`REVIEW`/`HIGH` → `REQUIRES_OFFICER_REVIEW`.
All `PASS` and `LOW` → `ELIGIBLE_PENDING_OFFICER_CONFIRMATION`.
Never `APPROVE`. The officer is always the final authority.

---

## 7. Mock services

Each mock sits behind a small, replaceable interface so a real implementation can be dropped in
without touching routers or the UI.

| Module | Interface | Current implementation | Real replacement |
| --- | --- | --- | --- |
| `services/extraction.py` | `extract_fields(document) -> list[ExtractedFieldResult]` | Deterministic map from doc type to field set. Reads real text for `.txt`. `extraction_mode="MOCK"` | OCR engine + LLM structured output |
| `services/tender.py` | `extract_requirements(tender) -> list[RequirementDraft]` | Keyword/regex scan over the tender text, mapped to the 8 canonical categories. `source="AI_EXTRACTED"` | LLM prompt + Pydantic schema validation |
| `services/verification.py` | `verify(requirement, fields, document) -> VerificationOutcome` | GSTIN / PAN / Udyam format + checksum validation, presence check, numeric threshold comparison. `method="FORMAT_CHECK"` / `"PRESENCE"` / `"THRESHOLD"`, `source="LOCAL_RULE (no government API)"` | Real GSTN/PAN/Udyam portal calls |
| `services/recommendation.py` | `recommend(compliance, risk) -> Recommendation` | Templated narrative from real risk reasons | LLM narrative generation |

Guard rails baked into the code, not just the docs:
- Every response from these modules carries a `mode` field (`MOCK` / `RULE`), surfaced in the UI.
- `services/verification.py` has no HTTP client imported at all — a real portal call cannot
  silently appear.
- Fixed confidences (96–99%) live in one fixture constant, so the demo is reproducible.

---

## 8. Testing

### Backend — pytest (in `backend/tests/`, run against a temporary SQLite file)
The suite mirrors the SIH script one stage at a time (`test_01` … `test_14`):
1. `test_01_health_reports_registry_as_mock` — `/api/health`: no government API claim; real capabilities listed.
2. `test_02_demo_load_is_deterministic` — two loads → the same case, 8 requirements, 5 documents.
3. `test_03_requirements_are_extracted_with_confidence` — the 8 canonical requirements with confidence.
4. `test_04_documents_and_extraction_values` — GSTIN/PAN/Udyam/Company extracted values exact.
5. `test_05_verification_marks_seven_verified_and_one_missing` — OEM `MISSING`; `LOCAL_RULE` sources.
6. `test_06_compliance_is_computed_from_results` — 7 PASS / 1 REVIEW / 0 FAIL.
7. `test_07_risk_is_high_for_the_demo_case` — score 55 → HIGH, exactly three reasons.
8. `test_08_recommendation_requires_officer_review` — advisory, never an approve.
9. `test_09_decision_requires_all_officer_fields` — every field mandatory; short comment rejected.
10. `test_10_decision_is_persisted_and_closes_the_case` — decision stored; case `FINAL_DECISION`.
11. `test_11_evidence_chain_has_six_levels` — chains terminate at real documents and fields.
12. `test_12_audit_trail_records_every_stage` — all ten event types; exactly 7 `FIELD_VERIFIED`.
13. `test_13_upload_rejects_executables_and_sanitises_filenames` — `.exe` → 422; traversal stripped; opaque stored name.
14. `test_14_reset_clears_the_demo_workspace` — reset empties the workspace; dashboard zeroed; 404 after.

The pytest suite runs in-process via `TestClient`. A live two-server check
(`backend/live_e2e.py`) boots real uvicorn + Next.js over HTTP and asserts the same numbers end
to end, including CORS, served HTML and the built client bundle.

### Frontend — build gate
`npm run build` must pass with zero TypeScript errors. Page data-contracts are shared types in
`src/lib/types.ts` mirroring the Pydantic response models.

### Manual demo script (SIH rehearsal)
Exactly the sequence in README §6, from an empty database, timed end to end.

---

## 9. Deployment

- **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Single process, no workers
  needed (SQLite, demo scale). `DATABASE_URL` and `CORS_ORIGINS` from the environment.
- **Frontend**: `npm run build && npm start` (standalone). `NEXT_PUBLIC_API_URL` is the **only**
  API base URL — no hard-coded Render host, no `localhost` production fallback.
- **Failure behaviour**: if `NEXT_PUBLIC_API_URL` is missing in production, the frontend renders
  a configuration error panel rather than silently pointing at localhost.
- **Migrations**: `create_all` at startup for the demo. Alembic is listed as the first production
  step (a live-updating schema needs real migrations).

---

## 10. Future improvements

**Near term (post-demo)**
1. OIDC authentication with role-based access — the single biggest production gap.
2. Alembic migrations + PostgreSQL (multi-user writes).
3. Real OCR (`Tesseract`/cloud) behind the existing `extraction.py` interface.
4. Real LLM extraction with Pydantic-validated structured output + human validation loop.
5. GSTN / PAN / Udyam portal integrations with caching, rate limits and audit of every lookup.
6. Object storage with signed URLs, malware scanning and retention policies.

**Medium term**
7. Multi-tender comparison scoring, weighted technical evaluation.
8. Calibration of risk weights using historical decision data.
9. OCR model fine-tuning on real procurement documents.
10. Full-text/tender-corpus search with pgvector + RAG for requirement matching.
11. Officer analytics: TAT, rejection reasons, vendor performance history.
12. Hindi/bilingual tender support.

**Explicitly not planned**
Blockchain notarisation, IoT integration, ML-based auto-rejection. Auto-rejection is dangerous in
procurement and contradicts the product principle.

---

## 11. Principles honoured

- No login, as instructed.
- No old-project code reused — this repository was rebuilt from scratch.
- One workflow, deeply implemented, rather than many shallow features.
- One shared service layer; no duplicate APIs.
- No state-management library; server components + URL state only.
- Real and simulated behaviour are separated in code, in the API (`mode` fields) and in the UI.
- The system never decides. It recommends, and a human disposes.
