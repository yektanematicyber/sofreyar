# FastAPI Dependency Injection Reference: Safreyar Backend

## Overview
FastAPI dependencies (`Depends`) manage database connection lifetimes, security authentication, permission checks, and shared service access.

---

## 1. Database Session Dependency (`get_db`)

The database dependency manages a single session per request, ensuring automatic commit or rollback and session closure even on unhandled exceptions:

```python
from typing import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Usage in Route Handlers:
```python
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    ...
```

---

## 2. Authentication Dependency (`get_current_user`)

Extracts the HTTP Bearer token from the `Authorization` header, decodes and verifies the JWT, and loads the active user from the database.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session

from app.auth import JWT_SECRET_KEY, JWT_ALGORITHM
from app.database import get_db
from app.models.user import User

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
```

---

## 3. Testing Overrides in Pytest

When running tests, override dependencies via `app.dependency_overrides`:

```python
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = lambda: mock_user
```

Always clean up overrides in fixture teardown:
```python
app.dependency_overrides.clear()
```
