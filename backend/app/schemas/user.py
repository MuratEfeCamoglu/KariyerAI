from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.models.user import UserRole


def _check_password(value: str) -> str:
    if len(value) < 10:
        raise ValueError("Şifre en az 10 karakter olmalı")
    # bcrypt yalnızca ilk 72 baytı kullanır; fazlası sessizce yok sayılmasın diye reddedilir.
    if len(value.encode()) > 72:
        raise ValueError("Şifre en fazla 72 bayt olabilir")
    return value


Password = Annotated[str, AfterValidator(_check_password)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: FullName
    password: Password
    role: UserRole = UserRole.RECRUITER


class UserUpdate(BaseModel):
    full_name: FullName | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: Password | None = None
