import hashlib
import hmac
import secrets
from datetime import timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models import AuthSession, RateLimitBucket, User, utcnow

password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash("deloya-timing-equalisation-only")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(request: Request, response: Response) -> str:
    value = request.cookies.get("csrf_token") or secrets.token_urlsafe(32)
    response.set_cookie("csrf_token", value, httponly=False, secure=get_settings().cookie_secure,
                        samesite="lax", max_age=86400 * 30, path="/")
    return value


def issue_session(db: Session, user: User, response: Response, family_id=None):
    settings = get_settings()
    refresh = secrets.token_urlsafe(48)
    session = AuthSession(user_id=user.id, refresh_hash=token_hash(refresh),
                          expires_at=utcnow() + timedelta(days=settings.refresh_token_days))
    if family_id:
        session.family_id = family_id
    db.add(session)
    db.flush()
    access = jwt.encode({"sub": str(user.id), "sid": str(session.id), "iat": utcnow(),
                         "exp": utcnow() + timedelta(minutes=settings.access_token_minutes),
                         "iss": "deloya", "aud": "deloya-web"}, settings.jwt_secret, algorithm="HS256")
    for name, value, age in [("access_token", access, settings.access_token_minutes * 60),
                              ("refresh_token", refresh, settings.refresh_token_days * 86400)]:
        response.set_cookie(name, value, httponly=True, secure=settings.cookie_secure,
                            samesite="lax", max_age=age, path="/")
    return session


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"],
                             issuer="deloya", audience="deloya-web",
                             options={"require": ["exp", "iat", "sub", "sid"]})
        session = db.get(AuthSession, UUID(payload["sid"]))
        if not session or session.revoked or session.expires_at <= utcnow() or str(session.user_id) != payload["sub"]:
            return None
        user = db.get(User, session.user_id)
        return user if user and user.active else None
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None


def current_user(user: User | None = Depends(optional_user)) -> User:
    if not user:
        raise HTTPException(401, "Inicie sessão para continuar")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Acesso reservado à administração")
    return user


def rate_limit(db: Session, request: Request, scope: str, limit: int = 20, seconds: int = 60):
    # PostgreSQL-backed atomic buckets work across workers and serverless instances.
    now = utcnow()
    db.execute(delete(RateLimitBucket).where(RateLimitBucket.window_start < now - timedelta(days=1)))
    window = int(now.timestamp()) // seconds * seconds
    key = token_hash(f"{scope}:{request.client.host if request.client else 'unknown'}:{window}")
    result = db.execute(insert(RateLimitBucket).values(key=key, window_start=now, count=1)
                        .on_conflict_do_update(index_elements=[RateLimitBucket.key],
                                               set_={"count": RateLimitBucket.count + 1})
                        .returning(RateLimitBucket.count)).scalar_one()
    db.commit()
    if result > limit:
        raise HTTPException(429, "Demasiadas tentativas. Aguarde um minuto.", headers={"Retry-After": str(seconds)})


def verify_csrf(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"} or request.url.path.startswith("/api/v1/payment-webhooks/"):
        return
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in get_settings().allowed_frontend_origins:
        raise HTTPException(403, "Origem não autorizada")
    cookie = request.cookies.get("csrf_token", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(403, "Token CSRF inválido. Actualize a página e tente novamente.")
