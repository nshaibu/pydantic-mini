import unittest
import typing
from dataclasses import field
from pydantic_mini import BaseModel, MiniAnnotated, Attrib
from pydantic_mini.exceptions import ValidationError


class TestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class MyModel(BaseModel):
            name: str
            age: int

        class DataClassField(BaseModel):
            school = field(default="knust")
            value = field(default_factory=lambda: 1)

        class AnnotatedDataClass(BaseModel):
            email: MiniAnnotated[
                str, Attrib(pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=13)  # noqa:
            ]
            value: MiniAnnotated[int, Attrib(gt=4, lt=20, default=5)]

        class UsingOptionalDataClass(BaseModel):
            value: typing.Optional[int]
            name: MiniAnnotated[typing.Optional[str], Attrib(max_length=20)]

        cls.MyModel = MyModel
        cls.DataClassField = DataClassField
        cls.AnnotatedDataClass = AnnotatedDataClass
        cls.UsingOptionalDataClass = UsingOptionalDataClass

    def test_simple_annotated_model(self):
        instance = self.MyModel(name="test", age=10)
        self.assertEqual(instance.name, "test")
        self.assertEqual(instance.age, 10)

        with self.assertRaises(TypeError):
            self.MyModel(name=12, age="hello")

    def test_dataclass_field(self):
        instance = self.DataClassField()
        self.assertEqual(instance.school, "knust")
        self.assertEqual(instance.value, 1)

        # validate detected type from default
        with self.assertRaises(TypeError):
            self.DataClassField(school=23, value="hello")

    def test_mini_annotated_annotation(self):
        instance = self.AnnotatedDataClass(value=10, email="ex@email.com")
        self.assertEqual(instance.email, "ex@email.com")
        self.assertEqual(instance.value, 10)

        with self.assertRaises(ValidationError):
            self.AnnotatedDataClass(value=10, email="ex")

        with self.assertRaises(ValidationError):
            self.AnnotatedDataClass(value=10, email="looooooooong-email@example.com")

    def test_fields_with_or_without_default_values_cause_error(self):
        class Person(BaseModel):
            name: str = "nafiu"
            school: str

        class Person1(BaseModel):
            name: str
            school: str = "knust"

        p1 = Person(school="knust")
        self.assertEqual(p1.name, "nafiu")
        self.assertEqual(p1.school, "knust")

        p2 = Person1(name="nafiu")
        self.assertEqual(p2.name, "nafiu")
        self.assertEqual(p2.school, "knust")

        # validate positional arguments are required
        with self.assertRaises(TypeError):
            Person(name="nafiu")

        with self.assertRaises(TypeError):
            Person1(school="knust")

    def test_figured_out_optional_field_from_annotation_has_none_value(self):
        p = self.UsingOptionalDataClass()
        self.assertEqual(p.value, None)
        self.assertEqual(p.name, None)

    def test_model_creation_with_dict(self):
        param = {"name": "nafiu", "age": 12}
        instance = self.MyModel.loads(param, _format="dict")
        self.assertEqual(instance.name, "nafiu")
        self.assertEqual(instance.age, 12)

    def test_model_serialization_with_dict(self):
        instance = self.MyModel(name="nafiu", age=12)
        _dict = instance.dump(_format="dict")
        self.assertIsInstance(_dict, dict)
        self.assertEqual(_dict, {"name": "nafiu", "age": 12})

    def test_multiple_model_creation_with_dict(self):
        params = [
            {"name": "nafiu", "age": 12},
            {"name": "shaibu", "age": 13},
            {"name": "nshaibu", "age": 14},
        ]
        instance = self.MyModel.loads(params, _format="dict")
        self.assertIsInstance(instance, list)
        self.assertEqual(len(instance), len(params))

    def test_inner_model_creation_with_dict_and_list(self):
        class School(BaseModel):
            name: str
            location: str

        class Person(BaseModel):
            name: str
            school: typing.List[School]

        instance = Person(name="nafiu", school=[School("knust", location="kumasi")])
        self.assertIsInstance(instance, Person)
        self.assertEqual(instance.name, "nafiu")
        self.assertEqual(instance.school[0].name, "knust")
        self.assertEqual(instance.school[0].location, "kumasi")

        # convert dict to BaseModel test
        instance1 = Person(
            name="shaibu", school=[{"name": "knust", "location": "kumasi"}]
        )
        self.assertIsInstance(instance1, Person)
        self.assertEqual(instance1.name, "shaibu")
        self.assertEqual(instance1.school[0].name, "knust")
        self.assertEqual(instance1.school[0].location, "kumasi")

        # multiple
        instance2 = Person(name="nshaibu", school=[{"name": "knust", "location": "kumasi"}, School("legon", location="accra")])
        self.assertIsInstance(instance2, Person)
        self.assertEqual(instance2.name, "nshaibu")
        self.assertEqual(len(instance2.school), 2)

    def test_inner_model_creation_with_normal_class(self):
        class School:
            def __init__(self, name: str, location: str):
                self.name: str = name
                self.location: str = location

        class Student(BaseModel):
            name: str
            school: School

        student = Student(name="nafiu", school=School("knust", location="kumasi"))
        self.assertIsInstance(student, Student)
        self.assertEqual(student.name, "nafiu")
        self.assertIsInstance(student.school, School)
        self.assertEqual(student.school.name, "knust")
        self.assertEqual(student.school.location, "kumasi")

        # multiple entries
        with self.assertRaises(TypeError):
            Student(name="nafiu", school=[School("knust", location="kumasi")])

        class Person(BaseModel):
            name: str
            school: typing.List[School]

        person = Person(name="nafiu", school=[School("knust", location="kumasi")])
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "nafiu")
        self.assertIsInstance(person.school, list)
        self.assertEqual(len(person.school), 1)
        self.assertEqual(person.school[0].name, "knust")
        self.assertEqual(person.school[0].location, "kumasi")

        instance1 = Person(
            name="shaibu", school=[{"name": "knust", "location": "kumasi"}, School("legon", location="accra")]
        )
        self.assertIsInstance(instance1, Person)
        self.assertEqual(instance1.name, "shaibu")
        self.assertIsInstance(instance1.school, list)
        self.assertEqual(len(instance1.school), 2)



