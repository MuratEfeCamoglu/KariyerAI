from pydantic import BaseModel, EmailStr

from app.schemas.user import FullName, Password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Herkese açık kayıt; rol istekten alınmaz, hesap her zaman iş arayan (seeker) olur."""

    email: EmailStr
    full_name: FullName
    password: Password
