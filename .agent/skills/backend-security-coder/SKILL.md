---
name: backend-security-coder
description: Backend security, authentication, and vulnerability remediation skill for Safreyar Backend. Enforces OWASP API Security Top 10, robust JWT authorization, password hashing hardening with bcrypt, and input sanitization.
---

# Backend Security Coder: Safreyar API Hardening Guide

This skill provides expert API security principles, defense-in-depth patterns, and vulnerability prevention for `safreyar-backend`.

## 1. Authentication & Password Security

### Password Hashing Standards:
* **Library:** `bcrypt` (`bcrypt==5.0.0`).
* **Salt Generation:** Never use fixed salts. Always use `bcrypt.gensalt(rounds=12)`.
* **Verification:** Use `bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))`.
* **Password Limits:** Limit max length to `72` bytes (Bcrypt's maximum effective input size) in Pydantic:
  ```python
  password: str = Field(min_length=8, max_length=72)
  ```

---

## 2. JWT Access Token Security

### Implementation Rules:
1. **Secret Key Strength:** `JWT_SECRET_KEY` must be a high-entropy cryptographically random string (at least 256 bits / 32 bytes) loaded from environment variables. Never commit fallback secrets to source code.
2. **Algorithm Pinning:** Explicitly specify `algorithms=["HS256"]` in `jwt.decode()`. Never allow algorithm auto-detection or `"none"` algorithms.
3. **Expiration Enforcement:** Always verify the `"exp"` claim against UTC timestamps (`datetime.now(timezone.utc)`).
4. **Minimal Payload:** Only store the user identity (`"sub": str(user_id)`) and expiration (`"exp"`). Never store passwords, emails, or sensitive PII in JWT payloads.

---

## 3. OWASP API Security Top 10 for Safreyar

* **BOLA (Broken Object Level Authorization):**
  * In `/pantry/{item_id}` endpoints, always scope queries by both `id` AND `user_id`:
    ```python
    item = db.query(PantryItem).filter(
        PantryItem.id == item_id,
        PantryItem.user_id == current_user.id
    ).first()
    ```
  * If not found, return `404 Not Found` (rather than `403 Forbidden`) to avoid leaking the existence of other users' IDs.
* **Mass Assignment:**
  * Never dump untrusted client dictionaries directly into ORM models (e.g. `User(**request.json())`).
  * Always parse through explicit Pydantic V2 schemas (`UserRegister`, `PantryItemCreate`).
* **Broken Authentication:**
  * Return generic error messages on login failures (`"Invalid email or password"`) to prevent account enumeration.

For complete checklists and audit rules, see [references/jwt-and-owasp-checklist.md](file:///c:/Users/Lenovo/Documents/safreyar-backend/.agent/skills/backend-security-coder/references/jwt-and-owasp-checklist.md).
