import typing
import inspect
from enum import Enum
from dataclasses import fields, Field, field, MISSING, is_dataclass
from .typing import (
    is_mini_annotated,
    get_type,
    get_origin,
    get_args,
    get_forward_type,
    Annotated,
    Attrib,
    is_collection,
    is_optional_type,
    is_builtin_type,
    is_initvar_type,
    is_class_var_type,
)
from .utils import init_class
from .exceptions import ValidationError

if typing.TYPE_CHECKING:
    from .base import BaseModel


class MiniField:

    __slots__ = (
        "name",
        "private_name",
        "expected_type",
        "_mini_annotated_type",
        "_actual_annotated_type",
        "_query",
        "type_annotation_args",
        "is_builtin",
        "is_enum",
        "is_model",
        "is_collection",
        "is_class",
        "is_forward_reference",
        "default",
        "default_factory",
    )

    def __init__(
        self,
        name: str,
        mini_annotated: typing.Type[Annotated],
        dc_field_obj: typing.Optional[Field] = None,
    ):
        if not is_mini_annotated(mini_annotated):
            raise ValidationError(
                "Field '{}' should be annotated with 'MiniAnnotated'.".format(name),
                params={"field": name, "annotation": mini_annotated},
            )
        self.name = name
        self.private_name = f"_{name}"

        # type decomposition
        self._mini_annotated_type = mini_annotated
        self._actual_annotated_type = mini_annotated.__args__[0]
        self._query: Attrib = mini_annotated.__metadata__[0]
        self.type_annotation_args: typing.Optional[typing.Tuple[typing.Any]] = (
            self.type_can_be_validated(self._actual_annotated_type)
        )

        self.is_collection, self.expected_type = is_collection(
            self._actual_annotated_type
        )

        if not self.is_collection:
            self.expected_type = (
                self.type_annotation_args[0]
                if self.type_annotation_args
                else typing.Any
            )

        self.is_builtin = is_builtin_type(self.expected_type)
        self.is_enum = isinstance(self.expected_type, type) and issubclass(
            self.expected_type, Enum
        )
        self.is_model = hasattr(
            self.expected_type, "__pydantic_mini_extra_config__"
        ) or is_dataclass(self.expected_type)
        self.is_class = inspect.isclass(self.expected_type)
        self.is_forward_reference = True

        # Mirror dataclass Field internal state
        self.default = dc_field_obj.default
        self.default_factory = dc_field_obj.default_factory

    def __get__(self, instance: "BaseModel", owner: typing.Any = None) -> typing.Any:
        if instance is None:
            return self

        value = instance.__dict__.get(self.private_name, MISSING)

        if value is MISSING:
            if self.default is not MISSING:
                value = self.default
            elif self.default_factory is not MISSING:
                value = self.default_factory()
            else:
                raise AttributeError(
                    f"'{owner.__name__}' object has no attribute '{self.name}'"
                )

            # Cache the default back to the instance
            instance.__dict__[self.private_name] = value

        return value

    def __set__(self, instance: "BaseModel", value: typing.Any) -> None:
        config = self.get_model_config(instance)
        strict_mode = config.get("strict_mode", False)
        disable_typecheck = config.get("disable_typecheck", False)
        disable_all_validation = config.get("disable_all_validation", False)

        if value is not None and type(value) is not self.expected_type:
            try:
                if self.is_builtin:
                    value = self.expected_type(value)
                elif self.is_enum:
                    value = self.expected_type(value)
                elif self.is_model and isinstance(value, dict):
                    # Specialized fast-init for nested models
                    value = self.expected_type(**value)
            except (ValueError, TypeError):
                # If coercion fails, we let the type validator catch it
                pass

        if self.expected_type is not typing.Any and not isinstance(
            value, self.expected_type
        ):
            raise TypeError(
                f"Field '{self.name}' expected {self.expected_type.__name__}, "
                f"got {type(value).__name__}."
            )

        instance.__dict__[self.private_name] = value

    @staticmethod
    def get_model_config(instance: "BaseModel") -> dict:
        return {}

    def _value_coerce(
        self, value: typing.Any, fd: Field, resolved_field_type: typing.Any
    ) -> None:
        if self.is_collection:
            if self.type_annotation_args and isinstance(value, (dict, list)):
                value = value if isinstance(value, list) else [value]
                inner_type: type = self.type_annotation_args[0]

                if is_builtin_type(inner_type):
                    setattr(
                        self,
                        fd.name,
                        self.expected_type([inner_type(val) for val in value]),
                    )
                elif (
                    (isinstance(inner_type, type) and issubclass(inner_type, BaseModel))
                    or is_dataclass(inner_type)
                    or inspect.isclass(inner_type)
                ):
                    setattr(
                        self,
                        fd.name,
                        self.expected_type(
                            [
                                (
                                    init_class(inner_type, val)
                                    if isinstance(val, dict)
                                    else val
                                )
                                for val in value
                            ]
                        ),
                    )
        elif self._actual_annotated_type:
            if isinstance(value, dict):
                if self.is_model or self.is_class:
                    setattr(self, fd.name, init_class(self.expected_type, value))

            # Enums (Coerce string/int to Enum member)
            elif self.is_enum:
                if value is not None and not isinstance(value, self.expected_type):
                    try:
                        setattr(self, fd.name, self.expected_type(value))
                    except ValueError:
                        pass
            # Primitives (Last-ditch coercion for strings to int/float)
            elif self.is_builtin:
                if value is not None and not isinstance(value, self.expected_type):
                    try:
                        setattr(self, fd.name, self.expected_type(value))
                    except (ValueError, TypeError):
                        pass

    def _field_type_validator(
        self, value: typing.Any, instance: "BaseModel", fd: Field
    ) -> None:

        if not self._query.has_default() and value is None:
            raise ValidationError(
                "Field '{}' should not be empty.".format(self.name),
                params={"field": self.name, "annotation": self._mini_annotated_type},
            )

        self._query.execute_field_validators(instance, fd)

        if self._actual_annotated_type and typing.Any not in self.type_annotation_args:
            # is_type_collection, _ = is_collection(expected_annotated_type)
            if self.is_collection:
                actual_type = self.expected_type
                if actual_type and actual_type is not typing.Any:
                    if any([not isinstance(val, actual_type) for val in value]):
                        raise TypeError(
                            "Expected a collection of values of type '{}'. Values: {} ".format(
                                actual_type, value
                            )
                        )
            elif not isinstance(value, self.type_annotation_args):
                raise TypeError(
                    f"Field '{fd.name}' should be of type {self.type_annotation_args}, "
                    f"but got {type(value).__name__}."
                )

        self._query.validate(value, fd.name)

    @staticmethod
    def type_can_be_validated(typ) -> typing.Optional[typing.Tuple]:
        origin = get_origin(typ)
        if origin is typing.Union:
            type_args = get_args(typ)
            if type_args:
                return tuple([get_type(_type) for _type in type_args])
        else:
            return (get_type(typ),)

        return None
