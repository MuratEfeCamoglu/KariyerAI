from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, jobs, users
from app.core.errors import DomainError, FieldValidationError, translate_validation_errors

app = FastAPI(title="KariyerAI API", version="0.1.0")

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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
