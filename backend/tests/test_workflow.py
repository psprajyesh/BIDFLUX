"""End-to-end workflow tests for the BIDFLUX demo scenario.

Fourteen tests, one per stage or property that matters to the demo. They run against
the deterministic SIH dataset, so they assert real values rather than shapes alone.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# The deterministic demo fixture. These are the values the scenario must produce.
DEMO_REQUIREMENTS = 8
DEMO_DOCUMENTS = 5
DEMO_VERIFIED = 7
DEMO_MISSING_CODE = "OEM_AUTHORIZATION"
DEMO_RISK_LEVEL = "HIGH"
DEMO_RECOMMENDATION = "REQUIRES_OFFICER_REVIEW"


def test_01_health_reports_registry_as_mock(client: TestClient) -> None:
    """The service is up and never claims a live government registry."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_mode"] == "mock"

    capabilities = body["capabilities"]
    assert "no government API" in capabilities["registry_verification"]
    # The parts that must be real are real.
    for capability in (
        "case_management",
        "file_storage",
        "compliance_rules",
        "risk_scoring",
        "audit_trail",
        "evidence_chain",
        "officer_decision",
    ):
        assert capabilities[capability] == "real", capability


def test_02_demo_load_is_deterministic(client: TestClient) -> None:
    """Loading twice yields the same tender, requirements and document count."""
    first = client.post("/api/demo/load").json()
    second = client.post("/api/demo/load").json()

    assert first["tender_reference"] == "TND/2026/001"
    assert first["tender_title"] == "Supply of Medical Equipment"
    assert first["bidder_name"] == "ABC Technologies"
    assert first["requirements"] == DEMO_REQUIREMENTS
    assert first["documents"] == DEMO_DOCUMENTS

    # Idempotent: the scenario is replaced, not accumulated.
    assert second["verification_id"] == first["verification_id"]
    assert len(client.get("/api/verifications").json()) == 1


def test_03_requirements_are_extracted_with_confidence(client: TestClient, demo_id: str) -> None:
    """Eight eligibility requirements exist, each with an extraction confidence."""
    body = client.get(f"/api/verifications/{demo_id}/tender").json()
    requirements = body["requirements"]

    assert len(requirements) == DEMO_REQUIREMENTS
    codes = {r["code"] for r in requirements}
    assert DEMO_MISSING_CODE in codes
    assert {"GST_REGISTRATION", "PAN", "UDYAM_REGISTRATION", "MINIMUM_EXPERIENCE"} <= codes
    assert all(0.0 < r["confidence"] <= 1.0 for r in requirements)
    assert body["notice"], "AI validation notice must be present"


def test_04_documents_and_extraction_values(client: TestClient, demo_id: str) -> None:
    """Five documents are on file and the required field values are exact."""
    body = client.get(f"/api/verifications/{demo_id}/documents").json()
    assert len(body["documents"]) == DEMO_DOCUMENTS

    fields = {
        field["field_name"]: field
        for doc in body["documents"]
        for field in doc["extracted_fields"]
    }
    assert fields["GSTIN"]["field_value"] == "37XXXXXXXXXX1Z5"
    assert fields["GSTIN"]["confidence"] == pytest.approx(0.98)
    assert fields["PAN"]["field_value"] == "ABCDE1234F"
    assert fields["Udyam Number"]["field_value"] == "UDYAM-AP-XX-XXXXXXX"
    assert fields["Company"]["field_value"] == "ABC Technologies"

    # Extraction is simulated and must say so.
    assert all(f["extraction_mode"] == "MOCK" for f in fields.values())

    # The OEM letter is expected but deliberately absent.
    assert body["missing_expected"] == ["OEM Authorization Letter"]


def test_05_verification_marks_seven_verified_and_one_missing(
    client: TestClient, demo_id: str
) -> None:
    """7 of 8 requirements verify; the OEM authorisation is MISSING."""
    run = client.post(f"/api/verifications/{demo_id}/verification/run")
    assert run.status_code == 200
    body = run.json()
    assert body["results"] == DEMO_REQUIREMENTS
    assert body["verified"] == DEMO_VERIFIED
    assert body["missing"] == 1
    assert body["mode"] == "RULE"

    results = client.get(f"/api/verifications/{demo_id}/verification").json()
    by_code = {r["requirement_code"]: r for r in results}
    assert by_code[DEMO_MISSING_CODE]["status"] == "MISSING"
    assert by_code[DEMO_MISSING_CODE]["method"] == "PRESENCE"
    assert by_code["MINIMUM_EXPERIENCE"]["status"] == "VERIFIED"
    assert by_code["MINIMUM_EXPERIENCE"]["method"] == "THRESHOLD"

    # No result may imply a government registry was queried.
    assert all("LOCAL_RULE" in r["source"] for r in results)


def test_06_compliance_is_computed_from_results(client: TestClient, verified_demo: str) -> None:
    """Compliance derives from stored verification results: 7 PASS, 1 REVIEW."""
    body = client.get(f"/api/verifications/{verified_demo}/compliance").json()
    assert body["total"] == DEMO_REQUIREMENTS
    assert body["pass_count"] == DEMO_VERIFIED
    assert body["review_count"] == 1
    assert body["fail_count"] == 0

    rows = {r["requirement_code"]: r for r in body["rows"]}
    assert rows[DEMO_MISSING_CODE]["status"] == "REVIEW"
    assert rows["GST_REGISTRATION"]["status"] == "PASS"


def test_07_risk_is_high_for_the_demo_case(client: TestClient, assessed_demo: str) -> None:
    """Score 55 lands in the HIGH band, with reasons naming the real gap."""
    body = client.get(f"/api/verifications/{assessed_demo}/risk").json()
    assert body["level"] == DEMO_RISK_LEVEL
    assert body["score"] == 55
    assert body["verified_count"] == DEMO_VERIFIED
    assert body["total_count"] == DEMO_REQUIREMENTS

    # Exactly the three findings the case actually produces.
    assert len(body["reasons"]) == 3
    joined = " ".join(body["reasons"]).lower()
    assert "oem authorization" in joined
    assert "evidence incomplete" in joined
    assert "officer review" in joined


def test_08_recommendation_requires_officer_review(client: TestClient, assessed_demo: str) -> None:
    """The recommendation is advisory and points at the missing document."""
    body = client.get(f"/api/verifications/{assessed_demo}/recommendation").json()
    assert body["code"] == DEMO_RECOMMENDATION
    assert body["risk_level"] == DEMO_RISK_LEVEL
    assert body["rationale"]
    assert any("officer" in line.lower() for line in body["rationale"])


def test_09_decision_requires_all_officer_fields(client: TestClient, assessed_demo: str) -> None:
    """Officer name, ID, decision and comment are all mandatory."""
    complete = {
        "decision": "CLARIFICATION_REQUESTED",
        "comment": "OEM authorisation letter not supplied; request clarification.",
        "officer_name": "R. Iyer",
        "officer_id": "OFF-2026-014",
    }

    for missing in ("decision", "comment", "officer_name", "officer_id"):
        payload = {k: v for k, v in complete.items() if k != missing}
        response = client.post(f"/api/verifications/{assessed_demo}/decision", json=payload)
        assert response.status_code == 422, f"{missing} should be required"

    # A comment that is present but too short is also rejected.
    response = client.post(
        f"/api/verifications/{assessed_demo}/decision",
        json={**complete, "comment": "short"},
    )
    assert response.status_code == 422


def test_10_decision_is_persisted_and_closes_the_case(
    client: TestClient, assessed_demo: str
) -> None:
    """A valid decision is stored and moves the case to FINAL_DECISION."""
    response = client.post(
        f"/api/verifications/{assessed_demo}/decision",
        json={
            "decision": "CLARIFICATION_REQUESTED",
            "comment": "OEM authorisation letter not supplied; request clarification.",
            "officer_name": "R. Iyer",
            "officer_id": "OFF-2026-014",
        },
    )
    assert response.status_code == 200
    decision = response.json()
    assert decision["officer_name"] == "R. Iyer"
    assert decision["officer_id"] == "OFF-2026-014"
    assert decision["decision"] == "CLARIFICATION_REQUESTED"

    stored = client.get(f"/api/verifications/{assessed_demo}/decision").json()
    assert stored["id"] == decision["id"]

    detail = client.get(f"/api/verifications/{assessed_demo}").json()
    assert detail["status"] == "FINAL_DECISION"
    assert detail["has_decision"] is True


def test_11_evidence_chain_has_six_levels(client: TestClient, assessed_demo: str) -> None:
    """Evidence is traceable across all six levels back to a source document."""
    body = client.get(f"/api/verifications/{assessed_demo}/evidence").json()

    levels = [level["entity"] for level in body["levels"]]
    assert levels == [
        "Bidder",
        "Document",
        "ExtractedData",
        "Verification",
        "Requirement",
        "ComplianceResult",
    ]
    assert body["bidder"]["name"] == "ABC Technologies"
    assert body["chains"], "at least one traced chain is required"

    # Every chain terminates at a real document and a real field.
    for chain in body["chains"]:
        assert chain["document_label"]
        assert chain["field_name"]
        assert chain["field_value"]

    gst = next(c for c in body["chains"] if c["requirement_code"] == "GST_REGISTRATION")
    assert gst["field_name"] == "GSTIN"
    assert gst["field_value"] == "37XXXXXXXXXX1Z5"
    assert gst["confidence"] == pytest.approx(0.98)
    assert gst["document_label"] == "GST Certificate"
    assert gst["compliance_status"] == "PASS"

    # A field that maps to no requirement is informational, not an exception.
    unlinked = next(c for c in body["chains"] if c["requirement_code"] == "")
    assert unlinked["compliance_status"] == "NOT_APPLICABLE"
    assert "not linked" in unlinked["compliance_reason"].lower()


def test_12_audit_trail_records_every_stage(client: TestClient, assessed_demo: str) -> None:
    """Each workflow stage writes an audit event as it happens."""
    client.post(
        f"/api/verifications/{assessed_demo}/decision",
        json={
            "decision": "REJECTED",
            "comment": "Rejected for the demonstration of the audit trail.",
            "officer_name": "R. Iyer",
            "officer_id": "OFF-2026-014",
        },
    )

    events = client.get(f"/api/verifications/{assessed_demo}/audit").json()
    types = [event["event_type"] for event in events]

    for expected in (
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
    ):
        assert expected in types, f"missing audit event {expected}"

    # Field-level verification is recorded per result, not summarised.
    assert types.count("FIELD_VERIFIED") == DEMO_VERIFIED

    # The trail is append-only and time ordered.
    times = [event["created_at"] for event in events]
    assert times == sorted(times)


def test_13_upload_rejects_executables_and_sanitises_filenames(
    client: TestClient, demo_id: str
) -> None:
    """Executable types are refused and traversal names never reach storage."""
    blocked = client.post(
        f"/api/verifications/{demo_id}/documents",
        data={"doc_type": "OTHER", "label": "payload"},
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert blocked.status_code == 422

    accepted = client.post(
        f"/api/verifications/{demo_id}/documents",
        data={"doc_type": "OTHER", "label": "notes"},
        files={"file": ("../../../etc/passwd.txt", b"plain text notes", "text/plain")},
    )
    assert accepted.status_code == 201

    # The traversal path is stripped from the name shown to the user.
    shown_name = accepted.json()["file_name"]
    assert ".." not in shown_name
    assert "/" not in shown_name and "\\" not in shown_name
    assert shown_name == "passwd.txt"

    # But nothing on disk keeps the client-supplied name: the file is stored under an
    # opaque generated name, so an attacker cannot influence the storage path.
    from app.config import get_settings

    stored = list(get_settings().storage_dir.glob("*"))
    uploaded = [p for p in stored if p.suffix == ".txt"]
    assert uploaded, "the upload should have been written to storage"
    for path in uploaded:
        assert path.name != "passwd.txt"
        assert len(path.stem) == 32, f"{path.name} is not a generated name"
        assert path.parent == get_settings().storage_dir


def test_14_reset_clears_the_demo_workspace(client: TestClient, demo_id: str) -> None:
    """Reset removes demo cases, empties the dashboard and returns a 404 after."""
    assert client.get("/api/dashboard").json()["total_verifications"] >= 1

    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    assert response.json()["deleted_verifications"] >= 1

    assert client.get("/api/verifications").json() == []
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["total_verifications"] == 0
    assert dashboard["compliance_rate"] == 0
    assert client.get(f"/api/verifications/{demo_id}").status_code == 404
