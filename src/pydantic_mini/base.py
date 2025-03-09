import typing
from dataclasses import dataclass, fields, Field
from .typing import is_mini_annotated, get_type
from .exceptions import ValidationError


class SchemaMeta(type):

    def __new__(cls, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, SchemaMeta)]
        if not parents:
            return super().__new__(cls, name, bases, attrs)

        cls._validate_annotated_field(attrs)
        new_class = super().__new__(cls, name, bases, attrs)

        new_class = dataclass(new_class)

        # for name, _field in new_class.__dataclass_fields__.items():
        #     setattr(new_class, name, _field)
        return new_class

    @staticmethod
    def _validate_annotated_field(attrs):
        annotation_fields = attrs.get("__annotations__", {})
        for field_name, annotation in annotation_fields.items():
            if not is_mini_annotated(annotation):
                raise TypeError(
                    "Field '{}' should be annotated with 'MiniAnnotated'.".format(
                        field_name
                    )
                )


class BaseModel(metaclass=SchemaMeta):

    def __post_init__(self):
        """
        The validation is performed by calling a function named:
            `validate_<field_name>(self, value, field) -> field.type`
        """

        for fd in fields(self):
            method = getattr(self, f"validate_{fd.name}", None)
            if method and callable(method):
                setattr(self, fd.name, method(getattr(self, fd.name), field=fd))

    def _field_type_validator(self, fd: Field):
        value = getattr(self, fd.name, None)
        field_type = fd.type
        import pdb;pdb.set_trace()

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

        expected_type = (
            hasattr(field_type, "__args__") and field_type.__args__[0] or None
        )
        expected_type = (
            expected_type and self.type_can_be_validated(expected_type) or None
        )

        if expected_type and expected_type is not typing.Any:
            if not isinstance(value, expected_type):
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

