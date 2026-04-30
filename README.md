<p align="center">
  <img src="FullLogo_Transparent_NoBuffer.png" width="375" height="275" alt="Weaverlet" title="Weaverlet">
</p>

<p align="center">
  <b>OOP for Plotly Dash — make your dashboards composable.</b>
</p>

<p align="center">
  Vanilla Dash and Dash Pages give you primitives, not encapsulation: callbacks live globally, IDs are strings you manage by hand, and the same widget can't be dropped into two apps without surgery. Weaverlet packages layout + callbacks + state into reusable Python classes, with auto-unique IDs, typed inter-component signals, and a <code>keep_mounted</code> router that preserves WebGL state across navigation.
</p>

<p align="center">
  <a href="https://pypi.org/project/weaverlet/"><img src="https://img.shields.io/pypi/v/weaverlet.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/weaverlet/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"></a>
</p>

---

Weaverlet, developed by the [Observatorio Metropolitano CentroGeo](https://observatoriogeo.mx), turns a [Plotly Dash](https://dash.plotly.com/) app into a hierarchy of reusable Python classes. Each `WeaverletComponent` owns its own layout, callbacks, and identifiers; you compose them into a tree, hand the root to `WeaverletApp`, and ship.

It's aimed at:

- **Data scientists** whose dashboard has outgrown a single file and needs structure.
- **Dash developers** who want true component reuse instead of copy-paste between apps.
- **React-style developers** looking for the same class-based component paradigm, server-side, in pure Python.

## What Weaverlet adds on top of vanilla Dash

- **Class-based encapsulation** — layout, callbacks, state, and IDs live together in one class. Instantiate it twice for two independent copies that don't step on each other.
- **Auto-unique IDs** — the `Identifier()` descriptor generates a Dash-unique ID per instance. No more managing string IDs by hand or hitting `DuplicateIdError` when reusing a widget.
- **Signal-based events** — `SignalComponent` + `SignalInput`/`SignalOutput`/`SignalTrigger` replace ad-hoc `dcc.Store` + manual callback wiring as the canonical inter-component event bus.
- **State-preserving routing** *(new in 0.3)* — `SimpleRouterComponent(keep_mounted=True)` keeps every route mounted and toggles CSS, so WebGL canvases (dash-leaflet maps, dash-sylvereye graphs, Plotly WebGL) and React state (`n_clicks`, selections, scroll position) survive navigation.
- **Session-based auth routing** — `AuthRouterComponent` gates routes via `flask.session` out of the box.
- **Shared context** — one dict propagates to every component in the DAG; no prop-drilling, no globals.

## Weaverlet vs Dash Pages

[Dash Pages](https://dash.plotly.com/urls) (built into Dash 2.5+) and Weaverlet both solve "multi-page Dash" but at different levels of abstraction. Pages is a *routing convention* — drop a file in `pages/`, register it, get a route. Weaverlet is a *component framework* — write classes, compose them, navigate without losing state.

| Capability | Dash Pages | Weaverlet |
|---|---|---|
| Built-in to Dash | ✓ (Dash ≥ 2.5) | One `pip install` |
| Routing source | Filesystem (`pages/*.py`) | Programmatic `routes` dict, computed at runtime |
| Path templating (`/users/<id>`) | ✓ | Via `pathname` / `search` parsing |
| Page-level encapsulation | One module per page | Reusable component classes; same class can power N routes |
| Cross-page widget reuse | Imports + manual callback wiring | Instantiate the same class anywhere; auto-unique IDs |
| Inter-component events | `dcc.Store` + global callbacks | `SignalComponent` typed events |
| **State across navigation** | Unmount + remount on every route change | `keep_mounted=True` preserves React + WebGL state |
| Auth gating | DIY | `AuthRouterComponent` + Flask sessions |
| Auto-discovered nav menu | ✓ (`dash.page_registry`) | Build it yourself |

**Reach for Dash Pages when** your dashboard is content-heavy, each page is roughly independent, you want filesystem-driven routing, and you don't need to preserve state across navigation. It's the simpler tool and ships with Dash.

**Reach for Weaverlet when** you have shared widget logic across pages, when WebGL components (maps, network graphs, 3D plots) shouldn't reset on navigation, when you want typed inter-component events instead of `dcc.Store` plumbing, or when your dashboard has grown past the "one file per page" model and needs proper encapsulation.

The two aren't mutually exclusive — Weaverlet apps can coexist alongside a Pages-based site in the same Dash deployment if that fits your migration path.

## What's new in 0.3.0

Released April 2026 — full notes in [CHANGELOG.md](CHANGELOG.md).

- **Dash 4.x** support; Python ≥ 3.12; dependency pins relaxed (Flask / werkzeug now resolved transitively, no longer hard-pinned).
- **`SimpleRouterComponent(keep_mounted=True, preserve_path="/...")`** for state preservation across route changes.
- **Top-level imports** — `from weaverlet import WeaverletComponent, ...` works directly; no need to drill into `weaverlet.base` / `weaverlet.components`.
- **Permissive `get_layout` signatures** — components declare any subset of `(pathname, hash, href, search, user, protected_route)` and the router passes only what's declared.
- **`DashProxy` under the hood** so `dash_extensions.javascript.assign()`, `Serverside(...)` return wrappers, and `group=` multi-output callbacks all work without extra wiring.
- **`assets_folder` auto-resolves** to the user's main script directory — no manual asset path setup needed.
- **60-test pytest suite**; build via `pyproject.toml` + hatchling.
- **`jupyter-dash`** moved to an optional extra (`pip install weaverlet[jupyter]`).

## Install

```bash
pip install weaverlet
```

(or `uv add weaverlet` if you're on uv.)

Optional extras:

| Extra | Pulls in | Use when |
|---|---|---|
| `weaverlet[examples]` | `dash-bootstrap-components`, `dash-mantine-components` | Running the bundled examples 11–14 |
| `weaverlet[jupyter]` | `dash[jupyter]` | Constructing `WeaverletApp(jupyter_mode=True)` |
| `weaverlet[dev]` | `pytest`, `pytest-playwright` | Hacking on Weaverlet itself |

## Quick start

A single-page app that echoes user input:

```python
from weaverlet import WeaverletComponent, WeaverletApp, Identifier
from dash_extensions.enrich import Input, Output
from dash import html, dcc


class EchoComponent(WeaverletComponent):
    text_input_id = Identifier()
    echo_div_id = Identifier()

    def get_layout(self):
        return html.Div([
            dcc.Input(id=self.text_input_id, type="text"),
            html.Div(id=self.echo_div_id),
        ])

    def register_callbacks(self, app):
        @app.callback(Output(self.echo_div_id, "children"),
                      Input(self.text_input_id, "value"))
        def echo(text_value):
            return text_value or ""


WeaverletApp(root_component=EchoComponent()).app.run()
```

A multipage app with WebGL-safe state preservation:

```python
from weaverlet import (
    WeaverletComponent, WeaverletApp, SimpleRouterComponent,
)
from dash import html


class HomePage(WeaverletComponent):
    def get_layout(self):
        return html.Div("Home — your dash-leaflet map goes here.")


class AboutPage(WeaverletComponent):
    def get_layout(self):
        return html.Div("About — switch back to Home; the map's zoom survives.")


class NotFound(WeaverletComponent):
    def get_layout(self):
        return html.Div("404")


router = SimpleRouterComponent(
    routes={"/": HomePage(), "/about": AboutPage()},
    not_found_page_component=NotFound(),
    keep_mounted=True,        # keep all routes mounted; toggle CSS only
    preserve_path="/",        # which route owns the document flow (default: first)
)
WeaverletApp(root_component=router).app.run()
```

> ⚠️ When `keep_mounted=True`, every entry in `routes` must map to a *distinct* component instance. Aliasing two paths to the same instance would mount that instance's `Identifier`-bearing layout twice and trigger `DuplicateIdError`. With the default `keep_mounted=False`, aliasing is fine.

## Examples

The [`examples/`](examples) folder has 14 self-contained scripts, ordered by complexity:

| # | File | Demonstrates |
|--:|---|---|
| 01 | [`01_helloworld_app.py`](examples/01_helloworld_app.py) | Minimal layout-only component |
| 02 | [`02_echo_app.py`](examples/02_echo_app.py) | Layout + callbacks + `Identifier` |
| 03 | [`03_greeting_app.py`](examples/03_greeting_app.py) | Constructor-injected state |
| 04 | [`04_router_app.py`](examples/04_router_app.py) | Multipage with `SimpleRouterComponent` |
| 05 | [`05_auth_router_app.py`](examples/05_auth_router_app.py) | Session-protected routes via `AuthRouterComponent` |
| 06 | [`06_redirect_app.py`](examples/06_redirect_app.py) | Programmatic redirect from a callback |
| 07 | [`07_signal_input.py`](examples/07_signal_input.py) | Signals carrying a payload |
| 08 | [`08_signal_trigger.py`](examples/08_signal_trigger.py) | Edge-only triggers |
| 09 | [`09_signal_chain_app.py`](examples/09_signal_chain_app.py) | Chained signal pipeline |
| 10 | [`10_div_signal_trigger_app.py`](examples/10_div_signal_trigger_app.py) | Signal-driven `<div>` updates |
| 11 | [`11_dbc_app.py`](examples/11_dbc_app.py) | Single-page Weaverlet + Dash Bootstrap |
| 12 | [`12_dbc_multipage_app.py`](examples/12_dbc_multipage_app.py) | Multipage with DBC navbar |
| 13 | [`13_dbc_modal_app.py`](examples/13_dbc_modal_app.py) | DBC modal triggered by signals |
| 14 | [`14_dmc_multipage_app.py`](examples/14_dmc_multipage_app.py) | Dash Mantine + AppShell + `keep_mounted` state preservation |

## Compatibility

| | |
|---|---|
| Python | ≥ 3.12 |
| Dash | ≥ 4.1.0, < 5.0.0 |
| dash-extensions | ≥ 1.0.0, < 3.0.0 (1.x and 2.x both supported) |

## For LLM coding assistants

Weaverlet ships a [`ReadMe.LLM.md`](ReadMe.LLM.md) following the [ReadMe.LLM methodology](https://readmellm.github.io/) — rules, context, 14 worked examples, API signatures, and patterns specifically formatted for LLMs like Claude, GPT, and Codex. To use it from another project, drop one of these URLs into your prompt or have your assistant fetch it:

- **Latest:** [`https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@main/ReadMe.LLM.md`](https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@main/ReadMe.LLM.md)
- **Pinned to v0.3.0:** [`https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@v0.3.0/ReadMe.LLM.md`](https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@v0.3.0/ReadMe.LLM.md)

There's also an [`llms.txt`](llms.txt) at the repo root following the [llmstxt.org](https://llmstxt.org/) convention — a short index that tools like Cursor and Claude Code can auto-discover.

## Contributing & support

- Bug reports and feature requests: [GitHub issues](https://github.com/observatoriogeo/weaverlet/issues).
- Tests: `pip install -e ".[dev]"` then `pytest` (60 tests, ~1 second).
- Migrating from 0.2.x? See [CHANGELOG.md](CHANGELOG.md) — most code keeps working unchanged; the main gotcha is `app.run_server()` → `app.run()` (Dash 4 removed the old name).

## License

Weaverlet is open-source software [licensed under the MIT license](LICENSE).
