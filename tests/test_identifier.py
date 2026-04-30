"""Identifier descriptor — uniqueness, immutability, no __init__ dependency."""
from __future__ import annotations

import pytest
from dash import html

from weaverlet import Identifier, WeaverletComponent


class _Comp(WeaverletComponent):
    a = Identifier()
    b = Identifier()

    def get_layout(self):
        return html.Div(id=self.a)


def test_identifier_unique_across_instances():
    c1, c2 = _Comp(), _Comp()
    assert c1.a != c2.a
    assert c1.b != c2.b


def test_identifier_stable_within_instance():
    c = _Comp()
    assert c.a == c.a
    assert c.b == c.b


def test_identifier_distinct_across_attrs():
    c = _Comp()
    assert c.a != c.b


def test_identifier_format_includes_class_and_attr():
    c = _Comp()
    assert "_Comp_a_" in c.a
    assert "_Comp_b_" in c.b


def test_identifier_rejects_assignment():
    c = _Comp()
    with pytest.raises(TypeError):
        c.a = "anything"


def test_identifier_class_access_returns_descriptor():
    # Accessing through the class (not an instance) yields the descriptor itself.
    assert isinstance(_Comp.a, Identifier)


def test_identifier_does_not_require_super_init_first():
    """Identifier must not depend on _id existing on the instance — i.e.,
    accessing it before super().__init__() runs must still work."""

    class Early(WeaverletComponent):
        x = Identifier()

        def __init__(self):
            # Touch the identifier BEFORE super().__init__() runs.
            self._captured = self.x
            super().__init__()

        def get_layout(self):
            return html.Div(id=self.x)

    e = Early()
    assert e._captured == e.x
