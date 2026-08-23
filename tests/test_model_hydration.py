import threading
import typing
import unittest

from formax import BaseModel, MiniAnnotated, Attrib, ValidationFlags
from dataclasses import field

from formax.base import _HYDRATION_WRAPPER_ATTR


class MyModel(BaseModel):
    name: str
    age:  int


class DataClassField(BaseModel):
    school = field(default="knust")
    value  = field(default_factory=lambda: 1)


class AnnotatedDataClass(BaseModel):
    email: MiniAnnotated[
        str, Attrib(pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=13)
    ]
    value: MiniAnnotated[int, Attrib(gt=4, lt=20, default=5)]


class UsingOptionalDataClass(BaseModel):
    value: typing.Optional[int]
    name:  MiniAnnotated[typing.Optional[str], Attrib(max_length=20)]


class DisabledAllValidationClass(BaseModel):
    email: MiniAnnotated[
        str, Attrib(pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=13)
    ]
    value: MiniAnnotated[int, Attrib(gt=4, lt=20, default=5)]

    class Config:
        validation = ValidationFlags.NONE


class ModelWithSetstate(BaseModel):
    name: str
    age:  int

    def __setstate__(self, state: dict) -> None:
        # Custom restoration — uppercases name to prove __setstate__ was called.
        super().__setstate__(state)
        self.name = state.get("name", "").upper()



class TestHydrateFormax(unittest.TestCase):



    def test_plain_model_hydration(self):
        """Fields are populated correctly for a plain name/age model."""
        state    = {"name": "Alice", "age": 30}
        instance = MyModel.hydrate_formax_model(state)

        self.assertIsInstance(instance, MyModel)
        self.assertEqual(instance.name, "Alice")
        self.assertEqual(instance.age,  30)

    def test_dataclass_field_model_hydration(self):
        """field() defaults are irrelevant — hydration applies state directly."""
        state    = {"school": "oxford", "value": 42}
        instance = DataClassField.hydrate_formax_model(state)

        self.assertIsInstance(instance, DataClassField)
        self.assertEqual(instance.school, "oxford")
        self.assertEqual(instance.value,  42)

    def test_annotated_model_hydration_skips_validation(self):
        """Validation constraints (pattern, gt/lt) are bypassed during hydration.

        email violates the pattern constraint and value violates gt=4/lt=20 —
        both would raise during normal construction but must succeed here
        because hydration operates on already-validated checkpoint state.
        """
        state    = {"email": "not-an-email", "value": 999}
        instance = AnnotatedDataClass.hydrate_formax_model(state)

        self.assertIsInstance(instance, AnnotatedDataClass)
        self.assertEqual(instance.email, "not-an-email")
        self.assertEqual(instance.value, 999)

    def test_optional_fields_hydration(self):
        """Optional fields accept None without raising."""
        state    = {"value": None, "name": None}
        instance = UsingOptionalDataClass.hydrate_formax_model(state)

        self.assertIsNone(instance.value)
        self.assertIsNone(instance.name)

    def test_optional_fields_with_values(self):
        """Optional fields also accept concrete values."""
        state    = {"value": 7, "name": "Bob"}
        instance = UsingOptionalDataClass.hydrate_formax_model(state)

        self.assertEqual(instance.value, 7)
        self.assertEqual(instance.name,  "Bob")

    def test_disabled_validation_model_hydration(self):
        """Models with ValidationFlags.NONE hydrate correctly."""
        state    = {"email": "bad", "value": -1}
        instance = DisabledAllValidationClass.hydrate_formax_model(state)

        self.assertEqual(instance.email, "bad")
        self.assertEqual(instance.value, -1)



    def test_round_trip_fidelity(self):
        """Hydrated instance matches original constructed instance field-for-field."""
        original  = MyModel(name="Carol", age=25)
        hydrated  = MyModel.hydrate_formax_model(original.__getstate__().copy())

        self.assertEqual(hydrated.name, original.name)
        self.assertEqual(hydrated.age,  original.age)

    def test_annotated_round_trip(self):
        """Round-trip for a valid AnnotatedDataClass instance."""
        original = AnnotatedDataClass(email="a@b.co", value=10)
        hydrated = AnnotatedDataClass.hydrate_formax_model(original.__getstate__().copy())

        self.assertEqual(hydrated.email, original.email)
        self.assertEqual(hydrated.value, original.value)



    def test_setstate_called_when_defined(self):
        """__setstate__ is used instead of __dict__.update when present.

        ModelWithSetstate uppercases name in __setstate__ — if it runs,
        name will be "DAVE", not "dave".
        """
        state    = {"name": "dave", "age": 40}
        instance = ModelWithSetstate.hydrate_formax_model(state)

        self.assertEqual(instance.name, "DAVE")   # __setstate__ ran
        self.assertEqual(instance.age,  40)


    def test_wrapper_applied_once_on_repeated_hydration(self):
        """Hydrating the same class multiple times wraps __init__ exactly once."""
        MyModel.hydrate_formax_model({"name": "E1", "age": 1})
        MyModel.hydrate_formax_model({"name": "E2", "age": 2})
        MyModel.hydrate_formax_model({"name": "E3", "age": 3})

        init = MyModel.__init__
        # The wrapper should be present exactly once — not nested.
        self.assertTrue(getattr(init, _HYDRATION_WRAPPER_ATTR, False))
        # The wrapped original must NOT itself be a hydration wrapper.
        self.assertFalse(
            getattr(init._original_init, _HYDRATION_WRAPPER_ATTR, False)
        )

    def test_repeated_hydration_produces_correct_instances(self):
        """Repeated hydration produces independent, correctly populated instances."""
        a = MyModel.hydrate_formax_model({"name": "Alice", "age": 1})
        b = MyModel.hydrate_formax_model({"name": "Bob",   "age": 2})
        c = MyModel.hydrate_formax_model({"name": "Carol", "age": 3})

        self.assertEqual(a.name, "Alice")
        self.assertEqual(b.name, "Bob")
        self.assertEqual(c.name, "Carol")
        self.assertIsNot(a, b)
        self.assertIsNot(b, c)


    def test_normal_construction_unaffected_after_hydration(self):
        """Wrapping __init__ does not break subsequent normal construction."""
        MyModel.hydrate_formax_model({"name": "Hydrated", "age": 99})

        # Normal construction must still validate and construct correctly.
        normal = MyModel(name="Normal", age=20)
        self.assertEqual(normal.name, "Normal")
        self.assertEqual(normal.age,  20)

    def test_normal_construction_still_validates(self):
        """Validation still fires for normally constructed annotated models."""
        # email violates the pattern — must raise during normal construction.
        with self.assertRaises(Exception):
            AnnotatedDataClass(email="not-an-email", value=10)


    def test_hydrating_sentinel_not_on_instance(self):
        """_hydrating is a constructor kwarg, not an instance attribute."""
        instance = MyModel.hydrate_formax_model({"name": "Test", "age": 5})
        self.assertNotIn("_hydrating", instance.__dict__)



    def test_concurrent_hydration_produces_correct_instances(self):
        """Concurrent hydrations of the same class all produce correct results.

        Verifies the benign-race argument: even if multiple threads race
        to wrap __init__, all produce correctly populated instances and
        the wrapper is not multiply nested.
        """
        results:  typing.List[MyModel] = []
        errors:   typing.List[Exception] = []
        lock      = threading.Lock()

        def hydrate(name: str, age: int) -> None:
            try:
                instance = MyModel.hydrate_formax_model({"name": name, "age": age})
                with lock:
                    results.append(instance)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [
            threading.Thread(target=hydrate, args=(f"User{i}", i))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, "Concurrent hydration raised: %s" % errors)
        self.assertEqual(len(results), 20)

        # All instances are correctly populated.
        names = {r.name for r in results}
        ages  = {r.age  for r in results}
        self.assertEqual(names, {f"User{i}" for i in range(20)})
        self.assertEqual(ages,  set(range(20)))

        # Wrapper applied exactly once — not nested.
        init = MyModel.__init__
        self.assertTrue(getattr(init, _HYDRATION_WRAPPER_ATTR, False))
        self.assertFalse(
            getattr(init._original_init, _HYDRATION_WRAPPER_ATTR, False)
        )

    def test_concurrent_hydration_different_classes(self):
        """Concurrent hydration of different classes does not cross-contaminate."""
        results: typing.Dict[str, typing.List] = {"my": [], "optional": []}
        errors:  typing.List[Exception] = []
        lock     = threading.Lock()

        def hydrate_my(i: int) -> None:
            try:
                inst = MyModel.hydrate_formax_model({"name": f"M{i}", "age": i})
                with lock:
                    results["my"].append(inst)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        def hydrate_optional(i: int) -> None:
            try:
                inst = UsingOptionalDataClass.hydrate_formax_model({"value": i, "name": f"O{i}"})
                with lock:
                    results["optional"].append(inst)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = (
            [threading.Thread(target=hydrate_my,       args=(i,)) for i in range(10)]
          + [threading.Thread(target=hydrate_optional, args=(i,)) for i in range(10)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results["my"]),       10)
        self.assertEqual(len(results["optional"]), 10)

        for inst in results["my"]:
            self.assertIsInstance(inst, MyModel)
        for inst in results["optional"]:
            self.assertIsInstance(inst, UsingOptionalDataClass)
