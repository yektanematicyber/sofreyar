---
name: docker-pro
description: Containerization and DevOps orchestration skill for Safreyar Backend. Covers multi-stage Docker builds, Docker Compose service healthchecks, network configuration for mobile emulators, and environment configuration management.
---

# Docker Pro: Safreyar Containerization Guide

This skill provides expert containerization and orchestration standards for `safreyar-backend`.

## 1. Environment Architecture

Safreyar uses two parallel environment definitions:
1. **`.env` (Local Development):**
   * Configures local Postgres host (e.g. `localhost:5432`) and local dev secrets.
2. **`.env.docker` (Docker Compose):**
   * Configures internal docker network hostnames (`db:5432`).
   * Explicitly sets `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

---

## 2. Docker Compose Standards

The standard composition in `docker-compose.yml` ensures that the API backend waits for PostgreSQL to be strictly healthy before starting:

```yaml
services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-safreyar}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env.docker}
      POSTGRES_DB: ${POSTGRES_DB:-safreyar}
    volumes:
      - safreyar_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-safreyar} -d ${POSTGRES_DB:-safreyar}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-safreyar}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-safreyar}
    ports:
      - "8001:8001"
    depends_on:
      db:
        condition: service_healthy
```

---

## 3. Connecting Mobile Emulators to the Docker Backend

* **Android Studio Official Emulator:**
  * Connect via `http://10.0.2.2:8001` (Android loopback router to host machine).
* **MEmu, BlueStacks, LDPlayer, or Physical Device:**
  * Find the host's LAN IP address (`ipconfig` $\to$ IPv4, e.g. `192.168.1.15`).
  * Connect via `http://192.168.x.x:8001`.
  * Ensure Windows Firewall allows inbound connections on port 8001.

For multi-stage build optimization and caching patterns, see [references/container-optimization.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/docker-pro/references/container-optimization.md).
