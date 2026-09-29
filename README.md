# BIDFLUX

**AI-Powered Procurement Compliance Platform**

Deterministic SIH 2026 demo of a tender-compliance verification workflow: from tender upload
to a traceable officer decision, with a complete audit trail and evidence chain.

```
AI ASSISTS. RULES VERIFY. OFFICER DECIDES. EVERYTHING IS AUDITABLE.
```

> **No login.** The application opens directly on the dashboard.

---

## 1. Overview

BIDFLUX processes a public-sector tender verification in one continuous workflow:

```
New Verification → Tender Upload → AI Tender Analysis → Requirements
→ Bidder Documents → OCR / Extraction → Verification → Compliance Matrix
→ Risk Analysis → AI Recommendation → Officer Review → Final Decision
→ Audit Trail → Evidence
```

Built as a two-app monorepo:

| Layer | Stack | Purpose |
| --- | --- | --- |
| `backend/` | FastAPI · Python 3.11 · SQLAlchemy 2.0 · SQLite · REST | All business logic and data |
| `frontend/` | Next.js 16 App Router · React 19 · TypeScript · Tailwind CSS v4 | Dashboard and workflow UI |

### What is real and what is simulated

| Real | Simulated (clearly labelled `MOCK` / `DEMO` in the UI) |
| --- | --- |
| Verification case, tender, bidder and document persistence | AI requirement extraction from tender text |
| File upload, validation, storage, sanitisation | OCR / document field extraction + confidence scores |
| Format, presence and threshold verification rules | GST / PAN / Udyam **registry lookups** (no government API is called) |
| Compliance matrix, risk scoring, recommendation rules | AI recommendation wording (rule-generated) |
| Officer decision, audit trail, evidence chain | — |

**There is no government API integration.** GST, PAN and Udyam are validated by local
format and checksum rules, and the result is labelled `LOCAL_RULE (no government API)`.
BIDFLUX never approves automatically — the officer decision is mandatory.

See [`approach.md`](./approach.md) for the full capability matrix.

---

## 2. Folder structure

```
BIDFLUX/
├── README.md
├── approach.md                  # scope, architecture, DB, API, mock services
├── design.md                    # design system: colour, type, layout, components
├── .gitignore                   # secrets, .env, venv, node_modules, *.db
│
├── backend/
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── bidflux.db               # created on first run
│   ├── storage/                 # uploaded files (sanitised names)
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, static mount, lifespan
│   │   ├── config.py            # env settings (pydantic-settings)
│   │   ├── database.py          # engine, SessionLocal, get_db
│   │   ├── enums.py             # status + mode constants
│   │   ├── errors.py            # error envelope + handlers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── entities.py      # 11 SQLAlchemy models
│   │   ├── schemas/
│   │   │   └── __init__.py      # Pydantic request/response contracts
│   │   ├── services/            # ALL business logic lives here
│   │   │   ├── audit.py         # append-only event writer (injected)
│   │   │   ├── storage.py       # file validation, sanitisation, save
│   │   │   ├── cases.py         # verification CRUD + aggregates
│   │   │   ├── tender.py        # MOCK requirement extraction
│   │   │   ├── documents.py     # upload + MOCK extraction
│   │   │   ├── verification.py  # format / presence / threshold rules
│   │   │   ├── compliance.py    # matrix builder
│   │   │   ├── risk.py          # weighted risk scoring
│   │   │   ├── recommendation.py# rule-based recommendation
│   │   │   ├── evidence.py      # 6-level evidence chain
│   │   │   ├── workflow.py      # derived current_step + status
│   │   │   ├── reports.py       # dashboard + report aggregates
│   │   │   └── demo.py          # deterministic SIH fixture loader/reset
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── verifications.py # create/list/get, tender, documents, verify
│   │       ├── workflow.py      # compliance, risk, recommendation, decision
│   │       ├── evidence.py      # evidence + audit
│   │       ├── demo.py          # demo load / reset
│   │       └── system.py        # health, dashboard, reports
│   └── tests/
│       └── test_workflow.py     # pytest suite over the full demo flow
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── postcss.config.mjs
    ├── eslint.config.mjs
    └── src/
        ├── app/
        │   ├── layout.tsx           # shell: sidebar + header
        │   ├── globals.css          # Tailwind v4 theme tokens
        │   ├── page.tsx             # Dashboard
        │   ├── verification/
        │   │   ├── page.tsx         # Verification list
        │   │   ├── new/page.tsx     # New Verification
        │   │   └── [id]/page.tsx    # 9-step workflow
        │   ├── documents/page.tsx
        │   ├── compliance/page.tsx
        │   ├── evidence/page.tsx
        │   ├── audit/page.tsx
        │   ├── reports/page.tsx
        │   └── settings/page.tsx
        ├── components/
        │   ├── shell/    Sidebar, Header, PageShell
        │   ├── ui/       Badge, StatusBadge, Button, Card, Table, Alert, …
        │   └── workflow/ WorkflowStepper, stage panels, OfficerDecision
        └── lib/
            ├── api.ts      # fetch wrapper over NEXT_PUBLIC_API_URL
            ├── types.ts    # shared response types
            └── format.ts   # date / currency / percent helpers
```

---

## 3. Setup

### Prerequisites
- Python **3.11+**
- Node.js **20+**
- npm **10+**

No database server, no Docker, no external services.

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

---

## 4. Run instructions

Two terminals.

**Terminal 1 — API on `http://localhost:8000`**

```bash
cd backend
.venv\Scripts\activate        # Windows
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI on `http://localhost:3000`**

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**. No login. You land on the Dashboard.

Check the API: <http://localhost:8000/api/health> · interactive docs at
<http://localhost:8000/docs>.

### Production build

```bash
cd frontend
npm run build
npm start          # serves on :3000, reads NEXT_PUBLIC_API_URL
```

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Tests

```bash
cd backend
.venv\Scripts\activate
python -m pytest -q
```

The pytest suite runs in-process via `TestClient`. For a live two-server check that boots real
uvicorn + Next.js over HTTP (full scenario, CORS, served HTML and the built client bundle —
never touching your `bidflux.db`):

```bash
backend\.venv\Scripts\python.exe backend\live_e2e.py
```

---

## 5. Environment variables

The backend reads these through `pydantic-settings`; all have working defaults for local
development, so nothing must be set to run the demo.

| Variable | Default | Used by | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./bidflux.db` | backend | SQLAlchemy connection string |
| `CORS_ORIGINS` | `http://localhost:3000` | backend | Comma-separated exact-origin allow-list for CORS. No `*` in production |
| `MAX_UPLOAD_MB` | `10` | backend | Hard file-size limit; the full upload is buffered into memory first, then validated before anything is written |
| `STORAGE_DIR` | `./storage` | backend | Where sanitised uploads are written |
| `APP_ENV` | `development` | both | `development` \| `production` — shown as a chip in the sidebar |
| `AI_MODE` | `mock` | backend | The only mode this build ships with — simulated services are labelled `MOCK` in the API responses. `disabled` is reserved; no manual requirement-entry UI ships, so the demo stays on `mock` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | frontend | **The only** API base URL. No hard-coded hosts, no localhost fallback in production |

Copy `.env.example` to `.env` to override. `.env` is git-ignored — **no secrets are committed**.

---

## 6. Demo workflow (SIH script)

The whole demo runs on one verification ID, e.g. `VER-2026-000001`.

| Step | Action | Screen |
| --- | --- | --- |
| 1 | Click **New Verification** → enter tender reference `TND/2026/001`, title *Supply of Medical Equipment*, tendering authority | `/verification/new` |
| 2 | **Create Verification** → the case opens at step 1 *Tender* | `/verification/[id]` |
| 3 | Upload a tender file (or leave it and press **Load SIH Demo Documents** to skip straight to seeded data) | step 1 |
| 4 | **Analyse Tender** → 8 requirements extracted: GST Registration, PAN, Udyam Registration, OEM Authorization, Minimum Experience, Turnover, Technical Specification, Financial Eligibility. Banner: *"AI-extracted requirements require officer validation before final use."* | step 2 |
| 5 | Review documents → press **Load SIH Demo Documents** to load 5 documents (GST, PAN, Udyam, Experience, Turnover; OEM Authorization **absent**) | steps 3–4 |
| 6 | **Process Documents** → extraction table `Field \| Value \| Source \| Confidence`, incl. GSTIN `37XXXXXXXXXX1Z5` 98%, PAN `ABCDE1234F` 97%, Udyam `UDYAM-AP-XX-XXXXXXX` 96%, Company `ABC Technologies` 99% | step 4 |
| 7 | **Run Verification** → GST ✓, PAN ✓, Udyam ✓, Experience ✓, Turnover ✓, OEM ⚠ MISSING | step 5 |
| 8 | **Calculate Compliance** → matrix: 7 PASS, OEM **REVIEW**, 7/8 requirements verified | step 6 |
| 9 | **Assess Risk** → **HIGH**, reasons: OEM authorisation missing · evidence incomplete · officer review required | step 7 |
| 10 | **Generate Recommendation** → **REQUIRES OFFICER REVIEW** (never an approval) | step 8 |
| 11 | Compliance Status: **REVIEW REQUIRED**. Critical exception: *OEM Authorization missing*. Choose **APPROVE / REJECT / REQUEST CLARIFICATION**, add a comment, **Record Decision** — saved with decision, comment, timestamp and verification ID | step 9 |
| 12 | **Audit Trail** → tender uploaded, requirements extracted, documents processed, GST/PAN/Udyam verified, OEM missing, compliance calculated, risk calculated, recommendation generated, officer decision recorded | `/audit` |
| 13 | **Evidence** → Bidder → Document → Extracted Data → Verification → Requirement → Compliance Result | `/evidence` |

**Rehearsal tip:** `Load SIH Demo Documents` is idempotent and fully deterministic — the same
eight requirements, the same extracted values and the same 7/8 result every single run.
Use **Reset Demo Data** (Dashboard) to clear and re-run.

To test the upload path without the fixture, any `.txt`, `.pdf` or `.docx` file works;
requirement extraction reads `.txt` content and falls back to the canonical 8-category
template for binary formats.

---

## 7. Deployment

**Backend** (any Python host — Render, Railway, Fly, Azure App Service, EC2)

```
Build command:  pip install -r requirements.txt
Start command:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
Env:            DATABASE_URL, CORS_ORIGINS=<your frontend domain>, APP_ENV=production
```

**Frontend** (Vercel or any Node host)

```
Build command:  npm run build
Start command:  npm start
Env:            NEXT_PUBLIC_API_URL=<backend URL>   # set in the host dashboard
```

Set `NEXT_PUBLIC_API_URL` in the host's environment variables — it is inlined at build time.
If it is missing in production the UI shows a configuration error instead of falling back to
`localhost`. Add the deployed frontend origin to the backend's `CORS_ORIGINS`.

The database file lives on the container filesystem; for a real deployment point `DATABASE_URL`
at PostgreSQL and introduce migrations (see `approach.md` §10).

---

## 8. Design

Full specification in [`design.md`](./design.md) — colours, typography, layout, sidebar,
dashboard, cards, buttons, tables, status badges, workflow stepper and responsive behaviour.

---

## 9. Known limitations

Honest list, matching the demo scope:

- **No authentication.** Intentionally excluded for SIH. Anyone with the URL has full access.
- **No government registry integration.** GST/PAN/Udyam use local format and checksum rules.
- **OCR, requirement extraction and confidence scores are simulated**, not ML-derived.
- **Single-process SQLite.** Not built for concurrent multi-user writes.
- **No migrations.** Schema is created at startup; fine for a demo, not for production.

---

## 10. Licence

Provided as an SIH 2026 demonstration project.
