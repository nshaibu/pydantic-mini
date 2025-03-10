from pydantic_mini.typing import MiniAnnotated
from pydantic_mini.base import BaseModel


class MyModel(BaseModel):
    name: str
    age: int


p = MyModel(name="John", age=22)
print(p.dump("json"))

v = MyModel.loads({"name": "John1", "age": 322}, _format="dict")
print(v)
import pdb;pdb.set_trace()
