# Changelog

## 0.3.1 — 2026-04-30

Patch release. Fixes the `weaverlet[jupyter]` extra and `WeaverletApp(jupyter_mode=True)` path, both of which were broken on arrival in 0.3.0:

- `pyproject.toml` declared `jupyter = ["dash[jupyter]>=4.1"]`, but **Dash 4.x has no `jupyter` extra** (declared extras: `async`, `ci`, `dev`, `testing`, `celery`, `diskcache`, `compress`, `cloud`, `ag-grid`). Installing `weaverlet[jupyter]` was a silent no-op.
- `WeaverletApp(jupyter_mode=True)` did `from jupyter_dash import JupyterDash`, but the standalone `jupyter_dash` package was archived in 2022 and Dash 4 absorbed Jupyter integration into core (as `dash.jupyter_dash`, exposed as a singleton instance). The import always failed, even after installing the (non-existent) extra.

### Migration

Dash 4 ships built-in Jupyter support that doesn't need a separate `JupyterDash` class anymore. Construct `WeaverletApp` normally and pass `jupyter_mode='inline'` (or `'tab'` / `'external'`) to `.app.run()`:

```python
wapp = WeaverletApp(root_component=...)
wapp.app.run(jupyter_mode='inline')
```

No extras required.

### Breaking changes (vs 0.3.0)

- **`weaverlet[jupyter]` extra removed.** It never installed anything useful; `pip install weaverlet[jupyter]` will now error out, but the migration path above doesn't need any extra at all.
- **`WeaverletApp(jupyter_mode=True)` raises `TypeError`** with a migration message pointing at `app.run(jupyter_mode=...)`. The default `jupyter_mode=False` (or omitting it) is unchanged.

---

## 0.3.0 — 2026-04-29

First major refresh since 0.2.0 (2024). Modernizes the dependency stack and
adds WebGL-safe routing while keeping the public API backwards-compatible
where it matters.

### Breaking changes

- **Drop Python < 3.12.** The package no longer installs on older interpreters.
- **Drop hard pins** on Flask, werkzeug, dash, dash_extensions, jupyter-dash.
  The triple-pin in 0.2.0 made Weaverlet unresolvable in any modern environment.
  Dependencies are now declared as open ranges (`dash>=4.1.0,<5.0.0`,
  `dash-extensions>=1.0.0,<3.0.0`); Flask/werkzeug are resolved transitively.
- **`jupyter-dash` is now optional.** Install with `pip install weaverlet[jupyter]`
  if you pass `WeaverletApp(..., jupyter_mode=True)`. Otherwise importing
  `weaverlet` no longer pulls in `jupyter-dash`.
- **Build system switched** from `setup.py` (setuptools) to `pyproject.toml`
  (PEP 621 / hatchling). Existing install commands (`pip install weaverlet`,
  `pip install -e .`) continue to work.
- **`Identifier` id format changed** from `{hex_id}-{name}-{attr}` to
  `{ClassName}_{attr}_{hex_id_of_instance}`. IDs are opaque and only used
  symbolically as `self.<identifier>`, so user code is unaffected — but any
  code that compared the *string form* of an id will break.
- **`get_page_root()` removed.** The old per-router tree walk that assigned
  page roots to each route's children was unused and added complexity. If you
  relied on it, file an issue.
- **`StoreComponent` requires the dash-extensions multiplexer/group** to
  register multiple callbacks against the same `Output`. This worked in 0.2
  via dash-extensions 0.0.65; in 1.x/2.x it is provided by `DashProxy` (which
  Weaverlet now uses by default). No action required if you use
  `WeaverletApp`; raw Dash users need to pick up `DashProxy` themselves.

### New features

- **`SimpleRouterComponent(keep_mounted=True, preserve_path=...)`** for
  WebGL-safe multipage. When `keep_mounted=True`, every route is rendered at
  startup and the router toggles `style` instead of unmounting — preserving
  the canvas state of `dash-sylvereye` (PixiJS), `dash-leaflet`, and Plotly
  WebGL backends across navigation. The `preserve_path` route uses
  `visibility:hidden` (canvas survives even WebGL-strict libraries); other
  routes use `display:none`. Default is `keep_mounted=False` (unchanged
  behavior — drop-in replacement for 0.2 routers).
- **`AuthRouterComponent(keep_mounted=True, preserve_path=...)`** — same
  state-preservation feature for the auth-gated router. Routes are
  pre-rendered with placeholder values (`user=None`, `protected_route=""`);
  a separate callback re-renders the login wrapper's children with the
  actual `protected_route` whenever an unauthenticated visit hits a
  login-required route, so the legacy login-redirect pattern keeps working
  in keep_mounted mode. Apps that need the live `user` value should read
  `flask.session[user_session_key]` from inside their callbacks rather
  than capturing `user` from `get_layout`.
- **Aliasing under `keep_mounted=True`**. `routes={"/": page_a, "/home": page_a}`
  no longer raises `DuplicateIdError`; both paths share a single canonical
  wrapper. The same generalization underlies the shared-`not_found` handling.
- **Dynamic 404**. When `keep_mounted=True` and the URL doesn't match any
  route, the not-found wrapper's children are re-rendered with the live
  pathname — so a `f"Page {pathname} not found"` template displays the
  actual URL the user typed instead of the empty-string placeholder used
  at startup.
- **WebGL-safe shared `not_found`.** If `not_found_page_component` is the
  same instance as one of the routes, the router reuses that route's wrapper
  instead of mounting a duplicate (no more `DuplicateIdError`).
- **`WeaverletApp` uses `dash_extensions.enrich.DashProxy`** under the hood,
  which keeps `dash_extensions.javascript.assign()` functions registered in
  `window.dashExtensions.default.*`. This unblocks `dash-leaflet` style
  handlers and similar uses without any extra wiring.
- **`assets_folder` auto-resolves** to the directory of the user's main script,
  so `dashExtensions_default.js` (and any user-authored asset) is served by
  Dash without configuration. After resolving, `WeaverletApp` also re-dumps
  the `dash_extensions.javascript.assign()` namespace into that directory —
  important because `assign()` writes to a CWD-relative path by default,
  which doesn't match Dash's served path when the script is run from a
  different working directory (common with `uv run`, IDEs, and test
  runners). Without this re-dump, `dash-leaflet` style handlers and similar
  uses fail with "No match for function0". Override with
  `WeaverletApp(..., assets_folder="...")` if needed.
- **`WeaverletApp` exposes `title`, `external_stylesheets`, `assets_folder`**
  as named keyword arguments. Other Dash kwargs continue to flow through via
  `**dash_kwargs`.
- **Routed `get_layout()` is permissive about its signature.** Components no
  longer have to declare `get_layout(self, pathname, hash, href, search)` to
  be routable — declare just the kwargs you need (`(self)`, `(self, pathname)`,
  `(self, pathname, hash, href, search, user)`, etc.) and the router will
  pass only what your signature accepts. Implemented via
  `weaverlet.base._call_with_router_kwargs`.
- **`weaverlet.__version__`** exposes the version string.
- **Top-level re-exports** — `from weaverlet import WeaverletComponent,
  Identifier, WeaverletApp, SimpleRouterComponent, ...` now works directly,
  no need to drill into `weaverlet.base` / `weaverlet.components`.

### Internal

- Component children are now discovered by introspecting `__dict__` on each
  walk (with cycle detection via `visited`), instead of pre-computing
  `_children` once and walking it four times. The `Components{List,Dict,
  OrderedDict}` ABCs are still recognized for collection-style children.
- All component modules migrated from `import dash_html_components as html` /
  `import dash_core_components as dcc` to `from dash import html, dcc`.
- `ServersideOutput` (dash-extensions 0.0.65) is gone; the helper
  `ServersideSignalOutput()` now returns a plain `Output` and callers wrap
  the *return value* with `Serverside(...)` — the dash-extensions 1.x/2.x
  pattern. `Serverside` is re-exported from `weaverlet`.
- `DetatchedComponentRef` renamed to `DetachedComponentRef` (typo fix);
  the original name is preserved as an alias.

### Compat

The following public names continue to import and behave the same way as in
0.2.0: `WeaverletComponent`, `Identifier`, `WeaverletApp`, `RouterComponent`,
`SimpleRouterComponent`, `AuthRouterComponent`, `StoreComponent`,
`StoreComponentOp`, `SignalComponent`, `DivSignalComponent`,
`EmptyLayoutComponent`, `RedirectComponent`, `WeaverletException`,
`SignalInput`, `SignalOutput`, `SignalTrigger`, `SignalState`,
`SignalGroup`, `ServersideSignalOutput`, `ComponentsDict`,
`ComponentsList`, `ComponentsOrderedDict`, `DetatchedComponentRef`,
`DEFAULT_COMPONENT_NAME`.
