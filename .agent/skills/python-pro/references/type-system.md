# Python 3.12+ Modern Typing Reference

## 1. Type Annotations Quick Guide

| Concept | Python 3.12+ (Use This) | Legacy Python (<3.10) (Avoid) |
|---|---|---|
| Nullable type | `str | None` | `Optional[str]` |
| Union type | `int | float` | `Union[int, float]` |
| List of items | `list[str]` | `List[str]` |
| Dictionary | `dict[str, Any]` | `Dict[str, Any]` |
| Set | `set[int]` | `Set[int]` |
| Tuple | `tuple[int, str]` | `Tuple[int, str]` |
| Homogeneous Tuple | `tuple[int, ...]` | `Tuple[int, ...]` |
| Callable | `Callable[[int], str]` | `Callable[[int], str]` |

---

## 2. Pydantic V2 Type Integration

When declaring fields in Pydantic models:

```python
from datetime import date, datetime
from pydantic import BaseModel, Field

class PantryItemCreate(BaseModel):
    ingredient_id: int = Field(gt=0, description="Foreign key to ingredient")
    quantity: float = Field(gt=0, description="Non-zero positive quantity")
    unit: str = Field(min_length=1, max_length=50)
    expiry_date: date | None = Field(default=None, description="Optional ISO date YYYY-MM-DD")
```

---

## 3. Generic Protocols & Domain Abstractions

Use `typing.Protocol` for compile-time duck typing across repository and service interfaces without runtime inheritance overhead:

```python
from typing import Protocol, TypeVar

T = TypeVar("T")

class Repository(Protocol[T]):
    def get_by_id(self, item_id: int) -> T | None: ...
    def create(self, item: T) -> T: ...
    def delete(self, item_id: int) -> bool: ...
```
