from abc import ABC, abstractmethod
import string
import random
from collections import OrderedDict
from .logger import logger
from dash_extensions.enrich import Input, Output, Trigger, State
from dash_extensions.enrich import Dash

COMPONENT_IDS_LENGTH = 7
DEFAULT_COMPONENT_NAME = 'unnamed'


def SignalInput(signal):
    return Input(signal.signal_id, signal.signal_attr)

def SignalOutput(signal):
    return Output(signal.signal_id, signal.signal_attr)

def SignalTrigger(signal):
    return Trigger(signal.signal_id, signal.signal_attr)

def SignalState(signal):
    return State(signal.signal_id, signal.signal_attr)

def SignalGroup(signal):
    return signal.signal_group_id



class WeaverletException(Exception):
    pass


class DetatchedComponentRef(object):
    '''
    Wrapper class to make a references to a component without including it in the Weaverlet Component Tree (WCT).
    Useful for preventing component loops in the WCT.
    '''
    def __init__(self, component):
        self.component = component    
    def __getattr__(self,attr):
        return getattr(self.component, attr)


class WeaverletComponent(ABC):

    def __init__(self, name=DEFAULT_COMPONENT_NAME):        
        self._hex_id = self._get_random_hex_string(length=COMPONENT_IDS_LENGTH)
        self._name = name
        self._set_id(self._hex_id, self._name)
        self._context = {}

    def initialize(self):
        pass

    def register_callbacks(self, app):
        pass
        
    def get_children(self):
        return self._children

    def get_page_root(self):
        return self._page_root

    def get_parent(self):
        return self._parent

    def _set_id(self, hex_id, name):
        self._id = hex_id + '-' + name

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name
        self._set_id(self._hex_id, self._name)

    def get_context(self):
        return self._context

    @abstractmethod
    def get_layout(self):
        pass 

    def __call__(self, *args, **kwargs):
        """
        logger.debug(
            f'[{type(self).__name__}.__call__] page root = {self.get_page_root()}')
        logger.debug(
            f'[{type(self).__name__}.__call__] parent = {self.get_parent()}')
        logger.debug(
            f'[{type(self).__name__}.__call__] self = {self}')
        """
        return self.get_layout(*args, **kwargs)

    @staticmethod
    def _get_random_hex_string(length):
        return ''.join(random.choice(string.hexdigits.lower()) for _ in range(length))

    def __str__(self):
        address = hex(id(self))
        return f'<{self.get_id()} of {type(self).__name__} at {address}>'


class RouterComponent(WeaverletComponent):
    """
    just a label class.
    """

    def __init__(self):
        super().__init__()


class Identifier():

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not '_id' in instance.__dict__:
            raise TypeError(
                'Component instance is missing the "_id" instance attribute.')
        return instance._id + '-' + self.name

    def __set__(self, instance, value):
        raise TypeError(
            'Cannot manually assign a value to an Identifier.')


class ComponentsDict(dict, ABC):
    @abstractmethod
    def get_components():
        pass


class ComponentsList(list, ABC):
    @abstractmethod
    def get_components():
        pass


class ComponentsOrderedDict(OrderedDict, ABC):
    @abstractmethod
    def get_components():
        pass

class WeaverletApp():

    def __init__(self, root_component, context={}, prevent_initial_callbacks=True, suppress_callback_exceptions=True, **kwargs):
        self.root_component = root_component
                
        self.app = Dash(**kwargs)        
        
        self.context = context        
                
        # configure Dash app
        self.app.config.prevent_initial_callbacks = prevent_initial_callbacks
        self.app.config.suppress_callback_exceptions = suppress_callback_exceptions

        # set the children of each component in the component tree
        logger.info(
            '[WeaverletApp.__init__] finding children in components ...')
        self._find_children_recursive(component=self.root_component, level=0)

        # set the page root of each component in the component tree
        logger.info(
            '[WeaverletApp.__init__] setting page roots in components ...')
        self.root_component._page_root = None
        if isinstance(self.root_component, RouterComponent):
            # each child here (including not_found_component and the login component if present) is a different page root
            for child in self.root_component.get_children():
                child._page_root = None
                logger.info(
                    f'[WeaverletApp.__init__] setting page root = {child} in components ...')
                for grand_child in child.get_children():
                    self._set_page_root_recursive(
                        component=grand_child, page_root=child, level=0)
        else:
            for child in self.root_component.get_children():
                self._set_page_root_recursive(
                    component=child, page_root=self.root_component, level=0)

        # set the parent of each component in the component tree
        logger.info(
            '[WeaverletApp.__init__] setting the parents in components ...')
        self.root_component._parent = None
        if isinstance(self.root_component, RouterComponent):
            for child in self.root_component.get_children():
                child._parent = None
                logger.info(
                    f'[WeaverletApp.__init__] setting parent = {child} in children components ...')
                for grand_child in child.get_children():
                    self._set_parent_recursive(
                        component=grand_child, parent=child, level=0)
        else:
            for child in self.root_component.get_children():
                self._set_parent_recursive(
                    component=child, parent=self.root_component, level=0)

        # set the context of each component in the component tree
        logger.info(
            '[WeaverletApp.__init__] setting the context in components ...')        
        self._set_context_recursive(component=self.root_component, context=self.context, level=0)

        # run initialize() for all componentes
        logger.info(
            '[WeaverletApp.__init__] running initialize() in components ...')        
        self._run_initialize_recursive(component=self.root_component, level=0)

        # set the Dash app layout
        logger.info(
            '[WeaverletApp.__init__] setting Dash app layout ...')        
        self.app.layout = self.root_component()
        #app.validation_layout = self.root_component()

        # run the register_callback method of each component in the component tree
        logger.info(
            '[WeaverletApp.__init__] registering callbacks in components ...')
        self._register_callbacks_recursive(
            self.app, component=self.root_component, level=0)

    @staticmethod
    def _find_children(component):
        children = []
        for attr_name in dir(component):
            attr = getattr(component, attr_name)
            if isinstance(attr, ComponentsList):
                children += attr.get_components()
            elif isinstance(attr, ComponentsDict):
                children += attr.get_components()
            elif isinstance(attr, ComponentsOrderedDict):
                children += attr.get_components()
            elif isinstance(attr, WeaverletComponent):
                children.append(attr)
            
        return children

    def _find_children_recursive(self, component, level):
        log_string = '[WeaverletApp._find_children_recursive] ' + \
            '\t'*level + f'Setting children for {component}'
        logger.info(log_string)

        component._children = self._find_children(component)
        for child in component.get_children():
            self._find_children_recursive(child, level+1)

    def _set_page_root_recursive(self, component, page_root, level):
        log_string = '[WeaverletApp._set_page_root_recursive] ' + \
            '\t'*level + f'Setting page root for {component}'
        logger.info(log_string)

        component._page_root = page_root
        for child in component.get_children():
            self._set_page_root_recursive(child, page_root, level+1)

    def _set_parent_recursive(self, component, parent, level):
        log_string = '[WeaverletApp._set_parent_recursive] ' + \
            '\t'*level + f'Setting the parent for {component}'
        logger.info(log_string)

        component._parent = parent
        for child in component.get_children():
            self._set_parent_recursive(child, component, level+1)

    def _register_callbacks_recursive(self, app, component, level):

        log_string = '[WeaverletApp._register_callbacks_recursive] ' + \
            '\t'*level + f'Registering callbacks for {component}'
        logger.info(log_string)

        component.register_callbacks(app)
        for child in component.get_children():
            self._register_callbacks_recursive(app, child, level+1)

    def _set_context_recursive(self, component, context, level):

        log_string = '[WeaverletApp._set_context_recursive] ' + \
            '\t'*level + f'Setting context for {component}'
        logger.info(log_string)

        component._context = context
        for child in component.get_children():
            self._set_context_recursive(child, context, level+1)

    def _run_initialize_recursive(self, component, level):

        log_string = '[WeaverletApp._run_initialize_recursive] ' + \
            '\t'*level + f'Running initialize() for {component}'
        logger.info(log_string)
        
        component.initialize()

        for child in component.get_children():
            self._run_initialize_recursive(child, level+1)