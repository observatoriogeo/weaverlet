from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet.base import SignalOutput, SignalTrigger, WeaverletComponent, WeaverletApp, Identifier
from weaverlet.components import SignalComponent


class SignalTriggerComponent(WeaverletComponent):

    trigger_button_id = Identifier()
    label_p_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signal_component = SignalComponent()

    def get_layout(self):
        return html.Div(
            [
                self.signal_component(),  # child component
                html.Button('Click to trigger signal',
                            id=self.trigger_button_id),
                html.P(id=self.label_p_id)
            ]
        )

    def register_callbacks(self, app):

        @app.callback(
            SignalOutput(self.signal_component),
            Trigger(self.trigger_button_id, 'n_clicks')
        )
        def button_click():
            return {}

        @app.callback(
            Output(self.label_p_id, 'children'),
            SignalTrigger(self.signal_component)
        )
        def label_update():
            return 'Signal triggered!'

 
signal_trigger_component = SignalTriggerComponent()
   
wapp = WeaverletApp(root_component=signal_trigger_component)
wapp.app.run_server(port=8089)
