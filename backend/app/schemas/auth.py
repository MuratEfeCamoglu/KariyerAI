from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.user import FullName, Password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Herkese açık kayıt; rol istekten alınmaz, yalnızca hesap türü seçilir.

    `seeker` hemen açılır, `recruiter` yönetici onayı bekler. Admin bu yoldan açılamaz.
    """

    email: EmailStr
    full_name: FullName
    password: Password
    account_type: Literal["seeker", "recruiter"] = "seeker"


class PendingRegistration(BaseModel):
    status: Literal["pending_approval"]
