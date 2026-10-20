import argparse
import getpass
import sys

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.errors import ConflictError
from app.models.user import User, UserRole
from app.schemas.user import Password
from app.services import demo
from app.services import jobs as jobs_service
from app.services import users as users_service
from app.storage.files import get_storage

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


def _find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def _is_active_recruiter(user: User) -> bool:
    return user.role == UserRole.RECRUITER and user.is_active and user.is_approved


def seed_demo(applications: int, owner_email: str | None = None) -> int:
    with SessionLocal() as db:
        if owner_email is not None:
            owner = _find_user(db, owner_email)
            if owner is None or not _is_active_recruiter(owner):
                print("Sahip etkin ve onaylı bir İK hesabı olmalı", file=sys.stderr)
                return 1
        else:
            owner = db.scalar(
                select(User)
                .where(User.role == UserRole.RECRUITER, User.is_active, User.is_approved)
                .order_by(User.id)
            )
            if owner is None:
                print(
                    "Önce bir İK hesabı oluşturun: kayıt olup yönetici onayı alın",
                    file=sys.stderr,
                )
                return 1
        result = demo.seed_demo(db, get_storage(), owner_id=owner.id, applications=applications)
    print(
        f"Demo ilanı oluşturuldu (id={result.job_id}), "
        f"{result.application_count} sentetik başvuru eklendi."
    )
    return 0


def transfer_jobs(from_email: str, to_email: str) -> int:
    with SessionLocal() as db:
        source = _find_user(db, from_email)
        if source is None:
            print("Kaynak kullanıcı bulunamadı", file=sys.stderr)
            return 1
        target = _find_user(db, to_email)
        if target is None or not _is_active_recruiter(target):
            print("Hedef etkin ve onaylı bir İK hesabı olmalı", file=sys.stderr)
            return 1
        count = jobs_service.transfer_jobs(db, from_user_id=source.id, to_user_id=target.id)
    print(f"{count} ilan devredildi.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin_parser = commands.add_parser("create-admin", help="İlk yönetici hesabını oluşturur")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--name", default="Yönetici", help="Görünen ad")
    seed_parser = commands.add_parser(
        "seed-demo", help="Demo ilanı ve sentetik başvurular (LLM çağrısı yapmaz)"
    )
    seed_parser.add_argument(
        "--applications",
        type=int,
        default=20,
        help="Başvuru sayısı (performans ölçümü için 500)",
    )
    seed_parser.add_argument(
        "--owner", help="İlanın sahibi İK hesabının e-postası (varsayılan: ilk onaylı İK)"
    )
    transfer_parser = commands.add_parser(
        "transfer-jobs", help="Bir kullanıcının tüm ilanlarını bir İK uzmanına devreder"
    )
    transfer_parser.add_argument("--from", dest="from_email", required=True)
    transfer_parser.add_argument("--to", dest="to_email", required=True)

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        return create_admin(args.email, args.name)
    if args.command == "seed-demo":
        if args.applications < 1:
            parser.error("--applications en az 1 olmalı")
        return seed_demo(args.applications, args.owner)
    if args.command == "transfer-jobs":
        return transfer_jobs(args.from_email, args.to_email)
    return 2


if __name__ == "__main__":
    sys.exit(main())
