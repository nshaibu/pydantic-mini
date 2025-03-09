from pydantic_mini.typing import MiniAnnotated
from pydantic_mini.base import BaseModel


class MyModel(BaseModel):
    name: MiniAnnotated[str]
    age: MiniAnnotated[int]


p = MyModel(name='John', age=22)
print(p)

