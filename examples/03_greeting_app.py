from weaverlet.base import WeaverletComponent, WeaverletApp
from dash import html

class GreetingComponent(WeaverletComponent):

    def __init__(self, greeting_name, **kwargs):
        super().__init__(**kwargs)
        self.greeting_name = greeting_name
                        
    def get_layout(self):        
        return html.Div(f'hello {self.greeting_name}!')
 
greeting_component = GreetingComponent(greeting_name='Oscar')
wapp = WeaverletApp(root_component=greeting_component)
wapp.app.run(port=8089)