from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.schemas.audit import AuditLogOut
from app.services import audit as audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_logs(_admin: AdminUser, db: DbSession) -> list[AuditLogOut]:
    return [
        AuditLogOut(
            id=entry.id,
            actor_id=entry.actor_id,
            actor_name=actor_name,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            payload=entry.payload,
            created_at=entry.created_at,
        )
        for entry, actor_name in audit_service.list_recent(db)
    ]
