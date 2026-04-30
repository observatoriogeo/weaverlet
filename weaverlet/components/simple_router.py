from __future__ import annotations

from dash import dcc, html
from dash_extensions.enrich import Input, Output, State

from ..base import (
    DEFAULT_COMPONENT_NAME,
    ComponentsDict,
    Identifier,
    RouterComponent,
    WeaverletComponent,
    WeaverletException,
    _call_with_router_kwargs,
)
from ..logger import logger

# Style sets for keep_mounted mode. The preserve_path wrapper stays mounted
# with visibility:hidden when not active (so its WebGL canvas survives a
# route change); other route wrappers use display:none which is cleaner for
# the document flow.
_VISIBLE_STYLE = {
    "position": "relative",
    "visibility": "visible",
    "pointerEvents": "auto",
    "zIndex": 1,
}
_HIDDEN_STYLE_PRESERVE = {
    "position": "relative",
    "visibility": "hidden",
    "pointerEvents": "none",
}
_HIDDEN_STYLE_DISPLAY_NONE = {"display": "none"}
_VISIBLE_STYLE_OVERLAY = {
    # Non-preserve route, when visible: overlay on top of the preserve
    # wrapper (which still reserves flow). Avoids stacked heights.
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "zIndex": 2,
}


class SimpleRoutes(ComponentsDict):
    def get_components(self):
        return list(self.values())


class SimpleRouterComponent(RouterComponent):

    content_id = Identifier()
    url_id = Identifier()

    def __init__(
        self,
        routes: dict,
        not_found_page_component: WeaverletComponent,
        use_prefix: bool = False,
        keep_mounted: bool = False,
        preserve_path: str | None = None,
        name: str = DEFAULT_COMPONENT_NAME,
    ) -> None:
        super().__init__()
        self.use_prefix = use_prefix
        self.routes = SimpleRoutes(routes)
        self.not_found_page_component = not_found_page_component
        self.keep_mounted = keep_mounted

        if keep_mounted and preserve_path is None and routes:
            preserve_path = next(iter(routes))
        self.preserve_path = preserve_path

        # Per-route wrapper IDs (only used in keep_mounted mode).
        self._route_wrapper_ids: dict[str, str] = {}
        for path in self.routes.keys():
            slug = path.strip("/").replace("/", "_") or "root"
            self._route_wrapper_ids[path] = (
                f"SimpleRouter_wrap_{slug}_{id(self):x}"
            )

        # If not_found is the same instance as some route, share its wrapper
        # to avoid DuplicateIdError.
        self._not_found_shared_path: str | None = None
        for path, comp in self.routes.items():
            if comp is not_found_page_component:
                self._not_found_shared_path = path
                break
        self._not_found_wrapper_id: str | None = (
            None
            if self._not_found_shared_path is not None
            else f"SimpleRouter_wrap_notfound_{id(self):x}"
        )

        self.set_name(name)

    def get_children(self):
        children = list(self.routes.values())
        if self.not_found_page_component not in children:
            children.append(self.not_found_page_component)
        return children

    def _resolve_prefix(self) -> str:
        if not self.use_prefix:
            return ""
        ctx = self.get_context()
        if "prefix" not in ctx:
            raise WeaverletException(
                'use_prefix = True but the "prefix" key was not found in the context.'
            )
        return ctx["prefix"]

    def get_layout(self):
        if self.keep_mounted:
            prefix = self._resolve_prefix()
            children = [dcc.Location(id=self.url_id, refresh=False)]
            for path, comp in self.routes.items():
                wrapper_id = self._route_wrapper_ids[path]
                init_style = (
                    {"position": "relative"}
                    if path == self.preserve_path
                    else _HIDDEN_STYLE_DISPLAY_NONE
                )
                children.append(
                    html.Div(
                        _call_with_router_kwargs(
                            comp,
                            pathname=f"{prefix}{path}",
                            hash="",
                            href="",
                            search="",
                        ),
                        id=wrapper_id,
                        style=init_style,
                    )
                )
            if self._not_found_wrapper_id is not None:
                children.append(
                    html.Div(
                        _call_with_router_kwargs(
                            self.not_found_page_component,
                            pathname="",
                            hash="",
                            href="",
                            search="",
                        ),
                        id=self._not_found_wrapper_id,
                        style=_HIDDEN_STYLE_DISPLAY_NONE,
                    )
                )
            return html.Div(children, style={"position": "relative"})
        else:
            return html.Div(
                [
                    dcc.Location(id=self.url_id, refresh=False),
                    html.Div(id=self.content_id),
                ]
            )

    def register_callbacks(self, app):
        if self.keep_mounted:
            outputs = [
                Output(self._route_wrapper_ids[p], "style") for p in self.routes
            ]
            if self._not_found_wrapper_id is not None:
                outputs.append(Output(self._not_found_wrapper_id, "style"))

            @app.callback(outputs, Input(self.url_id, "pathname"))
            def toggle_views(pathname):
                pathname = pathname or "/"
                prefix = self._resolve_prefix()
                # Match against prefixed routes.
                visible_path: str | None = None
                for route in self.routes.keys():
                    if pathname == f"{prefix}{route}":
                        visible_path = route
                        break
                if visible_path is None and self._not_found_shared_path is not None:
                    visible_path = self._not_found_shared_path

                def style_for(p: str):
                    if p == visible_path:
                        return (
                            _VISIBLE_STYLE
                            if p == self.preserve_path
                            else _VISIBLE_STYLE_OVERLAY
                        )
                    if p == self.preserve_path:
                        return _HIDDEN_STYLE_PRESERVE
                    return _HIDDEN_STYLE_DISPLAY_NONE

                styles = [style_for(p) for p in self.routes]
                if self._not_found_wrapper_id is not None:
                    styles.append(
                        _VISIBLE_STYLE
                        if visible_path is None
                        else _HIDDEN_STYLE_DISPLAY_NONE
                    )
                return styles
            return

        @app.callback(
            Output(self.content_id, "children"),
            Input(self.url_id, "pathname"),
            State(self.url_id, "hash"),
            State(self.url_id, "href"),
            State(self.url_id, "search"),
        )
        def route_callback(pathname, hash, href, search):
            prefix = self._resolve_prefix()
            for route in self.routes.keys():
                if pathname == f"{prefix}{route}":
                    logger.info(
                        f"[SimpleRouterComponent.register_callbacks.route] route {route} matched"
                    )
                    return _call_with_router_kwargs(
                        self.routes[route],
                        pathname=pathname,
                        hash=hash,
                        href=href,
                        search=search,
                    )
            logger.info(
                "[SimpleRouterComponent.register_callbacks.route] route not found"
            )
            return _call_with_router_kwargs(
                self.not_found_page_component,
                pathname=pathname,
                hash=hash,
                href=href,
                search=search,
            )
