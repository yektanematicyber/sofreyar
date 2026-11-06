# Container Optimization Reference: Safreyar Backend

## 1. Multi-Stage Dockerfile Pattern for Python 3.12

To minimize container attack surface, eliminate build-time compilers from the final image, and speed up CI/CD builds, adopt a multi-stage approach:

```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source
COPY . .

EXPOSE 8001

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8001"]
```

---

## 2. `.dockerignore` Essentials

Keep container contexts minimal by ensuring `.dockerignore` contains:
```text
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.venv-*/
.pytest_cache/
.coverage
htmlcov/
.git/
.gitignore
.kilo/
.agent/
*.log
```
