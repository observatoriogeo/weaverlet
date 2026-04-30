"""Permissive get_layout invocation — _call_with_router_kwargs and _safe_get_layout."""
from __future__ import annotations

from dash import html

from weaverlet import Identifier, WeaverletComponent
from weaverlet.base import _call_with_router_kwargs, _safe_get_layout


class _NoArgs(WeaverletComponent):
    d = Identifier()

    def get_layout(self):
        return html.Div("noargs", id=self.d)


class _Pathname(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname):
        return html.Div(f"path={pathname}", id=self.d)


class _AllRouterArgs(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f"{pathname}|{hash}|{href}|{search}", id=self.d)


class _UserAware(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname, user):
        return html.Div(f"{pathname}|{user}", id=self.d)


# -- _call_with_router_kwargs -------------------------------------------------

def test_call_with_router_kwargs_drops_unknown():
    out = _call_with_router_kwargs(
        _NoArgs(), pathname="/x", hash="h", href="hr", search="s"
    )
    assert "noargs" in out.children


def test_call_with_router_kwargs_passes_subset():
    out = _call_with_router_kwargs(
        _Pathname(), pathname="/x", hash="ignored", href="ignored", search="ignored"
    )
    assert out.children == "path=/x"


def test_call_with_router_kwargs_passes_all():
    out = _call_with_router_kwargs(
        _AllRouterArgs(), pathname="/x", hash="#h", href="http://x", search="?q"
    )
    assert out.children == "/x|#h|http://x|?q"


def test_call_with_router_kwargs_passes_user():
    out = _call_with_router_kwargs(
        _UserAware(), pathname="/x", user="alice", hash="ignored"
    )
    assert out.children == "/x|alice"


# -- _safe_get_layout ---------------------------------------------------------

def test_safe_get_layout_no_args():
    out = _safe_get_layout(_NoArgs())
    assert "noargs" in out.children


def test_safe_get_layout_injects_pathname_default():
    out = _safe_get_layout(_Pathname())
    assert out.children == "path=/"


def test_safe_get_layout_injects_all_router_placeholders():
    out = _safe_get_layout(_AllRouterArgs())
    # pathname="/", others ""
    assert out.children == "/||"  + "|"


def test_safe_get_layout_injects_user_none():
    out = _safe_get_layout(_UserAware())
    assert out.children == "/|None"


def test_safe_get_layout_respects_explicit_defaults():
    class _WithDefaults(WeaverletComponent):
        d = Identifier()

        def get_layout(self, label="default-label"):
            return html.Div(label, id=self.d)

    out = _safe_get_layout(_WithDefaults())
    assert out.children == "default-label"
