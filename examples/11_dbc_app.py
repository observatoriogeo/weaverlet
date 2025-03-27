# -*- coding: utf-8 -*-

import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from weaverlet.base import WeaverletApp, WeaverletComponent


class PrimaryNavbarComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, brand):
        layout = \
            dbc.NavbarSimple(
                brand=brand,
                color='primary',
                dark=True
            )

        return layout


class MainPageComponent(WeaverletComponent):

    def __init__(self, brand):
        super().__init__()
        self.primary_navbar = PrimaryNavbarComponent(name='primary_navbar')
        self.brand = brand

    def get_layout(self):
        layout = \
            html.Div(
                [
                    self.primary_navbar(brand=self.brand),  # child component
                    dbc.Container(
                        [
                            dcc.Markdown("# Hello world.")  # child component
                        ],
                        fluid=False,
                        style={"padding": "0px", 'width': "100%"}
                    )
                ]
            )

        return layout


main_page = MainPageComponent(brand='Brand of page')
wapp = WeaverletApp(root_component=main_page,
                    title='Simple Weaverlet + DBC app',
                    external_stylesheets=[dbc.themes.BOOTSTRAP])
wapp.app.run()
