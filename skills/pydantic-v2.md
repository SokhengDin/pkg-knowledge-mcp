---
package: pydantic
version_tested: 2.x
ecosystem: python
source: https://docs.pydantic.dev/latest/
updated: 2025-05-26
---

# Pydantic v2 — What Claude Code Needs to Know

## Model Definition

```python
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Annotated

class User(BaseModel):
    name: str
    age: int = Field(gt=0, le=150)
    email: str | None = None

user = User(name="Alice", age=30)
user.model_dump()           # {"name": "Alice", "age": 30, "email": None}
user.model_dump_json()      # '{"name":"Alice","age":30,"email":null}'
User.model_validate({"name": "Alice", "age": 30})  # from dict
User.model_validate_json('{"name": "Alice", "age": 30}')  # from JSON string
```

## v1 -> v2 Migration: What Broke

| v1 | v2 |
|---|---|
| `@validator('field')` | `@field_validator('field')` |
| `@root_validator` | `@model_validator(mode='before'\|'after')` |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj(d)` | `.model_validate(d)` |
| `.parse_raw(s)` | `.model_validate_json(s)` |
| `schema()` | `model_json_schema()` |
| `__fields__` | `model_fields` |
| `Config` inner class | `model_config = ConfigDict(...)` |
| `validator(..., always=True)` | `@field_validator(..., mode='before')` |

## Validators (v2 syntax)

```python
from pydantic import field_validator, model_validator

class Product(BaseModel):
    name: str
    price: float

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()

    @field_validator('price', mode='before')  # runs before type coercion
    @classmethod
    def parse_price(cls, v):
        if isinstance(v, str):
            return float(v.replace('$', ''))
        return v

    @model_validator(mode='after')  # runs after all fields validated
    def check_price_name_combo(self) -> 'Product':
        if self.name == 'free' and self.price > 0:
            raise ValueError('free product must have price 0')
        return self
```

## Config (v2 syntax)

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,             # immutable (was: allow_mutation=False)
        str_strip_whitespace=True,
        populate_by_name=True,   # was: allow_population_by_field_name
        extra='forbid',          # reject unknown fields
        arbitrary_types_allowed=True,
    )
```

## Field with Validation

```python
from pydantic import Field
from typing import Annotated

# Using Field directly
class Item(BaseModel):
    price: float = Field(gt=0, le=10000, description="Price in USD")
    tags: list[str] = Field(default_factory=list, max_length=10)

# Using Annotated (preferred for reuse)
PositiveFloat = Annotated[float, Field(gt=0)]
ShortStr = Annotated[str, Field(max_length=100)]

class Product(BaseModel):
    price: PositiveFloat
    name: ShortStr
```

## Nested Models & Serialisation

```python
class Address(BaseModel):
    street: str
    city: str

class Person(BaseModel):
    name: str
    address: Address

# Nested serialisation
p = Person(name="Alice", address=Address(street="123 Main St", city="SF"))
p.model_dump()  # {"name": "Alice", "address": {"street": "123 Main St", "city": "SF"}}
p.model_dump(exclude={"address": {"street"}})  # exclude nested fields
p.model_dump(include={"name"})                 # only include specified
```

## Discriminated Unions

```python
from typing import Literal, Union
from pydantic import BaseModel

class Cat(BaseModel):
    pet_type: Literal['cat']
    meows: int

class Dog(BaseModel):
    pet_type: Literal['dog']
    barks: float

class Owner(BaseModel):
    pet: Union[Cat, Dog] = Field(discriminator='pet_type')

# Pydantic routes to the correct type based on pet_type value
Owner.model_validate({"pet": {"pet_type": "cat", "meows": 5}})
```

## TypeAdapter — validate without a model

```python
from pydantic import TypeAdapter

ta = TypeAdapter(list[int])
ta.validate_python([1, 2, 3])       # [1, 2, 3]
ta.validate_python(["1", "2"])      # [1, 2] — coerces strings
ta.validate_json('[1, 2, 3]')
ta.json_schema()
```

## Key Gotchas

- `@field_validator` methods must be `@classmethod` in v2
- `mode='before'` runs before type coercion; `mode='after'` runs after (default)
- `model_validator(mode='wrap')` gives you the most control (raw values + handler)
- `model_dump(mode='json')` ensures all values are JSON-serialisable
- Pydantic v2 is 5–50× faster than v1 due to Rust core (pydantic-core)
- `model_rebuild()` needed if model references forward-declared types
