from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models import Note
from app.services.applications import get_application


def add_note(db: Session, *, application_id: int, author_id: int, body: str) -> Note:
    get_application(db, application_id)
    note = Note(application_id=application_id, author_id=author_id, body=body)
    db.add(note)
    db.commit()
    return note


def delete_note(db: Session, *, note_id: int, actor_id: int) -> None:
    """F10: not yalnızca yazarı tarafından silinebilir; admin dahil başkası 403 alır."""
    note = db.get(Note, note_id)
    if note is None:
        raise NotFoundError("Not bulunamadı")
    if note.author_id != actor_id:
        raise PermissionDeniedError("Yalnızca kendi notunuzu silebilirsiniz")
    db.delete(note)
    db.commit()
