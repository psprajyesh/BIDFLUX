"""MOCK requirement extraction from a tender.

`extract_requirements` is the seam where a real LLM call would go. The current
implementation is deterministic: it scans the tender text for the keyword set of each
canonical requirement. A tender that omits a clause yields fewer requirements — the
result is never a fixed list.
"""

from __future__ import annotations

import re

from ..config import Settings
from ..enums import ProcessingMode, RequirementSource
from ..errors import ValidationError
from .fixtures import REQUIREMENT_CATALOGUE, RequirementSpec

_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WS.sub(" ", (text or "").lower())


def extract_requirements(tender_text: str, settings: Settings) -> tuple[list[RequirementSpec], str]:
    """Return the requirements matched from ``tender_text`` plus the mode used.

    Mode is ``RULE`` when the tender supplied readable text and ``MOCK`` when the
    format carried no text and the canonical clause set was assumed.
    """
    text = normalise(tender_text)

    if not settings.ai_enabled:
        return [], ProcessingMode.RULE.value

    if not text.strip():
        # No readable text (e.g. a binary PDF). The demo assumes the full clause set
        # so the workflow can proceed; this is explicitly simulated.
        return list(REQUIREMENT_CATALOGUE), ProcessingMode.MOCK.value

    matched = [
        spec
        for spec in REQUIREMENT_CATALOGUE
        if any(keyword in text for keyword in spec.keywords)
    ]

    if not matched:
        raise ValidationError(
            "No procurement requirements were recognised in this tender document.",
            detail={"hint": "Upload a .txt tender, or load the SIH demo data."},
        )

    return matched, ProcessingMode.RULE.value


def build_requirement_rows(
    specs: list[RequirementSpec], tender_id: int, verification_id: str
) -> list:
    """Materialise :class:`Requirement` ORM objects from extracted specs."""
    from ..enums import RequirementCategory
    from ..models import Requirement

    return [
        Requirement(
            verification_id=verification_id,
            tender_id=tender_id,
            code=spec.code,
            title=spec.title,
            description=spec.description,
            category=spec.category.value,
            is_mandatory=spec.is_mandatory,
            source=RequirementSource.AI_EXTRACTED.value,
            confidence=spec.confidence,
            threshold_value=spec.threshold,
            sort_order=index,
            validated_by_officer=False,
        )
        for index, spec in enumerate(specs, start=1)
    ]
