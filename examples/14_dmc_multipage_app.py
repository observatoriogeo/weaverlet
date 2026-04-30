"""Multipage Weaverlet app with Dash Mantine Components.

Pattern mirrors examples/12_dbc_multipage_app.py but swaps dash-bootstrap-components
for dash-mantine-components. The one DMC-specific requirement is wrapping the
top-level layout in a `MantineProvider` so DMC components pick up the theme.

For WebGL-heavy pages (dash-leaflet maps, dash-sylvereye graphs, Plotly WebGL
backends), pass `keep_mounted=True` to SimpleRouterComponent so each route's
canvas state survives navigation. This example uses the default
`keep_mounted=False` since DMC alone has no WebGL state to preserve.
"""

import dash_mantine_components as dmc

from weaverlet import (
    SimpleRouterComponent,
    WeaverletApp,
    WeaverletComponent,
)


class SidebarComponent(WeaverletComponent):
    def get_layout(self):
        return dmc.Stack(
            [
                dmc.Title("Weaverlet + DMC", order=4),
                dmc.NavLink(label="Page A", href="/a"),
                dmc.NavLink(label="Page B", href="/b"),
            ],
            gap="xs",
            p="md",
        )


class PageComponent(WeaverletComponent):
    def __init__(self, title, body, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.body = body

    def get_layout(self):
        return dmc.Card(
            [
                dmc.Title(self.title, order=2),
                dmc.Space(h="md"),
                dmc.Text(self.body),
                dmc.Space(h="lg"),
                dmc.Button("Primary action", variant="filled"),
            ],
            withBorder=True,
            shadow="sm",
            padding="lg",
            m="md",
        )


class NotFoundComponent(WeaverletComponent):
    def get_layout(self, pathname):
        return dmc.Alert(
            f"Page {pathname} not found",
            title="404",
            color="red",
            m="md",
        )


class ShellComponent(WeaverletComponent):
    """Top-level shell: MantineProvider + sidebar + router-driven content."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = SidebarComponent()
        page_a = PageComponent(
            title="Page A",
            body="Welcome to Page A. This card is rendered by Dash Mantine Components.",
        )
        page_b = PageComponent(
            title="Page B",
            body="Welcome to Page B. Navigate via the sidebar to switch routes.",
        )
        not_found_page = NotFoundComponent()
        # For WebGL-heavy pages, pass keep_mounted=True so canvas state
        # survives navigation:
        #   self.router = SimpleRouterComponent(routes=..., keep_mounted=True)
        self.router = SimpleRouterComponent(
            routes={
                "/": page_a,
                "/a": page_a,
                "/b": page_b,
            },
            not_found_page_component=not_found_page,
        )

    def get_layout(self):
        return dmc.MantineProvider(
            dmc.Grid(
                [
                    dmc.GridCol(self.sidebar(), span=3),
                    dmc.GridCol(self.router(), span=9),
                ],
                gutter=0,
            ),
            theme={"primaryColor": "indigo"},
        )


wapp = WeaverletApp(
    root_component=ShellComponent(),
    title="Weaverlet + Dash Mantine Components",
)

if __name__ == "__main__":
    wapp.app.run()
