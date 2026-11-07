# Safreyar API Contract

**Backend:** FastAPI
**Database:** PostgreSQL
**API Base URL (Docker):** `http://localhost:8001`
**Swagger Documentation:** `http://localhost:8001/docs`

---

## 1. Authentication

All authentication endpoints use the `/auth` prefix.

### 1.1 Register

**Endpoint:** `POST /auth/register`

**Request Body:**

```json
{
  "name": "Ali Ahmadi",
  "email": "ali@example.com",
  "password": "Password123"
}
```

**Validation:**
- `name`: Required, 1–200 characters.
- `email`: Required, valid email address.
- `password`: Required, 8–72 characters.
- Extra whitespace in the name is normalized.
- Email is stored in lowercase.
- `confirm_password` is not required by the backend.

**Success Response:** `201 Created`

```json
{
  "id": 1,
  "name": "Ali Ahmadi",
  "email": "ali@example.com"
}
```

**Possible Errors:**
- `409 Conflict`: Email is already registered.
- `422 Unprocessable Entity`: Invalid request data.

### 1.2 Login

**Endpoint:** `POST /auth/login`

**Request Body:**

```json
{
  "email": "ali@example.com",
  "password": "Password123"
}
```

**Success Response:** `200 OK`

```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

The client must save the access token and send it in the Authorization header for protected endpoints.

**Authorization Header:**

```http
Authorization: Bearer JWT_TOKEN
```

**Possible Errors:**
- `401 Unauthorized`: Incorrect email or password.
- `422 Unprocessable Entity`: Invalid request data.

### 1.3 Get Current User

**Endpoint:** `GET /auth/me`

**Authentication:** Required.

**Success Response:** `200 OK`

```json
{
  "id": 1,
  "name": "Ali Ahmadi",
  "email": "ali@example.com"
}
```

### 1.4 Forgot Password

**Endpoint:** `POST /auth/forgot-password`

**Authentication:** Not required.

**Request Body:**

```json
{
  "email": "ali@example.com"
}
```

**Success Response:** `200 OK`

```json
{
  "message": "If this email is registered, password reset instructions have been sent.",
  "reset_token": "JWT_RESET_TOKEN"
}
```

*Note:* `reset_token` is included for testing and development until email SMTP service is connected. If the email is not registered, `reset_token` is `null` (preventing user enumeration).

### 1.5 Reset Password

**Endpoint:** `POST /auth/reset-password`

**Authentication:** Not required.

**Request Body:**

```json
{
  "token": "JWT_RESET_TOKEN",
  "new_password": "NewSecretPassword123"
}
```

**Validation:**
- `token`: Required.
- `new_password`: Required, 8–72 characters.

**Success Response:** `200 OK`

```json
{
  "message": "Password has been reset successfully. You can now log in."
}
```

**Possible Errors:**
- `400 Bad Request`: Invalid, expired, or already-used reset token.
- `422 Unprocessable Entity`: Validation failure (e.g. password shorter than 8 characters).


---

## 2. Ingredients

### 2.1 Search Ingredients

**Endpoint:** `GET /ingredients/search`

**Authentication:** Not required.

**Query Parameters:**
- `q`: Search text.
- `limit`: Maximum number of results. Default: 10, maximum: 50.

**Example:**

```http
GET /ingredients/search?q=گوجه&limit=10
```

**Success Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "گوجه فرنگی",
    "category": "سبزیجات",
    "default_unit": "عدد"
  }
]
```

The database currently contains 105 seeded ingredients, primarily with Persian names. English searches such as `tomato` may return no results if no matching English name exists.

---

## 3. Pantry

All pantry endpoints require JWT authentication.

### 3.1 Add Pantry Item

**Endpoint:** `POST /pantry`

**Request Body:**

```json
{
  "ingredient_id": 6,
  "quantity": 2,
  "unit": "عدد",
  "expiry_date": "2026-11-10"
}
```

`expiry_date` is optional and can be `null`.

**Success Response:** `201 Created`

```json
{
  "id": 1,
  "ingredient_id": 6,
  "quantity": 2,
  "unit": "عدد",
  "expiry_date": "2026-11-10",
  "created_at": "2026-11-04T10:00:00",
  "ingredient": {
    "id": 6,
    "name": "گوجه فرنگی",
    "category": "سبزیجات",
    "default_unit": "عدد"
  }
}
```

### 3.2 Get Pantry Items

**Endpoint:** `GET /pantry`

**Query Parameters:**
- `sort=id`: Sort by ID (default).
- `sort=expiry`: Sort by nearest expiration date first.

Items without an expiration date appear last when using `sort=expiry`.

**Example:**

```http
GET /pantry?sort=expiry
```

**Success Response:** `200 OK`

Returns a list of pantry items using the same response structure as Add Pantry Item.

### 3.3 Update Pantry Item

**Endpoint:** `PATCH /pantry/{item_id}`

**Request Body:**

```json
{
  "quantity": 3,
  "unit": "عدد",
  "expiry_date": "2026-11-12"
}
```

Only the fields that need to be updated should be sent.

**Success Response:** `200 OK`

Returns the updated pantry item.

### 3.4 Delete Pantry Item

**Endpoint:** `DELETE /pantry/{item_id}`

**Success Response:** `204 No Content`

---

## 4. Common API Rules

- Content type for JSON requests: `application/json`.
- Protected endpoints require a valid JWT access token.
- Send the token using `Authorization: Bearer <token>`.
- Dates use the ISO format: `YYYY-MM-DD`.
- Quantity must be greater than zero.
- Invalid request data returns `422 Unprocessable Entity`.
- Missing or invalid authentication returns `401 Unauthorized`.
- **Rate Limiting:** Auth endpoints enforce sliding-window rate limits to prevent brute-force attacks:
  - `POST /auth/login`: 5 requests per 60 seconds.
  - `POST /auth/register`: 5 requests per 60 seconds.
  - `POST /auth/forgot-password`: 3 requests per 10 minutes.
  - `POST /auth/reset-password`: 5 requests per 5 minutes.
  - When a rate limit is exceeded, the server returns `429 Too Many Requests` with a `Retry-After: <seconds>` header.


---

## 5. Development Environment

### Local Backend

Run the backend locally:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Base URL:

```text
http://127.0.0.1:8001
```

### Docker Backend

Start the Docker services:

```powershell
docker compose --env-file .env.docker up -d --build
```

Base URL:

```text
http://localhost:8001
```

### Android Emulator

For Android Studio's standard emulator, use:

```text
http://10.0.2.2:8001/
```

For MEmu or another emulator, use the host computer's accessible LAN IPv4 address:

```text
http://HOST_LAN_IP:8001/
```

The backend must be reachable from the emulator, and Android development builds using HTTP must allow cleartext traffic.

---

## 6. Future Planned Features

The following features are planned and are not part of the currently implemented API contract:

- AI-powered meal suggestions.
- Recipe details and recipe management.
- Nutrition analysis.
- Daily and weekly meal planning.
- Shopping list generation.
- Expiration notifications.
- Ingredient scanning and OCR.
- AI-based ingredient substitutions.
