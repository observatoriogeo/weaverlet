from __future__ import annotations

from dash import dcc, html
from dash.exceptions import PreventUpdate
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
from ._styles import (
    HIDDEN_STYLE_DISPLAY_NONE as _HIDDEN_STYLE_DISPLAY_NONE,
    HIDDEN_STYLE_PRESERVE as _HIDDEN_STYLE_PRESERVE,
    VISIBLE_STYLE as _VISIBLE_STYLE,
    VISIBLE_STYLE_OVERLAY as _VISIBLE_STYLE_OVERLAY,
)


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

        # Detect aliasing: when several paths point at the same component
        # instance (e.g. {"/": page_a, "/a": page_a}), pick the first path
        # encountered as the *canonical* one and have aliased paths share
        # its wrapper. This avoids DuplicateIdError when keep_mounted=True
        # would otherwise mount the same Identifier-bearing layout twice.
        self._canonical_path: dict[int, str] = {}
        for path, comp in self.routes.items():
            self._canonical_path.setdefault(id(comp), path)

        # Canonical paths in iteration order — the unique instances we
        # actually need to render once each.
        self._unique_paths: list[str] = []
        seen_ids: set[int] = set()
        for path, comp in self.routes.items():
            if id(comp) not in seen_ids:
                seen_ids.add(id(comp))
                self._unique_paths.append(path)

        # Default preserve_path = first declared path; if the caller passed
        # an aliased path, normalize to its canonical so wrapper lookups
        # always hit the canonical entry.
        if keep_mounted and preserve_path is None and routes:
            preserve_path = self._unique_paths[0] if self._unique_paths else None
        if preserve_path is not None and preserve_path in self.routes:
            preserve_path = self._canonical_path[id(self.routes[preserve_path])]
        self.preserve_path = preserve_path

        # Wrapper IDs: every path resolves to its canonical wrapper id.
        self._route_wrapper_ids: dict[str, str] = {}
        for path, comp in self.routes.items():
            canonical = self._canonical_path[id(comp)]
            if canonical not in self._route_wrapper_ids:
                slug = canonical.strip("/").replace("/", "_") or "root"
                self._route_wrapper_ids[canonical] = (
                    f"SimpleRouter_wrap_{slug}_{id(self):x}"
                )
            self._route_wrapper_ids[path] = self._route_wrapper_ids[canonical]

        # If not_found is the same instance as some route, share its
        # canonical wrapper instead of mounting a duplicate.
        self._not_found_shared_path: str | None = None
        for path, comp in self.routes.items():
            if comp is not_found_page_component:
                self._not_found_shared_path = self._canonical_path[id(comp)]
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
            # Render only one wrapper per *unique* component instance.
            # Aliased paths share a single wrapper, so the same instance
            # never mounts twice.
            for path in self._unique_paths:
                comp = self.routes[path]
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
            # One Output per *unique* wrapper (aliased paths share wrappers).
            outputs = [
                Output(self._route_wrapper_ids[p], "style") for p in self._unique_paths
            ]
            if self._not_found_wrapper_id is not None:
                outputs.append(Output(self._not_found_wrapper_id, "style"))

            @app.callback(outputs, Input(self.url_id, "pathname"))
            def toggle_views(pathname):
                pathname = pathname or "/"
                prefix = self._resolve_prefix()
                # Any matching path (including aliases) maps to the same
                # canonical wrapper.
                visible_canonical: str | None = None
                for route in self.routes.keys():
                    if pathname == f"{prefix}{route}":
                        visible_canonical = self._canonical_path[id(self.routes[route])]
                        break
                if visible_canonical is None and self._not_found_shared_path is not None:
                    visible_canonical = self._not_found_shared_path

                def style_for(p: str):
                    if p == visible_canonical:
                        return (
                            _VISIBLE_STYLE
                            if p == self.preserve_path
                            else _VISIBLE_STYLE_OVERLAY
                        )
                    if p == self.preserve_path:
                        return _HIDDEN_STYLE_PRESERVE
                    return _HIDDEN_STYLE_DISPLAY_NONE

                styles = [style_for(p) for p in self._unique_paths]
                if self._not_found_wrapper_id is not None:
                    styles.append(
                        _VISIBLE_STYLE
                        if visible_canonical is None
                        else _HIDDEN_STYLE_DISPLAY_NONE
                    )
                return styles

            # Dynamic 404: when the not_found component is its own
            # instance (not shared with a route), re-render its wrapper's
            # children on every unmatched-pathname change so messages like
            # f"Page {pathname} not found" reflect the actual URL. Matched
            # paths skip this via PreventUpdate (the not_found wrapper is
            # hidden on those, anyway).
            if self._not_found_wrapper_id is not None:
                @app.callback(
                    Output(self._not_found_wrapper_id, "children"),
                    Input(self.url_id, "pathname"),
                    prevent_initial_call=True,
                )
                def update_not_found_content(pathname):
                    prefix = self._resolve_prefix()
                    for route in self.routes.keys():
                        if pathname == f"{prefix}{route}":
                            raise PreventUpdate
                    return _call_with_router_kwargs(
                        self.not_found_page_component,
                        pathname=pathname or "",
                        hash="",
                        href="",
                        search="",
                    )
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
