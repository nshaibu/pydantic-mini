import csv
import json
import typing
from dataclasses import asdict
from abc import ABC, abstractmethod
from .utils import init_class

if typing.TYPE_CHECKING:
    from .base import BaseModel


class BaseModelFormatter(ABC):
    format_name: str = None

    @abstractmethod
    def encode(
        self, _type: typing.Type["BaseModel"], obj: typing.Dict[str, typing.Any]
    ) -> "BaseModel":
        pass

    @abstractmethod
    def decode(self, instance: "BaseModel") -> typing.Any:
        pass

    @classmethod
    def get_formatters(cls):
        for subclass in cls.__subclasses__():
            yield from subclass.get_formatters()
            yield subclass

    @classmethod
    def get_formatter(cls, *args, format_name: str, **kwargs) -> "BaseModelFormatter":
        for subclass in cls.get_formatters():
            if subclass.format_name == format_name:
                return subclass(*args, **kwargs)
        raise KeyError(f"Format {format_name} not found")


class DictModelFormatter(BaseModelFormatter):
    format_name = "dict"

    def _encode(
        self, _type: typing.Type["BaseModel"], obj: typing.Dict[str, typing.Any]
    ) -> "BaseModel":
        instance = init_class(_type, obj)
        # force execute post init again for normal field validation
        instance.__post_init__()
        return instance

    def encode(
        self,
        _type: typing.Type["BaseModel"],
        obj: typing.Union[
            typing.Dict[str, typing.Any], typing.List[typing.Dict[str, typing.Any]]
        ],
    ) -> typing.Union["BaseModel", typing.List["BaseModel"]]:
        if isinstance(obj, dict):
            return self._encode(_type, obj)
        elif isinstance(obj, list):
            content = []
            for item in obj:
                content.append(self._encode(_type, item))
            return content
        else:
            raise TypeError("Object must be dict or list")

    def decode(self, instance: "BaseModel") -> typing.Dict[str, typing.Any]:
        return asdict(instance)


class JSONModelFormatter(DictModelFormatter):
    format_name = "json"

    def encode(
        self, _type: typing.Type["BaseModel"], obj: str
    ) -> typing.Union["BaseModel", typing.List["BaseModel"]]:
        obj = json.loads(obj)
        if isinstance(obj, dict):
            return super().encode(_type, obj)
        elif isinstance(obj, list):
            content = []
            for value in obj:
                content.append(super().encode(_type, value))
            return content
        else:
            raise TypeError(f"Type {obj} is not JSON serializable")

    def decode(self, instance: "BaseModel") -> str:
        return json.dumps(super().decode(instance))


class CSVModelFormatter(DictModelFormatter):
    format_name = "csv"

    def encode(self, _type: typing.Type["BaseModel"], file: str):
        pass

    def decode(self, instance: "BaseModel") -> str:
        pass
