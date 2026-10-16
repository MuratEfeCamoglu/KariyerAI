from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: int | None
    payload: dict[str, Any]
    created_at: datetime
