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
from pydantic_mini import BaseModel, MiniAnnotated, Attrib
from pydantic_mini.exceptions import ValidationError

# Custom validation for not accepting name kofi
def kofi_not_accepted(instance, value: str):
    if value == "kofi":
        # validators must raise ValidationError when validation fails.
        raise ValidationError("Age must be a positive number.")
    
    # If you want to apply a transformation and save the result into the model, 
    # return the transformed result you want to save. For instance, if you want the names to be capitalized, 
    # return the capitalized version.
    return value.upper()

class Employee(BaseModel):
    name: MiniAnnotated[str, Attrib(max_length=20, validators=[kofi_not_accepted])]
    age: MiniAnnotated[int, Attrib(default=40, gt=20)]
    email: MiniAnnotated[str, Attrib(pattern="/^\S+@\S+\.\S+$/")]
    school: str
    
    # You can define validators by adding a method with the name 
    # "validate_<FIELD_NAME>" e.g to validate school name
    def validate_school(self, value):
      if len(value) > 20:
        raise ValidationError("School names cannot be greater than 20")

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

## Contributing

Contributions are welcome! If you'd like to help improve the library, please fork the repository and submit a pull request.

---

## License

`pydantic-mini` is open-source and available under the GPL License.

---