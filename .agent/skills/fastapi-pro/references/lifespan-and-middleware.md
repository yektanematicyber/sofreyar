# FastAPI Lifespan and Middleware Reference

## 1. Modern ASGI Lifespan Pattern

In FastAPI `>=0.93.0`, startup and shutdown logic must be encapsulated in an `@asynccontextmanager` function passed to `FastAPI(lifespan=...)`.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup phase ---
    # In production, table creation is managed exclusively by Alembic migrations.
    # Base.metadata.create_all(bind=engine) should only run if explicitly enabled for local dev.
    yield
    # --- Shutdown phase ---
    # Dispose of engine connection pools cleanly
    engine.dispose()

app = FastAPI(
    title="Safreyar API",
    description="Backend API for the Safreyar application",
    version="0.1.0",
    lifespan=lifespan,
)
```

---

## 2. CORS Middleware Configuration

To ensure Flutter mobile apps, web dashboards, MEmu emulators, and local browsers can communicate with the backend, configure `CORSMiddleware` cleanly:

```python
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://10.0.2.2:8001",  # Standard Android emulator loopback
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 3. Global Exception Handling

Ensure all unexpected errors return consistent JSON responses without leaking internal stack traces:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )
```
