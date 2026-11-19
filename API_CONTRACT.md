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

## 4. AI Meal Suggestions & Recipes

This module provides AI-driven Persian recipe generation based on the authenticated user's pantry contents.

### 4.1 Generate Meal Suggestions

**Endpoint:** `POST /suggestions`  
**Authentication:** Required (`Authorization: Bearer <token>`)

**Request Body:**

```json
{
  "meal_type": "lunch",
  "servings": 2
}
```

**Validation:**
- `meal_type`: Required. Allowed values: `"breakfast"`, `"lunch"`, `"dinner"`, `"snack"`.
- `servings`: Required integer, must be greater than zero (`> 0`). Default is `2`.
- **Source of truth:** Pantry inventory is loaded directly from the database for the authenticated user. Client cannot manipulate available ingredients.
- **Expiry prioritization:** Ingredients closest to expiration (lowest days left) are prioritized to minimize food waste.

**Caching Behavior:**
- A deterministic SHA-256 cache key is computed from: `user_id`, `meal_type`, `servings`, model version, and normalized/sorted pantry items (ingredient IDs, names, quantities, units, expiry dates).
- If identical pantry state and parameters were processed within `RECIPE_CACHE_EXPIRE_HOURS` (default: 24h), cached recipes are returned instantly without calling the LLM.
- Any change in pantry quantities, units, or expiry dates automatically generates a different hash, invalidating the previous cache.

**Rate Limiting:**
- Throttled per authenticated user (`SUGGESTIONS_RATE_LIMIT_TIMES` / `SUGGESTIONS_RATE_LIMIT_SECONDS`, default: 10 requests per 60 seconds).
- Exceeding the quota returns `429 Too Many Requests` with a `Retry-After: <seconds>` header.

**Success Response:** `200 OK`

```json
[
  {
    "id": 12,
    "user_id": 1,
    "title": "املت گوجه‌فرنگی قهوه‌خانه‌ای",
    "summary": "یک املت اصیل و لذیذ ایرانی با گوجه‌فرنگی پخته و تخم‌مرغ تازه، مناسب برای صبحانه یا شام سریع.",
    "emoji": "🍳",
    "cooking_time": 15,
    "time_minutes": 15,
    "difficulty": "easy",
    "servings": 2,
    "ingredients": [
      {
        "name": "تخم‌مرغ",
        "amount": 4.0,
        "unit": "piece",
        "in_pantry": true
      },
      {
        "name": "گوجه‌فرنگی",
        "amount": 4.0,
        "unit": "piece",
        "in_pantry": true
      },
      {
        "name": "روغن مایع",
        "amount": 20.0,
        "unit": "ml",
        "in_pantry": false
      }
    ],
    "uses": ["تخم‌مرغ", "گوجه‌فرنگی"],
    "missing": ["روغن مایع"],
    "steps": [
      "گوجه‌فرنگی‌ها را رنده یا نگینی خرد کرده و در تابه تفت دهید تا آب آن به آرامی تبخیر شود.",
      "روغن مایع، نمک و فلفل را به گوجه‌ها اضافه کرده و کمی تفت دهید تا روغن خوش‌رنگ شود.",
      "تخم‌مرغ‌ها را روی گوجه‌ها شکسته، به آرامی مخلوط کنید و بگذارید با حرارت ملایم ببندد."
    ],
    "nutrition": {
      "calories": 210,
      "protein_g": 13.0,
      "fiber_g": 2.0,
      "carbs_g": 6.0,
      "fat_g": 15.0
    },
    "created_at": "2026-11-19T14:30:00"
  }
]
```

**Standardized Error Responses:**

| HTTP Status | Error Code | Description | Example Detail |
|---|---|---|---|
| `400 Bad Request` | `EMPTY_PANTRY` | User pantry contains zero items | `انبار شما خالی است. لطفاً ابتدا موادی به انبار خود اضافه کنید.` |
| `422 Unprocessable Entity` | `INVALID_REQUEST` | Unsupported meal type or non-positive servings | `داده‌های ورودی نامعتبر است.` |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | User exceeded suggestions quota | `سقف مجاز درخواست‌های پیشنهاد غذا به پایان رسیده است.` |
| `502 Bad Gateway` | `LLM_PROVIDER_ERROR` | Anthropic/Claude API unreachable | `خطا در برقراری ارتباط با ارائه‌دهنده هوش مصنوعی.` |
| `502 Bad Gateway` | `INVALID_LLM_RESPONSE` | LLM response failed validation after retry | `پاسخ دریافتی از هوش مصنوعی ساختار معتبری نداشت.` |
| `504 Gateway Timeout` | `LLM_TIMEOUT` | LLM call exceeded timeout threshold | `پاسخ سرویس هوش مصنوعی بیش از حد مجاز طول کشید.` |

---

### 4.2 Get Saved Recipe Details

**Endpoint:** `GET /recipes/{id}`  
**Authentication:** Required (`Authorization: Bearer <token>`)

**Path Parameters:**
- `id` (integer, required): Database primary key ID of the saved recipe.

**Security & Data Isolation:**
- Only the user who generated/saved the recipe can access it.
- If the recipe does not exist or belongs to another user, the server returns `404 Not Found` with error code `RECIPE_NOT_FOUND`.
- Does not invoke the LLM.

**Success Response:** `200 OK`

```json
{
  "id": 12,
  "user_id": 1,
  "title": "املت گوجه‌فرنگی قهوه‌خانه‌ای",
  "summary": "یک املت اصیل و لذیذ ایرانی با گوجه‌فرنگی پخته و تخم‌مرغ تازه، مناسب برای صبحانه یا شام سریع.",
  "emoji": "🍳",
  "cooking_time": 15,
  "time_minutes": 15,
  "difficulty": "easy",
  "servings": 2,
  "ingredients": [
    {
      "name": "تخم‌مرغ",
      "amount": 4.0,
      "unit": "piece",
      "in_pantry": true
    }
  ],
  "uses": ["تخم‌مرغ"],
  "missing": ["روغن"],
  "steps": ["گوجه‌ها را تفت دهید..."],
  "nutrition": {
    "calories": 210,
    "protein_g": 13.0,
    "fiber_g": 2.0,
    "carbs_g": 6.0,
    "fat_g": 15.0
  },
  "created_at": "2026-11-19T14:30:00"
}
```

**Possible Errors:**
- `401 Unauthorized`: Missing or invalid Bearer token.
- `404 Not Found`: Recipe with given ID does not exist or belongs to another user (`RECIPE_NOT_FOUND`).

---

## 5. Common API Rules

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

## 6. Development Environment

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

## 7. Future Planned Features

The following features are planned for future sprints:

- Nutrition goal tracking & historical analytics.
- Daily and weekly meal schedule planning.
- Automated grocery shopping list generation.
- Daily push notifications for items nearing expiration ($\le 3$ days).
- Receipt & ingredient packaging barcode/OCR scanner.
- Semantic ingredient substitution engine (e.g. Greek yogurt for sour cream).
