import random
from dash import html
from dash_extensions.enrich import Output, Input
from weaverlet.base import SignalOutput, SignalInput, WeaverletComponent, WeaverletApp, Identifier
from weaverlet.components import SignalComponent


class SignalInputComponent(WeaverletComponent):

    trigger_button_id = Identifier()
    label_p_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signal_component = SignalComponent()

    def get_layout(self):
        return html.Div(
            [
                self.signal_component(),  # child component
                html.Button('Click to trigger signal with input',
                            id=self.trigger_button_id),
                html.P(id=self.label_p_id)
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            SignalOutput(self.signal_component),
            Input(self.trigger_button_id, 'n_clicks')
        )
        def button_click(n_clicks):
            return {'n_clicks': n_clicks, 'random_number': random.random()}

        @app.callback(
            Output(self.label_p_id, 'children'),
            SignalInput(self.signal_component)
        )
        def label_update(signal_input):
            return f'Signal triggered! Signal input: {signal_input}'

 
signal_trigger_component = SignalInputComponent()
   
wapp = WeaverletApp(root_component=signal_trigger_component)
wapp.app.run_server(port=8089)
