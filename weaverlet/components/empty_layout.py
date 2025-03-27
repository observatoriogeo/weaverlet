# pyright: reportMissingImports=false

from dash import html
from ..base import WeaverletComponent, Identifier, DEFAULT_COMPONENT_NAME


class EmptyLayoutComponent(WeaverletComponent):

    _empty_div_id = Identifier()
    
    def __init__(self, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.set_name(name)

    def get_layout(self):
        layout = \
            html.Div(id=self._empty_div_id)
        return layout    
