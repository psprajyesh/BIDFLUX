"""Live two-server end-to-end verification for BIDFLUX.

Starts a real uvicorn on http://127.0.0.1:8123 and the built Next.js frontend on
http://127.0.0.1:3000, then walks the whole SIH scenario over actual HTTP. The
checks mirror backend/tests/test_workflow.py (same numbers) plus the web wiring
checks a TestClient run cannot show: static routes render, the client bundle
carries the configured API base, and CORS answers cross-origin requests.

It always uses throwaway data: DATABASE_URL and STORAGE_DIR are pointed at a temp
directory, so the checked-in bidflux.db and backend/storage/ are never touched.

Usage (from anywhere):
    backend\\.venv\\Scripts\\python.exe backend\\live_e2e.py [--no-build]

Exit status:
    0  every check passed, both servers stopped, temp data removed
    1  a check failed, a server would not start, or teardown leaked a process
"""

from __future__ import annotations

import glob
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"

API_HOST = "127.0.0.1"
API_PORT = 8123
WEB_PORT = 3000
API_BASE = f"http://{API_HOST}:{API_PORT}"
WEB_BASE = f"http://127.0.0.1:{WEB_PORT}"
API_ORIGIN = "http://localhost:3000"

WORKDIR = Path(os.environ.get("TEMP", "/tmp")) / "bidflux-live-e2e"
LOG_API = WORKDIR / "api.log"
LOG_WEB = WORKDIR / "web.log"
DB_URL = f"sqlite:///{(WORKDIR / 'live.db').as_posix()}"
STORAGE_DIR = WORKDIR / "storage"

DEMO_REQUIREMENTS = 8
DEMO_DOCUMENTS = 5
DEMO_VERIFIED = 7
GOOD_DECISION = {
    "decision": "CLARIFICATION_REQUESTED",
    "comment": "OEM authorisation letter not supplied; request clarification.",
    "officer_name": "R. Iyer",
    "officer_id": "OFF-2026-014",
}
FRONTEND_ROUTES = [
    ("/", "root dashboard"),
    ("/verification", "case list"),
    ("/verification/new", "new case"),
    ("/verification/VER-2026-000001", "case detail (dynamic)"),
    ("/documents", "documents"),
    ("/compliance", "compliance"),
    ("/evidence", "evidence"),
    ("/audit", "audit"),
    ("/reports", "reports"),
    ("/settings", "settings"),
]
EVIDENCE_LEVELS = [
    "Bidder",
    "Document",
    "ExtractedData",
    "Verification",
    "Requirement",
    "ComplianceResult",
]
AUDIT_EXPECTED = {
    "TENDER_UPLOADED",
    "REQUIREMENTS_EXTRACTED",
    "DOCUMENTS_UPLOADED",
    "DOCUMENTS_PROCESSED",
    "VERIFICATION_COMPLETED",
    "COMPLIANCE_CALCULATED",
    "RISK_CALCULATED",
    "RECOMMENDATION_GENERATED",
    "OFFICER_DECISION_RECORDED",
    "DOCUMENT_MISSING",
}

GLOBAL_TIMEOUT_S = 330
RUN_START = time.monotonic()

results: list[tuple[str, bool, str]] = []
client = None  # httpx.Client


def report(label: str, detail: str) -> None:
    results.append((label, True, detail))


def fail(label: str, detail: str) -> None:
    results.append((label, False, detail))


def elapsed() -> float:
    return time.monotonic() - RUN_START


def check_assert(label: str, fn) -> None:
    if elapsed() > GLOBAL_TIMEOUT_S:
        fail(label, "aborted: global watchdog exceeded")
        return
    try:
        detail = fn()
        report(label, str(detail) if detail else "ok")
    except Exception as exc:  # noqa: BLE001 - the runner reports every failure
        fail(label, f"{type(exc).__name__}: {exc}")


def wait_for_port(port: int, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((API_HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def wait_until_healthy() -> None:
    """Block until the API health endpoint answers."""
    for _ in range(40):
        try:
            if client.get(f"{API_BASE}/api/health", timeout=2.0).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1.0)
    _dump_logs("API never became healthy")
    raise RuntimeError("API did not become healthy within 40s")


def wait_until_web_healthy() -> None:
    """Block until the frontend root answers after `next start` has launched."""
    for _ in range(30):
        try:
            if client.get(f"{WEB_BASE}/", timeout=2.0).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1.0)
    _dump_logs("frontend never became healthy")
    raise RuntimeError("frontend did not become healthy within 30s")


def _dump_logs(why: str) -> None:
    print(f"\n[logs] {why}\n")
    for path in (LOG_API, LOG_WEB):
        if path.exists():
            print(f"--- {path.name} ---")
            print(path.read_text(errors="replace")[-4000:])


def _require_build() -> None:
    """Produce an up-to-date bundle so the web checks are meaningful."""
    if "--no-build" in sys.argv:
        return
    node = shutil.which("node")
    next_bin = FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"
    if not node:
        raise RuntimeError("node not found on PATH (needed to build the frontend)")
    if not next_bin.exists():
        raise RuntimeError(f"next executable missing: {next_bin}\n   run `npm install` in {FRONTEND}")
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = API_BASE
    proc = subprocess.Popen(
        [node, str(next_bin), "build"],
        cwd=str(FRONTEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        code = proc.wait(timeout=240)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("frontend build timed out after 240s")
    if code != 0:
        raise RuntimeError(f"frontend build failed (exit {code})")


def _stop(proc: subprocess.Popen | None, label: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    if proc.poll() is None:
        fail(label, "process leaked after teardown")


# --------------------------------------------------------------------------- #
# Checks (each mirrors a stage of the SIH scenario)
# --------------------------------------------------------------------------- #


def c_health():
    body = client.get(f"{API_BASE}/api/health", timeout=8).json()
    assert body["status"] == "ok"
    assert body["ai_mode"] == "mock"
    caps = body["capabilities"]
    assert "no government API" in caps["registry_verification"]
    for cap in ("case_management", "file_storage", "compliance_rules", "risk_scoring",
                "audit_trail", "evidence_chain", "officer_decision"):
        assert caps[cap] == "real", cap
    return f"ai_mode={body['ai_mode']}"


def c_demo_load():
    first = client.post(f"{API_BASE}/api/demo/load", timeout=8).json()
    second = client.post(f"{API_BASE}/api/demo/load", timeout=8).json()
    assert first["tender_reference"] == "TND/2026/001"
    assert first["tender_title"] == "Supply of Medical Equipment"
    assert first["bidder_name"] == "ABC Technologies"
    assert first["requirements"] == DEMO_REQUIREMENTS
    assert first["documents"] == DEMO_DOCUMENTS
    assert second["verification_id"] == first["verification_id"]
    cases = client.get(f"{API_BASE}/api/verifications", timeout=8).json()
    assert len(cases) == 1
    return f"case {first['verification_id']} ({DEMO_REQUIREMENTS} req, {DEMO_DOCUMENTS} docs)"


def c_tender(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/tender", timeout=8).json()
    requirements = body["requirements"]
    assert len(requirements) == DEMO_REQUIREMENTS
    codes = {r["code"] for r in requirements}
    assert "OEM_AUTHORIZATION" in codes
    assert {"GST_REGISTRATION", "PAN", "UDYAM_REGISTRATION", "MINIMUM_EXPERIENCE"} <= codes
    assert all(0.0 < r["confidence"] <= 1.0 for r in requirements)
    assert body["notice"]
    return f"{len(requirements)} requirements with confidence"


def c_documents(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/documents", timeout=8).json()
    assert len(body["documents"]) == DEMO_DOCUMENTS
    fields = {
        f["field_name"]: f
        for doc in body["documents"]
        for f in doc["extracted_fields"]
    }
    assert fields["GSTIN"]["field_value"] == "37XXXXXXXXXX1Z5"
    assert abs(fields["GSTIN"]["confidence"] - 0.98) < 1e-9
    assert fields["PAN"]["field_value"] == "ABCDE1234F"
    assert fields["Udyam Number"]["field_value"] == "UDYAM-AP-XX-XXXXXXX"
    assert fields["Company"]["field_value"] == "ABC Technologies"
    assert all(f["extraction_mode"] == "MOCK" for f in fields.values())
    assert body["missing_expected"] == ["OEM Authorization Letter"]
    return f"{DEMO_DOCUMENTS} docs, 4 exact fields, MOCK flagged, OEM missing"


def c_run(vid):
    body = client.post(f"{API_BASE}/api/verifications/{vid}/verification/run", timeout=8).json()
    assert body["results"] == DEMO_REQUIREMENTS
    assert body["verified"] == DEMO_VERIFIED
    assert body["missing"] == 1
    assert body["mode"] == "RULE"
    results_body = client.get(f"{API_BASE}/api/verifications/{vid}/verification", timeout=8).json()
    by_code = {r["requirement_code"]: r for r in results_body}
    assert by_code["OEM_AUTHORIZATION"]["status"] == "MISSING"
    assert by_code["OEM_AUTHORIZATION"]["method"] == "PRESENCE"
    assert by_code["MINIMUM_EXPERIENCE"]["status"] == "VERIFIED"
    assert by_code["MINIMUM_EXPERIENCE"]["method"] == "THRESHOLD"
    assert all("LOCAL_RULE" in r["source"] for r in results_body)
    return f"{DEMO_VERIFIED} verified, 1 missing, mode RULE"


def c_dashboard_scale(vid):
    dashboard = client.get(f"{API_BASE}/api/dashboard", timeout=8).json()
    rate = dashboard["compliance_rate"]
    assert isinstance(rate, (int, float)) and 0.0 <= rate <= 100.0, f"rate {rate} not 0-100"
    assert rate > 80.0, f"expected ~87.5 but got {rate}"
    return f"compliance_rate={rate} (0-100 scale, not a fraction)"


def c_compliance(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/compliance", timeout=8).json()
    assert body["total"] == DEMO_REQUIREMENTS
    assert body["pass_count"] == DEMO_VERIFIED
    assert body["review_count"] == 1
    assert body["fail_count"] == 0
    rows = {r["requirement_code"]: r for r in body["rows"]}
    assert rows["OEM_AUTHORIZATION"]["status"] == "REVIEW"
    assert rows["GST_REGISTRATION"]["status"] == "PASS"
    return f"{body['pass_count']} PASS / {body['review_count']} REVIEW"


def c_risk(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/risk", timeout=8).json()
    assert body["level"] == "HIGH"
    assert body["score"] == 55
    assert body["verified_count"] == DEMO_VERIFIED
    assert body["total_count"] == DEMO_REQUIREMENTS
    assert len(body["reasons"]) == 3
    joined = " ".join(body["reasons"]).lower()
    assert "oem authorization" in joined
    assert "evidence incomplete" in joined
    assert "officer review" in joined
    return f"HIGH score=55 ({len(body['reasons'])} reasons, exactly 3)"


def c_recommendation(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/recommendation", timeout=8).json()
    assert body["code"] == "REQUIRES_OFFICER_REVIEW"
    assert body["risk_level"] == "HIGH"
    assert body["rationale"]
    assert any("officer" in line.lower() for line in body["rationale"])
    return body["code"]


def c_decision_validation(vid):
    for missing in ("decision", "comment", "officer_name", "officer_id"):
        payload = {k: v for k, v in GOOD_DECISION.items() if k != missing}
        response = client.post(f"{API_BASE}/api/verifications/{vid}/decision", json=payload, timeout=8)
        assert response.status_code == 422, f"{missing} should be required"
    response = client.post(
        f"{API_BASE}/api/verifications/{vid}/decision",
        json={**GOOD_DECISION, "comment": "short"},
        timeout=8,
    )
    assert response.status_code == 422
    return "missing fields and short comment all 422"


def c_decision(vid):
    response = client.post(f"{API_BASE}/api/verifications/{vid}/decision", json=GOOD_DECISION, timeout=8)
    assert response.status_code == 200
    decision = response.json()
    assert decision["officer_name"] == "R. Iyer"
    assert decision["officer_id"] == "OFF-2026-014"
    assert decision["decision"] == "CLARIFICATION_REQUESTED"
    stored = client.get(f"{API_BASE}/api/verifications/{vid}/decision", timeout=8).json()
    assert stored["id"] == decision["id"]
    detail = client.get(f"{API_BASE}/api/verifications/{vid}", timeout=8).json()
    assert detail["status"] == "FINAL_DECISION"
    assert detail["has_decision"] is True
    return f"{decision['decision']} recorded, case FINAL_DECISION"


def c_evidence(vid):
    body = client.get(f"{API_BASE}/api/verifications/{vid}/evidence", timeout=8).json()
    levels = [level["entity"] for level in body["levels"]]
    assert levels == EVIDENCE_LEVELS
    assert body["bidder"]["name"] == "ABC Technologies"
    assert body["chains"]
    for chain in body["chains"]:
        assert chain["document_label"]
        assert chain["field_name"]
        assert chain["field_value"]
    gst = next(c for c in body["chains"] if c["requirement_code"] == "GST_REGISTRATION")
    assert gst["field_name"] == "GSTIN"
    assert gst["field_value"] == "37XXXXXXXXXX1Z5"
    assert abs(gst["confidence"] - 0.98) < 1e-9
    assert gst["document_label"] == "GST Certificate"
    assert gst["compliance_status"] == "PASS"
    unlinked = next(c for c in body["chains"] if c["requirement_code"] == "")
    assert unlinked["compliance_status"] == "NOT_APPLICABLE"
    assert "not linked" in unlinked["compliance_reason"].lower()
    return f"{len(EVIDENCE_LEVELS)} levels, {len(body['chains'])} chains traced"


def c_audit(vid):
    events = client.get(f"{API_BASE}/api/verifications/{vid}/audit", timeout=8).json()
    types = [event["event_type"] for event in events]
    for expected in AUDIT_EXPECTED:
        assert expected in types, f"missing audit event {expected}"
    assert types.count("FIELD_VERIFIED") == DEMO_VERIFIED
    times = [event["created_at"] for event in events]
    assert times == sorted(times)
    return f"{len(events)} append-ordered events, {DEMO_VERIFIED} FIELD_VERIFIED"


def c_uploads(vid):
    blocked = client.post(
        f"{API_BASE}/api/verifications/{vid}/documents",
        data={"doc_type": "OTHER", "label": "payload"},
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
        timeout=8,
    )
    assert blocked.status_code == 422

    accepted = client.post(
        f"{API_BASE}/api/verifications/{vid}/documents",
        data={"doc_type": "OTHER", "label": "notes"},
        files={"file": ("../../../etc/passwd.txt", b"plain text notes", "text/plain")},
        timeout=8,
    )
    assert accepted.status_code == 201
    shown = accepted.json()["file_name"]
    assert ".." not in shown
    assert "/" not in shown and "\\" not in shown
    assert shown == "passwd.txt"

    stored = list(STORAGE_DIR.glob("*.txt"))
    assert stored, "upload should have been written to storage"
    for path in stored:
        assert path.name != "passwd.txt"
        assert len(path.stem) == 32, f"{path.name} is not an opaque generated name"
    return "exe refused; traversal sanitised; opaque stored name"


def c_reports(vid):
    body = client.get(f"{API_BASE}/api/reports/summary", timeout=8).json()
    assert body["total"] >= 1
    assert body["rows"]
    assert body["generated_at"]
    return f"{body['total']} report row(s) with generated_at"


def c_reset(vid):
    before = client.get(f"{API_BASE}/api/dashboard", timeout=8).json()
    assert before["total_verifications"] >= 1
    response = client.post(f"{API_BASE}/api/demo/reset", timeout=8)
    assert response.status_code == 200
    assert response.json()["deleted_verifications"] >= 1
    assert client.get(f"{API_BASE}/api/verifications", timeout=8).json() == []
    dashboard = client.get(f"{API_BASE}/api/dashboard", timeout=8).json()
    assert dashboard["total_verifications"] == 0
    assert dashboard["compliance_rate"] == 0
    assert client.get(f"{API_BASE}/api/verifications/{vid}", timeout=8).status_code == 404

    # The scenario can be re-seeded cleanly after a reset.
    reloaded = client.post(f"{API_BASE}/api/demo/load", timeout=8).json()
    assert reloaded["verification_id"] == vid
    return "cleared; dashboard zeroed; re-load returns the same id"


def w_routes():
    checked = []
    for path, label in FRONTEND_ROUTES:
        response = client.get(f"{WEB_BASE}{path}", timeout=15)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        checked.append(label)
    return ", ".join(checked)


def w_shell():
    html = client.get(f"{WEB_BASE}/", timeout=15).text
    assert "BIDFLUX" in html
    assert "Evidence Chain" in html
    return "brand + sidebar nav in served HTML"


def w_bundle():
    hits = 0
    for path in glob.glob(str(FRONTEND / ".next" / "static" / "chunks" / "*.js")):
        with open(path, "rb") as handle:
            if b"127.0.0.1:8123" in handle.read():
                hits += 1
    assert hits, "client bundle missing the configured NEXT_PUBLIC_API_URL"
    return f"API base baked into {hits} chunk(s)"


def w_cors():
    preflight = client.request(
        "OPTIONS",
        f"{API_BASE}/api/verifications",
        headers={
            "Origin": API_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=8,
    )
    assert "access-control-allow-origin" in preflight.headers
    assert preflight.headers["access-control-allow-origin"].rstrip("/") == API_ORIGIN
    simple = client.get(
        f"{API_BASE}/api/health",
        headers={"Origin": API_ORIGIN},
        timeout=8,
    )
    assert "access-control-allow-origin" in simple.headers
    assert simple.headers["access-control-allow-origin"].rstrip("/") == API_ORIGIN
    return "OPTIONS preflight + simple GET both answer the browser origin"


def main() -> int:
    global client

    try:
        import httpx
    except ImportError:
        print("httpx is required: run this script with backend\\.venv\\Scripts\\python.exe")
        return 1

    if WORKDIR.exists():
        shutil.rmtree(WORKDIR, ignore_errors=True)
    WORKDIR.mkdir(parents=True)
    STORAGE_DIR.mkdir(parents=True)

    backend_env = os.environ.copy()
    backend_env["DATABASE_URL"] = DB_URL
    backend_env["STORAGE_DIR"] = str(STORAGE_DIR)
    backend_env["CORS_ORIGINS"] = API_ORIGIN
    backend_env["APP_ENV"] = "test"

    api_proc: subprocess.Popen | None = None
    web_proc: subprocess.Popen | None = None

    try:
        _require_build()

        api_log = open(LOG_API, "w", encoding="utf-8", errors="replace")
        try:
            api_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    API_HOST,
                    "--port",
                    str(API_PORT),
                ],
                cwd=str(BACKEND),
                env=backend_env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
            )
        finally:
            api_log.close()

        client = httpx.Client(timeout=httpx.Timeout(8.0), follow_redirects=True)
        wait_until_healthy()

        try:
            web_log = open(LOG_WEB, "w", encoding="utf-8", errors="replace")
            try:
                node = shutil.which("node")
                if not node:
                    raise RuntimeError("node not found on PATH (needed for `next start`)")
                web_proc = subprocess.Popen(
                    [node, str(FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"),
                     "start", "-p", str(WEB_PORT)],
                    cwd=str(FRONTEND),
                    stdout=web_log,
                    stderr=subprocess.STDOUT,
                )
            finally:
                web_log.close()
            if not wait_for_port(WEB_PORT, 30):
                _dump_logs("frontend port never opened")
                raise RuntimeError("next start did not open port 3000 within 30s")
            wait_until_web_healthy()
        except Exception:
            _stop(api_proc, "api")
            raise

        vid = client.post(f"{API_BASE}/api/demo/load", timeout=8).json()["verification_id"]

        scenario = [
            ("01 health/registry-mock", lambda: c_health()),
            ("02 demo load deterministic", lambda: c_demo_load()),
            ("03 tender requirements", lambda: c_tender(vid)),
            ("04 documents + extraction values", lambda: c_documents(vid)),
            ("05 verification run (7/8)", lambda: c_run(vid)),
            ("06 compliance matrix", lambda: c_compliance(vid)),
            ("06b dashboard rate is 0-100", lambda: c_dashboard_scale(vid)),
            ("07 risk scoring", lambda: c_risk(vid)),
            ("08 recommendation", lambda: c_recommendation(vid)),
            ("09 decision validation (422)", lambda: c_decision_validation(vid)),
            ("10 decision persisted", lambda: c_decision(vid)),
            ("11 evidence chain", lambda: c_evidence(vid)),
            ("12 audit trail", lambda: c_audit(vid)),
            ("13 upload hardening", lambda: c_uploads(vid)),
            ("14 reports summary", lambda: c_reports(vid)),
            ("15 reset cleanly", lambda: c_reset(vid)),
        ]
        web = [
            ("16 web routes render", lambda: w_routes()),
            ("17 served HTML shell", lambda: w_shell()),
            ("18 bundle carries API base", lambda: w_bundle()),
            ("19 CORS answers browser origin", lambda: w_cors()),
        ]

        for label, fn in scenario + web:
            check_assert(label, fn)

    except RuntimeError as exc:
        print(f"\n[setup error] {exc}")
        return 1
    finally:
        _stop(web_proc, "web")
        _stop(api_proc, "api")

    passed = 0
    for label, ok, detail in results:
        tag = "PASS" if ok else "FAIL"
        print(f"{tag}  {label:<38} {detail}")
        passed += ok

    failed = len(results) - passed
    print("")
    if failed == 0:
        print(f"ALL PASSED ({len(results)} checks)")
        if results and elapsed() < GLOBAL_TIMEOUT_S:
            shutil.rmtree(WORKDIR, ignore_errors=True)
        return 0

    print(f"FAILURES ({failed}/{len(results)}), logs kept at {WORKDIR}")
    _dump_logs("failures above")
    return 1


if __name__ == "__main__":
    sys.exit(main())