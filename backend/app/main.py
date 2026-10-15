from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import auth, users
from app.core.errors import DomainError

app = FastAPI(title="KariyerAI API", version="0.1.0")


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
