# pyright: reportMissingImports=false

from dash import dcc, html
from dash_extensions.enrich import Input, Output, State
from ..base import RouterComponent, ComponentsDict, Identifier, ComponentsDict, WeaverletException, DEFAULT_COMPONENT_NAME
from ..logger import logger


class SimpleRoutes(ComponentsDict):
    def get_components(self):
        return self.values()


class SimpleRouterComponent(RouterComponent):

    content_id = Identifier()
    url_id = Identifier()

    def __init__(self, routes, not_found_page_component, use_prefix=False, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.use_prefix = use_prefix
        self.routes = SimpleRoutes(routes)
        self.not_found_page_component = not_found_page_component
        self.set_name(name)

    def get_layout(self):
        layout = \
            html.Div([
                dcc.Location(id=self.url_id, refresh=False),
                html.Div(id=self.content_id)
            ])
        return layout

    def register_callbacks(self, app):

        @app.callback(
            Output(self.content_id, 'children'),
            Input(self.url_id, 'pathname'),
            State(self.url_id, 'hash'),
            State(self.url_id, 'href'),
            State(self.url_id, 'search')
        )
        def route_callback(pathname, hash, href, search):

            if self.use_prefix:
                if 'prefix' in self.get_context():
                    prefix = self.get_context()['prefix']
                else:
                    raise WeaverletException(
                        'use_prefix = True but the "prefix" key was not found in the context.')
            else:
                prefix = ''

            for route in self.routes.keys():
                if pathname == f'{prefix}{route}':
                    logger.info(
                        f'[SimpleRouterComponent.register_callbacks.route] route {route} matched')
                    return self.routes[route](pathname, hash, href, search)

            # user tried to reach a different page
            logger.info(
                f'[SimpleRouterComponent.register_callbacks.route] route not found')
            return self.not_found_page_component(pathname=pathname)
