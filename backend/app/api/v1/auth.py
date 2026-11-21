from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (DUMMY_PASSWORD_HASH, csrf_token, current_user, hash_password, issue_session,
                               optional_user, rate_limit, token_hash, verify_password)
from app.database.session import get_db
from app.models import Address, AuthSession, User, utcnow
from app.schemas.requests import AccountDelete, AddressInput, Login, PasswordChange, ProfileUpdate, Register
from app.services.accounts import change_password, close_account, lock_active_account, update_profile
from app.services.presentation import entity, user_data

router = APIRouter()


@router.get("/auth/session")
def session(request: Request, response: Response, user=Depends(optional_user)):
    return {"user": user_data(user) if user else None, "csrf_token": csrf_token(request, response)}


@router.post("/auth/register", status_code=201)
def register(data: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(db, request, "register", 10)
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Este email já está registado")
    user = User(name=data.name, email=email, phone=data.phone, password_hash=hash_password(data.password),
                is_demo=get_settings().payment_mode == "demo")
    db.add(user)
    db.flush()
    issue_session(db, user, response)
    db.commit()
    return {"user": user_data(user), "csrf_token": csrf_token(request, response)}


@router.post("/auth/login")
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(db, request, "login", 15)
    user = db.scalar(select(User).where(User.email == str(data.email).lower())
                     .with_for_update(key_share=True, read=False)
                     .execution_options(populate_existing=True))
    # Equalise the costly password path for unknown accounts.
    valid = verify_password(data.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Email ou palavra-passe incorrectos")
    issue_session(db, user, response)
    db.commit()
    return {"user": user_data(user), "csrf_token": csrf_token(request, response)}


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(db, request, "refresh", 30)
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Sessão expirada")
    initial = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == token_hash(token)))
    if not initial:
        raise HTTPException(401, "Sessão inválida")
    user = db.scalar(select(User).where(User.id == initial.user_id).with_for_update(key_share=True, read=False)
                     .execution_options(populate_existing=True))
    old = db.scalar(select(AuthSession).where(AuthSession.id == initial.id).with_for_update()
                    .execution_options(populate_existing=True))
    if old.revoked:
        db.execute(update(AuthSession).where(AuthSession.family_id == old.family_id).values(revoked=True))
        db.commit()
        raise HTTPException(401, "Refresh token reutilizado; inicie sessão novamente")
    if old.expires_at <= utcnow() or not user or not user.active:
        raise HTTPException(401, "Sessão expirada")
    old.revoked = True
    issue_session(db, user, response, old.family_id)
    db.commit()
    return {"user": user_data(user), "csrf_token": csrf_token(request, response)}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if token:
        session = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == token_hash(token)))
        if session:
            db.execute(select(User.id).where(User.id == session.user_id).with_for_update(key_share=True, read=False))
            db.execute(update(AuthSession).where(AuthSession.family_id == session.family_id).values(revoked=True))
            db.commit()
    for name in ("access_token", "refresh_token"):
        response.delete_cookie(name, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    return {"message": "Sessão terminada"}


@router.get("/me")
def me(user=Depends(current_user)):
    return user_data(user)


@router.patch("/me")
def update_me(data: ProfileUpdate, request: Request, response: Response,
              user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"profile:{user.id}", 15)
    user, changed_email = update_profile(db, user, data)
    if changed_email:
        issue_session(db, user, response)
    db.commit()
    return user_data(user)


@router.post("/me/password")
def update_password(data: PasswordChange, request: Request, response: Response,
                    user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"password-change:{user.id}", 5)
    user = change_password(db, user, data.current_password, data.new_password)
    issue_session(db, user, response)
    db.commit()
    return {"message": "Palavra-passe alterada. As outras sessões foram terminadas."}


@router.delete("/me")
def delete_me(data: AccountDelete, request: Request, response: Response,
              user=Depends(current_user), db: Session = Depends(get_db)):
    rate_limit(db, request, f"account-delete:{user.id}", 5)
    close_account(db, user, data.current_password)
    db.commit()
    for name in ("access_token", "refresh_token"):
        response.delete_cookie(name, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    return {"message": "Conta eliminada. O histórico de transacções e apoio foi conservado.",
            "retained_records": True}


@router.get("/me/addresses")
def addresses(user=Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Address).where(Address.user_id == user.id)).all()
    return {"items": [entity(a, "label", "address", "province", "district", "phone") for a in items], "total": len(items)}


@router.post("/me/addresses", status_code=201)
def add_address(data: AddressInput, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    count = len(db.scalars(select(Address.id).where(Address.user_id == user.id)).all())
    if count >= 20:
        raise HTTPException(409, "Limite de 20 moradas atingido")
    address = Address(user_id=user.id, **data.model_dump())
    db.add(address)
    db.commit()
    return entity(address, "label", "address", "province", "district", "phone")


@router.patch("/me/addresses/{address_id}")
def update_address(address_id: UUID, data: AddressInput, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    if not address:
        raise HTTPException(404, "Morada não encontrada")
    for key, value in data.model_dump().items():
        setattr(address, key, value)
    db.commit()
    return entity(address, "label", "address", "province", "district", "phone")


@router.delete("/me/addresses/{address_id}")
def delete_address(address_id: UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    user = lock_active_account(db, user)
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == user.id))
    if not address:
        raise HTTPException(404, "Morada não encontrada")
    db.delete(address)
    db.commit()
    return {"message": "Morada removida"}
