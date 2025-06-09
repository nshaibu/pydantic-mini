# pydantic-mini

**pydantic-mini** is a lightweight Python library that extends the functionality of Python's native `dataclass` 
by providing built-in validation, serialization, and support for custom validators. It is designed to be simple, 
minimalistic, and based entirely on Python’s standard library, making it perfect for projects, data validation, 
and object-relational mapping (ORM) without relying on third-party dependencies.

## Features

- **Type and Value Validation**: 
  - Enforces type validation for fields using field annotations.
  - Includes built-in validators for common field types.
  
- **Custom Validators**: 
  - Easily define your own custom validation functions for specific fields.

- **Serialization Support**: 
  - Instances can be serialized to JSON, dictionaries, and CSV formats.

- **Lightweight and Fast**: 
  - Built entirely on Python’s standard library, no external dependencies are required.

- **Supports Multiple Input Formats**: 
  - Accepts data in various formats, including JSON, dictionaries, CSV, etc.

- **Simple ORM Capabilities**: 
  - Use the library to build lightweight ORMs (Object-Relational Mappers) for basic data management.

---

## Installation

You can install `pydantic-mini` from PyPI once it's available:

```bash
pip install pydantic-mini
```

Alternatively, you can clone this repository and use the code directly in your project.

---

## Usage

### 1. Define a Dataclass with Validation

```python
from pydantic_mini import BaseModel

class Person(BaseModel):
    name: str
    age: int
```

### 2. Adding Validators For Individual Fields

You can define your own validators.

```python
import typing
from pydantic_mini import BaseModel, MiniAnnotated, Attrib
from pydantic_mini.exceptions import ValidationError


# NOTE: All validators can be used for field values transformation
# by returning the transformed value from the validator function or method.

# NOTE: Validators must raise ValidationError if validation condition fails.
# NOTE: pydantic_mini use type annotation to enforce type constraints.
# NOTE: pre-formatters are used for formatting values before typechecking runtime is executed.

# Custom validation for not accepting name kofi
def kofi_not_accepted(instance, value: str):
  if value == "kofi":
    # validators must raise ValidationError when validation fails.
    raise ValidationError("Kofi is not a valid name")

  # If you want to apply a transformation and save the result into the model, 
  # return the transformed result you want to save. For instance, if you want the names to be capitalized, 
  # return the capitalized version.
  return value.upper()


class Employee(BaseModel):
  name: MiniAnnotated[str, Attrib(max_length=20, validators=[kofi_not_accepted])]
  age: MiniAnnotated[int, Attrib(default=40, gt=20)]
  email: MiniAnnotated[str, Attrib(pattern=r"^\S+@\S+\.\S+$")]
  school: str

  # You can define validators by adding a method with the name 
  # "validate_<FIELD_NAME>" e.g to validate school name
  def validate_school(self, value, field):
    if len(value) > 20:
      raise ValidationError("School names cannot be greater than 20")

  # You can apply a general rule or transformation to all fields by implementing
  # the method "validate". it takes the argument value and field
  def validate(self, value, field):
    if len(value) > 10:
      raise ValidationError("Too long")


# implement model __model_init__
class C(BaseModel):
  i: int
  j: typing.Optional[int]
  database: InitVar[typing.Optional[DatabaseType]] = None

  def __model_init__(self, database):
    if self.j is None and database is not None:
      self.j = database.lookup('j')

```

**NOTE**: All validators can applied transformations to a field when they return the transformed value.

### 3. Creating Instances from Different Formats

#### From JSON:

```python
import json
from pydantic_mini import Basemodel

class PersonModel(BaseModel):
  name: str
  age: int

data = '{"name": "John", "age": 30}'
person = PersonModel.loads(data, _format="json")
print(person)
```

#### From Dictionary:

```python
data = {"name": "Alice", "age": 25}
person = PersonModel.loads(data, _format="dict")
print(person)
```

#### From CSV:

```python
csv_data = "name,age\nJohn,30\nAlice,25"
people = PersonModel.loads(csv_data, _format="csv")
for person in people:
    print(person)
```

### 4. Serialization

`pydantic-mini` supports serializing instances to JSON, dictionaries, or CSV formats.

```python
# Serialize to JSON
json_data = person.dump(_format="json")
print(json_data)

# Serialize to a dictionary
person_dict = person.dump(_format="dict")
print(person_dict)
```

### 5. Simple ORM Use Case

You can use this library to create simple ORMs for in-memory databases.

```python
# Example: Create a simple in-memory ORM for a list of "Person" instances
people_db = []

# Add a new person to the database
new_person = Person(name="John", age=30)
people_db.append(new_person)

# Query the database (e.g., filter by age)
adults = [p for p in people_db if p.age >= 18]
print(adults)
```

## Supported Formats

- **JSON**: Convert data to and from JSON format easily.
- **Dict**: Instantiating and serializing data as dictionaries.
- **CSV**: Read from and write to CSV format directly.

---

## Model Configuration
| Field                    | Type | Default | Description                                                   |
| ------------------------ | ---- | ------- |---------------------------------------------------------------|
| `init`                   | bool | `True`  | Whether the `__init__` method is generated for the dataclass. |
| `repr`                   | bool | `True`  | Whether a `__repr__` method is generated.                     |
| `eq`                     | bool | `True`  | Enables the generation of `__eq__` for comparisons.           |
| `order`                  | bool | `False` | Enables ordering methods (`__lt__`, `__gt__`, etc.).          |
| `unsafe_hash`            | bool | `False` | Allows an unsafe implementation of `__hash__`.                |
| `frozen`                 | bool | `False` | Makes the dataclass instances immutable.                      |
| `disable_typecheck`      | bool | `False` | Disable runtime type checking in models.                      |
| `disable_all_validation` | bool | `False` | Disable **all** validation logic (type + custom rules).       |


## Example
```python
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
```

## Contributing

Contributions are welcome! If you'd like to help improve the library, please fork the repository and submit a pull request.

---

## License

`pydantic-mini` is open-source and available under the GPL License.

---