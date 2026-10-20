from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(_admin: AdminUser, db: DbSession) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in users_service.list_users(db)]


@router.post("", status_code=201)
def create_user(body: UserCreate, admin: AdminUser, db: DbSession) -> UserOut:
    user = users_service.create_user(
        db,
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        role=body.role,
        actor_id=admin.id,
    )
    return UserOut.model_validate(user)


@router.post("/{user_id}/approve")
def approve_user(user_id: int, admin: AdminUser, db: DbSession) -> UserOut:
    user = users_service.approve_user(db, user_id=user_id, actor_id=admin.id)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reject", status_code=204)
def reject_user(user_id: int, admin: AdminUser, db: DbSession) -> None:
    users_service.reject_user(db, user_id=user_id, actor_id=admin.id)


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession) -> UserOut:
    user = users_service.update_user(
        db,
        user_id=user_id,
        actor_id=admin.id,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        password=body.password,
    )
    return UserOut.model_validate(user)
