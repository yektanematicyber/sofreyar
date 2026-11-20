import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine
from app import models
from app.exceptions import AppException
from app.routers import auth, ingredients, pantry, recipes, suggestions

logger = logging.getLogger("safreyar.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create missing tables for local development if not already present.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Safreyar API",
    description="Backend API for the Safreyar application",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Custom exception handler ensuring standard machine-readable error codes."""
    content = {
        "detail": exc.detail,
        "error_code": exc.error_code,
    }
    if exc.extra:
        content["extra"] = exc.extra
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic validation errors with consistent INVALID_REQUEST error code."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "داده‌های ورودی نامعتبر است.",
            "error_code": "INVALID_REQUEST",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Maps unhandled database errors to standard DATABASE_ERROR 500 response."""
    logger.exception("Database error occurred: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "خطای داخلی در پایگاه داده رخ داده است.",
            "error_code": "DATABASE_ERROR",
        },
    )


app.include_router(auth.router)
app.include_router(ingredients.router)
app.include_router(pantry.router)
app.include_router(suggestions.router)
app.include_router(recipes.router)


@app.get("/")
def home():
    return {"message": "Safreyar backend is running!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
