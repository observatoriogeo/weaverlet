# pyright: reportMissingImports=false

import dash
from weaverlet.components.signal import SignalComponent
from dash import dcc, html
from ..base import WeaverletComponent, Identifier, DEFAULT_COMPONENT_NAME, WeaverletException
from dash_extensions.enrich import Input, Output, State, Trigger
from ..logger import logger

class StoreComponentOp():
    STORE = 'store'
    MERGE = 'merge'
    CLEAN = 'clean'

class StoreComponent(WeaverletComponent):

    store_attr = 'data'

    # external ids
    store_id = Identifier()    

    # internal ids
    _store_group_id = Identifier()
    
    def __init__(self, name=DEFAULT_COMPONENT_NAME):
        super().__init__()
        self.set_name(name)

        # internal signals
        self._clean_signal = SignalComponent(name='clean_signal')
        self._store_signal = SignalComponent(name='store_signal')
        self._merge_signal = SignalComponent(name='merge_signal')

        # input signals
        self.input_signal  = SignalComponent(name='input_signal')

    def get_layout(self):
        layout = \
            html.Div(
                [
                    self._clean_signal(),
                    self._store_signal(),
                    self._merge_signal(),
                    self.input_signal(),                    
                    dcc.Store(id=self.store_id, data={})
                ]
            )
            
        return layout

    def register_callbacks(self, app):
        
        @app.callback(
            Output(self._store_signal.signal_id, self._store_signal.signal_attr),
            Output(self._merge_signal.signal_id, self._merge_signal.signal_attr),
            Output(self._clean_signal.signal_id, self._clean_signal.signal_attr),
            Input(self.input_signal.signal_id, self.input_signal.signal_attr),            
        )
        def input_signal(input_signal_data):
            logger.debug(f'[StoreComponent.register_callbacks.input_signal] ! input_signal_data = {input_signal_data}') 
            if input_signal_data['op'] == StoreComponentOp.STORE:
                return input_signal_data['data'], dash.no_update, dash.no_update
            elif input_signal_data['op'] == StoreComponentOp.MERGE:
                return dash.no_update, input_signal_data['data'], dash.no_update
            elif input_signal_data['op'] == StoreComponentOp.CLEAN:
                return dash.no_update, dash.no_update, self._clean_signal.signal_default_retval
            else:
                raise WeaverletException(f'Unkown store operation: {input_signal_data["op"]}')

        @app.callback(
            Output(self.store_id, self.store_attr),
            Input(self._store_signal.signal_id, self._store_signal.signal_attr),
            group = self._store_group_id
        )
        def store_signal(_store_signal_input):
            logger.debug(f'[StoreComponent.register_callbacks.store_signal] ! _store_signal_input = {_store_signal_input}') 
            return _store_signal_input

        @app.callback(
            Output(self.store_id, self.store_attr),
            Input(self._merge_signal.signal_id, self._merge_signal.signal_attr),
            State(self.store_id, self.store_attr),
            group = self._store_group_id
        )
        def merge_signal(new_data, current_data):
            logger.debug(f'[StoreComponent.register_callbacks.merge_signal] ! input: new_data = {new_data}, current_data = {current_data}')            
            merged_data = {**current_data, **new_data}   
            logger.debug(f'[StoreComponent.register_callbacks.merge_signal] storing {merged_data}')
            return merged_data

        @app.callback(
            Output(self.store_id, self.store_attr),
            Trigger(self._clean_signal.signal_id, self._clean_signal.signal_attr),
            group = self._store_group_id
        )
        def clean_signal():        
            logger.debug(f'[StoreComponent.register_callbacks.clean_signal] !')    
            return {}