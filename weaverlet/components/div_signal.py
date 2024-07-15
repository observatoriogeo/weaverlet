# pyright: reportMissingImports=false

import dash_html_components as html
from ..base import WeaverletComponent, Identifier, DEFAULT_COMPONENT_NAME


class DivSignalComponent(WeaverletComponent):

    signal_id = Identifier()
    signal_group_id = Identifier()
    signal_attr = 'children'
    signal_default_retval = {}

    def __init__(self, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.set_name(name)

    def get_layout(self):
        layout = \
            html.Div(id=self.signal_id, children='')
        return layout

    def register_callbacks(self, app):
        pass
