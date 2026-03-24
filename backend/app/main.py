from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.articles import router as articles_router
from app.api.routes.settings import router as settings_router
from app.api.routes.sources import router as sources_router
from app.core.config import get_settings
from app.db import create_db_and_tables

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"message": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"message": str(exc)})


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Research Blog Reading Tracker API is running."}


app.include_router(sources_router, prefix=settings.api_prefix)
app.include_router(articles_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
