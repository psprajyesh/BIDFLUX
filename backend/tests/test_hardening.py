"""Regression tests for the post-review hardening fixes.

These pin the behaviours added after the final review: JSON-safe 422 responses,
idempotent recomputation (no audit spam, honest ``computed_at``), risk signals,
stale-risk cleanup on re-analysis and a reset that also clears stored files.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings


def test_blank_title_returns_json_safe_422(client: TestClient) -> None:
    """Whitespace-only payloads yield a clean 422, never a tokeniser 500."""
    response = client.post("/api/verifications", json={"title": "   "})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    # The details must be JSON-serialisable (a ValueError ctx used to blow up here).
    assert isinstance(body["error"]["detail"], list)


def test_officer_name_that_strips_below_length_is_rejected(
    client: TestClient, demo_id: str
) -> None:
    """A name that collapses to fewer than the required characters is a 422."""
    response = client.post(
        f"/api/verifications/{demo_id}/decision",
        json={
            "decision": "APPROVED",
            "comment": "This comment is comfortably long enough.",
            "officer_name": "   a   ",
            "officer_id": "OFF-2026-001",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_stripped_valid_title_is_accepted(client: TestClient) -> None:
    """Validators run before length checks, so padded input should normalise."""
    response = client.post(
        "/api/verifications", json={"title": "   New tender case   "}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "New tender case"


def test_recompute_is_idempotent_and_computed_at_is_stable(
    client: TestClient, assessed_demo: str
) -> None:
    """Re-opening compliance/risk does not spam the trail or re-date the result."""
    events = client.get(f"/api/verifications/{assessed_demo}/audit").json()

    def count(key: str) -> int:
        return sum(1 for e in events if e["event_type"] == key)

    assert count("COMPLIANCE_CALCULATED") == 1
    assert count("RISK_CALCULATED") == 1

    first_compliance = client.get(f"/api/verifications/{assessed_demo}/compliance").json()
    second_compliance = client.get(f"/api/verifications/{assessed_demo}/compliance").json()
    assert second_compliance["computed_at"] == first_compliance["computed_at"]

    first_risk = client.get(f"/api/verifications/{assessed_demo}/risk").json()
    second_risk = client.get(f"/api/verifications/{assessed_demo}/risk").json()
    assert second_risk["computed_at"] == first_risk["computed_at"]

    events = client.get(f"/api/verifications/{assessed_demo}/audit").json()
    assert sum(1 for e in events if e["event_type"] == "COMPLIANCE_CALCULATED") == 1
    assert sum(1 for e in events if e["event_type"] == "RISK_CALCULATED") == 1


def test_risk_response_has_contributing_signals(client: TestClient, assessed_demo: str) -> None:
    """The risk endpoint lists the weighted drivers, not an empty array."""
    body = client.get(f"/api/verifications/{assessed_demo}/risk").json()
    signals = {s["code"]: s for s in body["signals"]}

    assert "REVIEW_REQUIRED" in signals
    assert "MISSING_EVIDENCE" in signals
    assert signals["REVIEW_REQUIRED"]["weight"] == 35
    assert signals["MISSING_EVIDENCE"]["weight"] == 20
    # The demo case has no failing row and passes the 80% ratio, so those are absent.
    assert "NON_COMPLIANT_REQUIREMENTS" not in signals
    assert "LOW_VERIFIED_RATIO" not in signals


def test_reanalyse_drops_stale_risk(
    client: TestClient, verified_demo: str
) -> None:
    """Re-extracting requirements invalidates any risk computed from the old ones."""
    client.get(f"/api/verifications/{verified_demo}/compliance")
    client.get(f"/api/verifications/{verified_demo}/risk")
    assert client.get(f"/api/verifications/{verified_demo}/risk").status_code == 200

    response = client.post(f"/api/verifications/{verified_demo}/tender/analyse")
    assert response.status_code == 200

    # The fresh requirements have not been verified yet, so risk cannot exist.
    assert client.get(f"/api/verifications/{verified_demo}/risk").status_code == 409
    detail = client.get(f"/api/verifications/{verified_demo}").json()
    assert detail["has_risk"] is False


def test_reset_removes_stored_files(client: TestClient, demo_id: str) -> None:
    """A reset deletes the demo's files from disk, not just its database rows."""
    settings = get_settings()
    assert settings.storage_dir.exists()
    before = len(list(settings.storage_dir.glob("*")))
    assert before >= 6  # one tender + five bidder documents

    documents = client.get(f"/api/verifications/{demo_id}/documents").json()
    assert len(documents["documents"]) == 5
    # one tender file + five submitted documents, all written to storage
    assert before >= 6

    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    assert response.json()["deleted_verifications"] >= 1

    after = len(list(settings.storage_dir.glob("*")))
    # The six files belonging to the current demo case are gone (any files left by
    # earlier tests in the shared tmp dir are untouched).
    assert before - after >= 6