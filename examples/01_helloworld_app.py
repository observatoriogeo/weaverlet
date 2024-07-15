from weaverlet.base import WeaverletComponent, WeaverletApp
from dash import html

class HelloWorldComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
                        
    def get_layout(self):        
        return html.Div(f'hello world!')

helloworld_component = HelloWorldComponent()
wapp = WeaverletApp(root_component=helloworld_component)
wapp.app.run_server(port=8086)
