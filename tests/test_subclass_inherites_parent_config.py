import pytest
import typing
from formax import BaseModel

from formax.utils import FORMAX_MODEL_CONFIG



def test_subclass_inherits_parent_config():
    """Verifies a subclass completely inherits the parent's Config if it defines none."""
    class Parent(BaseModel):
        class Config:
            foo = "parent-value"

    class Child(Parent):
        pass  # Defines no Config of its own

    child_model_config = getattr(Child, FORMAX_MODEL_CONFIG, None)
    parent_model_config = getattr(Parent, FORMAX_MODEL_CONFIG, None)

    assert child_model_config is not None
    assert parent_model_config is not None
    assert child_model_config._config is parent_model_config._config
    assert child_model_config._config.foo == "parent-value"


def test_subclass_overrides_parent_config():
    """Verifies a subclass can explicitly override the parent's Config."""
    class Parent(BaseModel):
        class Config:
            foo = "parent-value"

    class Child(Parent):
        class Config:
            foo = "child-value"

    child_model_config = getattr(Child, FORMAX_MODEL_CONFIG, None)
    parent_model_config = getattr(Parent, FORMAX_MODEL_CONFIG, None)

    assert child_model_config is not None
    assert parent_model_config is not None

    # The Child should use its own Config class instead of the Parent's
    assert child_model_config._config is Child.Config
    assert child_model_config._config.foo == "child-value"


def test_grandchild_inherits_grandparent_config():
    """Verifies that Config lookup resolves down multiple levels of inheritance."""
    class Grandparent(BaseModel):
        class Config:
            foo = "grandparent-value"

    class Parent(Grandparent):
        pass  # Inherits grandparent config

    class Child(Parent):
        pass  # Should still inherit grandparent config via Parent

    child_model_config = getattr(Child, FORMAX_MODEL_CONFIG, None)
    parent_model_config = getattr(Parent, FORMAX_MODEL_CONFIG, None)
    grandparent_model_config = getattr(Grandparent, FORMAX_MODEL_CONFIG, None)

    assert child_model_config is not None
    assert parent_model_config is not None
    assert grandparent_model_config is not None

    assert child_model_config._config is Grandparent.Config
    assert child_model_config._config.foo == "grandparent-value"


def test_no_config_defined_anywhere():
    """Verifies that the metaclass gracefully handles cases where no Config is provided."""
    class Parent(BaseModel):
        pass  # No Config

    class Child(Parent):
        pass  # No Config

    child_model_config = getattr(Child, FORMAX_MODEL_CONFIG, None)
    parent_model_config = getattr(Parent, FORMAX_MODEL_CONFIG, None)

    assert child_model_config is not None
    assert parent_model_config is not None
    assert child_model_config._config is None
