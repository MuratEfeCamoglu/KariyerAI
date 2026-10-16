from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

# KVKK (F12): payload'a yalnızca id, durum, puan, model/prompt sürümü gibi kişisel olmayan
# değerler girer. Bilinen kişisel veri anahtarları burada ikinci savunma hattı olarak reddedilir.
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {"email", "full_name", "name", "phone", "password", "original_filename", "cv_text"}
)


def record(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    data = payload or {}
    leaked = _FORBIDDEN_PAYLOAD_KEYS.intersection(data)
    if leaked:
        raise ValueError(f"Audit payload kişisel veri alanı içeremez: {sorted(leaked)}")
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=data,
    )
    db.add(entry)
    return entry


RECENT_LIMIT = 500


def list_recent(db: Session, limit: int = RECENT_LIMIT) -> list[tuple[AuditLog, str | None]]:
    """F12: son kayıtlar, yeniden eskiye; işlemi yapanın adıyla (sistem işleri için None)."""
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return [(entry, name) for entry, name in rows]
