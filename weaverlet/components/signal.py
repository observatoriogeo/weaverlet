# pyright: reportMissingImports=false

from dash import dcc
from ..base import WeaverletComponent, Identifier, DEFAULT_COMPONENT_NAME


class SignalComponent(WeaverletComponent):

    signal_id = Identifier()
    signal_group_id = Identifier()
    signal_attr = 'data'
    signal_default_retval = {}

    def __init__(self, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.set_name(name)

    def get_layout(self):
        layout = \
            dcc.Store(id=self.signal_id, data={})
        return layout

    def register_callbacks(self, app):
        pass
