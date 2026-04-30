"""AuthRouterComponent — session-based login flow + flexible get_layout signatures."""
from __future__ import annotations

from unittest.mock import patch

import pytest
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


# -- keep_mounted mode --------------------------------------------------------


def _build_keep_mounted_router(**kwargs):
    return AuthRouterComponent(
        routes={
            "/": {"component": _ProtectedPage(), "login_required": True},
            "/login": {"component": _LoginPage(), "login_required": False},
            "/public": {"component": _PublicPage(), "login_required": False},
        },
        not_found_page_component=_NotFound(),
        keep_mounted=True,
        **kwargs,
    )


def _capture_callbacks(router):
    captured: list = []

    class _CapApp:
        def callback(self, *args, **kwargs):
            def deco(fn):
                captured.append(fn)
                return fn

            return deco

    router.register_callbacks(_CapApp())
    return captured


def test_keep_mounted_renders_all_auth_routes_at_startup():
    """Pre-render every route, including the login page and protected pages,
    once each."""
    from weaverlet import WeaverletApp

    router = _build_keep_mounted_router()
    app = WeaverletApp(router)  # must not raise
    rendered = str(app.app.layout)
    # Login is pre-rendered with placeholder protected_route="".
    assert "login(target=)" in rendered
    # Protected page is pre-rendered with placeholder user=None.
    assert "hello None" in rendered
    # Public page renders normally.
    assert "public" in rendered


def test_keep_mounted_default_preserve_path_is_first_unique_route():
    router = _build_keep_mounted_router()
    assert router.preserve_path == "/"


def test_keep_mounted_toggle_redirects_protected_route_to_login_when_no_session():
    """Hitting a protected route without a session: the login wrapper is
    visible, the protected wrapper is hidden."""
    router = _build_keep_mounted_router()
    toggle_views = _capture_callbacks(router)[0]
    # _unique_paths order is ['/', '/login', '/public']; not_found wrapper
    # appended at the end.
    with patch("weaverlet.components.auth_router.session", {}):
        styles = toggle_views("/")
    protected_style, login_style, public_style, nf_style = styles
    # Protected wrapper is hidden (preserve_path -> visibility:hidden).
    assert protected_style.get("visibility") == "hidden"
    # Login wrapper is visible (overlay).
    assert login_style.get("position") == "absolute"
    assert login_style.get("zIndex") == 2


def test_keep_mounted_toggle_renders_protected_route_when_session_present():
    router = _build_keep_mounted_router()
    toggle_views = _capture_callbacks(router)[0]
    with patch("weaverlet.components.auth_router.session", {"user": "alice"}):
        styles = toggle_views("/")
    protected_style = styles[0]
    # protected_route ('/') is the preserve_path AND is visible.
    assert protected_style.get("visibility") == "visible"


def test_keep_mounted_toggle_public_route_visible_without_session():
    router = _build_keep_mounted_router()
    toggle_views = _capture_callbacks(router)[0]
    with patch("weaverlet.components.auth_router.session", {}):
        styles = toggle_views("/public")
    public_style = styles[2]
    assert public_style.get("position") == "absolute"  # overlay (not preserve_path)


def test_keep_mounted_login_wrapper_rerenders_with_actual_protected_route():
    """When a protected route triggers a login redirect, the login wrapper's
    children are re-rendered with the actual `protected_route` so the
    LoginPage's button can redirect back after auth."""
    from dash.exceptions import PreventUpdate

    router = _build_keep_mounted_router()
    callbacks = _capture_callbacks(router)
    # toggle_views, update_login_for_redirect, update_not_found_content
    assert len(callbacks) == 3
    update_login = callbacks[1]

    # Hitting "/" without session: login should re-render with protected_route="/"
    with patch("weaverlet.components.auth_router.session", {}):
        out = update_login("/")
    assert "login(target=/)" in out.children

    # Hitting "/" with a session: PreventUpdate (no need to re-render login).
    with patch("weaverlet.components.auth_router.session", {"user": "alice"}):
        with pytest.raises(PreventUpdate):
            update_login("/")

    # Hitting a public route: PreventUpdate.
    with patch("weaverlet.components.auth_router.session", {}):
        with pytest.raises(PreventUpdate):
            update_login("/public")


def test_keep_mounted_dynamic_404_rerenders_with_pathname():
    from dash.exceptions import PreventUpdate

    router = _build_keep_mounted_router()
    callbacks = _capture_callbacks(router)
    update_404 = callbacks[2]

    with patch("weaverlet.components.auth_router.session", {}):
        out = update_404("/totally-missing")
    assert "404@/totally-missing" in out.children

    with patch("weaverlet.components.auth_router.session", {}):
        with pytest.raises(PreventUpdate):
            update_404("/public")


def test_keep_mounted_aliased_routes_share_one_wrapper():
    """Same instance under two paths must share a wrapper (same as SimpleRouter)."""
    protected = _ProtectedPage()
    router = AuthRouterComponent(
        routes={
            "/": {"component": protected, "login_required": True},
            "/home": {"component": protected, "login_required": True},
            "/login": {"component": _LoginPage(), "login_required": False},
        },
        not_found_page_component=_NotFound(),
        keep_mounted=True,
    )
    assert router._route_wrapper_ids["/"] == router._route_wrapper_ids["/home"]
    assert router._unique_paths == ["/", "/login"]
