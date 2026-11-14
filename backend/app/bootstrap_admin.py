"""Create an administrator explicitly without changing existing accounts."""
import argparse
import os

from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models import User
from app.schemas.requests import Register


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrador Deloya")
    args = parser.parse_args()
    load_dotenv("../.env")
    load_dotenv(".env")
    try:
        data = Register(name=args.name, email=args.email, password=os.environ.get("ADMIN_PASSWORD", ""))
    except ValidationError:
        raise SystemExit("Verifique --name, --email e ADMIN_PASSWORD (12 a 128 caracteres); nenhuma conta foi criada.") from None
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == str(data.email).lower())):
            raise SystemExit("A conta já existe; nenhuma permissão ou password foi alterada")
        db.add(User(name=data.name, email=str(data.email).lower(), role="admin", is_demo=False,
                    password_hash=hash_password(data.password)))
        db.commit()
    print("Administrador criado. Altere ADMIN_PASSWORD no gestor de segredos após o bootstrap.")


if __name__ == "__main__":
    main()
