from weaverlet.base import WeaverletComponent, WeaverletApp
from weaverlet.components import SimpleRouterComponent
from dash import html


class PageAComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f'hello from Page A!')


class PageBComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f'hello from Page B!')


class PageNotFoundComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname):
        return html.Div(f'Page not found!')


page_a_component = PageAComponent()
page_b_component = PageBComponent()
not_found_page_component = PageNotFoundComponent()

routes = {
    '/': page_a_component,
    '/page_a': page_a_component,
    '/page_b': page_b_component
}
router_component = SimpleRouterComponent(
    routes=routes,
    not_found_page_component=not_found_page_component
)

wapp = WeaverletApp(root_component=router_component)
wapp.app.run_server(port=8089)
