"""Children discovery, DAG walk, cycle handling, DetachedComponentRef."""
from __future__ import annotations

from dash import html

from weaverlet import (
    ComponentsDict,
    ComponentsList,
    ComponentsOrderedDict,
    DetachedComponentRef,
    DetatchedComponentRef,
    Identifier,
    WeaverletComponent,
)


class _Leaf(WeaverletComponent):
    d = Identifier()

    def get_layout(self):
        return html.Div(id=self.d)


class _LeafChildren(ComponentsList):
    def get_components(self):
        return list(self)


class _LeafDict(ComponentsDict):
    def get_components(self):
        return list(self.values())


class _LeafOrdered(ComponentsOrderedDict):
    def get_components(self):
        return list(self.values())


def test_get_children_finds_direct_attribute():
    parent = _Leaf()
    parent.child = _Leaf()
    children = parent.get_children()
    assert parent.child in children


def test_get_children_finds_components_list():
    parent = _Leaf()
    parent.kids = _LeafChildren([_Leaf(), _Leaf()])
    children = parent.get_children()
    assert len(children) == 2
    assert all(isinstance(c, _Leaf) for c in children)


def test_get_children_finds_components_dict():
    parent = _Leaf()
    parent.kids = _LeafDict({"a": _Leaf(), "b": _Leaf()})
    children = parent.get_children()
    assert len(children) == 2


def test_get_children_finds_components_ordered_dict():
    parent = _Leaf()
    a, b = _Leaf(), _Leaf()
    parent.kids = _LeafOrdered([("a", a), ("b", b)])
    assert parent.get_children() == [a, b]


def test_get_children_skips_plain_collections():
    """A plain list/dict of components is invisible — by design."""
    parent = _Leaf()
    parent.plain_list = [_Leaf(), _Leaf()]
    parent.plain_dict = {"x": _Leaf()}
    assert parent.get_children() == []


def test_wlt_walk_yields_self_and_descendants():
    root = _Leaf()
    root.a = _Leaf()
    root.b = _Leaf()
    walked = list(root._wlt_walk())
    assert root in walked
    assert root.a in walked
    assert root.b in walked
    assert len(walked) == 3


def test_wlt_walk_sets_parent():
    root = _Leaf()
    root.a = _Leaf()
    list(root._wlt_walk())
    assert root.a.get_parent() is root


def test_wlt_walk_handles_cycles():
    """Cycles must not loop forever."""
    a, b = _Leaf(), _Leaf()
    a.peer = b
    b.peer = a  # cycle
    walked = list(a._wlt_walk())
    # Each component visited exactly once, regardless of the back-edge.
    assert len(walked) == 2
    assert set(map(id, walked)) == {id(a), id(b)}


def test_detached_component_ref_hides_from_walker():
    """A DetachedComponentRef wrapper must not be picked up as a child."""
    a = _Leaf()
    b = _Leaf()
    a.detached = DetachedComponentRef(b)
    walked = list(a._wlt_walk())
    # b should NOT be visited — the wrapper is opaque to the walker.
    assert b not in walked
    assert len(walked) == 1


def test_detached_component_ref_proxies_attribute_access():
    leaf = _Leaf()
    ref = DetachedComponentRef(leaf)
    assert ref.d == leaf.d  # Identifier proxied through


def test_detached_alias_matches_renamed_class():
    assert DetatchedComponentRef is DetachedComponentRef
