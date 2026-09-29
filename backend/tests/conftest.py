"""Shared pytest fixtures.

Every test runs against a throwaway SQLite file and an empty storage directory, so
the suite never touches the developer's real database. Tables are dropped and
recreated per test, which keeps tests independent regardless of execution order.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

TMP_ROOT = Path(tempfile.mkdtemp(prefix="bidflux-tests-"))
# setdefault, not assignment: an explicit DATABASE_URL from the environment wins.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(TMP_ROOT / 'test.db').as_posix()}")
os.environ.setdefault("STORAGE_DIR", str(TMP_ROOT / "storage"))
os.environ.setdefault("MAX_UPLOAD_MB", "1")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient over a database that is empty before and after each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def demo_case(client: TestClient) -> dict:
    """Load the deterministic SIH demo scenario and return its payload."""
    response = client.post("/api/demo/load")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def demo_id(demo_case: dict) -> str:
    return demo_case["verification_id"]


@pytest.fixture
def verified_demo(client: TestClient, demo_id: str) -> str:
    """The demo case with verification run, so compliance can be computed."""
    response = client.post(f"/api/verifications/{demo_id}/verification/run")
    assert response.status_code == 200, response.text
    return demo_id


@pytest.fixture
def assessed_demo(verified_demo: str, client: TestClient) -> str:
    """The demo case taken through compliance, risk and recommendation.

    The pipeline is strictly ordered — compliance before risk, risk before a
    recommendation or a decision — so tests of the later stages need this.
    """
    for stage in ("compliance", "risk", "recommendation"):
        response = client.get(f"/api/verifications/{verified_demo}/{stage}")
        assert response.status_code == 200, f"{stage}: {response.text}"
    return verified_demo



@pytest.fixture
def new_case(client: TestClient) -> str:
    """An empty verification, used for upload-validation tests."""
    response = client.post(
        "/api/verifications",
        json={"title": "Fresh verification", "tender_reference": "TND/2026/999"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
