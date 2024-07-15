# -*- coding: utf-8 -*-

import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from weaverlet.base import WeaverletApp, WeaverletComponent, Identifier
from weaverlet.components import SimpleRouterComponent


class PrimaryNavbarComponent(WeaverletComponent):  

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, brand):
        layout = \
            dbc.NavbarSimple(
                children=[
                    dbc.NavItem(dbc.NavLink('Page A', href='/a')),
                    dbc.NavItem(dbc.NavLink('Page B', href='/b'))
                ],
                brand=brand,
                color='primary',
                dark=True
            )

        return layout


class MainPageComponent(WeaverletComponent):

    def __init__(self, brand, page_content_component):
        super().__init__()
        self.primary_navbar = PrimaryNavbarComponent(name='primary_navbar')
        self.page_content_component = page_content_component
        self.brand = brand

    def get_layout(self, pathname, hash, href, search):
        layout = \
            html.Div(
                [
                    self.primary_navbar(brand=self.brand),  # child component
                    dbc.Container(
                        [
                            self.page_content_component()  # child component
                        ],
                        fluid=True,
                        style={"padding": "0px", 'width': "100%"}
                    )
                ]
            )

        return layout


class ContentComponent(WeaverletComponent):

    def __init__(self, body, **kwargs):
        super().__init__(**kwargs)
        self.body = body

    def get_layout(self):
        layout = \
            dbc.Container([
                dcc.Markdown(self.body)
            ])

        return layout


class NotFoundPageComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname):
        layout = \
            dcc.Markdown(f"# Page {pathname} not found!")

        return layout


page_a_markdown = """
# Page A \

This is the content of Page A.
"""

page_b_markdown = """
# Page B \

This is the content of Page B.
"""

content_page_a = ContentComponent(body=page_a_markdown)
content_page_b = ContentComponent(body=page_b_markdown)
page_a_main_page = MainPageComponent(brand='Brand of Page A',
                                     page_content_component=content_page_a)
page_b_main_page = MainPageComponent(brand='Brand of Page B',
                                     page_content_component=content_page_b)
not_found_page = NotFoundPageComponent()

routes = {
    '/': page_a_main_page,
    '/a': page_a_main_page,
    '/b': page_b_main_page
}
router = SimpleRouterComponent(
    routes=routes,
    not_found_page_component=not_found_page
)
wapp = WeaverletApp(root_component=router,
                    title='Simple Weaverlet + DBC app',
                    external_stylesheets=[dbc.themes.COSMO])

wapp.app.run_server()
