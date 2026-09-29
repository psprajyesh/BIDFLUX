"""Append-only audit writer.

Injected into every other service so no service writes audit rows by hand, and
none can silently forget to. Rows are never updated or deleted by application code.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..enums import ActorType, AuditEventType


class AuditService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record(
        self,
        verification_id: str,
        event_type: AuditEventType,
        message: str,
        *,
        stage: str = "",
        actor: ActorType = ActorType.SYSTEM,
        metadata: dict | None = None,
    ) -> None:
        from ..models import AuditEvent

        self._db.add(
            AuditEvent(
                verification_id=verification_id,
                event_type=event_type.value,
                actor=actor.value,
                stage=stage,
                message=message,
                metadata_json=metadata or {},
            )
        )
