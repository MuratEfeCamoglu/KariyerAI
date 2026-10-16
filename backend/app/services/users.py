from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services import audit


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    actor_id: int | None,
) -> User:
    normalized_email = email.lower()
    if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise ConflictError("Bu e-posta adresiyle bir kullanıcı zaten var")

    user = User(
        email=normalized_email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        actor_id=actor_id,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        payload={"role": role.value},
    )
    db.commit()
    return user


def update_user(
    db: Session,
    *,
    user_id: int,
    actor_id: int,
    full_name: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    password: str | None = None,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Kullanıcı bulunamadı")
    if is_active is False and user.id == actor_id:
        raise ValidationError("Kendi hesabınızı pasifleştiremezsiniz")

    # Son aktif yönetici kaybedilirse kullanıcı yönetimi ve KVKK silme işlemleri kimse
    # tarafından yapılamaz hale gelir; rol düşürme ve pasifleştirme bu yüzden engellenir.
    loses_admin = (
        user.role is UserRole.ADMIN
        and user.is_active
        and ((role is not None and role is not UserRole.ADMIN) or is_active is False)
    )
    if loses_admin:
        other_admins = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN, User.is_active, User.id != user.id
            )
        )
        if not other_admins:
            raise ConflictError("Sistemde en az bir aktif yönetici kalmalı")

    changes: dict[str, str | bool] = {}
    if full_name is not None:
        user.full_name = full_name
    if role is not None and role != user.role:
        user.role = role
        changes["role"] = role.value
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        changes["is_active"] = is_active
    if password is not None:
        user.password_hash = hash_password(password)
        changes["password_changed"] = True

    audit.record(
        db,
        actor_id=actor_id,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        payload=changes,
    )
    db.commit()
    return user
