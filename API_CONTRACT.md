# Safreyar API Contract



**Project:** Safreyar  

**Backend:** FastAPI + PostgreSQL  

**Frontend:** Kotlin  

**API Base URL (Local):** `http://127.0.0.1:8001`



---



## 1. Authentication



### 1.1 Register



**Endpoint:** `POST /auth/register`  

**Authentication:** Not required  

**Success Status:** `201 Created`



Request Body:



```json

{

  "first_name": "Ali",

  "last_name": "Ahmadi",

  "email": "ali@example.com",

  "password": "Password123",

  "confirm_password": "Password123"

}

```



Success Response:



```json

{

  "id": 1,

  "first_name": "Ali",

  "last_name": "Ahmadi",

  "email": "ali@example.com"

}

```



Possible Errors:

- `409 Conflict`: Email already registered.

- `422 Unprocessable Entity`: Invalid input.



### 1.2 Login



**Endpoint:** `POST /auth/login`  

**Authentication:** Not required  

**Success Status:** `200 OK`



Request Body:



```json

{

  "email": "ali@example.com",

  "password": "Password123"

}

```



Success Response:



```json

{

  "access_token": "JWT_TOKEN",

  "token_type": "bearer"

}

```



Possible Errors:

- `401 Unauthorized`: Incorrect email or password.

- `422 Unprocessable Entity`: Invalid input.



**Important:** The frontend must save the access token securely and use it for authenticated requests.



### 1.3 Get Current User



**Endpoint:** `GET /auth/me`  

**Authentication:** Required



Header:



```http

Authorization: Bearer YOUR_ACCESS_TOKEN

```



Success Response:



```json

{

  "id": 1,

  "first_name": "Ali",

  "last_name": "Ahmadi",

  "email": "ali@example.com"

}

```



---



## 2. Ingredients



### 2.1 Search Ingredients



**Endpoint:** `GET /ingredients/search`  

**Authentication:** Not required



Query Parameters:



| Parameter | Required | Description |

|---|---|---|

| q | Yes | Ingredient name or search text |

| limit | No | Maximum results (default: 10, max: 50) |



Example:



```http

GET /ingredients/search?q=tomato&limit=10

```



Success Response:



```json



  {

    "id": 1,

    "name": "Tomato",

    "category": "Vegetable",

    "default_unit": "kg"

  }

]

```



---



## 3. Pantry



All pantry endpoints require JWT authentication.



Required Header:



```http

Authorization: Bearer YOUR_ACCESS_TOKEN

```



### 3.1 Add Pantry Item



**Endpoint:** `POST /pantry`  

**Success Status:** `201 Created`



Request Body:



```json

{

  "ingredient_id": 1,

  "quantity": 2,

  "unit": "kg",

  "expiry_date": "2026-11-10"

}

```



`expiry_date` can be `null`.



Success Response:



```json

{

  "id": 1,

  "ingredient_id": 1,

  "quantity": 2,

  "unit": "kg",

  "expiry_date": "2026-11-10",

  "created_at": "2026-11-01T10:00:00",

  "ingredient": {

    "id": 1,

    "name": "Tomato",

    "category": "Vegetable",

    "default_unit": "kg"

  }

}

```



Possible Errors:

- `401 Unauthorized`: Missing or invalid token.

- `404 Not Found`: Ingredient does not exist.

- `422 Unprocessable Entity`: Invalid input.



### 3.2 Get Pantry Items



**Endpoint:** `GET /pantry`  

**Authentication:** Required



Optional Query Parameter:



| Parameter | Values | Default |

|---|---|---|

| sort | `id`, `expiry` | `id` |



Examples:



```http

GET /pantry

```



```http

GET /pantry?sort=expiry

```



`sort=expiry` sorts items by nearest expiration date first. Items without an expiration date appear last.



Success Response:



```json



  {

    "id": 1,

    "ingredient_id": 1,

    "quantity": 2,

    "unit": "kg",

    "expiry_date": "2026-11-10",

    "created_at": "2026-11-01T10:00:00",

    "ingredient": {

      "id": 1,

      "name": "Tomato",

      "category": "Vegetable",

      "default_unit": "kg"

    }

  }

]

```



Each user can only access their own pantry items.



### 3.3 Update Pantry Item



**Endpoint:** `PATCH /pantry/{item_id}`  

**Authentication:** Required



Request Body (partial update):



```json

{

  "quantity": 3

}

```



Other supported fields:

- `quantity`

- `unit`

- `expiry_date`



Success Response: Updated pantry item.



Possible Errors:

- `401 Unauthorized`: Missing or invalid token.

- `404 Not Found`: Item does not exist or does not belong to the current user.

- `422 Unprocessable Entity`: Invalid input.



### 3.4 Delete Pantry Item



**Endpoint:** `DELETE /pantry/{item_id}`  

**Authentication:** Required  

**Success Status:** `204 No Content`



Example:



```http

DELETE /pantry/1

```



Success response has no body.



Possible Errors:

- `401 Unauthorized`: Missing or invalid token.

- `404 Not Found`: Item does not exist or does not belong to the current user.



---



## 4. Authentication Rules



For all protected endpoints, include:



```http

Authorization: Bearer YOUR_ACCESS_TOKEN

```



The token is obtained from:



```http

POST /auth/login

```



If the token is missing or invalid, the API returns `401 Unauthorized`.



---



## 5. General API Rules



- Request and response bodies use JSON.

- Dates use `YYYY-MM-DD`.

- Date-time values use ISO 8601 format.

- Quantity must be greater than zero.

- Email addresses must be valid.

- Passwords must contain at least 8 characters.

- Registration requires matching `password` and `confirm_password`.

- Pantry records are isolated by user.

- Do not hardcode the production API URL in the Android application.



---



## 6. Local Development



Local backend URL:



```text

http://127.0.0.1:8001

```



Swagger documentation:



```text

http://127.0.0.1:8001/docs

```



**Android Emulator:** Use `http://10.0.2.2:8001` instead of `127.0.0.1` when connecting to a backend running on the host computer.



**Physical Android Device:** Use the computer's local network IP address, with the backend configured to accept network connections.



---



## 7. Future APIs



The following features are not part of the current API contract yet:



- AI meal suggestions

- Recipe management

- Nutrition analysis

- Shopping lists

- Expiration notifications

- OCR and image processing



These endpoints will be documented when implemented.

