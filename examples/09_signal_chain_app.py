import random
from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet.base import SignalOutput, SignalInput, WeaverletComponent, WeaverletApp, Identifier
from weaverlet.components import SignalComponent


class SignalChainComponent(WeaverletComponent):

    trigger_button_id = Identifier()
    label_p_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signal_1_component = SignalComponent()
        self.signal_2_component = SignalComponent()
        self.signal_3_component = SignalComponent()

    def get_layout(self):
        return html.Div(
            [
                self.signal_1_component(),
                self.signal_2_component(),
                self.signal_3_component(),
                html.Button('Click to trigger signal chain',
                            id=self.trigger_button_id),
                html.P(id=self.label_p_id)
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            SignalOutput(self.signal_1_component),
            Trigger(self.trigger_button_id, 'n_clicks')
        )
        def button_click():
            return {}

        @app.callback(
            SignalOutput(self.signal_2_component),
            SignalInput(self.signal_1_component)
        )
        def signal_1(signal_input):
            signal_input['random_number_1'] = random.random()
            return signal_input

        @app.callback(
            SignalOutput(self.signal_3_component),
            SignalInput(self.signal_2_component)
        )
        def signal_2(signal_input):
            signal_input['random_number_2'] = random.random()
            return signal_input

        @app.callback(
            Output(self.label_p_id, 'children'),
            SignalInput(self.signal_3_component)
        )
        def signal_3(signal_input):
            return f'Signal chain triggered! data: {signal_input}'


signal_trigger_component = SignalChainComponent()

wapp = WeaverletApp(root_component=signal_trigger_component)
wapp.app.run_server(port=8089)
