# pyright: reportMissingImports=false
# TODO: use signals instead of Store

from dash import dcc, html
from dash_extensions.enrich import Input, Output, State
from ..base import WeaverletComponent, Identifier, WeaverletException, DEFAULT_COMPONENT_NAME


class RedirectComponent(WeaverletComponent):

    redirect_clientside_callback = \
        """
        function(href, prefix) {
            const use_prefix_url = prefix.prefix + href.url;
            window.open(use_prefix_url, href.target);
            return '';
        }
        """

    href_id = Identifier()
    _dummy_div_id = Identifier()
    href_attr = 'data'
    _prefix_id = Identifier()

    def __init__(self, name=DEFAULT_COMPONENT_NAME, use_prefix=False):
        super().__init__()
        self.set_name(name)
        self.use_prefix = use_prefix

    def get_layout(self):

        if self.use_prefix:
            if 'prefix' in self.get_context():
                prefix_data = {'prefix': self.get_context()['prefix']}
            else:
                raise WeaverletException(
                    'use_prefix = True but the "prefix" key was not found in the context.')
        else:
            prefix_data = {'prefix': ''}

        return \
            html.Div(
                [
                    html.Div(id=self._dummy_div_id, style={'display': 'none'}),
                    dcc.Store(id=self._prefix_id, data=prefix_data),
                    dcc.Store(id=self.href_id)
                ]
            )

    def register_callbacks(self, app):

        app.clientside_callback(
            self.redirect_clientside_callback,
            Output(self._dummy_div_id, 'children'),
            Input(self.href_id, self.href_attr),
            State(self._prefix_id, 'data')
        )
