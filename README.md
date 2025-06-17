# Pydantic-Mini Documentation

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Validation](#validation)
- [Serialization](#serialization)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

## Overview

Pydantic-mini is a lightweight Python library that extends the functionality of Python's native dataclass by providing built-in validation, serialisation, and support for custom validators. It is designed to be simple, minimalistic, and based entirely on Python's standard library, making it perfect for projects requiring data validation and object-relational mapping (ORM) without relying on third-party dependencies.

### Key Features

- **Type and Value Validation**: Enforces type validation for fields using field annotations with built-in validators for common field types
- **Custom Validators**: Easily define custom validation functions for specific fields
- **Serialisation Support**: Instances can be serialised to JSON, dictionaries, and CSV formats
- **Lightweight and Fast**: Built entirely on Python's standard library with no external dependencies
- **Multiple Input Formats**: Accepts data in various formats, including JSON, dictionaries, CSV, etc.
- **Simple ORM Capabilities**: Build lightweight ORMs for basic data management

## Installation

### From PyPI (when available)
```bash
pip install pydantic-mini
```

### From Source
```bash
git clone https://github.com/nshaibu/pydantic-mini.git
cd pydantic-mini
# Use the code directly in your project
```

## Quick Start

Here's a simple example to get you started:

```python
from pydantic_mini import BaseModel

class Person(BaseModel):
    name: str
    age: int

# Create an instance
person = Person(name="Alice", age=30)
print(person)  # Person(name='Alice', age=30)

# Validation happens automatically
try:
    invalid_person = Person(name="Bob", age="not_a_number")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Core Concepts

### BaseModel

`BaseModel` is the foundation class that all your data models should inherit from. It provides:
- Automatic type validation
- Serialization capabilities
- Custom validation support
- Configuration options

### MiniAnnotated

`MiniAnnotated` is used to add metadata and validation rules to fields:

```python
from pydantic_mini import BaseModel, MiniAnnotated, Attrib

class User(BaseModel):
    username: MiniAnnotated[str, Attrib(max_length=20)]
    age: MiniAnnotated[int, Attrib(gt=0, default=18)]
```

### Attrib

`Attrib` defines field attributes and validation rules:
- `default`: Default value for the field
- `default_factory`: Function to generate default value
- `max_length`: Maximum length for strings
- `gt`: Greater than validation for numbers
- `pattern`: Regex pattern for string validation
- `validators`: List of custom validator functions

## API Reference

### BaseModel

The base class for all data models.

#### Class Methods

##### `loads(data, _format="dict")`
Load data from various formats into model instances.

**Parameters:**
- `data`: Input data (string, dict, or other format-specific data)
- `_format`: Format of input data (`"json"`, `"dict"`, `"csv"`)

**Returns:** Model instance or list of instances (for CSV)

**Example:**
```python
# From JSON string
json_data = '{"name": "John", "age": 30}'
person = Person.loads(json_data, _format="json")

# From dictionary
dict_data = {"name": "Alice", "age": 25}
person = Person.loads(dict_data, _format="dict")

# From CSV
csv_data = "name,age\nJohn,30\nAlice,25"
people = Person.loads(csv_data, _format="csv")
```

#### Instance Methods

##### `dump(_format="dict")`
Serialize the model instance to various formats.

**Parameters:**
- `_format`: Output format (`"json"`, `"dict"`, `"csv"`)

**Returns:** Serialized data in the specified format

**Example:**
```python
person = Person(name="John", age=30)

# To JSON string
json_output = person.dump(_format="json")

# To dictionary
dict_output = person.dump(_format="dict")
```

##### `__model_init__(self, **kwargs)`
Optional method for custom initialization logic.

**Example:**
```python
from typing import Optional
from dataclasses import InitVar

class DatabaseModel(BaseModel):
    id: int
    name: str
    database: InitVar[Optional[object]] = None
    
    def __model_init__(self, database):
        if database is not None:
            # Custom initialization logic
            self.id = database.get_next_id()
```

## Validation

### Type Validation

Pydantic-mini automatically validates field types based on annotations:

```python
class Product(BaseModel):
    name: str
    price: float
    quantity: int
    is_available: bool
```

### Built-in Validators

Use `Attrib` to add built-in validation rules:

```python
class User(BaseModel):
    username: MiniAnnotated[str, Attrib(max_length=20)]
    age: MiniAnnotated[int, Attrib(gt=18)]
    email: MiniAnnotated[str, Attrib(pattern=r"^\S+@\S+\.\S+$")]
    score: MiniAnnotated[float, Attrib(default=0.0)]
```

### Custom Field Validators

Define custom validation functions:

```python
from pydantic_mini.exceptions import ValidationError

def validate_not_kofi(instance, value: str):
    if value.lower() == "kofi":
        raise ValidationError("Kofi is not a valid name")
    return value.upper()  # Transform the value

class Employee(BaseModel):
    name: MiniAnnotated[str, Attrib(validators=[validate_not_kofi])]
    department: str
```

### Method-based Validators

Define validators as methods with the pattern `validate_<field_name>`:

```python
class School(BaseModel):
    name: str
    students_count: int
    
    def validate_name(self, value, field):
        if len(value) > 50:
            raise ValidationError("School name too long")
        return value
    
    def validate_students_count(self, value, field):
        if value < 0:
            raise ValidationError("Students count cannot be negative")
        return value
```

### Global Validators

Apply validation rules to all fields:

```python
class StrictModel(BaseModel):
    field1: str
    field2: str
    field3: str
    
    def validate(self, value, field):
        if isinstance(value, str) and len(value) > 100:
            raise ValidationError(f"Field {field.name} is too long")
        return value
```

### Validator Notes

- **Transformation**: Validators can transform values by returning the modified value
- **Error Handling**: Validators must raise `ValidationError` when validation fails
- **Type Enforcement**: Type annotation constraints are enforced at runtime
- **Pre-formatting**: Use validators for formatting values before type checking

## Serialization

### Supported Formats

Pydantic-mini supports three serialization formats:

#### JSON
```python
person = Person(name="John", age=30)

# Serialize to JSON
json_str = person.dump(_format="json")
print(json_str)  # '{"name": "John", "age": 30}'

# Deserialize from JSON
person = Person.loads('{"name": "Alice", "age": 25}', _format="json")
```

#### Dictionary
```python
# Serialize to dictionary
person_dict = person.dump(_format="dict")
print(person_dict)  # {'name': 'John', 'age': 30}

# Deserialize from dictionary
person = Person.loads({"name": "Bob", "age": 35}, _format="dict")
```

#### CSV
```python
# Deserialize from CSV (returns list of instances)
csv_data = "name,age\nJohn,30\nAlice,25\nBob,35"
people = Person.loads(csv_data, _format="csv")

for person in people:
    print(person)
```

## Configuration

### Model Configuration

Configure model behavior using the `Config` class:

```python
import os
from datetime import datetime
import typing

class EventResult(BaseModel):
    error: bool
    task_id: str
    event_name: str
    content: typing.Any
    init_params: typing.Optional[typing.Dict[str, typing.Any]]
    call_params: typing.Optional[typing.Dict[str, typing.Any]]
    process_id: MiniAnnotated[int, Attrib(default_factory=lambda: os.getpid())]
    creation_time: MiniAnnotated[float, Attrib(default_factory=lambda: datetime.now().timestamp())]
    
    class Config:
        unsafe_hash = False
        frozen = False
        eq = True
        order = False
        disable_typecheck = False
        disable_all_validation = False
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `init` | `bool` | `True` | Whether the `__init__` method is generated for the dataclass |
| `repr` | `bool` | `True` | Whether a `__repr__` method is generated |
| `eq` | `bool` | `True` | Enables the generation of `__eq__` for comparisons |
| `order` | `bool` | `False` | Enables ordering methods (`__lt__`, `__gt__`, etc.) |
| `unsafe_hash` | `bool` | `False` | Allows an unsafe implementation of `__hash__` |
| `frozen` | `bool` | `False` | Makes the dataclass instances immutable |
| `disable_typecheck` | `bool` | `False` | Disable runtime type checking in models |
| `disable_all_validation` | `bool` | `False` | Disable all validation logic (type + custom rules) |

## Advanced Usage

### Using InitVar

For fields that are only used during initialization:

```python
from dataclasses import InitVar
import typing

class DatabaseRecord(BaseModel):
    id: int
    name: str
    database: InitVar[typing.Optional[object]] = None
    
    def __model_init__(self, database):
        if database is not None and self.id is None:
            self.id = database.get_next_id()
```

### Default Factories

Use `default_factory` for dynamic default values:

```python
import uuid
from datetime import datetime

class Task(BaseModel):
    id: MiniAnnotated[str, Attrib(default_factory=lambda: str(uuid.uuid4()))]
    created_at: MiniAnnotated[float, Attrib(default_factory=lambda: datetime.now().timestamp())]
    title: str
    completed: MiniAnnotated[bool, Attrib(default=False)]
```

### Simple ORM Usage

Create lightweight ORMs for in-memory data management:

```python
class PersonORM:
    def __init__(self):
        self.people_db = []
    
    def create(self, **kwargs):
        person = Person(**kwargs)
        self.people_db.append(person)
        return person
    
    def find_by_age(self, min_age):
        return [p for p in self.people_db if p.age >= min_age]
    
    def find_by_name(self, name):
        return [p for p in self.people_db if p.name == name]

# Usage
orm = PersonORM()
orm.create(name="John", age=30)
orm.create(name="Alice", age=25)
orm.create(name="Bob", age=35)

adults = orm.find_by_age(18)
johns = orm.find_by_name("John")
```

## Examples

### Complete User Management Example

```python
import re
from typing import Optional, List
from pydantic_mini import BaseModel, MiniAnnotated, Attrib
from pydantic_mini.exceptions import ValidationError

def validate_strong_password(instance, password: str):
    """Validate password strength."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit")
    return password

def validate_username(instance, username: str):
    """Validate username format."""
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValidationError("Username can only contain letters, numbers, and underscores")
    return username.lower()

class User(BaseModel):
    username: MiniAnnotated[str, Attrib(
        max_length=30, 
        validators=[validate_username]
    )]
    email: MiniAnnotated[str, Attrib(
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )]
    password: MiniAnnotated[str, Attrib(validators=[validate_strong_password])]
    age: MiniAnnotated[int, Attrib(gt=13, default=18)]
    is_active: MiniAnnotated[bool, Attrib(default=True)]
    roles: Optional[List[str]] = None
    
    def validate_age(self, value, field):
        if value > 120:
            raise ValidationError("Age seems unrealistic")
        return value
    
    class Config:
        frozen = False
        eq = True

# Usage example
try:
    user = User(
        username="JohnDoe123",
        email="john@example.com",
        password="SecurePass123",
        age=25,
        roles=["user", "admin"]
    )
    
    # Serialize user
    user_json = user.dump(_format="json")
    print("User JSON:", user_json)
    
    # Load from JSON
    loaded_user = User.loads(user_json, _format="json")
    print("Loaded user:", loaded_user)
    
except ValidationError as e:
    print(f"Validation error: {e}")
```

### E-commerce Product Example

```python
from decimal import Decimal
from typing import Optional, List
from enum import Enum

class ProductStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"

def validate_price(instance, price: float):
    if price < 0:
        raise ValidationError("Price cannot be negative")
    if price > 1000000:
        raise ValidationError("Price too high")
    return round(price, 2)

def validate_sku(instance, sku: str):
    if not re.match(r"^[A-Z]{2,3}-\d{4,6}$", sku):
        raise ValidationError("SKU must be in format XX-NNNN or XXX-NNNNNN")
    return sku.upper()

class Product(BaseModel):
    name: MiniAnnotated[str, Attrib(max_length=100)]
    sku: MiniAnnotated[str, Attrib(validators=[validate_sku])]
    price: MiniAnnotated[float, Attrib(validators=[validate_price])]
    description: Optional[str] = None
    category: str
    tags: Optional[List[str]] = None
    stock_quantity: MiniAnnotated[int, Attrib(default=0)]
    status: str = ProductStatus.ACTIVE.value
    
    def validate_stock_quantity(self, value, field):
        if value < 0:
            raise ValidationError("Stock quantity cannot be negative")
        return value
    
    def validate_category(self, value, field):
        valid_categories = ["electronics", "clothing", "books", "home", "sports"]
        if value.lower() not in valid_categories:
            raise ValidationError(f"Category must be one of: {valid_categories}")
        return value.lower()

# Create products
products = [
    Product(
        name="Wireless Headphones",
        sku="EL-1234",
        price=99.99,
        description="High-quality wireless headphones",
        category="electronics",
        tags=["wireless", "audio", "bluetooth"],
        stock_quantity=50
    ),
    Product(
        name="Python Programming Book",
        sku="BK-5678",
        price=29.99,
        category="books",
        stock_quantity=25
    )
]

# Serialize to JSON
products_json = [p.dump(_format="json") for p in products]
print("Products JSON:", products_json)
```

## Error Handling

### ValidationError

All validation failures raise `ValidationError`:

```python
from pydantic_mini.exceptions import ValidationError

try:
    user = User(username="", email="invalid-email", age=-5)
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Handle the error appropriately
```

### Best Practices for Error Handling

```python
def create_user_safely(user_data):
    try:
        user = User.loads(user_data, _format="dict")
        return {"success": True, "user": user}
    except ValidationError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}

# Usage
result = create_user_safely({
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123"
})

if result["success"]:
    print("User created:", result["user"])
else:
    print("Error:", result["error"])
```

## Performance Considerations

### Disabling Validation

For performance-critical scenarios, you can disable validation:

```python
class FastModel(BaseModel):
    field1: str
    field2: int
    
    class Config:
        disable_typecheck = True
        disable_all_validation = True
```

### Efficient Serialization

Choose the appropriate serialization format based on your needs:
- Use `dict` format for Python-to-Python communication
- Use `json` format for API responses and storage
- Use `csv` format for data export and reporting

## Contributing

Contributions are welcome! To contribute to pydantic-mini:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
git clone https://github.com/nshaibu/pydantic-mini.git
cd pydantic-mini
# Set up your development environment
# Run tests
python -m pytest tests/
```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Add docstrings for public APIs
- Write comprehensive tests for new features

## License

Pydantic-mini is open-source and available under the GPL License.

## Changelog

### Future Releases
- Additional built-in validators
- Performance optimisations
- Extended serialisation formats
- Better error messages
- Comprehensive test suite

---

*This documentation is for pydantic-mini, a lightweight alternative to Pydantic with zero external dependencies.*
