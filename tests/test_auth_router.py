"""AuthRouterComponent — session-based login flow + flexible get_layout signatures."""
from __future__ import annotations

from unittest.mock import patch

from dash import html

from weaverlet import AuthRouterComponent, Identifier, WeaverletComponent


class _LoginPage(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname, hash, href, search, protected_route):
        return html.Div(f"login(target={protected_route})", id=self.d)


class _ProtectedPage(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname, hash, href, search, user):
        return html.Div(f"hello {user} at {pathname}", id=self.d)


class _PublicPage(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname):
        return html.Div(f"public {pathname}", id=self.d)


class _NotFound(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname):
        return html.Div(f"404@{pathname}", id=self.d)


def _build_router():
    return AuthRouterComponent(
        routes={
            "/": {"component": _ProtectedPage(), "login_required": True},
            "/login": {"component": _LoginPage(), "login_required": False},
            "/public": {"component": _PublicPage(), "login_required": False},
        },
        not_found_page_component=_NotFound(),
    )


def _capture_route_callback(router):
    captured = {}

    class _CapApp:
        def callback(self, *args, **kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    return captured["fn"]


def test_protected_route_redirects_when_no_session():
    router = _build_router()
    fn = _capture_route_callback(router)
    with patch("weaverlet.components.auth_router.session", {}):
        out = fn("/", "", "", "")
    # Should render the login page with the protected target embedded.
    assert "login(target=/)" in out.children


def test_protected_route_renders_when_session_present():
    router = _build_router()
    fn = _capture_route_callback(router)
    with patch("weaverlet.components.auth_router.session", {"user": "alice"}):
        out = fn("/", "", "", "")
    assert "hello alice at /" in out.children


def test_public_route_renders_without_session():
    router = _build_router()
    fn = _capture_route_callback(router)
    with patch("weaverlet.components.auth_router.session", {}):
        out = fn("/public", "", "", "")
    assert "public /public" in out.children


def test_unknown_route_falls_through_to_not_found():
    router = _build_router()
    fn = _capture_route_callback(router)
    with patch("weaverlet.components.auth_router.session", {}):
        out = fn("/missing", "", "", "")
    assert "404@/missing" in out.children
