from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.database import models  # noqa: F401  (registers the tables)
from app.database.database import Base, engine
from app.routers import (auth, community, pages, progress, resources, roadmap, tasks, tech_updates, users)
from app.services.errors import ExternalServiceError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates missing tables on startup
    yield


app = FastAPI(title="Student Guide", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

for module in (auth, users, roadmap, resources, tasks, tech_updates, progress, community, pages):
    app.include_router(module.router)


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://i.ytimg.com; frame-ancestors 'none'")
    return response


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "Student Guide"}
