from dash import html
from dash_extensions.enrich import Output, Trigger
from flask import session
from weaverlet.base import WeaverletComponent, WeaverletApp, Identifier
from weaverlet.components import AuthRouterComponent, RedirectComponent


class LoginPageComponent(WeaverletComponent):

    login_button_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redirect_component = RedirectComponent()

    def get_layout(self, pathname, hash, href, search, protected_route):
        self.protected_route = protected_route
        return html.Div(
            [
                self.redirect_component(),  # child component
                html.Button('Click to login', id=self.login_button_id)
            ]
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.redirect_component.href_id,
                   self.redirect_component.href_attr),
            Trigger(self.login_button_id, 'n_clicks')
        )
        def redirect_to_protected_route():
            session['user'] = 'Omar'
            return {'url': self.protected_route, 'target': '_self'}


class ProtectedPageComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search, user):
        return html.Div(f'Welcome, {user}!')


class PageNotFoundComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname):
        return html.Div(f'Page not found!')


login_page_component = LoginPageComponent()
protected_page_component = ProtectedPageComponent()
not_found_page_component = PageNotFoundComponent()

routes = {
    '/': {'component': protected_page_component, 'login_required': True},
    '/login': {'component': login_page_component, 'login_required': False}
}
router_component = AuthRouterComponent(
    routes=routes,
    not_found_page_component=not_found_page_component
)

wapp = WeaverletApp(root_component=router_component)
wapp.app.run_server(port=8089)
