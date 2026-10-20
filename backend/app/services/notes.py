from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models import Application, Job, Note
from app.services.applications import get_application


def add_note(db: Session, *, application_id: int, author_id: int, body: str, owner_id: int) -> Note:
    get_application(db, application_id, owner_id=owner_id)
    note = Note(application_id=application_id, author_id=author_id, body=body)
    db.add(note)
    db.commit()
    return note


def delete_note(db: Session, *, note_id: int, actor_id: int, owner_id: int) -> None:
    """F10: not yalnızca yazarı tarafından silinebilir.

    Önce çalışma alanı kontrolü: başka İK uzmanının notu, olmayan not gibi 404 verir.
    """
    note = db.scalar(
        select(Note)
        .join(Application, Application.id == Note.application_id)
        .join(Job, Job.id == Application.job_id)
        .where(Note.id == note_id, Job.created_by == owner_id)
    )
    if note is None:
        raise NotFoundError("Not bulunamadı")
    if note.author_id != actor_id:
        raise PermissionDeniedError("Yalnızca kendi notunuzu silebilirsiniz")
    db.delete(note)
    db.commit()
