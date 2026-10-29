
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.routers import auth, ingredients, pantry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create missing tables for local development.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Safreyar API",
    description="Backend API for the Safreyar application",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(ingredients.router)
app.include_router(pantry.router)


@app.get("/")
def home():
    return {"message": "Safreyar backend is running!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
