import typing
import inspect
import logging
import json
from dataclasses import MISSING, asdict
from abc import ABC, abstractmethod

if typing.TYPE_CHECKING:
    from .base import BaseModel


logger = logging.getLogger(__name__)


def get_function_call_args(
    func, params: typing.Union[typing.Dict[str, typing.Any], object]
) -> typing.Dict[str, typing.Any]:
    """
    Extracts the arguments for a function call from the provided parameters.

    Args:
        func: The function for which arguments are to be extracted.
        params: A dictionary of parameters containing
                the necessary arguments for the function.

    Returns:
        A dictionary where the keys are the function argument names
        and the values are the corresponding argument values.
    """
    params_dict = {}
    try:
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.name != "self":
                value = (
                    params.get(param.name, param.default)
                    if isinstance(params, dict)
                    else getattr(params, param.name, param.default)
                )
                if value is not MISSING and value is not inspect.Parameter.empty:
                    params_dict[param.name] = value
                else:
                    params_dict[param.name] = None
    except (ValueError, KeyError) as e:
        logger.warning(f"Parsing {func} for call parameters failed {str(e)}")

    for key in ["args", "kwargs"]:
        if key in params_dict and params_dict[key] is None:
            params_dict.pop(key, None)
    return params_dict


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
    def get_formatter(cls, format_name: str):
        for subclass in cls.get_formatters():
            if subclass.format_name == format_name:
                return subclass
        raise KeyError(f"Format {format_name} not found")


class DictModelFormatter(BaseModelFormatter):
    format_name = "dict"

    def encode(
        self, _type: typing.Type["BaseModel"], obj: typing.Dict[str, typing.Any]
    ) -> "BaseModel":
        kwargs = get_function_call_args(_type.__init__, obj)
        excluded_kwargs = {
            key: obj[key] for key in obj.keys() if key not in kwargs.keys()
        }
        instance = _type(**kwargs)
        if excluded_kwargs:
            instance.__dict__.update(excluded_kwargs)
        # force execute post init again for normal field validation
        instance.__post_init__()
        return instance

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
