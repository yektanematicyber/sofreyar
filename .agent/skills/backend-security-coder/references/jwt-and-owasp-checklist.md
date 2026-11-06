# JWT & OWASP Security Checklist Reference

## 1. OWASP API Security Audit Checklist

- [ ] **BOLA Prevention:** All single-resource GET, PATCH, and DELETE operations verify ownership (`user_id == current_user.id`).
- [ ] **Authentication Token Verification:** Tokens validated with algorithm pinning (`HS256`) and UTC expiration.
- [ ] **Data Sanitization:** All textual inputs trimmed of excess spaces and validated against allowed character sets.
- [ ] **Safe SQL Execution:** All queries constructed using SQLAlchemy ORM or parameterized statements (no string interpolation into SQL).
- [ ] **Password Storage:** Hashed with bcrypt using 12 salt rounds; plain passwords never stored or returned in JSON responses.
- [ ] **Error Handling:** Unhandled 500 exceptions caught by global exception handlers; no raw database or stack trace leaked to clients.
- [ ] **CORS Protection:** Explicit allowlist of allowed domains rather than wildcard `*` with credentials enabled.
- [ ] **Rate Limiting:** Authentication routes (`/auth/login`, `/auth/register`) protected against brute-force attacks.

---

## 2. Hardened Token Verification Snippet

```python
import os
from datetime import datetime, timezone
import jwt
from fastapi import HTTPException, status

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```
