"""Minimal app used by the browser test — two pages, each with a counter
button + click-count display, wired through `keep_mounted=True` so we can
assert that state survives navigation in a real browser.

Boot with:  `PORT=<n> python -m tests.fixtures.keep_mounted_app`
Or import-and-call `build_app(port=...)` from a test fixture.
"""
from __future__ import annotations

import os
import sys

from dash import dcc, html
from dash_extensions.enrich import Input, Output

from weaverlet import (
    Identifier,
    SimpleRouterComponent,
    WeaverletApp,
    WeaverletComponent,
)


class _Page(WeaverletComponent):
    btn_id = Identifier()
    out_id = Identifier()
    nav_a_id = Identifier()
    nav_b_id = Identifier()

    def __init__(self, label, **kw):
        super().__init__(**kw)
        self.label = label

    def get_layout(self):
        return html.Div(
            [
                html.H2(f"Page {self.label}"),
                # dcc.Link routes through dcc.Location's pushState, which is
                # what makes navigation SPA-style. html.A would do a full
                # browser reload and unmount everything — defeating the
                # whole point of keep_mounted.
                dcc.Link("Go to A", href="/", id=self.nav_a_id),
                html.Span(" | "),
                dcc.Link("Go to B", href="/b", id=self.nav_b_id),
                html.Hr(),
                html.Button("Click me", id=self.btn_id),
                html.Div(id=self.out_id, **{"data-testid": f"out-{self.label}"}),
            ]
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.out_id, "children"),
            Input(self.btn_id, "n_clicks"),
            prevent_initial_call=True,
        )
        def update(n_clicks):
            return f"clicks: {n_clicks or 0}"


class _NotFound(WeaverletComponent):
    def get_layout(self, pathname):
        return html.Div(f"404: {pathname}")


def build_app():
    page_a = _Page("A", name="page_a")
    page_b = _Page("B", name="page_b")
    router = SimpleRouterComponent(
        routes={"/": page_a, "/b": page_b},
        not_found_page_component=_NotFound(),
        keep_mounted=True,
    )
    return WeaverletApp(root_component=router, title="keep_mounted browser fixture")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    app = build_app()
    # Print our own ready marker to stderr so the parent can wait on it
    # (Dash also prints its own "Running on" line; we add a second one
    # in case Dash logs change).
    print(f"WLT_FIXTURE_READY port={port}", file=sys.stderr, flush=True)
    app.app.run(port=port, debug=False)
