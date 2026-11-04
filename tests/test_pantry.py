
from app.models import Ingredient


def create_user_and_token(client, email):
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "TestPassword123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    return response.json()["access_token"]


def create_ingredient(db_session):
    ingredient = Ingredient(
        name="Test Potato",
        category="Vegetable",
        default_unit="kg",
    )
    db_session.add(ingredient)
    db_session.commit()
    db_session.refresh(ingredient)
    return ingredient.id


def add_pantry_item(client, token, ingredient_id, quantity=2, expiry_date="2026-12-10"):
    return client.post(
        "/pantry",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "ingredient_id": ingredient_id,
            "quantity": quantity,
            "unit": "kg",
            "expiry_date": expiry_date,
        },
    )


def test_create_pantry_item(client, db_session):
    token = create_user_and_token(client, "pantry1@example.com")
    ingredient_id = create_ingredient(db_session)

    response = add_pantry_item(client, token, ingredient_id)

    assert response.status_code == 201
    assert response.json()["quantity"] == 2
    assert response.json()["ingredient"]["name"] == "Test Potato"


def test_list_pantry_items(client, db_session):
    token = create_user_and_token(client, "pantry2@example.com")
    ingredient_id = create_ingredient(db_session)

    add_pantry_item(client, token, ingredient_id)

    response = client.get(
        "/pantry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_sort_pantry_by_expiry(client, db_session):
    token = create_user_and_token(client, "pantry3@example.com")
    ingredient_id = create_ingredient(db_session)

    add_pantry_item(client, token, ingredient_id, expiry_date="2026-12-20")
    add_pantry_item(client, token, ingredient_id, expiry_date="2026-12-05")
    add_pantry_item(client, token, ingredient_id, expiry_date=None)

    response = client.get(
        "/pantry?sort=expiry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    items = response.json()

    assert len(items) == 3
    assert items[0]["expiry_date"] == "2026-12-05"
    assert items[1]["expiry_date"] == "2026-12-20"
    assert items[2]["expiry_date"] is None


def test_update_pantry_item(client, db_session):
    token = create_user_and_token(client, "pantry4@example.com")
    ingredient_id = create_ingredient(db_session)

    created = add_pantry_item(client, token, ingredient_id)
    item_id = created.json()["id"]

    response = client.patch(
        f"/pantry/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"quantity": 5},
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 5


def test_delete_pantry_item(client, db_session):
    token = create_user_and_token(client, "pantry5@example.com")
    ingredient_id = create_ingredient(db_session)

    created = add_pantry_item(client, token, ingredient_id)
    item_id = created.json()["id"]

    response = client.delete(
        f"/pantry/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    list_response = client.get(
        "/pantry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_pantry_requires_authentication(client):
    response = client.get("/pantry")

    assert response.status_code == 401


def test_user_cannot_access_another_users_item(client, db_session):
    token1 = create_user_and_token(client, "owner@example.com")
    token2 = create_user_and_token(client, "other@example.com")

    ingredient_id = create_ingredient(db_session)

    created = add_pantry_item(client, token1, ingredient_id)
    item_id = created.json()["id"]

    response = client.get(
        "/pantry",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 200
    assert response.json() == []

    update_response = client.patch(
        f"/pantry/{item_id}",
        headers={"Authorization": f"Bearer {token2}"},
        json={"quantity": 99},
    )

    assert update_response.status_code == 404

    delete_response = client.delete(
        f"/pantry/{item_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert delete_response.status_code == 404
