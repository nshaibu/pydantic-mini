from __future__ import annotations
import re
import logging
import sys
import types
import typing
import collections
from dataclasses import MISSING, Field, InitVar

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_origin, get_args
else:
    from typing import Annotated, get_origin, get_args

from .exceptions import ValidationError

if typing.TYPE_CHECKING:
    from .base import BaseModel

__all__ = (
    "MiniAnnotated",
    "Attrib",
    "get_type",
    "is_collection",
    "is_optional_type",
    "is_type",
    "is_mini_annotated",
    "NoneType",
    "ModelConfigWrapper",
    "is_builtin_type",
    "InitVar",
    "is_initvar_type",
    "is_class_var_type",
    "get_origin",
    "get_args",
)

logger = logging.getLogger(__name__)


# backward compatibility
NoneType = getattr(types, "NoneType", type(None))


_DATACLASS_CONFIG_FIELD: typing.List[str] = [
    "init",
    "repr",
    "eq",
    "order",
    "unsafe_hash",
    "frozen",
]

_NON_DATACLASS_CONFIG_FIELD: typing.List[str] = [
    "disable_typecheck",
    "disable_all_validation",
]


class ModelConfigWrapper:
    init: bool = True
    repr: bool = True
    eq: bool = True
    order: bool = False
    unsafe_hash: bool = False
    frozen: bool = False
    disable_typecheck: bool = False
    disable_all_validation: bool = False

    def __init__(self, config: typing.Type):
        self.config = config

    def get_config(self, name: str) -> typing.Any:
        if self.config and hasattr(self.config, name):
            return getattr(self.config, name, None)
        return getattr(self.__class__, name, None)

    def get_dataclass_config(self) -> typing.Dict[str, typing.Any]:
        dt = collections.OrderedDict()
        for config_field in _DATACLASS_CONFIG_FIELD:
            dt[config_field] = self.get_config(config_field)
        return dt

    def get_non_dataclass_config(self) -> typing.Dict[str, typing.Any]:
        dt = collections.OrderedDict()
        for config_field in _NON_DATACLASS_CONFIG_FIELD:
            dt[config_field] = self.get_config(config_field)
        return dt


class Attrib:
    __slots__ = (
        "default",
        "default_factory",
        "pre_formatter",
        "required",
        "allow_none",
        "gt",
        "ge",
        "lt",
        "le",
        "min_length",
        "max_length",
        "pattern",
        "_validators",
    )

    def __init__(
        self,
        default: typing.Optional[typing.Any] = MISSING,
        default_factory: typing.Optional[typing.Callable[[], typing.Any]] = MISSING,
        pre_formatter: typing.Callable[[typing.Any], typing.Any] = MISSING,
        required: bool = False,
        allow_none: bool = False,
        gt: typing.Optional[float] = None,
        ge: typing.Optional[float] = None,
        lt: typing.Optional[float] = None,
        le: typing.Optional[float] = None,
        min_length: typing.Optional[int] = None,
        max_length: typing.Optional[int] = None,
        pattern: typing.Optional[typing.Union[str, typing.Pattern]] = None,
        validators: typing.Optional[
            typing.List[typing.Callable[[typing.Any], typing.Any]]
        ] = MISSING,
    ):
        """
        Represents a data attribute with optional validation, default values, and formatting logic.

        Attributes (via __slots__):
            default (Any): A default value for the attribute, if provided.
            default_factory (Callable): A callable that generates a default value.
            pre_formatter (Callable): A function to preprocess/format the value before validation.
            required (bool): Whether the attribute is required.
            allow_none (bool): Whether None is an acceptable value.
            gt (float): Value must be greater than this (exclusive).
            ge (float): Value must be greater than or equal to this (inclusive).
            lt (float): Value must be less than this (exclusive).
            le (float): Value must be less than or equal to this (inclusive).
            min_length (int): Minimum allowed length (for iterable types like strings/lists).
            max_length (int): Maximum allowed length.
            pattern (str or Pattern): Regex pattern the value must match (typically for strings).
            _validators (List[Callable]): Custom validators to run on the value.

        Args:
            default (Any, optional): Static default value to use if none is provided.
            default_factory (Callable, optional): Function that returns a default value.
            pre_formatter (Callable, optional): Function to format/preprocess the value before validation.
            required (bool): Whether this field is required (default: False).
            allow_none (bool): Whether None is allowed as a value (default: False).
            gt, ge, lt, le (float, optional): Numeric comparison constraints.
            min_length, max_length (int, optional): Length constraints for sequences.
            pattern (str or Pattern, optional): Regex pattern constraint.
            validators (List[Callable], optional): Additional callables that validate the input.
        """
        self.default = default
        self.default_factory = default_factory
        self.pre_formatter = pre_formatter
        self.required = required
        self.allow_none = allow_none
        self.gt = gt
        self.ge = ge
        self.lt = lt
        self.le = le
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

        if validators is not MISSING:
            self._validators = (
                validators if isinstance(validators, (list, tuple)) else [validators]
            )
        else:
            self._validators = []

    def __repr__(self):
        return (
            "Attrib("
            f"default={self.default!r},"
            f"default_factory={self.default_factory!r},"
            ")"
        )

    def has_default(self):
        return self.default is not MISSING or self.default_factory is not MISSING

    def has_pre_formatter(self):
        return self.pre_formatter is not None and callable(self.pre_formatter)

    def _get_default(self) -> typing.Any:
        if self.default is not MISSING:
            return self.default
        elif self.default_factory is not MISSING:
            return self.default_factory()

    def execute_pre_formatter(self, instance, fd: Field) -> None:
        if self.has_pre_formatter():
            value = getattr(instance, fd.name, None)
            try:
                value = self.pre_formatter(value)
                if self.allow_none and value is None:
                    setattr(instance, fd.name, None)
                else:
                    setattr(instance, fd.name, value)
            except Exception as exc:
                logger.error(
                    "Pre-formatter error for %s : %s", (fd.name, exc), exc_info=exc
                )
                raise RuntimeError(
                    f"Error occurred while executing the pre-formatter for field: {fd.name}"
                ) from exc

    def validate(self, value: typing.Any, field_name: str) -> typing.Optional[bool]:
        value = value or self._get_default()

        if self.allow_none and value is None:
            return True

        if self.required and value is None:
            raise ValidationError(
                f"Field '{field_name}' is required but not provided (value is None).",
                params={"field_name": field_name},
            )

        for name in ("gt", "ge", "lt", "le", "min_length", "max_length", "pattern"):
            validation_factor = getattr(self, name, None)

            # Skip the validation if 'validation_factor' is None, or if both 'value'
            # and 'self.default' are None
            if validation_factor is None or value is None:
                continue

            validator = getattr(self, f"_validate_{name}")
            validator(value)
        return True

    def execute_field_validators(self, instance: "BaseModel", fd: Field) -> None:
        for validator in self._validators:
            try:
                result = validator(instance, getattr(instance, fd.name))
                if result is not None:
                    setattr(instance, fd.name, result)
                elif self.allow_none:
                    setattr(instance, fd.name, None)
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError(str(e)) from e

    def _validate_gt(self, value: typing.Any):
        try:
            if not (value > self.gt):
                raise ValidationError(
                    f"Field value '{value}' is not greater than '{self.gt}'",
                    params={"gt": self.gt},
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'gt' to supplied value {value!r}"
            )

    def _validate_ge(self, value: typing.Any):
        try:
            if not (value >= self.ge):
                raise ValidationError(
                    f"Field value '{value}' is not greater than or equal to '{self.ge}'",
                    params={"ge": self.ge},
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'ge' to supplied value {value!r}"
            )

    def _validate_lt(self, value: typing.Any):
        try:
            if not (value < self.lt):
                raise ValidationError(
                    f"Field value '{value}' is not less than '{self.lt}'",
                    params={"lt": self.lt},
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'lt' to supplied value {value!r}"
            )

    def _validate_le(self, value: typing.Any):
        try:
            if not (value <= self.le):
                raise ValidationError(
                    f"Field value '{value}' is not less than or equal to '{self.le}'",
                    params={"le": self.le},
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'le' to supplied value {value!r}"
            )

    def _validate_min_length(self, value: typing.Any):
        try:
            if not (len(value) >= self.min_length):
                raise ValidationError(
                    "too_short",
                    {
                        "field_type": "Value",
                        "min_length": self.min_length,
                        "actual_length": len(value),
                    },
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'min_length' to supplied value {value!r}"
            )

    def _validate_max_length(self, value: typing.Any):
        try:
            actual_length = len(value)
            if actual_length > self.max_length:
                raise ValidationError(
                    f"Value is too long. {actual_length} > {self.max_length}",
                    {
                        "field_type": "Value",
                        "max_length": self.max_length,
                        "actual_length": actual_length,
                    },
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'max_length' to supplied value {value!r}"
            )

    def _validate_pattern(self, value: typing.Any):
        try:
            if not re.match(self.pattern, value):
                raise ValidationError(
                    f"Field value '{value}' does not match pattern",
                    params={"pattern": self.pattern, "value": value},
                )
        except TypeError:
            raise TypeError(
                f"Unable to apply constraint 'pattern' to supplied value {value!r}"
            )


def is_mini_annotated(typ) -> bool:
    origin = get_origin(typ)
    return (
        origin
        and origin is Annotated
        and hasattr(typ, "__metadata__")
        and Attrib in [inst.__class__ for inst in typ.__metadata__]
    )


def is_type(typ):
    try:
        is_typ = isinstance(typ, type)
    except TypeError:
        is_typ = False
    return is_typ


def is_initvar_type(typ):
    if hasattr(typ, "type"):
        if isinstance(typ, InitVar):
            return typ.__class__.__name__ == "InitVar"
        return hasattr(typ, "__name__") and typ.__name__ == "InitVar"
    return False


def is_class_var_type(typ) -> bool:
    return typ is typing.ClassVar or get_origin(typ) is typing.ClassVar


def get_type(typ):
    if is_type(typ):
        return typ

    if is_optional_type(typ):
        type_args = get_args(typ)
        if type_args:
            return get_type(type_args[0])
        else:
            return

    origin = get_origin(typ)
    if is_type(origin):
        return origin

    type_args = get_args(typ)
    if len(type_args) > 0:
        return get_type(type_args[0])


def is_optional_type(typ):
    if hasattr(typ, "__origin__") and typ.__origin__ is typing.Union:
        return NoneType in typ.__args__
    elif typ is typing.Optional:
        return True
    return False


def is_collection(typ) -> typing.Tuple[bool, typing.Optional[type]]:
    origin = get_origin(typ)
    if origin and origin in (
        list,
        tuple,
        frozenset,
        set,
        collections.deque,
    ):
        return True, origin
    return False, None


def is_builtin_type(typ):
    typ = typ if isinstance(typ, type) else type(typ)
    return typ.__module__ in ("builtins", "__builtins__")


class MiniAnnotated:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.MiniAnnotated")

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type MiniAnnotated cannot be instantiated.")

    @typing._tp_cache
    def __class_getitem__(cls, params):
        if not isinstance(params, tuple):
            params = (params, Attrib())

        if len(params) != 2:
            raise TypeError(
                "MiniAnnotated[...] should be used with exactly two arguments (a type and an Attrib)."
            )

        typ = params[0]

        actual_typ = get_type(typ)
        if actual_typ is None:
            raise ValueError("'{}' is not a type".format(params[0]))

        query = params[1]
        if not isinstance(query, Attrib):
            raise TypeError("Parameter '{}' must be instance of Attrib".format(1))
        return Annotated[typ, query]
