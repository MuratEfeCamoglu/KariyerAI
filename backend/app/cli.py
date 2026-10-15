import argparse
import getpass
import sys

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from app.core.db import SessionLocal
from app.core.errors import ConflictError
from app.models.user import UserRole
from app.schemas.user import Password
from app.services import users as users_service

_password_adapter: TypeAdapter[str] = TypeAdapter(Password)


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Şifre (en az 10 karakter): ")
        try:
            _password_adapter.validate_python(password)
        except PydanticValidationError as exc:
            print(exc.errors()[0]["msg"].removeprefix("Value error, "), file=sys.stderr)
            continue
        if getpass.getpass("Şifre (tekrar): ") != password:
            print("Şifreler eşleşmiyor", file=sys.stderr)
            continue
        return password


def create_admin(email: str, full_name: str) -> int:
    password = _prompt_password()
    with SessionLocal() as db:
        try:
            user = users_service.create_user(
                db,
                email=email,
                full_name=full_name,
                password=password,
                role=UserRole.ADMIN,
                actor_id=None,
            )
        except ConflictError as exc:
            print(exc.detail, file=sys.stderr)
            return 1
        print(f"Admin oluşturuldu (id={user.id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin_parser = commands.add_parser("create-admin", help="İlk yönetici hesabını oluşturur")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--name", default="Yönetici", help="Görünen ad")

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        return create_admin(args.email, args.name)
    return 2


if __name__ == "__main__":
    sys.exit(main())
