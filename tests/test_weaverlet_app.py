"""WeaverletApp — boot, context propagation, assets_folder, jupyter_mode."""
from __future__ import annotations

import os
import sys

import pytest
from dash import html
from dash_extensions.enrich import DashProxy

from weaverlet import (
    Identifier,
    SimpleRouterComponent,
    WeaverletApp,
    WeaverletComponent,
)


class _Trivial(WeaverletComponent):
    d = Identifier()

    def get_layout(self):
        return html.Div("hello", id=self.d)


class _ContextSpy(WeaverletComponent):
    d = Identifier()

    def __init__(self):
        super().__init__()
        self.seen_context = None
        self.initialize_called = False

    def initialize(self):
        self.seen_context = self.get_context()
        self.initialize_called = True

    def get_layout(self):
        return html.Div("spy", id=self.d)


def test_app_boots_with_trivial_root():
    app = WeaverletApp(_Trivial())
    assert isinstance(app.app, DashProxy)
    assert app.app.layout is not None


def test_root_alias_matches_root_component():
    root = _Trivial()
    app = WeaverletApp(root)
    assert app.root is root
    assert app.root_component is root


def test_context_propagates_to_every_component():
    spy_a = _ContextSpy()
    spy_b = _ContextSpy()
    parent = _Trivial()
    parent.a = spy_a
    parent.b = spy_b
    ctx = {"prefix": "/app", "feature_flag": True}
    WeaverletApp(parent, context=ctx)
    assert spy_a.seen_context == ctx
    assert spy_b.seen_context == ctx
    assert spy_a.initialize_called and spy_b.initialize_called


def test_initialize_runs_before_callbacks():
    """initialize() must run *before* register_callbacks()."""
    order = []

    class _Tracking(WeaverletComponent):
        d = Identifier()

        def initialize(self):
            order.append("init")

        def register_callbacks(self, app):
            order.append("cb")

        def get_layout(self):
            return html.Div("t", id=self.d)

    WeaverletApp(_Tracking())
    assert order == ["init", "cb"]


def test_assets_folder_auto_resolves_to_main_module_dir(tmp_path, monkeypatch):
    """When assets_folder is None, the app should derive it from __main__."""
    fake_main_file = tmp_path / "user_app.py"
    fake_main_file.write_text("# fake")
    fake_main = type(sys)("fake_main")
    fake_main.__file__ = str(fake_main_file)
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    app = WeaverletApp(_Trivial())
    expected = os.path.join(str(tmp_path), "assets")
    assert app.app.config.assets_folder == expected


def test_assets_folder_explicit_overrides_auto(tmp_path):
    explicit = str(tmp_path / "custom_assets")
    app = WeaverletApp(_Trivial(), assets_folder=explicit)
    assert app.app.config.assets_folder == explicit


def test_title_kwarg_passes_through():
    app = WeaverletApp(_Trivial(), title="my dashboard")
    assert app.app.title == "my dashboard"


def test_external_stylesheets_kwarg_passes_through():
    sheets = ["https://example.test/style.css"]
    app = WeaverletApp(_Trivial(), external_stylesheets=sheets)
    # DashProxy stores the list on the app config.
    assert sheets[0] in app.app.config.external_stylesheets


def test_suppress_callback_exceptions_default_true():
    app = WeaverletApp(_Trivial())
    assert app.app.config.suppress_callback_exceptions is True


def test_suppress_callback_exceptions_can_be_disabled():
    app = WeaverletApp(_Trivial(), suppress_callback_exceptions=False)
    assert app.app.config.suppress_callback_exceptions is False


def test_jupyter_mode_without_extra_raises_helpful_error(monkeypatch):
    """jupyter_mode=True with no jupyter_dash should raise ImportError naming the extra."""
    # Force the import to fail even if the package happens to be installed.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jupyter_dash":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="weaverlet\\[jupyter\\]"):
        WeaverletApp(_Trivial(), jupyter_mode=True)


def test_router_as_root_does_not_explode_on_layout():
    """A SimpleRouterComponent as the root has get_layout(self) — no router
    args needed at boot. _safe_get_layout must handle this."""

    class _Page(WeaverletComponent):
        d = Identifier()

        def get_layout(self):
            return html.Div("p", id=self.d)

    class _NF(WeaverletComponent):
        d = Identifier()

        def get_layout(self, pathname):
            return html.Div("nf", id=self.d)

    router = SimpleRouterComponent(routes={"/": _Page()}, not_found_page_component=_NF())
    app = WeaverletApp(router)
    assert app.app.layout is not None
