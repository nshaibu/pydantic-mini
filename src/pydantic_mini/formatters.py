import csv
import json
import typing
from dataclasses import asdict
from abc import ABC, abstractmethod

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from .utils import init_class

if typing.TYPE_CHECKING:
    from .base import BaseModel


_BLOCK_SIZE = 1024


class BaseModelFormatter(ABC):
    format_name: str = None

    @classmethod
    def is_format_name(cls, format_name: str) -> bool:
        format_names = (
            isinstance(cls.format_name, (list, tuple))
            and format_name
            or [cls.format_name]
        )
        return format_name in format_names

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
    def get_formatter(cls, format_name: str, **config) -> "BaseModelFormatter":
        for subclass in cls.get_formatters():
            if subclass.is_format_name(format_name):
                return subclass(**config)
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

    def encode(
        self, _type: typing.Type["BaseModel"], file: str
    ) -> typing.List["BaseModel"]:
        with open(file, "r", newline="") as f:
            sample = f.read(_BLOCK_SIZE)
            dialect = csv.Sniffer().sniff(sample)
            has_header = csv.Sniffer().has_header(sample)
            f.seek(0)
            if not has_header:
                raise FileExistsError(f"File {file} does not have header")
            reader = csv.DictReader(f, dialect=dialect)
            return [super().encode(_type, row) for row in reader]

    def decode(
        self, instance: typing.Union["BaseModel", typing.List["BaseModel"]]
    ) -> str:
        instances = instance if isinstance(instance, (list, tuple)) else [instance]
        with StringIO() as f:
            writer = csv.DictWriter(f, dialect=csv.excel, fieldnames=[])
            for index, obj in enumerate(instances):
                instance_dict = super().decode(obj)
                if index == 0:
                    writer.fieldnames = list(instance_dict.keys())
                    writer.writeheader()
                writer.writerow(instance_dict)

            context = f.getvalue()

        return context
