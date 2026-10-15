import pytest
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.services import audit


def test_record_persists_entry(db: Session) -> None:
    audit.record(
        db, actor_id=None, action="job.create", entity_type="job", entity_id=7, payload={"x": 1}
    )
    db.commit()

    entry = db.query(AuditLog).one()
    assert (entry.action, entry.entity_type, entry.entity_id, entry.payload) == (
        "job.create",
        "job",
        7,
        {"x": 1},
    )
    assert entry.created_at is not None


@pytest.mark.parametrize("key", ["email", "full_name", "phone", "original_filename", "cv_text"])
def test_record_rejects_personal_data_keys(db: Session, key: str) -> None:
    with pytest.raises(ValueError, match="kişisel veri"):
        audit.record(
            db, actor_id=None, action="x", entity_type="x", entity_id=1, payload={key: "değer"}
        )
