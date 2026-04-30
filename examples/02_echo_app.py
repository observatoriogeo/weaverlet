from weaverlet.base import WeaverletComponent, WeaverletApp, Identifier
from dash.dependencies import Input, Output
from dash import html, dcc


class EchoComponent(WeaverletComponent):

    text_input_id = Identifier()    
    echo_div_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self):
        return html.Div([
            dcc.Input(id=self.text_input_id,
                      type='text'),
            html.Div(id=self.echo_div_id)
        ])

    def register_callbacks(self, app):
        @app.callback(
            Output(self.echo_div_id, 'children'),
            Input(self.text_input_id, 'value')
        )
        def update_echo_div(text_value):
            return f'{text_value}'


greeting_component = EchoComponent()
wapp = WeaverletApp(root_component=greeting_component)
wapp.app.run(port=8089)
 