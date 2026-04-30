from __future__ import annotations

import inspect
import os
import sys
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any

from dash_extensions.enrich import (
    DashProxy,
    Input,
    Output,
    Serverside,
    State,
    Trigger,
)

from .logger import logger

DEFAULT_COMPONENT_NAME = "unnamed"
COMPONENT_IDS_LENGTH = 7


def SignalInput(signal):
    return Input(signal.signal_id, signal.signal_attr)


def SignalOutput(signal):
    return Output(signal.signal_id, signal.signal_attr)


def ServersideSignalOutput(signal):
    # In dash-extensions 2.x, Serverside is applied to the return value
    # of the callback (Serverside(value)), not to the Output declaration.
    # Kept for backwards-compat with code that expected a special Output;
    # callers should now wrap the returned data with Serverside(...).
    return Output(signal.signal_id, signal.signal_attr)


def SignalTrigger(signal):
    return Trigger(signal.signal_id, signal.signal_attr)


def SignalState(signal):
    return State(signal.signal_id, signal.signal_attr)


def SignalGroup(signal):
    return signal.signal_group_id


class WeaverletException(Exception):
    pass


class Identifier:
    """Descriptor that yields a Dash-unique id per (instance, attribute).

    The id is computed lazily on first access and cached on the instance,
    so it does not depend on any specific `__init__` ordering.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        cache = instance.__dict__.setdefault("_wlt_ids", {})
        if self.name not in cache:
            cache[self.name] = (
                f"{instance.__class__.__name__}_{self.name}_{id(instance):x}"
            )
        return cache[self.name]

    def __set__(self, instance, value):
        raise TypeError("Cannot manually assign a value to an Identifier.")


class WeaverletComponent(ABC):
    """Base component — encapsulates layout, callbacks, IDs, shared context."""

    def __init__(self, name: str = DEFAULT_COMPONENT_NAME) -> None:
        self.__dict__.setdefault("_wlt_ids", {})
        self._wlt_name = name
        self._wlt_parent: "WeaverletComponent | None" = None
        self._wlt_context: dict[str, Any] = {}

    # -- Lifecycle hooks -------------------------------------------------
    def initialize(self) -> None:
        pass

    def register_callbacks(self, app) -> None:
        pass

    # -- Identity / hierarchy --------------------------------------------
    def get_name(self) -> str:
        return self._wlt_name

    def set_name(self, name: str) -> None:
        self._wlt_name = name

    def get_parent(self) -> "WeaverletComponent | None":
        return self._wlt_parent

    def get_context(self) -> dict[str, Any]:
        return self._wlt_context

    def get_children(self) -> list["WeaverletComponent"]:
        children: list[WeaverletComponent] = []
        for v in self.__dict__.values():
            if isinstance(v, WeaverletComponent):
                children.append(v)
            elif isinstance(v, (ComponentsList, ComponentsDict, ComponentsOrderedDict)):
                children.extend(v.get_components())
        return children

    def get_id(self) -> str:
        return f"{self.__class__.__name__}_{id(self):x}"

    # -- Contract --------------------------------------------------------
    @abstractmethod
    def get_layout(self, *args, **kwargs):
        ...

    def __call__(self, *args, **kwargs):
        return self.get_layout(*args, **kwargs)

    def __str__(self) -> str:
        return f"<{self.get_id()} of {type(self).__name__} at {hex(id(self))}>"

    # -- DAG walker ------------------------------------------------------
    def _wlt_walk(self):
        visited = {id(self)}
        stack = [self]
        while stack:
            comp = stack.pop()
            yield comp
            for child in comp.get_children():
                if id(child) in visited:
                    continue
                visited.add(id(child))
                child._wlt_parent = comp
                stack.append(child)


class RouterComponent(WeaverletComponent):
    """Marker class — subclasses of this are routers (used by isinstance checks)."""

    def __init__(self, name: str = DEFAULT_COMPONENT_NAME) -> None:
        super().__init__(name)


class DetachedComponentRef:
    """Wrap a component so it is NOT discovered as a child by the DAG walker.

    Useful when component A needs a reference to component B that is already
    attached elsewhere in the tree, to avoid cycles.
    """

    def __init__(self, component: WeaverletComponent) -> None:
        self.component = component

    def __getattr__(self, attr):
        return getattr(self.component, attr)


# Backwards-compat alias for the original (typo'd) name.
DetatchedComponentRef = DetachedComponentRef


class ComponentsDict(dict, ABC):
    @abstractmethod
    def get_components(self):
        ...


class ComponentsList(list, ABC):
    @abstractmethod
    def get_components(self):
        ...


class ComponentsOrderedDict(OrderedDict, ABC):
    @abstractmethod
    def get_components(self):
        ...


def _call_with_router_kwargs(comp: WeaverletComponent, **router_kwargs):
    """Call comp.get_layout passing only the router kwargs it declares."""
    sig = inspect.signature(comp.get_layout)
    accepted = {k: v for k, v in router_kwargs.items() if k in sig.parameters}
    return comp.get_layout(**accepted)


def _safe_get_layout(comp: WeaverletComponent):
    """Call comp.get_layout, providing sensible placeholders for any
    router-style kwargs the signature declares without defaults."""
    sig = inspect.signature(comp.get_layout)
    kwargs: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        if name == "pathname":
            kwargs[name] = "/"
        elif name in ("hash", "href", "search", "protected_route"):
            kwargs[name] = ""
        elif name == "user":
            kwargs[name] = None
    return comp.get_layout(**kwargs)


class WeaverletApp:
    """Orchestrator — receives the root component, propagates context,
    registers callbacks, and produces a Dash app."""

    def __init__(
        self,
        root_component: WeaverletComponent,
        context: dict | None = None,
        title: str | None = None,
        external_stylesheets: list | None = None,
        suppress_callback_exceptions: bool = True,
        prevent_initial_callbacks: bool = True,
        assets_folder: str | None = None,
        jupyter_mode: bool = False,
        **dash_kwargs,
    ) -> None:
        self.root_component = root_component
        self.root = root_component  # alias
        self.context = context if context is not None else {}

        if assets_folder is None:
            main_module = sys.modules.get("__main__")
            if main_module is not None and hasattr(main_module, "__file__"):
                assets_folder = os.path.join(
                    os.path.dirname(os.path.abspath(main_module.__file__)),
                    "assets",
                )
            else:
                assets_folder = os.path.abspath("assets")

        kwargs: dict[str, Any] = {
            "suppress_callback_exceptions": suppress_callback_exceptions,
            "prevent_initial_callbacks": prevent_initial_callbacks,
            "assets_folder": assets_folder,
        }
        if title is not None:
            kwargs["title"] = title
        if external_stylesheets is not None:
            kwargs["external_stylesheets"] = external_stylesheets
        kwargs.update(dash_kwargs)

        if jupyter_mode:
            raise TypeError(
                "WeaverletApp(jupyter_mode=True) was removed in 0.3.1. "
                "Dash 4 has built-in Jupyter support that does not require "
                "a separate JupyterDash class — construct WeaverletApp "
                "normally and pass jupyter_mode='inline' (or 'tab' / "
                "'external') to .app.run() instead:\n"
                "\n"
                "    wapp = WeaverletApp(root_component=...)\n"
                "    wapp.app.run(jupyter_mode='inline')\n"
                "\n"
                "No extras are required; the integration ships with Dash."
            )
        self.app = DashProxy(__name__, **kwargs)

        # `dash_extensions.javascript.assign(...)` writes its JS to
        # `./assets/dashExtensions_default.js` — relative to CWD, not to
        # the script. When the user runs from a different CWD (e.g. from
        # an IDE, a uv subprocess, or a test runner), Dash ends up serving
        # an empty assets dir and downstream libraries (dash-leaflet style
        # handlers, etc.) fail with "No match for function0". Re-dump the
        # assigned namespace into the resolved assets_folder so the JS
        # actually lives where Dash will look for it.
        try:
            from dash_extensions.javascript import _default_name_space
            if _default_name_space.f_map:
                _default_name_space.dump(assets_folder)
        except ImportError:
            pass

        # Walk the tree once: propagate context and run initialize().
        logger.info("[WeaverletApp.__init__] propagating context and initializing components ...")
        for comp in self.root_component._wlt_walk():
            comp._wlt_context = self.context
            comp.initialize()

        # Set the layout (with permissive placeholder injection for the root).
        logger.info("[WeaverletApp.__init__] setting Dash app layout ...")
        self.app.layout = _safe_get_layout(self.root_component)

        # Register callbacks.
        logger.info("[WeaverletApp.__init__] registering callbacks in components ...")
        for comp in self.root_component._wlt_walk():
            comp.register_callbacks(self.app)
