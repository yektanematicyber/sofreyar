# Service and Repository Pattern Reference

## 1. Repository Implementation Example

Encapsulate all SQLAlchemy queries for the `PantryItem` entity inside `app/repositories/pantry.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.pantry_item import PantryItem

class PantryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_and_user(self, item_id: int, user_id: int) -> PantryItem | None:
        stmt = select(PantryItem).where(
            PantryItem.id == item_id,
            PantryItem.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def list_by_user(self, user_id: int, sort_by_expiry: bool = False) -> list[PantryItem]:
        stmt = select(PantryItem).where(PantryItem.user_id == user_id)
        if sort_by_expiry:
            # Nulls last when sorting by expiry date
            stmt = stmt.order_by(PantryItem.expiry_date.nulls_last(), PantryItem.id.asc())
        else:
            stmt = stmt.order_by(PantryItem.id.asc())
        return list(self.db.scalars(stmt).all())

    def create(self, item: PantryItem) -> PantryItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item: PantryItem) -> None:
        self.db.delete(item)
        self.db.commit()
```

---

## 2. Service Implementation Example

Encapsulate business logic in `app/services/pantry.py`:

```python
from app.repositories.pantry import PantryRepository
from app.models.pantry_item import PantryItem
from app.schemas.pantry_item import PantryItemCreate, PantryItemUpdate

class PantryService:
    def __init__(self, repo: PantryRepository):
        self.repo = repo

    def add_item(self, user_id: int, data: PantryItemCreate) -> PantryItem:
        item = PantryItem(
            user_id=user_id,
            ingredient_id=data.ingredient_id,
            quantity=data.quantity,
            unit=data.unit,
            expiry_date=data.expiry_date,
        )
        return self.repo.create(item)

    def remove_item(self, user_id: int, item_id: int) -> bool:
        item = self.repo.get_by_id_and_user(item_id=item_id, user_id=user_id)
        if not item:
            return False
        self.repo.delete(item)
        return True
```

---

## 3. Slim Router Implementation

The router now focuses strictly on HTTP handling and serialization:

```python
@router.post("/", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def add_pantry_item(
    payload: PantryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = PantryRepository(db)
    service = PantryService(repo)
    return service.add_item(user_id=current_user.id, data=payload)
```
