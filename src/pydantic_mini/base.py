import typing
import keyword
import inspect
from collections import OrderedDict
from dataclasses import dataclass, fields, Field, field, MISSING, is_dataclass
from .formatters import BaseModelFormatter
from .typing import (
    is_mini_annotated,
    get_type,
    get_origin,
    get_args,
    MiniAnnotated,
    Attrib,
    is_collection,
    is_optional_type,
    is_builtin_type,
    is_initvar_type,
    is_class_var_type,
    ModelConfigWrapper,
)
from .utils import init_class
from .exceptions import ValidationError


__all__ = ("BaseModel",)

PYDANTIC_MINI_EXTRA_MODEL_CONFIG = "__pydantic_mini_extra_config__"


class SchemaMeta(type):

    def __new__(cls, name, bases, attrs, **kwargs):
        parents = [b for b in bases if isinstance(b, SchemaMeta)]
        if not parents:
            return super().__new__(cls, name, bases, attrs)

        cls._prepare_model_fields(attrs)

        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        model_config_class: typing.Type = getattr(new_class, "Config", None)

        config = ModelConfigWrapper(model_config_class)

        setattr(
            new_class,
            PYDANTIC_MINI_EXTRA_MODEL_CONFIG,
            config.get_non_dataclass_config(),
        )

        return dataclass(new_class, **config.get_dataclass_config())

    @classmethod
    def get_non_annotated_fields(cls, attrs, exclude: typing.Tuple = None):
        if exclude is None:
            exclude = []

        for field_name, value in attrs.items():
            if isinstance(value, (classmethod, staticmethod, property)):
                continue

            # ignore ABC class internal state manager
            if "_abc_impl" == field_name:
                continue

            if (
                not field_name.startswith("__")
                and field_name not in exclude
                and not callable(value)
            ):
                if isinstance(value, Field):
                    typ = cls._figure_out_field_type_by_default_value(
                        field_name, value, attrs
                    )
                else:
                    typ = cls._figure_out_field_type_by_default_value(
                        field_name, value, attrs
                    )
                    value = field(default=value)

                if typ is not None:
                    yield field_name, typ, value

    @classmethod
    def get_fields(
        cls, attrs
    ) -> typing.List[typing.Tuple[typing.Any, typing.Any, typing.Any]]:
        field_dict = {}

        annotation_fields = attrs.get("__annotations__", {})

        for field_name, annotation in annotation_fields.items():
            field_tuple = field_name, annotation
            value = MISSING
            if field_name in attrs:
                value = attrs[field_name]
                value = value if isinstance(value, Field) else field(default=value)

            field_tuple = (*field_tuple, value)

            field_dict[field_name] = field_tuple

        # get fields without annotation
        for field_name, annotation, value in cls.get_non_annotated_fields(
            attrs, exclude=tuple(field_dict.keys())
        ):
            field_dict[field_name] = field_name, annotation, value

        return list(field_dict.values())

    @classmethod
    def _figure_out_field_type_by_default_value(
        cls, field_name: str, value: Field, attrs: typing.Dict[str, typing.Any]
    ) -> typing.Any:
        if isinstance(value, Field):
            if value.default is not MISSING:
                return type(value.default)
            elif value.default_factory is not MISSING:
                return type(value.default_factory())
        elif hasattr(value, "__class__"):
            return value.__class__
        else:
            if field_name in attrs:
                return type(value)

    @classmethod
    def _prepare_model_fields(cls, attrs: typing.Dict[str, typing.Any]) -> None:
        ann_with_defaults = OrderedDict()
        ann_without_defaults = OrderedDict()

        for field_name, annotation, value in cls.get_fields(attrs):
            if not isinstance(field_name, str) or not field_name.isidentifier():
                raise TypeError(
                    f"Field names must be valid identifiers: {field_name!r}"
                )
            if keyword.iskeyword(field_name):
                raise TypeError(f"Field names must not be keywords: {field_name!r}")

            if annotation is None:
                if value not in (MISSING, None):
                    annotation = cls._figure_out_field_type_by_default_value(
                        field_name, value, attrs
                    )

                if annotation is None:
                    raise TypeError(
                        f"Field '{field_name}' does not have type annotation. "
                        f"Figuring out field type from default value failed"
                    )

            if (
                is_initvar_type(annotation)
                or is_class_var_type(annotation)
                or annotation is typing.Any
            ):
                # let's ignore init-var and class-var, dataclass will take care of them
                # typing.Any does not require any type Validation
                ann_with_defaults[field_name] = annotation
                if field_name in attrs:
                    value = attrs[field_name]
                    attrs[field_name] = (
                        value.default if isinstance(value, Field) else value
                    )
                continue

            if not is_mini_annotated(annotation):
                if get_type(annotation) is None:
                    raise TypeError(
                        f"Field '{field_name}' must be annotated with a real type. {annotation} is not a type"
                    )
                annotation = MiniAnnotated[
                    annotation,
                    Attrib(
                        default=value.default if isinstance(value, Field) else value,
                        default_factory=(
                            value.default_factory if isinstance(value, Field) else value
                        ),
                    ),
                ]

            annotation_type = annotation.__args__[0]
            attrib = annotation.__metadata__[0]

            if is_optional_type(annotation_type):
                # all optional annotations without default value will have
                # None as default
                if not attrib.has_default():
                    attrib.default = None
                    attrs[field_name] = field(default=None)

            if value is MISSING:
                if attrib.has_default():
                    if attrib.default is not MISSING:
                        attrs[field_name] = field(default=attrib.default)
                    else:
                        attrs[field_name] = field(
                            default_factory=attrib.default_factory
                        )

            if attrib.has_default():
                ann_with_defaults[field_name] = annotation
            else:
                ann_without_defaults[field_name] = annotation

        ann_without_defaults.update(ann_with_defaults)

        if ann_without_defaults:
            attrs["__annotations__"] = ann_without_defaults


class PreventOverridingMixin:

    _protect = ["__init__", "__post_init__"]

    def __init_subclass__(cls, **kwargs):
        if cls.__name__ != "BaseModel":
            for attr_name in cls._protect:
                if attr_name in cls.__dict__:
                    raise PermissionError(
                        f"Model '{cls.__name__}' cannot override {attr_name!r}. "
                        f"Consider using __model_init__ for all your custom initialization"
                    )
        super().__init_subclass__(**kwargs)


class BaseModel(PreventOverridingMixin, metaclass=SchemaMeta):

    def __model_init__(self, *args, **kwargs) -> None:
        pass

    def __post_init__(self, *args, **kwargs) -> None:
        config = getattr(self, PYDANTIC_MINI_EXTRA_MODEL_CONFIG, {})
        disable_typecheck = config.get("disable_typecheck", False)
        disable_all_validation = config.get("disable_all_validation", False)

        for fd in fields(self):
            field_type = fd.type
            query: Attrib = (
                hasattr(field_type, "__metadata__")
                and field_type.__metadata__[0]
                or None
            )
            if query:
                # execute the pre-formatters for all the fields
                query.execute_pre_formatter(self, fd)

            if not disable_all_validation:
                # no type validation for Any field type and type checking is not disabled
                if field_type is not typing.Any and not disable_typecheck:
                    self._inner_schema_value_preprocessor(fd)
                    self._field_type_validator(fd)
                else:
                    # run other field validators when type checking is disabled
                    if query:
                        value = getattr(self, fd.name, None)
                        query.execute_field_validators(self, fd)
                        query.validate(value, fd.name)
                try:
                    result = self.validate(getattr(self, fd.name), fd)
                    if result is not None:
                        setattr(self, fd.name, result)
                except NotImplementedError:
                    pass

                method = getattr(self, f"validate_{fd.name}", None)
                if method and callable(method):
                    result = method(getattr(self, fd.name), fd)
                    if result is not None:
                        setattr(self, fd.name, result)

        self.__model_init__(*args, **kwargs)

    def _inner_schema_value_preprocessor(self, fd: Field):
        value = getattr(self, fd.name)
        field_type = fd.type

        actual_annotated_type = field_type.__args__[0]
        type_args = (
            hasattr(actual_annotated_type, "__args__")
            and actual_annotated_type.__args__
            or None
        )

        status, actual_type = is_collection(actual_annotated_type)
        if status:
            if type_args and isinstance(value, (dict, list)):
                value = value if isinstance(value, list) else [value]
                inner_type: type = type_args[0]
                if is_builtin_type(inner_type):
                    setattr(
                        self, fd.name, actual_type([inner_type(val) for val in value])
                    )
                elif (
                    isinstance(inner_type, BaseModel)
                    or is_dataclass(inner_type)
                    or inspect.isclass(inner_type)
                ):
                    setattr(
                        self,
                        fd.name,
                        actual_type(
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
        elif type_args is None and actual_annotated_type:
            actual_annotated_type = get_type(actual_annotated_type)
            if (
                isinstance(actual_annotated_type, BaseModel)
                or is_dataclass(actual_annotated_type)
                or inspect.isclass(actual_annotated_type)
            ):
                if isinstance(value, dict):
                    setattr(self, fd.name, init_class(actual_annotated_type, value))

    def _field_type_validator(self, fd: Field):
        value = getattr(self, fd.name, None)
        field_type = fd.type

        if not is_mini_annotated(field_type):
            raise ValidationError(
                "Field '{}' should be annotated with 'MiniAnnotated'.".format(fd.name),
                params={"field": fd.name, "annotation": field_type},
            )

        query = field_type.__metadata__[0]

        if not query.has_default() and value is None:
            raise ValidationError(
                "Field '{}' should not be empty.".format(fd.name),
                params={"field": fd.name, "annotation": field_type},
            )

        query.execute_field_validators(self, fd)

        expected_annotated_type = (
            hasattr(field_type, "__args__") and field_type.__args__[0] or None
        )
        actual_expected_type = (
            expected_annotated_type
            and self.type_can_be_validated(expected_annotated_type)
            or None
        )

        if expected_annotated_type and typing.Any not in actual_expected_type:
            is_type_collection, _ = is_collection(expected_annotated_type)
            if is_type_collection:
                actual_type = expected_annotated_type.__args__[0]
                if actual_type and actual_type is not typing.Any:
                    if any([not isinstance(val, actual_type) for val in value]):
                        raise TypeError(
                            "Expected a collection of values of type '{}'. Values: {} ".format(
                                actual_type, value
                            )
                        )
            elif not isinstance(value, actual_expected_type):
                raise TypeError(
                    f"Field '{fd.name}' should be of type {actual_expected_type}, "
                    f"but got {type(value).__name__}."
                )

        query.validate(value, fd.name)

    @staticmethod
    def type_can_be_validated(typ) -> typing.Optional[typing.Tuple]:
        origin = get_origin(typ)
        if origin is typing.Union:
            type_args = get_args(typ)
            if type_args:
                return tuple([get_type(_type) for _type in type_args])
        else:
            return (get_type(typ),)

    @staticmethod
    def get_formatter_by_name(name: str) -> BaseModelFormatter:
        return BaseModelFormatter.get_formatter(format_name=name)

    def validate(self, value: typing.Any, data_field: Field):
        """Implement this method to validate all fields"""
        raise NotImplementedError

    @classmethod
    def loads(
        cls, data: typing.Any, _format: str
    ) -> typing.Union[typing.List["BaseModel"], "BaseModel"]:
        return cls.get_formatter_by_name(_format).encode(cls, data)

    def dump(self, _format: str) -> typing.Any:
        return self.get_formatter_by_name(_format).decode(instance=self)
