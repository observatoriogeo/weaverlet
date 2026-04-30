from __future__ import annotations

from dash import dcc, html
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Input, Output, State
from flask import session

from ..base import (
    DEFAULT_COMPONENT_NAME,
    ComponentsDict,
    Identifier,
    RouterComponent,
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


class AuthRoutes(ComponentsDict):
    def get_components(self):
        return [value['component'] for value in self.values()]


class AuthRouterComponent(RouterComponent):

    content_id = Identifier()
    url_id = Identifier()

    def __init__(
        self,
        routes,
        not_found_page_component,
        user_session_key='user',
        login_route='/login',
        use_prefix=False,
        keep_mounted: bool = False,
        preserve_path: str | None = None,
        name=DEFAULT_COMPONENT_NAME,
    ):
        super().__init__()
        self.use_prefix = use_prefix
        self.routes = AuthRoutes(routes)
        self.not_found_page_component = not_found_page_component
        self.user_session_key = user_session_key
        self.login_route = login_route
        self.keep_mounted = keep_mounted

        # --- aliasing detection (only matters in keep_mounted mode, but
        # computing it unconditionally keeps the bookkeeping consistent) ---
        self._canonical_path: dict[int, str] = {}
        for path, entry in self.routes.items():
            self._canonical_path.setdefault(id(entry['component']), path)

        self._unique_paths: list[str] = []
        seen_ids: set[int] = set()
        for path, entry in self.routes.items():
            cid = id(entry['component'])
            if cid not in seen_ids:
                seen_ids.add(cid)
                self._unique_paths.append(path)

        if keep_mounted and preserve_path is None and routes:
            preserve_path = self._unique_paths[0] if self._unique_paths else None
        if preserve_path is not None and preserve_path in self.routes:
            preserve_path = self._canonical_path[
                id(self.routes[preserve_path]['component'])
            ]
        self.preserve_path = preserve_path

        # Wrapper IDs: every path resolves to its canonical wrapper id.
        self._route_wrapper_ids: dict[str, str] = {}
        for path, entry in self.routes.items():
            comp = entry['component']
            canonical = self._canonical_path[id(comp)]
            if canonical not in self._route_wrapper_ids:
                slug = canonical.strip("/").replace("/", "_") or "root"
                self._route_wrapper_ids[canonical] = (
                    f"AuthRouter_wrap_{slug}_{id(self):x}"
                )
            self._route_wrapper_ids[path] = self._route_wrapper_ids[canonical]

        # Shared not_found wrapper (matches SimpleRouter's behavior).
        self._not_found_shared_path: str | None = None
        for path, entry in self.routes.items():
            if entry['component'] is not_found_page_component:
                self._not_found_shared_path = self._canonical_path[
                    id(entry['component'])
                ]
                break
        self._not_found_wrapper_id: str | None = (
            None
            if self._not_found_shared_path is not None
            else f"AuthRouter_wrap_notfound_{id(self):x}"
        )

        self.set_name(name)

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
            for path in self._unique_paths:
                comp = self.routes[path]['component']
                wrapper_id = self._route_wrapper_ids[path]
                init_style = (
                    {"position": "relative"}
                    if path == self.preserve_path
                    else _HIDDEN_STYLE_DISPLAY_NONE
                )
                # Pre-render with placeholder values for `user` and
                # `protected_route`. With keep_mounted, components should
                # NOT capture these from get_layout — they get baked in
                # once and never refresh. For live values, read
                # `flask.session[user_session_key]` from inside callbacks.
                # The login wrapper's children are re-rendered separately
                # below so the legacy `protected_route`-via-get_layout
                # pattern keeps working.
                children.append(
                    html.Div(
                        _call_with_router_kwargs(
                            comp,
                            pathname=f"{prefix}{path}",
                            hash="",
                            href="",
                            search="",
                            user=None,
                            protected_route="",
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
            return html.Div([
                dcc.Location(id=self.url_id, refresh=False),
                html.Div(id=self.content_id),
            ])

    def register_callbacks(self, app):
        if self.keep_mounted:
            self._register_keep_mounted_callbacks(app)
            return

        @app.callback(
            Output(self.content_id, 'children'),
            Input(self.url_id, 'pathname'),
            State(self.url_id, 'hash'),
            State(self.url_id, 'href'),
            State(self.url_id, 'search'),
        )
        def route_callback(pathname, hash, href, search):
            prefix = self._resolve_prefix()

            for route in self.routes.keys():
                if pathname == f'{prefix}{route}':
                    logger.info(
                        f'[AuthRouterComponent.register_callbacks.route] route {route} matched'
                    )
                    if self.routes[route]['login_required']:
                        if self.user_session_key in session:
                            user = session[self.user_session_key]
                            return _call_with_router_kwargs(
                                self.routes[route]['component'],
                                pathname=pathname, hash=hash, href=href, search=search, user=user,
                            )
                        else:
                            return _call_with_router_kwargs(
                                self.routes[self.login_route]['component'],
                                pathname=pathname, hash=hash, href=href, search=search,
                                protected_route=f'{prefix}{route}',
                            )
                    else:
                        return _call_with_router_kwargs(
                            self.routes[route]['component'],
                            pathname=pathname, hash=hash, href=href, search=search,
                        )

            logger.info('[AuthRouterComponent.register_callbacks.route] route not found')
            return _call_with_router_kwargs(
                self.not_found_page_component, pathname=pathname,
            )

    def _register_keep_mounted_callbacks(self, app):
        outputs = [
            Output(self._route_wrapper_ids[p], "style") for p in self._unique_paths
        ]
        if self._not_found_wrapper_id is not None:
            outputs.append(Output(self._not_found_wrapper_id, "style"))

        @app.callback(outputs, Input(self.url_id, "pathname"))
        def toggle_views(pathname):
            pathname = pathname or "/"
            prefix = self._resolve_prefix()

            visible_canonical: str | None = None
            for route, entry in self.routes.items():
                if pathname == f"{prefix}{route}":
                    if entry['login_required'] and self.user_session_key not in session:
                        # Redirect to the login route's wrapper.
                        login_comp = self.routes[self.login_route]['component']
                        visible_canonical = self._canonical_path[id(login_comp)]
                    else:
                        visible_canonical = self._canonical_path[id(entry['component'])]
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

        # Re-render the login wrapper's children when redirecting from a
        # protected route, so LoginPage.get_layout receives the actual
        # `protected_route` it should redirect to after auth. This loses
        # any LoginPage React state on each redirect cycle — acceptable
        # for one-shot login flows, and the right trade-off vs leaving
        # `protected_route` stuck at the empty pre-render placeholder.
        login_comp = self.routes[self.login_route]['component']
        login_canonical = self._canonical_path[id(login_comp)]
        login_wrapper_id = self._route_wrapper_ids[login_canonical]

        @app.callback(
            Output(login_wrapper_id, "children"),
            Input(self.url_id, "pathname"),
            prevent_initial_call=True,
        )
        def update_login_for_redirect(pathname):
            pathname = pathname or "/"
            prefix = self._resolve_prefix()
            for route, entry in self.routes.items():
                full = f"{prefix}{route}"
                if pathname == full and entry.get('login_required'):
                    if self.user_session_key not in session:
                        return _call_with_router_kwargs(
                            self.routes[self.login_route]['component'],
                            pathname=pathname,
                            hash="",
                            href="",
                            search="",
                            protected_route=full,
                        )
            raise PreventUpdate

        # Dynamic 404 — same shape as SimpleRouter.
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
