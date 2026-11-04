from app.models import Ingredient


def test_search_ingredients(client, db_session):
    db_session.add(
        Ingredient(
            name="Test Tomato",
            category="Vegetable",
            default_unit="kg",
        )
    )
    db_session.commit()

    response = client.get("/ingredients/search?q=Tomato")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Tomato"


def test_search_ingredients_limit(client, db_session):
    db_session.add_all([
        Ingredient(name="Test Apple"),
        Ingredient(name="Test Apricot"),
        Ingredient(name="Test Avocado"),
    ])
    db_session.commit()

    response = client.get("/ingredients/search?q=Test&limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_ingredients_invalid_query(client):
    response = client.get("/ingredients/search?q=")

    assert response.status_code == 422


def test_search_ingredients_invalid_limit(client):
    response = client.get(
        "/ingredients/search?q=Tomato&limit=100"
    )

    assert response.status_code == 422