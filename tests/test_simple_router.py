"""SimpleRouterComponent — legacy + keep_mounted modes, use_prefix, shared not_found."""
from __future__ import annotations

import pytest
from dash import html

from weaverlet import (
    Identifier,
    SimpleRouterComponent,
    WeaverletApp,
    WeaverletComponent,
    WeaverletException,
)


class _Page(WeaverletComponent):
    d = Identifier()

    def __init__(self, label, **kw):
        super().__init__(**kw)
        self.label = label

    def get_layout(self, pathname=None):
        return html.Div(self.label, id=self.d)


class _NotFound(WeaverletComponent):
    d = Identifier()

    def get_layout(self, pathname):
        return html.Div(f"404@{pathname}", id=self.d)


# -- legacy mode (keep_mounted=False) -----------------------------------------

def test_legacy_router_layout_is_minimal():
    """Default behavior renders a single content <div> swapped on navigation."""
    home = _Page("home")
    router = SimpleRouterComponent(routes={"/": home}, not_found_page_component=_NotFound())
    app = WeaverletApp(router)
    # In legacy mode the layout is just (Location, content_div) — not pre-rendered.
    layout = app.app.layout
    assert isinstance(layout, html.Div)
    # No per-route wrapper IDs are used in this mode.
    assert router.keep_mounted is False


def test_legacy_router_invokes_correct_route():
    """The route_callback returns the layout of the matched route."""
    home = _Page("home")
    about = _Page("about")
    nf = _NotFound()
    router = SimpleRouterComponent(
        routes={"/": home, "/about": about},
        not_found_page_component=nf,
    )
    captured = {}

    class _CapApp:
        def callback(self, *args, **kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    fn = captured["fn"]
    assert fn("/", "", "", "").children == "home"
    assert fn("/about", "", "", "").children == "about"
    assert fn("/missing", "", "", "").children == "404@/missing"


def test_legacy_router_use_prefix_requires_context():
    home = _Page("home")
    router = SimpleRouterComponent(
        routes={"/": home}, not_found_page_component=_NotFound(), use_prefix=True
    )
    # No context['prefix'] yet -> should raise inside the callback.
    captured = {}

    class _CapApp:
        def callback(self, *a, **kw):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    with pytest.raises(WeaverletException):
        captured["fn"]("/", "", "", "")


def test_legacy_router_use_prefix_matches_prefixed_pathname():
    home = _Page("home")
    router = SimpleRouterComponent(
        routes={"/home": home}, not_found_page_component=_NotFound(), use_prefix=True
    )
    router._wlt_context = {"prefix": "/app"}
    captured = {}

    class _CapApp:
        def callback(self, *a, **kw):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    # f"{prefix}{route}" == "/app/home"
    assert captured["fn"]("/app/home", "", "", "").children == "home"
    # Bare prefix without route does NOT match.
    assert captured["fn"]("/app", "", "", "").children.startswith("404")


# -- keep_mounted mode --------------------------------------------------------

def test_keep_mounted_renders_all_routes_at_startup():
    home = _Page("home")
    about = _Page("about")
    router = SimpleRouterComponent(
        routes={"/": home, "/about": about},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
    )
    app = WeaverletApp(router)
    rendered = str(app.app.layout)
    assert "home" in rendered
    assert "about" in rendered


def test_keep_mounted_default_preserve_path_is_first_route():
    home = _Page("home")
    about = _Page("about")
    router = SimpleRouterComponent(
        routes={"/": home, "/about": about},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
    )
    assert router.preserve_path == "/"


def test_keep_mounted_explicit_preserve_path():
    home = _Page("home")
    about = _Page("about")
    router = SimpleRouterComponent(
        routes={"/": home, "/about": about},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
        preserve_path="/about",
    )
    assert router.preserve_path == "/about"


def test_keep_mounted_shared_not_found_skips_duplicate_wrapper():
    """If not_found is the same instance as a route, we must reuse that
    route's wrapper to avoid DuplicateIdError."""
    home = _Page("home")
    router = SimpleRouterComponent(
        routes={"/": home, "/other": _Page("other")},
        not_found_page_component=home,  # same instance as routes['/']
        keep_mounted=True,
    )
    app = WeaverletApp(router)  # must not raise
    assert router._not_found_shared_path == "/"
    assert router._not_found_wrapper_id is None
    # Layout still renders cleanly.
    assert "home" in str(app.app.layout)


def test_keep_mounted_independent_not_found_gets_its_own_wrapper():
    home = _Page("home")
    nf = _NotFound()
    router = SimpleRouterComponent(
        routes={"/": home},
        not_found_page_component=nf,
        keep_mounted=True,
    )
    assert router._not_found_shared_path is None
    assert router._not_found_wrapper_id is not None


def test_keep_mounted_toggle_callback_visible_path_styles():
    home = _Page("home")
    about = _Page("about")
    router = SimpleRouterComponent(
        routes={"/": home, "/about": about},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
    )
    captured = {}

    class _CapApp:
        def callback(self, *args, **kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    fn = captured["fn"]

    styles = fn("/")
    # routes order: ['/', '/about'] then optional not_found wrapper.
    home_style, about_style = styles[0], styles[1]
    # '/' is the preserve_path AND is visible -> _VISIBLE_STYLE (visibility:visible).
    assert home_style.get("visibility") == "visible"
    # '/about' hidden -> display:none.
    assert about_style.get("display") == "none"


def test_keep_mounted_toggle_callback_unknown_path_shows_not_found():
    home = _Page("home")
    nf = _NotFound()
    router = SimpleRouterComponent(
        routes={"/": home, "/about": _Page("about")},
        not_found_page_component=nf,
        keep_mounted=True,
    )
    captured = {}

    class _CapApp:
        def callback(self, *a, **kw):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    fn = captured["fn"]
    styles = fn("/nowhere")
    # The trailing style is the not_found wrapper, which should be visible.
    not_found_style = styles[-1]
    assert not_found_style.get("visibility") == "visible"


def test_keep_mounted_toggle_callback_with_use_prefix():
    home = _Page("home")
    router = SimpleRouterComponent(
        routes={"/": home, "/about": _Page("about")},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
        use_prefix=True,
    )
    router._wlt_context = {"prefix": "/app"}
    captured = {}

    class _CapApp:
        def callback(self, *a, **kw):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    router.register_callbacks(_CapApp())
    styles = captured["fn"]("/app/about")
    # '/about' should be the visible one — and since it's not preserve_path,
    # it gets the overlay style (position absolute, zIndex 2).
    about_style = styles[1]
    assert about_style.get("position") == "absolute"
    assert about_style.get("zIndex") == 2
