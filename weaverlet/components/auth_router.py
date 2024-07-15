# pyright: reportMissingImports=false, reportMissingModuleSource=false

from flask import session
import dash_html_components as html
import dash_core_components as dcc
from dash_extensions.enrich import Input, Output, State
from ..base import RouterComponent, ComponentsDict, Identifier, ComponentsDict, WeaverletException, DEFAULT_COMPONENT_NAME
from ..logger import logger


class AuthRoutes(ComponentsDict):
    def get_components(self):
        return [value['component'] for value in self.values()]


class AuthRouterComponent(RouterComponent):

    content_id = Identifier()
    url_id = Identifier()

    def __init__(self, routes, not_found_page_component, user_session_key='user', login_route='/login', use_prefix=False, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.use_prefix = use_prefix
        self.routes = AuthRoutes(routes)
        self.not_found_page_component = not_found_page_component
        self.user_session_key = user_session_key
        self.login_route = login_route
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
                        f'[AuthRouterComponent.register_callbacks.route] route {route} matched')
                    if(self.routes[route]['login_required']):
                        logger.info(
                            f'[AuthRouterComponent.register_callbacks.route] route {route} requires login')
                        if self.user_session_key in session:
                            logger.info(
                                f'[AuthRouterComponent.register_callbacks.route] user key found in session, rendering layout of {self.routes[route]["component"]}')
                            user = session[self.user_session_key]
                            return self.routes[route]['component'](pathname, hash, href, search, user)
                        else:
                            logger.info(
                                f'[AuthRouterComponent.register_callbacks.route] user key not found in session, rendering layout of {self.routes[self.login_route]["component"]}')
                            return self.routes[self.login_route]['component'](pathname, hash, href, search, f'{prefix}{route}')
                    else:
                        return self.routes[route]['component'](pathname, hash, href, search)

            # user tried to reach a different page
            logger.info(
                f'[AuthRouterComponent.register_callbacks.route] route not found')
            return self.not_found_page_component(pathname=pathname)
