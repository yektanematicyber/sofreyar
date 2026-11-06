---
name: backend-architect
description: Software architecture and domain modeling skill for Safreyar Backend. Guides clean 3-tier layering (Routers -> Services -> Repositories/ORM), Domain-Driven Design (DDD), API contract evolution, and roadmap feature scaling.
---

# Backend Architect: Safreyar Architecture Blueprint

This skill guides architectural decisions, structural patterns, and codebase evolution for `safreyar-backend`.

## 1. Architectural Vision: Moving Beyond "Fat Routers"

In early development, route handlers in `app/routers/` often combine request parsing, business logic, ORM queries, and transaction commits in one block. As Safreyar scales to support AI meal suggestions, recipes, nutrition tracking, and pantry expiration notifications, business logic must be decoupled into a clean 3-layer architecture:

```mermaid
flowchart TD
    Client["Client Request (JSON)"] --> Presentation["1. Presentation Layer (app/routers/)"]
    Presentation -->|Calls| Business["2. Business / Service Layer (app/services/)"]
    Business -->|Coordinates| Security["Security & Auth / External AI Services"]
    Business -->|Queries| DataAccess["3. Repository / Data Layer (app/repositories/ & models/)"]
    DataAccess -->|SQLAlchemy 2.0| Postgres[("PostgreSQL 17 Database")]
```

---

## 2. Layer Responsibilities

### 1. Presentation Layer (`app/routers/`):
* Receives HTTP request, extracts headers, path, query, and JSON body.
* Leverages Pydantic V2 schemas (`app/schemas/`) for strict data validation.
* Injects dependencies (`current_user`, `db`).
* Delegates work to the Service layer and returns HTTP status codes (`200`, `201`, `204`, etc.).

### 2. Service Layer (`app/services/`):
* Contains core business rules, transactional logic, and multi-entity orchestrations.
* Performs business validation (e.g., verifying that an added pantry item belongs to an existing ingredient and checking date validity).
* Interacts with AI meal generation APIs and external third-party services.
* Raises domain exceptions (e.g. `ItemAlreadyExistsError`, `PermissionDeniedError`) that the presentation layer maps to HTTP exceptions.

### 3. Repository Layer (`app/repositories/`):
* Encapsulates raw database queries and mutations using SQLAlchemy 2.0.
* Isolates SQL dialects and database mechanics away from business rules.
* Makes unit testing simple via mock repositories or in-memory data structures.

---

## 3. Domain Model Boundaries for Safreyar

```mermaid
erDiagram
    USERS ||--o{ PANTRY_ITEMS : "owns"
    INGREDIENTS ||--o{ PANTRY_ITEMS : "references"
    INGREDIENTS ||--o{ RECIPE_INGREDIENTS : "used in"
    RECIPES ||--o{ RECIPE_INGREDIENTS : "contains"
    USERS ||--o{ MEAL_PLANS : "plans"

    USERS {
        int id PK
        string name
        string email UK
        string hashed_password
    }

    INGREDIENTS {
        int id PK
        string name UK
        string category
        string default_unit
    }

    PANTRY_ITEMS {
        int id PK
        int user_id FK
        int ingredient_id FK
        float quantity
        string unit
        date expiry_date
        datetime created_at
    }
```

For practical implementation examples of the Service-Repository pattern, see [references/service-repository-pattern.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/backend-architect/references/service-repository-pattern.md).
