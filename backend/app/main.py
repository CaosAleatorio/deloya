from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.v1 import admin, attachments, auth, catalog, customer, reports, vendor
from app.core.config import get_settings
from app.core.request_limits import UploadBodyLimitMiddleware
from app.core.security import verify_csrf
from app.database.session import engine

settings = get_settings()
app = FastAPI(title="Deloya Marketplace API", version="0.1.0", dependencies=[Depends(verify_csrf)])
app.add_middleware(UploadBodyLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_frontend_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Content-Type", "X-CSRF-Token"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/v1/") else "no-cache"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={"detail": "O registo entra em conflito com dados existentes; verifique os campos únicos"})


@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "A base de dados está temporariamente indisponível"})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Never echo input values (which may contain passwords) in validation errors.
    return JSONResponse(status_code=422, content={"detail": "Verifique os campos indicados",
        "errors": [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]} for e in exc.errors()]})


@app.get("/", include_in_schema=False)
def api_home():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok", "version": "0.1.0"}
    except OperationalError:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})


for router in (auth.router, catalog.router, customer.router, vendor.router, admin.router, reports.router, attachments.router):
    app.include_router(router, prefix="/api/v1")
