import typing
import keyword
from dataclasses import dataclass, fields, Field, field, MISSING, is_dataclass
from .formatters import BaseModelFormatter
from .typing import (
    is_mini_annotated,
    get_type,
    MiniAnnotated,
    Attrib,
    is_collection,
    DEFAULT_MODEL_CONFIG,
    ModelConfig,
)
from .exceptions import ValidationError


class SchemaMeta(type):

    def __new__(cls, name, bases, attrs, **kwargs):
        parents = [b for b in bases if isinstance(b, SchemaMeta)]
        if not parents:
            return super().__new__(cls, name, bases, attrs)

        cls._prepare_model_fields(attrs)

        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        model_config: ModelConfig = getattr(new_class, "model_config", {})

        return dataclass(new_class, **model_config)

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
        for field_name, value in attrs.items():
            if field_name not in field_dict and isinstance(value, Field):
                if value.type is not MISSING:
                    typ = get_type(value.type)
                elif value.default is not MISSING:
                    typ = type(value.default)
                elif value.default_factory is not MISSING:
                    typ = type(value.default_factory())
                else:
                    continue
                field_dict[field_name] = field_name, typ, value

        return list(field_dict.values())

    @classmethod
    def _prepare_model_fields(cls, attrs):
        anns = {}
        for field_name, annotation, value in cls.get_fields(attrs):
            if not isinstance(field_name, str) or not field_name.isidentifier():
                raise TypeError(
                    f"Field names must be valid identifiers: {field_name!r}"
                )
            if keyword.iskeyword(field_name):
                raise TypeError(f"Field names must not be keywords: {field_name!r}")

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

            if value is MISSING:
                attrib = annotation.__metadata__[0]
                if attrib.has_default():
                    if attrib.default is not MISSING:
                        attrs[field_name] = field(default=attrib.default)
                    else:
                        attrs[field_name] = field(
                            default_factory=attrib.default_factory
                        )

            anns[field_name] = annotation

        if anns:
            attrs["__annotations__"] = anns


class BaseModel(metaclass=SchemaMeta):

    model_config = DEFAULT_MODEL_CONFIG

    def __post_init__(self):
        """
        The validation is performed by calling a function named:
            `validate_<field_name>(self, value, field) -> field.type`
        """

        for fd in fields(self):
            self._field_type_validator(fd)

            try:
                result = self.validate(getattr(self, fd.name), fd)
                if result is not None:
                    setattr(self, fd.name, result)
            except NotImplementedError:
                pass

            method = getattr(self, f"validate_{fd.name}", None)
            if method and callable(method):
                result = method(getattr(self, fd.name), field=fd)
                if result is not None:
                    setattr(self, fd.name, result)

    def _inner_schema_value_preprocessor(self, fd: Field):
        value = getattr(self, fd.name)
        field_type = fd.type

        status, actual_type = is_collection(field_type)
        if status:
            type_args = hasattr(field_type, "__args__") and field_type.__args__ or None
            if type_args and isinstance(value, (dict, list)):
                value = value if isinstance(value, list) else [value]
                inner_type: type = type_args[0]
                if isinstance(inner_type, BaseModel) or is_dataclass(inner_type):
                    setattr(
                        self,
                        fd.name,
                        actual_type([inner_type(**value) for val in value]),
                    )

    def _field_type_validator(self, fd: Field):
        value = getattr(self, fd.name, None)
        field_type = fd.type

        if not is_mini_annotated(field_type):
            raise ValidationError(
                "Field '{}' should be annotated with 'PipelineAnnotated'.".format(
                    fd.name
                ),
                params={"field": fd.name, "annotation": field_type},
            )

        query = field_type.__metadata__[0]

        if not query.has_default() and value is None:
            raise ValidationError(
                "Field '{}' should not be empty.".format(fd.name),
                params={"field": fd.name, "annotation": field_type},
            )

        query.execute_field_validators(self, fd)

        expected_type = (
            hasattr(field_type, "__args__") and field_type.__args__[0] or None
        )
        expected_type = (
            expected_type and self.type_can_be_validated(expected_type) or None
        )

        is_type_collection, _ = is_collection(expected_type)

        if expected_type and expected_type is not typing.Any:
            if is_type_collection:
                actual_type = expected_type.__args__[0]
                if actual_type:
                    if any([not isinstance(value, actual_type) for val in value]):
                        raise TypeError(
                            "Expected a collection of values of type '{}'. Values: {} ".format(
                                actual_type, value
                            )
                        )
            elif not isinstance(value, expected_type):
                raise TypeError(
                    f"Field '{fd.name}' should be of type {expected_type}, "
                    f"but got {type(value).__name__}."
                )

        query.validate(value, fd.name)

    @staticmethod
    def type_can_be_validated(typ) -> typing.Optional[typing.Tuple]:
        origin = typing.get_origin(typ)
        if origin is typing.Union:
            type_args = typing.get_args(typ)
            if type_args:
                return tuple([get_type(_type) for _type in type_args])
        else:
            return (get_type(typ),)

    @staticmethod
    def get_formatter_by_name(name: str) -> BaseModelFormatter:
        return BaseModelFormatter.get_formatter(format_name=name)

    def validate(self, value: typing.Any, fd: Field):
        """Implement this method to validate all fields"""
        raise NotImplementedError

    @classmethod
    def loads(
        cls, data: typing.Any, _format: str
    ) -> typing.Union[typing.List["BaseModel"], "BaseModel"]:
        return cls.get_formatter_by_name(_format).encode(cls, data)

    def dump(self, _format: str) -> typing.Any:
        return self.get_formatter_by_name(_format).decode(instance=self)
