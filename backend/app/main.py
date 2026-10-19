import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import applications, audit, auth, candidates, cv_checks, jobs, users
from app.core.db import get_session_factory
from app.core.errors import DomainError, FieldValidationError, translate_validation_errors
from app.services import pipeline

logger = logging.getLogger(__name__)


def _requeue_in_background(app: FastAPI) -> None:
    # Testler oturum fabrikasını dependency_overrides ile değiştirir; açılış da aynısını kullanmalı.
    factory_provider = app.dependency_overrides.get(get_session_factory, get_session_factory)
    session_factory = factory_provider()

    def run() -> None:
        try:
            pipeline.requeue_unfinished(session_factory)
            pipeline.requeue_unfinished_cv_checks(session_factory)
        except Exception:
            logger.exception("Açılışta yeniden kuyruğa alma başarısız")

    # Uzun sürebilir (LLM çağrıları); sunucunun açılmasını bekletmesin.
    threading.Thread(target=run, name="pipeline-requeue", daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _requeue_in_background(app)
    yield


app = FastAPI(title="KariyerAI API", version="0.1.0", lifespan=lifespan)

# Framework'ün kendi ürettiği hatalar (bilinmeyen yol, yanlış metot, okunamayan gövde) İngilizce
# gelir; API mesajları Türkçe olmalı (CLAUDE.md).
_FRAMEWORK_ERROR_MESSAGES = {
    400: "İstek gövdesi okunamadı",
    404: "Kaynak bulunamadı",
    405: "Bu işlem desteklenmiyor",
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = _FRAMEWORK_ERROR_MESSAGES.get(exc.status_code, "İstek işlenemedi")
    return JSONResponse(
        status_code=exc.status_code, content={"detail": detail}, headers=exc.headers
    )


@app.exception_handler(FieldValidationError)
async def field_validation_error_handler(
    _request: Request, exc: FieldValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.as_errors()})


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"detail": translate_validation_errors(exc.errors())}
    )


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(applications.notes_router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(cv_checks.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
