from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import (
    Application,
    ApplicationStatus,
    AuditLog,
    Candidate,
    Job,
    Note,
    ProcessingStatus,
    User,
)
from app.services import audit
from app.services.candidates import NO_TEXT, UNREADABLE
from app.services.jobs import get_job

PAGE_SIZE = 50

# Bu hatalar dosyanın kendisinden kaynaklanır; yeniden denemek sonucu değiştirmez.
_EXTRACTION_ERRORS = frozenset({NO_TEXT, UNREADABLE})
_ACTIVE = (ProcessingStatus.PENDING, ProcessingStatus.PROCESSING)


@dataclass(frozen=True)
class ApplicationFilters:
    min_score: int | None = None
    statuses: tuple[ApplicationStatus, ...] = ()
    parse_status: ProcessingStatus | None = None


@dataclass(frozen=True)
class ApplicationRow:
    application: Application
    candidate: Candidate


@dataclass(frozen=True)
class ApplicationPage:
    rows: list[ApplicationRow]
    total: int
    page: int
    page_size: int
    processing_count: int


def _filtered[*Ts](query: Select[*Ts], job_id: int, filters: ApplicationFilters) -> Select[*Ts]:
    query = query.where(Application.job_id == job_id)
    if filters.min_score:
        query = query.where(Application.score >= filters.min_score)
    if filters.statuses:
        query = query.where(Application.status.in_(filters.statuses))
    if filters.parse_status is not None:
        query = query.where(Candidate.parse_status == filters.parse_status)
    return query


def list_applications(
    db: Session, *, job_id: int, filters: ApplicationFilters, page: int
) -> ApplicationPage:
    """F7: puana göre azalan; puansızlar sonda; eşitlikte eskiden yeniye. 50 kayıt/sayfa."""
    get_job(db, job_id)
    base = select(Application, Candidate).join(Candidate, Candidate.id == Application.candidate_id)
    query = (
        _filtered(base, job_id, filters)
        .order_by(
            Application.score.desc().nulls_last(),
            Application.created_at.asc(),
            Application.id.asc(),
        )
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    )
    rows = [ApplicationRow(application=a, candidate=c) for a, c in db.execute(query).all()]

    count_query = _filtered(
        select(func.count(Application.id)).join(
            Candidate, Candidate.id == Application.candidate_id
        ),
        job_id,
        filters,
    )
    total = db.scalar(count_query) or 0

    # Otomatik yenileme filtreden bağımsız karar verir: ilanda işlenen kayıt kaldı mı (F7d)?
    processing_count = (
        db.scalar(
            select(func.count(Application.id))
            .join(Candidate, Candidate.id == Application.candidate_id)
            .where(
                Application.job_id == job_id,
                Candidate.parse_status.in_(_ACTIVE)
                | (
                    (Candidate.parse_status == ProcessingStatus.DONE)
                    & Application.score_status.in_(_ACTIVE)
                ),
            )
        )
        or 0
    )
    return ApplicationPage(
        rows=rows, total=total, page=page, page_size=PAGE_SIZE, processing_count=processing_count
    )


def _sort_key(experience: dict[str, Any]) -> tuple[int, str, str]:
    end = experience.get("end")
    return (1 if end == "present" else 0, str(end or ""), str(experience.get("start") or ""))


def last_position(parsed_data: dict[str, Any] | None) -> str | None:
    """Devam eden ya da en son biten deneyim; LLM'in sıralamasına güvenilmez."""
    experiences = (parsed_data or {}).get("experiences") or []
    if not experiences:
        return None
    latest = max(experiences, key=_sort_key)
    return str(latest.get("title")) if latest.get("title") else None


def mark_job_for_rescore(db: Session, job_id: int, *, actor_id: int | None) -> list[int]:
    """F6f: ayrıştırması tamamlanmış başvuruları yeniden puanlamaya alır; ayrıştırma tekrarlanmaz.

    Puanlaması sürmekte olanlar da "pending" yapılır; eski kriterlerle biten sonuç yazılmaz.
    """
    applications = db.scalars(
        select(Application)
        .join(Candidate, Candidate.id == Application.candidate_id)
        .where(
            Application.job_id == job_id,
            Candidate.parse_status == ProcessingStatus.DONE,
        )
        .order_by(Application.id)
    ).all()
    for application in applications:
        application.score_status = ProcessingStatus.PENDING
        application.score_error = None
    ids = [application.id for application in applications]
    audit.record(
        db,
        actor_id=actor_id,
        action="job.rescore",
        entity_type="job",
        entity_id=job_id,
        payload={"application_count": len(ids)},
    )
    db.commit()
    return ids


def retry_application(db: Session, *, application_id: int, actor_id: int) -> int:
    """F7e: ayrıştırma başarısızsa yeniden ayrıştırma + puanlama, yalnızca puanlama ise puanlama."""
    application = db.get(Application, application_id)
    if application is None:
        raise NotFoundError("Başvuru bulunamadı")
    candidate = db.get(Candidate, application.candidate_id)
    assert candidate is not None

    if candidate.parse_status is ProcessingStatus.FAILED:
        if candidate.parse_error in _EXTRACTION_ERRORS:
            raise ConflictError(
                "Bu dosyadan metin çıkarılamadı; yeniden denemek sonucu değiştirmez. "
                "CV'yi metin içeren bir PDF veya DOCX olarak yeniden yükleyin."
            )
        candidate.parse_status = ProcessingStatus.PENDING
        candidate.parse_error = None
        step = "parse"
    elif application.score_status is ProcessingStatus.FAILED:
        step = "score"
    else:
        raise ConflictError("Yeniden denenecek bir hata yok")

    application.score_status = ProcessingStatus.PENDING
    application.score_error = None
    audit.record(
        db,
        actor_id=actor_id,
        action="application.retry",
        entity_type="application",
        entity_id=application_id,
        payload={"step": step},
    )
    db.commit()
    return application_id


STATUS_CHANGE_ACTION = "application.status"


@dataclass(frozen=True)
class NoteView:
    note: Note
    author_name: str


@dataclass(frozen=True)
class StatusChangeView:
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    actor_id: int | None
    actor_name: str | None
    created_at: datetime


@dataclass(frozen=True)
class ApplicationDetail:
    application: Application
    candidate: Candidate
    job: Job
    notes: list[NoteView]
    status_history: list[StatusChangeView]


def get_application(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise NotFoundError("Başvuru bulunamadı")
    return application


def _status_history(db: Session, application_id: int) -> list[StatusChangeView]:
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(
            AuditLog.action == STATUS_CHANGE_ACTION,
            AuditLog.entity_type == "application",
            AuditLog.entity_id == application_id,
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).all()
    return [
        StatusChangeView(
            from_status=ApplicationStatus(entry.payload["from"]),
            to_status=ApplicationStatus(entry.payload["to"]),
            actor_id=entry.actor_id,
            actor_name=name,
            created_at=entry.created_at,
        )
        for entry, name in rows
    ]


def get_detail(db: Session, application_id: int) -> ApplicationDetail:
    """F8: aday detayının tek sayfada gösterdiği her şey."""
    application = get_application(db, application_id)
    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    assert candidate is not None and job is not None
    notes = [
        NoteView(note=note, author_name=name)
        for note, name in db.execute(
            select(Note, User.full_name)
            .join(User, User.id == Note.author_id)
            .where(Note.application_id == application_id)
            .order_by(Note.created_at.desc(), Note.id.desc())
        ).all()
    ]
    return ApplicationDetail(
        application=application,
        candidate=candidate,
        job=job,
        notes=notes,
        status_history=_status_history(db, application_id),
    )


def change_status(
    db: Session, *, application_id: int, status: ApplicationStatus, actor_id: int
) -> Application:
    """F9: her durumdan her duruma serbest geçiş; yalnızca kullanıcı isteğiyle çağrılır.

    Sistem (pipeline, puanlama) durumu hiçbir zaman değiştirmez — otomatik eleme yok (V1).
    """
    application = get_application(db, application_id)
    previous = application.status
    if previous is status:
        return application
    application.status = status
    audit.record(
        db,
        actor_id=actor_id,
        action=STATUS_CHANGE_ACTION,
        entity_type="application",
        entity_id=application_id,
        payload={"from": previous.value, "to": status.value},
    )
    db.commit()
    return application
