# Safreyar Backend (سفره‌یار)

Safreyar is a smart food pantry and AI-powered meal planning application backend built with FastAPI, PostgreSQL 17, SQLAlchemy 2.0, Pydantic V2, and Docker.

---

## 1. Features

- **Authentication:** JWT (HMAC-SHA256) with bcrypt password hashing and secure password recovery.
- **Pantry Management:** Track pantry items with quantities, units, and expiration dates.
- **Deterministic Food Safety:** Automatic backend business-logic filtering of expired items.
- **AI Meal Suggestions (`POST /suggestions`):** Suggests 3 realistic Persian recipes matching pantry ingredients.
- **Dual-Mode LLM Architecture:**
  - **`fake` (Default):** Offline, deterministic Persian recipes for local development and CI testing (0 API cost, 0 external network dependencies).
  - **`real` (OpenRouter):** Production AI provider utilizing OpenRouter's OpenAI-compatible Chat Completions API (`https://openrouter.ai/api/v1/chat/completions`) with configurable models (default: `google/gemma-4-26b-a4b-it:free`).
- **Resilient AI Pipeline:** One-shot retry on invalid JSON, token telemetry tracking, SHA-256 caching with versioning, and sliding-window rate limiting (in-memory or atomic Redis Lua script).
- **PostgreSQL 17 & Alembic:** Native `JSONB` recipe storage, foreign keys with cascade deletion, and optimized indexes.

---

## 2. LLM Configuration Modes

Safreyar strictly supports **two LLM modes**, configured via environment variables in `.env`:

### Mode 1: Fake Mode (Offline & Testing)
Used by default. Generates realistic, structured Persian recipes offline without calling any external service or consuming API credits.

```env
LLM_MODE=fake
LLM_API_KEY=
LLM_MODEL=google/gemma-4-26b-a4b-it:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_TIMEOUT_SECONDS=60.0
```

### Mode 2: OpenRouter Mode (Real AI Provider)
Connects asynchronously via `httpx` to OpenRouter's Chat Completions endpoint.

```env
LLM_MODE=real
LLM_API_KEY=YOUR_OPENROUTER_API_KEY
LLM_MODEL=google/gemma-4-26b-a4b-it:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_TIMEOUT_SECONDS=60.0
```

---

## 3. Quick Start

### Local Setup
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env

# 4. Run tests
pytest tests/ -v

# 5. Start development server
uvicorn app.main:app --reload --port 8001
```

### Docker Compose
```bash
docker compose up --build
```

---

## 4. API Documentation
Once running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
