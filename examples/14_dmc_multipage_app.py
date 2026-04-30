"""Multipage Weaverlet app with Dash Mantine Components.

Pattern mirrors examples/12_dbc_multipage_app.py but swaps dash-bootstrap-components
for dash-mantine-components, and uses DMC's `AppShell` for a more polished
dashboard layout (fixed header, sidebar with active-state highlighting,
scrollable main content area).

This example uses `keep_mounted=True` on the router so each page's state
survives navigation: click the counter on Page A, switch to Page B, come
back — the count is preserved (the component was never unmounted, only
hidden via CSS). Same mechanism is what keeps WebGL canvases (dash-leaflet,
dash-sylvereye) alive across route changes; for those, also consider
`preserve_path=` to point at the WebGL-heavy route.
"""

import dash_mantine_components as dmc
from dash_extensions.enrich import Input, Output

from weaverlet import (
    Identifier,
    SimpleRouterComponent,
    WeaverletApp,
    WeaverletComponent,
)


class SidebarComponent(WeaverletComponent):
    nav_a_id = Identifier()
    nav_b_id = Identifier()

    def get_layout(self):
        return dmc.AppShellNavbar(
            dmc.Stack(
                [
                    dmc.Text(
                        "Navigation",
                        size="xs",
                        c="dimmed",
                        fw=700,
                        tt="uppercase",
                        mb="xs",
                    ),
                    dmc.NavLink(
                        label="Page A",
                        description="Click counter demo",
                        href="/",
                        id=self.nav_a_id,
                    ),
                    dmc.NavLink(
                        label="Page B",
                        description="Greeting toggle demo",
                        href="/b",
                        id=self.nav_b_id,
                    ),
                ],
                gap="xs",
                p="md",
            ),
        )


class PageComponent(WeaverletComponent):
    """A page with a button whose behavior is supplied by the caller.

    Each instance owns its own button + output Text via Identifier descriptors,
    so the per-page callback wires inputs/outputs scoped to that instance only —
    the canonical Weaverlet pattern.
    """

    button_id = Identifier()
    output_id = Identifier()

    def __init__(self, title, badge, body, action_label, get_message, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.badge = badge
        self.body = body
        self.action_label = action_label
        self.get_message = get_message

    def get_layout(self):
        return dmc.Card(
            [
                dmc.CardSection(
                    dmc.Group(
                        [
                            dmc.Title(self.title, order=2),
                            dmc.Badge(self.badge, variant="light", color="indigo"),
                        ],
                        justify="space-between",
                    ),
                    inheritPadding=True,
                    withBorder=True,
                    py="sm",
                ),
                dmc.Space(h="md"),
                dmc.Text(self.body, size="sm"),
                dmc.Space(h="xl"),
                dmc.Group(
                    [
                        dmc.Button(
                            self.action_label,
                            id=self.button_id,
                            variant="filled",
                            color="indigo",
                        ),
                        dmc.Text(id=self.output_id, c="dimmed", size="sm"),
                    ],
                    gap="md",
                    align="center",
                ),
            ],
            withBorder=True,
            shadow="sm",
            padding="lg",
            radius="md",
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.output_id, "children"),
            Input(self.button_id, "n_clicks"),
            prevent_initial_call=True,
        )
        def update(n_clicks):
            return self.get_message(n_clicks or 0)


class NotFoundComponent(WeaverletComponent):
    def get_layout(self):
        return dmc.Alert(
            "The page you requested doesn't exist.",
            title="404 — Page not found",
            color="red",
            variant="light",
        )


class ShellComponent(WeaverletComponent):
    """Top-level shell: MantineProvider + AppShell + router-driven content."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = SidebarComponent()
        page_a = PageComponent(
            title="Page A",
            badge="Counter",
            body=(
                "Welcome to Page A. The button below increments a click counter that "
                "persists when you navigate to Page B and back, thanks to "
                "keep_mounted=True on the router."
            ),
            action_label="Increment counter",
            get_message=lambda n: f"Clicked {n} time{'s' if n != 1 else ''}.",
        )
        page_b = PageComponent(
            title="Page B",
            badge="Toggle",
            body=(
                "Welcome to Page B. The button below alternates a greeting. "
                "Switch to Page A and back — the toggle state survives."
            ),
            action_label="Toggle greeting",
            get_message=lambda n: "Hello!" if n % 2 == 1 else "Goodbye!",
        )
        not_found = NotFoundComponent()
        # With keep_mounted=True, every route entry pre-renders its component
        # once. Aliasing two paths to the same instance (e.g. "/" and "/a"
        # both pointing to page_a) would mount that instance twice and trigger
        # DuplicateIdError, so each path maps to a distinct component here.
        self.router = SimpleRouterComponent(
            routes={
                "/": page_a,
                "/b": page_b,
            },
            not_found_page_component=not_found,
            keep_mounted=True,
        )

    def get_layout(self):
        return dmc.MantineProvider(
            dmc.AppShell(
                [
                    dmc.AppShellHeader(
                        dmc.Group(
                            [
                                dmc.Title("Weaverlet", order=3, c="indigo"),
                                dmc.Badge("v0.3.0", variant="light", size="sm"),
                                dmc.Text("·", c="dimmed"),
                                dmc.Text(
                                    "Dash Mantine Components example",
                                    c="dimmed",
                                    size="sm",
                                ),
                            ],
                            h="100%",
                            px="md",
                            gap="sm",
                            align="center",
                        ),
                    ),
                    self.sidebar(),
                    dmc.AppShellMain(
                        dmc.Container(self.router(), size="md", py="xl"),
                    ),
                ],
                header={"height": 60},
                navbar={"width": 260, "breakpoint": "sm"},
                padding="md",
            ),
            theme={"primaryColor": "indigo"},
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.sidebar.nav_a_id, "active"),
            Output(self.sidebar.nav_b_id, "active"),
            Input(self.router.url_id, "pathname"),
            prevent_initial_call=False,
        )
        def highlight_active(pathname):
            pathname = pathname or "/"
            return pathname == "/", pathname == "/b"


wapp = WeaverletApp(
    root_component=ShellComponent(),
    title="Weaverlet + Dash Mantine Components",
)

if __name__ == "__main__":
    wapp.app.run()
