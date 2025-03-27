from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet.base import WeaverletComponent, WeaverletApp, Identifier
from weaverlet.components import SimpleRouterComponent, RedirectComponent


class RedirectPageComponent(WeaverletComponent):

    redirect_button_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.redirect_component = RedirectComponent()

    def get_layout(self, pathname, hash, href, search):        
        return html.Div(
            [
                self.redirect_component(),  # child component
                html.Button('Click to redirect to another page', id=self.redirect_button_id)
            ]
        )

    def register_callbacks(self, app):
        @app.callback(
            Output(self.redirect_component.href_id,
                   self.redirect_component.href_attr),
            Trigger(self.redirect_button_id, 'n_clicks')
        )
        def redirect():            
            return {'url': '/another_page', 'target': '_self'}

class AnotherPageComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f'Hello from another page!')

class PageNotFoundComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname):
        return html.Div(f'Page not found!')

redirect_page_component = RedirectPageComponent()
another_page_component = AnotherPageComponent()
not_found_page_component = PageNotFoundComponent()


routes = {
    '/': redirect_page_component,
    '/another_page': another_page_component
}
router_component = SimpleRouterComponent(
    routes=routes,
    not_found_page_component=not_found_page_component
)

wapp = WeaverletApp(root_component=router_component)
wapp.app.run(port=8089)
