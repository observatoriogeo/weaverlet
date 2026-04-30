# 🧵 Weaverlet — ReadMe.LLM (Part 1 : Rules — Extended)

## <Rules>

These rules define exactly how a large language model (e.g., GPT‑5, Claude Code, or Codex)
should read, reason about, and generate code for the **Weaverlet** framework. They are
maximally specific to avoid ambiguity and to ensure deterministic behavior.

**This document targets Weaverlet 0.3.0** (Python ≥ 3.12, Dash ≥ 4.1.0,
dash‑extensions ≥ 1.0). For 0.2.0 see the previous revision.

---

### 1 | Primary Principle
Always reason as a **Weaverlet developer**, not as a generic Dash developer.
All code must respect Weaverlet's *component-oriented*, *server‑side*, and *DAG‑based* architecture.

**You MUST:**
- Encapsulate UI and callbacks inside subclasses of `WeaverletComponent`.
- Compose apps by nesting components and calling children in layouts.
- Use Weaverlet routers, signals, and helpers instead of ad‑hoc Dash patterns.

**You MUST NOT:**
- Create raw `dash.Dash()` apps manually.
- Hardcode DOM IDs as strings.
- Implement cross‑component communication with ad‑hoc `dcc.Store` + vanilla callbacks.

---

### 2 | Imports and Namespaces
As of 0.3.0, the entire public API is re‑exported from the top‑level package.
**Prefer** `from weaverlet import ...`; the legacy submodule paths still work and
remain backwards‑compatible.

```python
# Preferred (v0.3+): single top-level import surface
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    SimpleRouterComponent, AuthRouterComponent,
    RedirectComponent, SignalComponent, DivSignalComponent,
    StoreComponent, StoreComponentOp, EmptyLayoutComponent,
    SignalInput, SignalOutput, SignalTrigger, SignalState, SignalGroup,
    ServersideSignalOutput, Serverside,
    DetachedComponentRef, WeaverletException,
)

# Legacy (still supported): from weaverlet.base / weaverlet.components
# from weaverlet.base import WeaverletComponent, WeaverletApp, Identifier, ...
# from weaverlet.components import SimpleRouterComponent, AuthRouterComponent, ...

# Allowed UI / I/O imports
from dash import html, dcc
from dash_extensions.enrich import Input, Output, State, Trigger
```

**Notes:**
- `Serverside` (a value wrapper applied to callback return values) replaces the
  old `ServersideOutput` (an Output type). The helper `ServersideSignalOutput()`
  now returns a plain `Output`; wrap the **return value** with `Serverside(...)`
  for serverside caching.
- `DetachedComponentRef` is the canonical name; `DetatchedComponentRef` (the
  original 0.2.0 spelling) is kept as a backwards‑compatible alias.
- Never rely on implicit imports or wildcard imports.

---

### 3 | Application Lifecycle
Every Weaverlet app follows this exact sequence:

1. **Define components** → subclass `WeaverletComponent`.
2. **Instantiate root** → `root = <Component>(...)`.
3. **Create app** → `wapp = WeaverletApp(root_component=root, context={...})`.
4. **Run / export**:
   - Interactive run → `wapp.app.run(port=8080)` (Dash 4 removed `app.run_server`).
   - WSGI export → `application = wapp.app.server`.

**Forbidden:** `app = dash.Dash(...)` or calling `app.layout = ...` outside Weaverlet.

**Internal note:** `WeaverletApp` constructs a `dash_extensions.enrich.DashProxy`
(not a plain `Dash`) so multi‑output `group=` callbacks (used by `StoreComponent`)
and `dash_extensions.javascript.assign()` registrations work without manual wiring.

---

### 4 | Component Contract
Each subclass of `WeaverletComponent` must obey the following contract.

| Method | Requirement | Notes |
|:--|:--|:--|
| `get_layout(self, *args, **kwargs)` | **Required** | Returns a Dash layout. May accept any subset of router‑injected kwargs (`pathname`, `hash`, `href`, `search`, `user`, `protected_route`); the router passes only what your signature declares. |
| `register_callbacks(self, app)` | Optional | Define component‑local callbacks here; must reference `self.<Identifier>` IDs. |
| `initialize(self)` | Optional | Prepare internal state or resources before layout binding. Runs **before** any `register_callbacks`. |
| `__call__(...)` | Required behavior | Must proxy to `get_layout(...)` and return a *layout instance* when used inside parent layouts. |

**Permissive signatures (v0.3):** routed components no longer have to declare
`(self, pathname, hash, href, search)`. Declare just what you need:

```python
class A(WeaverletComponent):
    def get_layout(self): ...                                  # zero router args
class B(WeaverletComponent):
    def get_layout(self, pathname): ...                        # only pathname
class C(WeaverletComponent):
    def get_layout(self, pathname, hash, href, search): ...    # full set
class D(WeaverletComponent):
    def get_layout(self, pathname, hash, href, search, user): ...  # AuthRouter pages
```

The router introspects the signature and passes only matching kwargs.

**Identifiers:** Every element ID must be declared as a class‑level `Identifier()` descriptor.
- Good: `submit_btn = Identifier()` → `html.Button(id=self.submit_btn, ...)`
- Bad: `html.Button(id="submit")`

The string form of an Identifier in 0.3+ is opaque (`{ClassName}_{attr}_{hex(id)}`).
Never compare or pattern‑match on it.

---

### 5 | Composition and Nesting
1. **Own your children:** declare child components as attributes in `__init__`.
   ```python
   class Parent(WeaverletComponent):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.child = ChildComponent()
   ```
2. **Call children in layout:** insert child layouts using `self.child(...)` inside `get_layout(...)`.
3. **No direct DOM mutation:** modify UI via callbacks updating Dash props only.
4. **DAG semantics:** the parent→child graph is a Weaverlet Component DAG walked by `WeaverletApp` to wire context, relationships, and callbacks. Cycles are broken by `DetachedComponentRef`.

---

### 6 | Routing and Navigation
1. **Static/public multipage:** use `SimpleRouterComponent`.
2. **Auth‑protected routes:** use `AuthRouterComponent` with `{'login_required': True}` entries.
3. **Router requirements:**
   - `routes`: `path → component` **or** `path → {'component': component, 'login_required': bool}`
   - `not_found_page_component`: a `WeaverletComponent` instance for 404s.
4. **Prefixing:** when a router or redirect is initialized with `use_prefix=True`, the app **must** be created with `WeaverletApp(context={'prefix': '<prefix>'})`.
5. **Redirection:** add a `RedirectComponent()` to the layout; in callbacks return:
   ```python
   {'url': '/target', 'target': '_self'}
   ```
   to its `href_attr` via `Output(redirect.href_id, redirect.href_attr)`.

#### 6.a | `keep_mounted` (v0.3 hero feature)
`SimpleRouterComponent` accepts `keep_mounted` (default `False`) and `preserve_path` (default = first route).

| Mode | Behavior | Use when |
|:--|:--|:--|
| `keep_mounted=False` (legacy) | Route callback **replaces** `children` of the content `<div>` on each navigation. Components are unmounted/remounted. | Default for non‑WebGL apps; lightest footprint. |
| `keep_mounted=True` | Every route entry is rendered **at startup**. Navigation only toggles CSS `style` per wrapper. Components are never unmounted, so React state, WebGL canvases, and `n_clicks` survive route changes. | Apps with `dash-leaflet`, `dash-sylvereye`, Plotly WebGL backends, or any state you want to persist across navigation. |

The `preserve_path` route uses `visibility:hidden` when inactive (canvas survives even WebGL‑strict libraries); other routes use `display:none` (lighter, cleaner flow).

**Constraint when `keep_mounted=True`:** every `routes` entry must map to a **distinct component instance**. Aliasing two paths to the same instance (e.g. `{"/": page_a, "/a": page_a}`) duplicates that instance's `Identifier`‑bearing layout in the DOM and triggers `DuplicateIdError`. With `keep_mounted=False` aliasing is fine.

**Edge case the router handles:** if `not_found_page_component` is the same instance as one of the routes, the router reuses that route's wrapper instead of mounting a duplicate.

```python
SimpleRouterComponent(
    routes={"/": page_a, "/b": page_b},
    not_found_page_component=not_found,
    keep_mounted=True,
    preserve_path="/",   # default = first route
)
```

---

### 7 | Signals and Event Flow
Use Weaverlet **signals** for inter/intra‑component events and data passing.

| Intent | Use | Callback decoration | Return / Input |
|:--|:--|:--|:--|
| Emit payload | `SignalOutput(sig)` | `@app.callback(SignalOutput(sig), ...)` | Return a **dict payload** (or `{}` for edge‑only). |
| React to payload | `SignalInput(sig)` | `@app.callback(Output(...), SignalInput(sig))` | Receives payload dict as a function arg. |
| React to edge | `SignalTrigger(sig)` | `@app.callback(Output(...), SignalTrigger(sig))` | No payload arg; fires on edge. |
| Grouping | `SignalGroup(sig)` | Use in multi‑output/grouped scenarios | Returns group id for advanced wiring. |
| Serverside cache | `Serverside(value)` wrapper on **return** | Plain `Output(...)` | Caches on the server, sends a token to the client. |

**Stateful store:** prefer `StoreComponent` for shared state with explicit ops:
- `StoreComponentOp.STORE` (overwrite), `MERGE` (shallow merge), `CLEAN` (reset).

**Forbidden:** using bare `dcc.Store` for cross‑component messaging.

---

### 8 | Callbacks and Identifiers
1. Define callbacks **inside** `register_callbacks(self, app)` for the owning component.
2. Reference IDs via `self.<identifier>` only; never use string literals.
3. Close over `self` safely; do not mutate other components directly.
4. Use `dash_extensions.enrich` (`Input`, `Output`, `State`, `Trigger`, `Serverside`) — `WeaverletApp.app` is a `DashProxy`, which makes `group=` (multi‑output multiplex) and `Serverside(...)` available without extra setup.

---

### 9 | Context Propagation
- `WeaverletApp(context=...)` propagates a dict to every component.
- Components retrieve it via `self.get_context()`.
- **Common keys:**
  - `"prefix"`: required by routers/redirects when `use_prefix=True`.
  - `"user"`: set by auth flows; expected by `AuthRouterComponent` pages.

---

### 10 | Naming and File Conventions
| Element | Convention | Example |
|:--|:--|:--|
| Component classes | `PascalCase` | `LoginPageComponent` |
| Identifiers | `snake_case` | `login_button_id` |
| Routes | lowercase with slashes | `/`, `/login`, `/page_a` |
| Example files | `NN_name_app.py` | `01_helloworld_app.py`, `14_dmc_multipage_app.py` |

---

### 11 | Error Handling and Diagnostics
- If unsure about inputs/params, **ask the user** for the missing info.
- If a route is 404:
  - Check that the route exists in `routes` map.
  - Check `use_prefix` vs `context['prefix']`.
- If IDs "collide" (`DuplicateIdError`) or callbacks don't fire:
  - Ensure all IDs are declared via `Identifier()` and referenced via `self.<id>`.
  - Ensure `register_callbacks` was defined in the owning component.
  - **If `keep_mounted=True`:** check that no two `routes` entries map to the same component instance (see §6.a).
- If redirect does nothing:
  - Ensure a `RedirectComponent` is present in the layout.
  - Ensure the callback returns the dict to `href_attr` with a valid `target`.
- If a signal appears silent:
  - Ensure emit → `SignalOutput(sig)`, and receiver uses `SignalInput(sig)` or `SignalTrigger(sig)` accordingly.
- If `dash_extensions.javascript.assign()` produces "No match for function0":
  - Confirm that the user ran the app from a script with a real `__file__` so `WeaverletApp` could auto‑resolve `assets_folder`. Otherwise pass `WeaverletApp(..., assets_folder="...")` explicitly.

---

### 12 | Security and Sessions
- For `AuthRouterComponent`, rely on `flask.session` within callbacks to set and read the user key (default `'user'`).
- **Never** log sensitive session data.
- Expose WSGI via `wapp.app.server` when deploying behind a proper server (gunicorn, uWSGI, etc.).

---

### 13 | Performance and Reliability
- Use **composition** and **reusability** to avoid large, monolithic components.
- Prefer **small, single‑responsibility** components with tight interfaces.
- Wire **signal chains** rather than deeply nested conditional callbacks.
- Use `keep_mounted=True` only when state preservation is needed; the default `False` is lighter (one route in DOM at a time).
- Implement light **smoke tests** for key callbacks and routes when possible (see Pattern K).

---

### 14 | What to Ask the User
When information is missing or ambiguous, ask concise questions:
- Required pages/routes and which are protected?
- Expected signal flow (who emits, who listens)?
- Any `use_prefix` requirement or deployment path?
- Should `keep_mounted=True` be enabled (e.g. for WebGL pages or persistent state)?
- Desired port, title, and base styling (e.g., DBC/DMC theme)?

---

### 15 | Forbidden Patterns (Recap)
- Creating Dash apps directly (`dash.Dash()`).
- Hardcoded ID strings instead of `Identifier()` descriptors.
- Cross‑component state via ad‑hoc `dcc.Store` without Weaverlet signals/store.
- Callbacks defined outside `register_callbacks(self, app)` of the owning component.
- Direct DOM or component mutation outside of Dash properties.
- Using `app.run_server(...)` (removed in Dash 4 — use `app.run(...)`).
- Aliasing two `routes` keys to the same component instance when `keep_mounted=True`.

</Rules>

# 🧵 Weaverlet — ReadMe.LLM (Part 2 : Context)

## <Context>

### Purpose
Weaverlet is a **Python-only, server-side, component-driven framework** for building
multi-page and interactive dashboard applications using Dash, but without requiring any
JavaScript, HTML, or CSS templating. It abstracts Dash into a high-level, class-based system
that promotes composability, modularity, and clarity.

It allows developers — and by extension, large language models — to design web dashboards
as hierarchies of Python objects rather than raw Dash code. Each object, called a
**Weaverlet Component**, encapsulates its own layout, callbacks, and communication logic,
and can be composed with others to form complex applications.

**Version 0.3.0** modernized Weaverlet for the current Dash 4.x ecosystem and added
WebGL-safe state preservation across route changes via `keep_mounted=True` —
the framework's primary new capability for visualization-heavy dashboards.

---

### Core Design Philosophy

1. **Component-driven development (CDD):**
   - Every UI element or logical block is a subclass of `WeaverletComponent`.
   - Components encapsulate their internal layout, callbacks, and local identifiers.

2. **Directed Acyclic Graph (DAG) of Components:**
   - Components are arranged hierarchically, forming a DAG that represents relationships
     (parent, child, root) and signal dependencies.
   - The DAG is walked once by `WeaverletApp` to propagate context and register callbacks.
   - Cycles are explicitly broken by wrapping a back‑reference in `DetachedComponentRef`.

3. **Signal-based communication:**
   - Weaverlet introduces **Signal Components**, a formal mechanism to propagate events or
     data across components without relying on hardwired Dash inputs/outputs.
   - Signals can be used for triggering callbacks, chaining actions, and sharing state.

4. **Router abstraction:**
   - Weaverlet extends Dash to support **multi-page applications** through dedicated router
     components such as `SimpleRouterComponent` and `AuthRouterComponent`.
   - These map URL routes to Weaverlet components dynamically.
   - `SimpleRouterComponent(keep_mounted=True)` keeps every page mounted at all times,
     toggling CSS visibility instead of unmounting — this preserves WebGL canvas state and
     in‑component React state across navigation.

5. **Context propagation:**
   - Shared state (e.g., `user`, `prefix`, or configuration parameters) can be distributed to
     all components through the `WeaverletApp(context={...})` parameter.
   - Context allows routers, redirects, and child components to share configuration data
     without tight coupling.

6. **Integration with Dash ecosystem:**
   - Weaverlet 0.3.x targets **Dash ≥ 4.1** and **dash‑extensions ≥ 1.0** (with 2.x supported).
   - It remains compatible with Dash Bootstrap Components (DBC) and Dash Mantine Components (DMC).
   - `WeaverletApp` constructs a `DashProxy`, enabling `group=` multi‑output callbacks and
     `dash_extensions.javascript.assign()` registrations out of the box.

7. **Minimal boilerplate philosophy:**
   - Weaverlet eliminates repetitive callback wiring and manual ID handling.
   - Identifiers are automatically generated via the `Identifier()` descriptor, ensuring
     globally unique, collision‑free IDs across components.
   - Routed components declare only the URL kwargs they actually need; the router passes
     only what the signature accepts.

---

### Advantages for LLM-based Coding

For models like GPT-5 or Claude Code, Weaverlet provides:
- **Structured mental model:** each class corresponds to a conceptual UI unit.
- **Safe composition patterns:** eliminates most callback ID mismatches and manual wiring errors.
- **Predictable architecture:** apps always start with a root `WeaverletComponent` and a single `WeaverletApp`.
- **Learnable API surface:** all key behaviors come from ~10 core classes and decorators, all importable from the top‑level `weaverlet` package.

LLMs should leverage this structure to:
- Propose or generate new components by subclassing `WeaverletComponent`.
- Compose dashboards hierarchically.
- Reuse routers and signal components to link pages and trigger events.
- Default routers to `keep_mounted=False` unless the user mentions WebGL components or per‑page state preservation.

---

### Conceptual Overview

```
┌─────────────────────────┐
│ WeaverletApp            │
│  ├── context {...}      │
│  └── root_component ─────────────────────┐
└─────────────────────────┘                │
                                           ▼
                            ┌─────────────────────────┐
                            │ WeaverletComponent (root) │
                            │  ├── children[...]       │
                            │  ├── get_layout()        │
                            │  ├── register_callbacks()│
                            │  └── signals[...]        │
                            └─────────────────────────┘
                                           │
                                           ▼
                      ┌──────────────────────────┐
                      │ Nested Components        │
                      │ (Routers, Modals, etc.)  │
                      └──────────────────────────┘
```

---

### Weaverlet's Place in the Stack

| Layer | Role |
|:------|:-----|
| **Dash 4.x** | Low-level web framework (callbacks, layout rendering) |
| **dash_extensions.enrich** | DashProxy, Trigger, Serverside, group= multi-output |
| **Weaverlet Base** | Component abstraction layer (classes, IDs, DAG walker) |
| **Weaverlet Components** | Reusable higher-level modules (routers, signals, stores) |
| **App-level Code** | User or model-defined dashboards composed of Weaverlet components |

---

### Terminology Summary

| Term | Description |
|:-----|:-------------|
| **Weaverlet Component** | A subclass of `WeaverletComponent` encapsulating layout and logic. |
| **Identifier** | Descriptor ensuring unique Dash element IDs per component instance. |
| **Signal** | Mechanism for data or event propagation between components. |
| **Router** | Component managing URL-based navigation and page rendering. |
| **`keep_mounted`** | Router mode that keeps all routes in the DOM and toggles visibility, preserving state across navigation. |
| **Redirect** | Component performing client-side navigation after a callback. |
| **Context** | Shared state dictionary propagated to all components in the DAG. |
| **DAG** | Directed Acyclic Graph linking components hierarchically. |
| **Store Component** | Specialized component for persistent app-wide data operations. |
| **DetachedComponentRef** | Wrapper that hides a component reference from the DAG walker (cycle prevention). |

---

### Implementation Stack (Conceptual)

```
WeaverletApp (DashProxy under the hood)
  └── Root WeaverletComponent
        ├── SimpleRouterComponent / AuthRouterComponent
        │     ├── RedirectComponent
        │     ├── LoginPageComponent
        │     └── ProtectedPageComponent
        ├── SignalComponent
        ├── StoreComponent
        └── Dash UI primitives (html, dcc, dbc, dmc)
```

---

### What the LLM Must Understand

When generating Weaverlet code, you are operating in a **high-level, declarative space**.
The model must:
1. Understand each component as a reusable Python class.
2. Recognize the DAG relationship between components.
3. Prefer composition over imperative control flow.
4. Use signal communication for data exchange, not global variables.
5. Treat `WeaverletApp` as the orchestrator of component context and routing.
6. Import from `weaverlet` (top-level) by default in 0.3.x code; reach into `weaverlet.base`/`weaverlet.components` only when interacting with private helpers.

</Context>

# 🧵 Weaverlet — ReadMe.LLM (Part 3 : Usage Examples — Extended)

## <UsageExamples>

Below are **14 complete examples** demonstrating Weaverlet's main concepts and patterns.
Each example follows a **Prompt → Code → Output → Notes for the LLM** structure,
as defined in the *ReadMe.LLM* methodology.

---

### <Example_01> Hello World — Layout-only Component

**Prompt:**
> Create the simplest Weaverlet app that displays "hello world" using a single component.

**Expected Result (Code):**
```python
from weaverlet import WeaverletComponent, WeaverletApp
from dash import html

class HelloWorldComponent(WeaverletComponent):
    def get_layout(self):
        return html.Div('hello world!')

helloworld_component = HelloWorldComponent()
wapp = WeaverletApp(root_component=helloworld_component)
wapp.app.run(port=8086)
```

**Expected Output:**
Running the app opens `http://localhost:8086` showing a blank white page
with the text **"hello world!"** centered in the body.

**Notes for the LLM:**
- Learn how a minimal `WeaverletComponent` encapsulates a static layout.
- Always subclass `WeaverletComponent` and call `WeaverletApp(root_component=...)`.
- The app must run using `wapp.app.run()` — **never** `app.run_server()` (removed in Dash 4) and never instantiate `dash.Dash()` directly.

---

### <Example_02> Echo — Layout + Callbacks + Identifier

**Prompt:**
> Build a Weaverlet app that echoes any text the user types into an input field.

**Expected Result (Code):**
```python
from weaverlet import WeaverletComponent, WeaverletApp, Identifier
from dash_extensions.enrich import Input, Output
from dash import html, dcc

class EchoComponent(WeaverletComponent):
    text_input_id = Identifier()
    echo_div_id = Identifier()

    def get_layout(self):
        return html.Div([
            dcc.Input(id=self.text_input_id, type='text', placeholder='Type here...'),
            html.Div(id=self.echo_div_id)
        ])

    def register_callbacks(self, app):
        @app.callback(Output(self.echo_div_id, 'children'), Input(self.text_input_id, 'value'))
        def update_echo_div(text_value):
            return text_value or ''

echo_component = EchoComponent()
wapp = WeaverletApp(root_component=echo_component)
wapp.app.run(port=8089)
```

**Expected Output:**
When you type in the input box, the same text appears below it in real-time.

**Notes for the LLM:**
- Learn to declare element IDs with `Identifier()` descriptors.
- Callbacks are always defined inside `register_callbacks(app)`.
- Each output/input references `self.<identifier>` attributes, not strings.
- Prefer `dash_extensions.enrich.Input`/`Output` over `dash.dependencies` — `WeaverletApp.app` is a `DashProxy` and the enrich types unlock `group=`, `Serverside(...)`, etc.

---

### <Example_03> Constructor State — Greeting

**Prompt:**
> Create a Weaverlet component that greets a name passed to its constructor.

**Expected Result (Code):**
```python
from weaverlet import WeaverletComponent, WeaverletApp
from dash import html

class GreetingComponent(WeaverletComponent):
    def __init__(self, greeting_name, **kwargs):
        super().__init__(**kwargs)
        self.greeting_name = greeting_name
    def get_layout(self):
        return html.Div(f'hello {self.greeting_name}!')

greeting_component = GreetingComponent('Oscar')
wapp = WeaverletApp(root_component=greeting_component)
wapp.app.run(port=8089)
```

**Expected Output:**
Shows "hello Oscar!" in the browser window.

**Notes for the LLM:**
- Components can receive configuration/state via the constructor.
- The value can be stored in `self.<attribute>` and rendered in layout.

---

### <Example_04> Multipage Routing — SimpleRouterComponent

**Prompt:**
> Build a Weaverlet app with two pages ("Page A" and "Page B") using a router.

**Expected Result (Code):**
```python
from weaverlet import WeaverletComponent, WeaverletApp, SimpleRouterComponent
from dash import html

class PageA(WeaverletComponent):
    def get_layout(self):
        return html.Div("Hello from Page A!")

class PageB(WeaverletComponent):
    def get_layout(self):
        return html.Div("Hello from Page B!")

class NotFound(WeaverletComponent):
    def get_layout(self, pathname):
        return html.Div(f"Page {pathname} not found!")

routes = {"/": PageA(), "/page_a": PageA(), "/page_b": PageB()}
router = SimpleRouterComponent(routes=routes, not_found_page_component=NotFound())
wapp = WeaverletApp(root_component=router)
wapp.app.run(port=8089)
```

**Expected Output:**
- Navigating to `/page_a` shows "Hello from Page A!"
- Navigating to `/page_b` shows "Hello from Page B!"
- Any other URL shows "Page <path> not found!"

**Notes for the LLM:**
- Use `SimpleRouterComponent` for multi-page apps.
- Page components may declare any subset of `(pathname, hash, href, search)` in `get_layout`; the router passes only what is declared.
- Always provide a `not_found_page_component`.
- The default `keep_mounted=False` means each page renders only when active. To preserve state across navigation, see Example 14.
- Aliasing (`/` and `/page_a` both pointing to the same `PageA()` instance) is fine in `keep_mounted=False`. With `keep_mounted=True` it would raise `DuplicateIdError` — use distinct instances or distinct routes.

---

### <Example_05> Auth-protected Routing — AuthRouterComponent

**Prompt:**
> Create a login-protected Weaverlet app that redirects unauthenticated users to `/login`.

**Expected Result (Code):**
```python
from dash import html
from dash_extensions.enrich import Output, Trigger
from flask import session
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    AuthRouterComponent, RedirectComponent,
)

class LoginPage(WeaverletComponent):
    login_btn = Identifier()
    def __init__(self):
        super().__init__()
        self.redirect = RedirectComponent()
    def get_layout(self, pathname, hash, href, search, protected_route):
        self.protected_route = protected_route
        return html.Div([self.redirect(), html.Button("Login", id=self.login_btn)])
    def register_callbacks(self, app):
        @app.callback(Output(self.redirect.href_id, self.redirect.href_attr),
                      Trigger(self.login_btn, "n_clicks"))
        def login():
            session["user"] = "Alice"
            return {"url": self.protected_route, "target": "_self"}

class ProtectedPage(WeaverletComponent):
    def get_layout(self, pathname, hash, href, search, user):
        return html.Div(f"Welcome {user}!")

class NotFound(WeaverletComponent):
    def get_layout(self, pathname):
        return html.Div(f"Page {pathname} not found!")

routes = {"/": {"component": ProtectedPage(), "login_required": True},
          "/login": {"component": LoginPage(), "login_required": False}}
router = AuthRouterComponent(routes=routes, not_found_page_component=NotFound())

WeaverletApp(root_component=router).app.run(port=8089)
```

**Expected Output:**
Visiting `/` redirects to `/login`. Clicking "Login" sets the user session and redirects back to `/`, showing "Welcome Alice!".

**Notes for the LLM:**
- Understand session-based routing via `AuthRouterComponent`.
- Auth pages must include a `RedirectComponent`.
- The router determines if `login_required` is True and redirects accordingly.
- The router passes `user` and `protected_route` only to pages whose `get_layout` declares them.

---

### <Example_06> Redirect from Callback

**Prompt:**
> Create a button that redirects to another page when clicked.

**Expected Result (Code):**
```python
from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    SimpleRouterComponent, RedirectComponent,
)

class RedirectPage(WeaverletComponent):
    btn = Identifier()
    def __init__(self):
        super().__init__()
        self.redirect = RedirectComponent()
    def get_layout(self):
        return html.Div([self.redirect(), html.Button("Go", id=self.btn)])
    def register_callbacks(self, app):
        @app.callback(Output(self.redirect.href_id, self.redirect.href_attr),
                      Trigger(self.btn, "n_clicks"))
        def do_redirect():
            return {"url": "/another_page", "target": "_self"}
```

**Expected Output:**
Clicking the "Go" button navigates to `/another_page`.

**Notes for the LLM:**
- Redirect logic lives in a callback returning a dict to `RedirectComponent.href_attr`.
- `RedirectComponent` handles the client-side navigation automatically.

---

### <Example_07> Signals with Payload

**Prompt:**
> Build a button that fires a signal containing random data, which updates a label.

**Expected Result (Code):**
```python
import random
from dash import html
from dash_extensions.enrich import Input, Output
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    SignalComponent, SignalOutput, SignalInput,
)

class SignalDemo(WeaverletComponent):
    btn = Identifier()
    out = Identifier()
    def __init__(self):
        super().__init__()
        self.sig = SignalComponent()
    def get_layout(self):
        return html.Div([self.sig(), html.Button("Emit", id=self.btn), html.P(id=self.out)])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig), Input(self.btn, "n_clicks"))
        def emit(n): return {"n_clicks": n, "rand": random.random()}
        @app.callback(Output(self.out, "children"), SignalInput(self.sig))
        def show(payload): return f"Signal fired: {payload}"
```

**Expected Output:**
Each click updates the label with a new random value.

**Notes for the LLM:**
- Understand signal-based communication (emit + receive).
- The first callback emits via `SignalOutput`; the second listens via `SignalInput`.

---

### <Example_08> Signals as Triggers

**Prompt:**
> Demonstrate a signal used purely as a trigger (no payload).

**Expected Result (Code):**
```python
from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    SignalComponent, SignalOutput, SignalTrigger,
)

class TriggerDemo(WeaverletComponent):
    btn = Identifier()
    out = Identifier()
    def __init__(self):
        super().__init__()
        self.sig = SignalComponent()
    def get_layout(self):
        return html.Div([self.sig(), html.Button("Trigger", id=self.btn), html.P(id=self.out)])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig), Trigger(self.btn, "n_clicks"))
        def fire(): return {}
        @app.callback(Output(self.out, "children"), SignalTrigger(self.sig))
        def show(): return "Signal triggered!"
```

**Expected Output:**
The label updates to "Signal triggered!" after clicking the button.

**Notes for the LLM:**
- Learn to emit and listen for pure triggers (edge-only signals).
- Use empty `{}` payloads to signify signal activation without data.

---

### <Example_09> Signal Chains

**Prompt:**
> Show how to chain multiple signal callbacks where each step enriches data from the previous one.

**Expected Result (Code):**
```python
import random
from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    SignalComponent, SignalOutput, SignalInput,
)

class ChainDemo(WeaverletComponent):
    btn = Identifier()
    out = Identifier()
    def __init__(self):
        super().__init__()
        self.sig1 = SignalComponent(); self.sig2 = SignalComponent(); self.sig3 = SignalComponent()
    def get_layout(self):
        return html.Div([self.sig1(), self.sig2(), self.sig3(),
                         html.Button("Start chain", id=self.btn), html.P(id=self.out)])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig1), Trigger(self.btn, "n_clicks"))
        def step1(): return {"stage": 1}
        @app.callback(SignalOutput(self.sig2), SignalInput(self.sig1))
        def step2(payload): payload["stage2"] = random.random(); return payload
        @app.callback(SignalOutput(self.sig3), SignalInput(self.sig2))
        def step3(payload): payload["stage3"] = random.random(); return payload
        @app.callback(Output(self.out, "children"), SignalInput(self.sig3))
        def done(payload): return f"Chain complete: {payload}"
```

**Expected Output:**
Clicking "Start chain" triggers three callbacks sequentially, ending with a message showing the enriched payload.

**Notes for the LLM:**
- Learn chaining signals for sequential async-like logic.
- Understand that signal flow can form a causal pipeline.

---

### <Example_10> Div Signal Trigger

**Prompt:**
> Trigger a signal that updates the contents of a div element.

**Expected Result (Code):**
```python
from dash import html
from dash_extensions.enrich import Output, Trigger
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    DivSignalComponent, SignalOutput, SignalTrigger,
)

class DivSignalDemo(WeaverletComponent):
    btn = Identifier(); out = Identifier()
    def __init__(self):
        super().__init__()
        self.sig = DivSignalComponent()
    def get_layout(self):
        return html.Div([self.sig(), html.Button("Trigger", id=self.btn), html.Div(id=self.out)])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig), Trigger(self.btn, "n_clicks"))
        def fire(): return {}
        @app.callback(Output(self.out, "children"), SignalTrigger(self.sig))
        def update(): return "Div updated by signal!"
```

**Expected Output:**
Each click replaces the text in the div with "Div updated by signal!".

**Notes for the LLM:**
- Use `DivSignalComponent` to trigger updates on `html.Div` elements.
- This pattern generalizes to visual refreshes and placeholders.

---

### <Example_11> Weaverlet + DBC (Single Page)

**Prompt:**
> Combine Weaverlet with Dash Bootstrap Components to create a single-page app with a navbar.

**Expected Result (Code):**
```python
import dash_bootstrap_components as dbc
from dash import html, dcc
from weaverlet import WeaverletApp, WeaverletComponent

class Navbar(WeaverletComponent):
    def get_layout(self, brand):
        return dbc.NavbarSimple(brand=brand, color="primary", dark=True)

class MainPage(WeaverletComponent):
    def __init__(self, brand):
        super().__init__()
        self.nav = Navbar(); self.brand = brand
    def get_layout(self):
        return html.Div([self.nav(brand=self.brand), dbc.Container([dcc.Markdown("# Hello world.")], fluid=False)])

wapp = WeaverletApp(root_component=MainPage("Brand"), external_stylesheets=[dbc.themes.BOOTSTRAP])
wapp.app.run()
```

**Expected Output:**
Displays a blue navbar labeled "Brand" and a container with the text "Hello world."

**Notes for the LLM:**
- Learn integration with DBC layouts while retaining Weaverlet structure.
- Pass props like `brand` between components.
- `external_stylesheets` is now a named kwarg of `WeaverletApp.__init__`.

---

### <Example_12> Weaverlet + DBC (Multipage)

**Prompt:**
> Create a multi-page DBC app using SimpleRouterComponent for navigation.

**Expected Result (Code):**
```python
import dash_bootstrap_components as dbc
from dash import html, dcc
from weaverlet import WeaverletApp, WeaverletComponent, SimpleRouterComponent

class Navbar(WeaverletComponent):
    def get_layout(self, brand):
        return dbc.NavbarSimple(children=[ dbc.NavItem(dbc.NavLink("Page A", href="/a")),
                                           dbc.NavItem(dbc.NavLink("Page B", href="/b")) ],
                                brand=brand, color="primary", dark=True)

class Content(WeaverletComponent):
    def __init__(self, body): super().__init__(); self.body = body
    def get_layout(self): return dbc.Container([dcc.Markdown(self.body)])

class Page(WeaverletComponent):
    def __init__(self, brand, body): super().__init__(); self.nav=Navbar(); self.body=body; self.brand=brand
    def get_layout(self):
        return html.Div([ self.nav(brand=self.brand),
                          dbc.Container([dcc.Markdown(self.body)], fluid=True) ])

routes = {"/": Page("Brand", "# Page A"), "/a": Page("Brand", "# Page A"), "/b": Page("Brand", "# Page B")}
router = SimpleRouterComponent(routes=routes,
                               not_found_page_component=Page("Brand", "# Not found"))

WeaverletApp(root_component=router, title="Simple Weaverlet + DBC app",
             external_stylesheets=[dbc.themes.COSMO]).app.run()
```

**Expected Output:**
- Navbar with links to "Page A" and "Page B".
- Clicking links updates the page content dynamically.

**Notes for the LLM:**
- Learn combining DBC navigation with Weaverlet routers.
- Recognize the typical composition: `Navbar` + `Router` + `Page`.
- Aliasing `/` and `/a` to distinct `Page("Brand", "# Page A")` instances is OK here because each call to `Page(...)` is a fresh instance. With `keep_mounted=True`, the same rule about distinct instances applies.

---

### <Example_13> Weaverlet + DBC Modal Controlled by Signals

**Prompt:**
> Add an "About" button to open a modal via Weaverlet signals.

**Expected Result (Code):**
```python
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_extensions.enrich import Output, Trigger
from weaverlet import (
    WeaverletApp, WeaverletComponent, Identifier,
    SimpleRouterComponent, SignalComponent,
    SignalTrigger, SignalOutput,
)


class AboutModalComponent(WeaverletComponent):

    modal_id = Identifier()
    close_button_id = Identifier()

    def __init__(self):
        super().__init__()
        self.open_modal_signal = SignalComponent()

    def get_layout(self):
        return html.Div([
            self.open_modal_signal(),
            dbc.Modal(
                [
                    dbc.ModalHeader('About'),
                    dbc.ModalBody(children=[
                        dcc.Markdown('''
                            #### About

                            By Alberto Garcia-Robledo.
                        ''')
                    ]),
                    dbc.ModalFooter(
                        dbc.Button('Close', id=self.close_button_id, className='ml-auto')
                    ),
                ],
                id=self.modal_id,
                size="lg",
            ),
        ])

    def register_callbacks(self, app):
        @app.callback(Output(self.modal_id, 'is_open'), Trigger(self.close_button_id, 'n_clicks'))
        def close_modal():
            return False

        @app.callback(Output(self.modal_id, 'is_open'), SignalTrigger(self.open_modal_signal))
        def open_modal():
            return True


class PrimaryNavbarComponent(WeaverletComponent):

    about_navlink_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.about_modal_component = AboutModalComponent()

    def get_layout(self, brand):
        return dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink('Page A', href='/a')),
                dbc.NavItem(dbc.NavLink('Page B', href='/b')),
                dbc.NavItem(dbc.NavLink('About', id=self.about_navlink_id, href='#')),
                self.about_modal_component(),
            ],
            brand=brand, color='primary', dark=True,
        )

    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.about_modal_component.open_modal_signal),
                      Trigger(self.about_navlink_id, 'n_clicks'))
        def open_modal():
            return {}


class MainPageComponent(WeaverletComponent):
    def __init__(self, brand, page_content_component):
        super().__init__()
        self.primary_navbar = PrimaryNavbarComponent(name='primary_navbar')
        self.page_content_component = page_content_component
        self.brand = brand

    def get_layout(self):
        return html.Div([
            self.primary_navbar(brand=self.brand),
            dbc.Container([self.page_content_component()], fluid=True,
                          style={"padding": "0px", "width": "100%"}),
        ])


class ContentComponent(WeaverletComponent):
    def __init__(self, body, **kwargs):
        super().__init__(**kwargs)
        self.body = body
    def get_layout(self):
        return dbc.Container([dcc.Markdown(self.body)])


class NotFoundPageComponent(WeaverletComponent):
    def get_layout(self, pathname):
        return dcc.Markdown(f"# Page {pathname} not found!")


page_a = MainPageComponent('Brand of Page A',
                           ContentComponent(body="# Page A\n\nThis is the content of Page A."))
page_b = MainPageComponent('Brand of Page B',
                           ContentComponent(body="# Page B\n\nThis is the content of Page B."))

router = SimpleRouterComponent(
    routes={'/': page_a, '/a': page_a, '/b': page_b},
    not_found_page_component=NotFoundPageComponent(),
)
WeaverletApp(root_component=router, title='Simple Weaverlet + DBC app',
             external_stylesheets=[dbc.themes.COSMO]).app.run()
```

**Expected Output:**
Clicking "About" opens a modal window showing markdown content "About — By Alberto Garcia-Robledo."

**Notes for the LLM:**
- Demonstrates how signals can trigger DBC modals.
- Learn hierarchical event propagation: Navbar → Modal via `SignalOutput` + `SignalTrigger`.
- Understand how reusable GUI components interact within a Weaverlet hierarchy.
- This example uses `from dash import html, dcc` (modern Dash 4 style); the legacy `dash_html_components` / `dash_core_components` packages no longer exist.

---

### <Example_14> Weaverlet + DMC + `keep_mounted` State Preservation

**Prompt:**
> Build a multipage app where each page has its own button, and the click state of each
> page survives when the user navigates away and comes back. Use Dash Mantine Components
> for a polished sidebar layout.

**Expected Result (Code):**
```python
import dash_mantine_components as dmc
from dash_extensions.enrich import Input, Output
from weaverlet import (
    Identifier, SimpleRouterComponent, WeaverletApp, WeaverletComponent,
)


class SidebarComponent(WeaverletComponent):
    nav_a_id = Identifier()
    nav_b_id = Identifier()

    def get_layout(self):
        return dmc.AppShellNavbar(
            dmc.Stack([
                dmc.NavLink(label="Page A", href="/", id=self.nav_a_id),
                dmc.NavLink(label="Page B", href="/b", id=self.nav_b_id),
            ], gap="xs", p="md")
        )


class PageComponent(WeaverletComponent):
    button_id = Identifier()
    output_id = Identifier()

    def __init__(self, title, action_label, get_message, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.action_label = action_label
        self.get_message = get_message

    def get_layout(self):
        return dmc.Card([
            dmc.Title(self.title, order=2),
            dmc.Space(h="md"),
            dmc.Button(self.action_label, id=self.button_id, variant="filled"),
            dmc.Space(h="md"),
            dmc.Text(id=self.output_id, c="dimmed"),
        ], withBorder=True, padding="lg", m="md")

    def register_callbacks(self, app):
        @app.callback(Output(self.output_id, "children"),
                      Input(self.button_id, "n_clicks"),
                      prevent_initial_call=True)
        def update(n_clicks):
            return self.get_message(n_clicks or 0)


class NotFoundComponent(WeaverletComponent):
    def get_layout(self):
        return dmc.Alert("Page not found.", title="404", color="red", m="md")


class ShellComponent(WeaverletComponent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = SidebarComponent()
        page_a = PageComponent("Page A", "Increment counter",
                               lambda n: f"Clicked {n} time{'s' if n != 1 else ''}.")
        page_b = PageComponent("Page B", "Toggle greeting",
                               lambda n: "Hello!" if n % 2 == 1 else "Goodbye!")
        # keep_mounted=True keeps each page in the DOM and toggles CSS visibility,
        # so n_clicks state and the Text output survive navigation.
        # Each route must map to a *distinct* component instance.
        self.router = SimpleRouterComponent(
            routes={"/": page_a, "/b": page_b},
            not_found_page_component=NotFoundComponent(),
            keep_mounted=True,
        )

    def get_layout(self):
        return dmc.MantineProvider(
            dmc.AppShell([
                dmc.AppShellHeader(
                    dmc.Title("Weaverlet + DMC", order=3, p="md"),
                ),
                self.sidebar(),
                dmc.AppShellMain(dmc.Container(self.router(), size="md", py="xl")),
            ], header={"height": 60}, navbar={"width": 240, "breakpoint": "sm"}),
            theme={"primaryColor": "indigo"},
        )

    def register_callbacks(self, app):
        # Highlight the active NavLink based on current URL.
        @app.callback(
            Output(self.sidebar.nav_a_id, "active"),
            Output(self.sidebar.nav_b_id, "active"),
            Input(self.router.url_id, "pathname"),
            prevent_initial_call=False,
        )
        def highlight(pathname):
            pathname = pathname or "/"
            return pathname == "/", pathname == "/b"


WeaverletApp(root_component=ShellComponent(),
             title="Weaverlet + Dash Mantine Components").app.run()
```

**Expected Output:**
- A two-column dashboard with a sidebar (Page A / Page B) and a main content area.
- Clicking the button on Page A increments a counter; switching to Page B and back
  preserves the count. Page B's greeting toggle behaves the same way — switching
  back to Page A doesn't reset it.
- The active NavLink in the sidebar highlights based on the current URL.

**Notes for the LLM:**
- `keep_mounted=True` is the v0.3 hero feature: every route is rendered at startup
  and navigation toggles CSS, never unmounting. State (React `n_clicks`, WebGL
  canvases, Plotly figures) survives.
- With `keep_mounted=True`, **never** alias two `routes` keys to the same component
  instance — that would mount the same `Identifier`-bearing layout twice and raise
  `DuplicateIdError`.
- The `preserve_path` kwarg (default = first route in `routes`) controls which
  route uses `visibility:hidden` (canvas-safe) vs `display:none` when hidden. Set
  it to your WebGL-heaviest route.
- The active-NavLink callback is registered in the *shell* (not the sidebar)
  because the shell owns both the sidebar (for the NavLink IDs) and the router
  (for the URL Input).

---

</UsageExamples>

# 🧵 Weaverlet — ReadMe.LLM (Part 4 : API Signatures)

## <APISignatures>

This section lists **LLM-oriented API signatures** for Weaverlet's core modules.
The goal is to let an LLM reliably synthesize correct code **without** needing to read the
entire source. Signatures focus on class contracts, method names, parameters, and return types.

**Re-export note (v0.3+):** Every public symbol below is also importable directly from the
top-level `weaverlet` package — `from weaverlet import WeaverletComponent, ...`. The
submodule paths (`weaverlet.base`, `weaverlet.components`) remain as compatibility aliases.

---

### Module: `weaverlet` (top-level)

```python
__version__: str  # e.g. "0.3.0"
```

All names listed under `weaverlet.base` and `weaverlet.components` below are re-exported here.

---

### Module: `weaverlet.base`

#### Exceptions
```python
class WeaverletException(Exception): ...
```

#### Identifier
```python
class Identifier:
    # Descriptor that yields a unique Dash id per (instance, attribute).
    # Cached lazily on instance.__dict__["_wlt_ids"]; works even before
    # super().__init__() has run.
    def __get__(self, instance, owner) -> str: ...
    def __set__(self, instance, value): ...  # Always raises TypeError.
```
**ID format (opaque):** `"{ClassName}_{attr_name}_{hex(id(instance))}"`. Treat as a token; do not parse.

#### Signal Adapters (callback helpers)
```python
def SignalInput(signal_component) -> Input: ...
def SignalOutput(signal_component) -> Output: ...
def ServersideSignalOutput(signal_component) -> Output: ...   # returns plain Output in 0.3+
def SignalTrigger(signal_component) -> Trigger: ...
def SignalState(signal_component) -> State: ...
def SignalGroup(signal_component) -> str: ...
```
For server‑side caching, wrap the **return value** of your callback with `Serverside(value)` (re‑exported from `dash_extensions.enrich`).

#### Core Component
```python
class WeaverletComponent(ABC):
    def __init__(self, name: str = "unnamed"): ...
    def initialize(self) -> None: ...
    def register_callbacks(self, app) -> None: ...
    def get_children(self) -> list["WeaverletComponent"]: ...   # live-computed from __dict__
    def get_parent(self) -> "WeaverletComponent | None": ...
    def get_context(self) -> dict: ...
    def get_id(self) -> str: ...
    def get_name(self) -> str: ...
    def set_name(self, name: str) -> None: ...
    @abstractmethod
    def get_layout(self, *args, **kwargs): ...
    def __call__(self, *args, **kwargs): ...   # Proxy to get_layout.
```
**Removed in 0.3.0:** `get_page_root()` (the per-router page-root walk was unused).

#### Component Collections (ABCs)
```python
class ComponentsDict(dict, ABC):
    def get_components(self) -> Iterable["WeaverletComponent"]: ...
class ComponentsList(list, ABC):
    def get_components(self) -> Iterable["WeaverletComponent"]: ...
class ComponentsOrderedDict(OrderedDict, ABC):
    def get_components(self) -> Iterable["WeaverletComponent"]: ...
```
Used by routers and by user code that wants to expose a collection of children to the DAG walker.

#### Detached references (cycle prevention)
```python
class DetachedComponentRef:
    def __init__(self, component: "WeaverletComponent") -> None: ...
    def __getattr__(self, attr): ...   # Proxies to wrapped component.

DetatchedComponentRef = DetachedComponentRef  # backwards-compatible alias
```

#### Router Base
```python
class RouterComponent(WeaverletComponent): ...   # Marker class.
```

#### Application Orchestrator
```python
class WeaverletApp:
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
    ) -> None: ...
    # Exposed attributes
    app: "dash_extensions.enrich.DashProxy"   # not a plain Dash
    root_component: WeaverletComponent
    root: WeaverletComponent                  # alias for root_component
    context: dict
```
**Notes:**
- `assets_folder` auto-resolves to `dirname(sys.modules['__main__'].__file__) + "/assets"` so `dash_extensions.javascript.assign()` works without manual wiring.
- `jupyter_mode=True` requires `pip install weaverlet[jupyter]`; otherwise raises `ImportError` with the install hint.
- Internally walks the DAG once via `WeaverletComponent._wlt_walk()` to propagate context, run `initialize()`, and register callbacks.

---

### Module: `weaverlet.components.simple_router`

```python
class SimpleRoutes(ComponentsDict):
    def get_components(self) -> list[WeaverletComponent]: ...

class SimpleRouterComponent(RouterComponent):
    content_id = Identifier()
    url_id = Identifier()
    def __init__(
        self,
        routes: dict[str, WeaverletComponent],
        not_found_page_component: WeaverletComponent,
        use_prefix: bool = False,
        keep_mounted: bool = False,
        preserve_path: str | None = None,
        name: str = "unnamed",
    ): ...
    def get_layout(self) -> "dash.html.Div": ...
    def register_callbacks(self, app): ...
```

**Notes for LLMs:**
- `routes` maps paths to component instances.
- When `use_prefix=True`, `WeaverletApp(context={'prefix': '...'} )` is required.
- `keep_mounted=True`: every route is rendered at startup; navigation toggles CSS only. Each `routes` entry must be a **distinct component instance**.
- `preserve_path` (default = first route in `routes`) is the route that uses `visibility:hidden` instead of `display:none` when hidden — required for canvases that can't survive `display:none`.
- If `not_found_page_component` is the same instance as one of the routes, the router shares that route's wrapper (no `DuplicateIdError`).
- Pages may declare any subset of `(pathname, hash, href, search)` in `get_layout(...)`; the router passes only what is declared.

---

### Module: `weaverlet.components.auth_router`

```python
class AuthRoutes(ComponentsDict):
    def get_components(self) -> list[WeaverletComponent]: ...

class AuthRouterComponent(RouterComponent):
    content_id = Identifier()
    url_id = Identifier()
    def __init__(
        self,
        routes: dict[str, dict],   # {path: {'component': WeaverletComponent, 'login_required': bool}}
        not_found_page_component: WeaverletComponent,
        user_session_key: str = "user",
        login_route: str = "/login",
        use_prefix: bool = False,
        name: str = "unnamed",
    ): ...
    def get_layout(self) -> "dash.html.Div": ...
    def register_callbacks(self, app): ...
```

**Notes for LLMs:**
- Redirects unauthenticated users to `login_route`.
- Auth pages often include a `RedirectComponent` to bounce back after login.
- `user_session_key` is read/written in `flask.session`.
- Pages may declare any subset of `(pathname, hash, href, search, user, protected_route)` in `get_layout(...)`.
- `keep_mounted` is **not** yet supported on `AuthRouterComponent` (planned for 0.3.x).

---

### Module: `weaverlet.components.redirect`

```python
class RedirectComponent(WeaverletComponent):
    href_id = Identifier()
    href_attr: str = "data"
    _dummy_div_id = Identifier()
    _prefix_id = Identifier()
    redirect_clientside_callback: str = "function(href, prefix){ ... }"
    def __init__(self, name: str = "unnamed", use_prefix: bool = False): ...
    def get_layout(self) -> "dash.html.Div": ...
    def register_callbacks(self, app): ...
```
**Usage:**
Return `{'url': '/target', 'target': '_self'}` (or `'_blank'`) to `Output(href_id, href_attr)` from a callback. When `use_prefix=True`, the prefix from `WeaverletApp(context={'prefix': '...'})` is applied client-side.

---

### Module: `weaverlet.components.signal`

```python
class SignalComponent(WeaverletComponent):
    signal_id = Identifier()
    signal_group_id = Identifier()
    signal_attr: str = "data"
    signal_default_retval: dict = {}
    def __init__(self, name: str = "unnamed"): ...
    def get_layout(self) -> "dash.dcc.Store": ...
    def register_callbacks(self, app): pass
```
**Paired helpers:** `SignalOutput`, `SignalInput`, `SignalTrigger`, `SignalState`, `SignalGroup`.

---

### Module: `weaverlet.components.div_signal`

```python
class DivSignalComponent(WeaverletComponent):
    signal_id = Identifier()
    signal_group_id = Identifier()
    signal_attr: str = "children"
    signal_default_retval: dict = {}
    def __init__(self, name: str = "unnamed"): ...
    def get_layout(self) -> "dash.html.Div": ...
    def register_callbacks(self, app): pass
```

---

### Module: `weaverlet.components.store`

```python
class StoreComponentOp:
    STORE = "store"
    MERGE = "merge"
    CLEAN = "clean"

class StoreComponent(WeaverletComponent):
    store_attr: str = "data"
    store_id = Identifier()
    _store_group_id = Identifier()
    # Internal signals: _store_signal, _merge_signal, _clean_signal
    # External input signal: input_signal
    def __init__(self, name: str = "unnamed"): ...
    def get_layout(self) -> "dash.html.Div": ...
    def register_callbacks(self, app): ...
```
**Usage:**
Emit to `input_signal` with one of:
- `{'op': StoreComponentOp.STORE, 'data': {...}}`
- `{'op': StoreComponentOp.MERGE, 'data': {...}}`
- `{'op': StoreComponentOp.CLEAN}`

`StoreComponent` relies on `dash_extensions.enrich`'s `group=` callbacks to allow multiple writers to the same `Output`. This works automatically because `WeaverletApp.app` is a `DashProxy`.

---

### Module: `weaverlet.components.empty_layout`

```python
class EmptyLayoutComponent(WeaverletComponent):
    _empty_div_id = Identifier()
    def __init__(self, name: str = "unnamed"): ...
    def get_layout(self) -> "dash.html.Div": ...
```

---

### Cross-cutting Notes for LLMs

- **Imports:** prefer `from weaverlet import ...` (top-level) in 0.3.x code.
- **Identifiers:** always reference `self.<identifier>` in callbacks and layout; do not use raw strings.
- **Routers:** page components may declare any subset of `(pathname, hash, href, search, user, protected_route)`; the router passes only what is declared.
- **Context:** supply `WeaverletApp(context={'prefix': '...'})` when routers/redirects use prefixes.
- **Signals:** for event flow, prefer `SignalComponent` + helpers over manual `dcc.Store` wiring.
- **Serverside:** wrap the **return value** with `Serverside(...)` instead of using a special Output type.
- **WSGI:** export via `wapp.app.server` when deploying behind a WSGI server.
- **Run command:** `wapp.app.run(...)` — `app.run_server` was removed in Dash 4.

</APISignatures>

# 🧵 Weaverlet — ReadMe.LLM (Part 5 : Patterns & Recipes)

## <Patterns>

This section provides **copy‑pasteable patterns** and **short recipes** that LLMs should prefer
when building Weaverlet apps. Each pattern includes intent, code, and guidance.

---

### Pattern A — Layout‑only Component
**Intent:** Encapsulate static UI.

```python
from weaverlet import WeaverletComponent
from dash import html

class StaticCard(WeaverletComponent):
    def get_layout(self, title="Title", body="Text"):
        return html.Div([html.H4(title), html.P(body)])
```

**Use inside a parent layout:**
```python
self.card = StaticCard()
# ...
return html.Div([ self.card(title="Hello", body="World") ])
```

---

### Pattern B — Component with Callbacks
**Intent:** Keep callbacks local to the owning component.

```python
from weaverlet import WeaverletComponent, Identifier
from dash_extensions.enrich import Input, Output
from dash import html, dcc

class Echo(WeaverletComponent):
    text = Identifier(); out = Identifier()
    def get_layout(self):
        return html.Div([ dcc.Input(id=self.text, type="text"),
                          html.Div(id=self.out) ])
    def register_callbacks(self, app):
        @app.callback(Output(self.out, "children"), Input(self.text, "value"))
        def echo(v): return v or ""
```

---

### Pattern C — Signals: Emit → Receive (with payload)
**Intent:** Decouple producers and consumers via `SignalComponent`.

```python
from weaverlet import (
    WeaverletComponent, Identifier, SignalComponent,
    SignalOutput, SignalInput,
)
from dash_extensions.enrich import Input, Output
from dash import html

class ProducerConsumer(WeaverletComponent):
    btn = Identifier(); out = Identifier()
    def __init__(self):
        super().__init__()
        self.sig = SignalComponent()
    def get_layout(self):
        return html.Div([ self.sig(), html.Button("Emit", id=self.btn), html.Div(id=self.out) ])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig), Input(self.btn, "n_clicks"))
        def emit(n): return {"n": n}
        @app.callback(Output(self.out, "children"), SignalInput(self.sig))
        def recv(payload): return f"payload: {payload}"
```

---

### Pattern D — Signals: Trigger (edge‑only)
**Intent:** Fire events without payloads.

```python
from weaverlet import (
    WeaverletComponent, Identifier, SignalComponent,
    SignalOutput, SignalTrigger,
)
from dash_extensions.enrich import Output, Trigger
from dash import html

class TriggerOnly(WeaverletComponent):
    btn = Identifier(); out = Identifier()
    def __init__(self):
        super().__init__(); self.sig = SignalComponent()
    def get_layout(self):
        return html.Div([ self.sig(), html.Button("Fire", id=self.btn), html.Div(id=self.out) ])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.sig), Trigger(self.btn, "n_clicks"))
        def fire(): return {}
        @app.callback(Output(self.out, "children"), SignalTrigger(self.sig))
        def show(): return "Triggered!"
```

---

### Pattern E — Signal Chains (A → B → C)
**Intent:** Sequential pipelines.

```python
from weaverlet import (
    WeaverletComponent, Identifier, SignalComponent,
    SignalOutput, SignalInput,
)
from dash_extensions.enrich import Output, Trigger
from dash import html

class Chain(WeaverletComponent):
    btn = Identifier(); out = Identifier()
    def __init__(self):
        super().__init__()
        self.a=SignalComponent(); self.b=SignalComponent(); self.c=SignalComponent()
    def get_layout(self):
        return html.Div([ self.a(), self.b(), self.c(),
                          html.Button("Start", id=self.btn), html.Div(id=self.out) ])
    def register_callbacks(self, app):
        @app.callback(SignalOutput(self.a), Trigger(self.btn, "n_clicks"))
        def s1(): return {"stage":1}
        @app.callback(SignalOutput(self.b), SignalInput(self.a))
        def s2(p): p["stage"]=2; return p
        @app.callback(SignalOutput(self.c), SignalInput(self.b))
        def s3(p): p["stage"]=3; return p
        @app.callback(Output(self.out, "children"), SignalInput(self.c))
        def done(p): return f"done: {p}"
```

---

### Pattern F — Simple Routing
**Intent:** Multi‑page public apps (default mode — pages unmount on navigation).

```python
from weaverlet import WeaverletComponent, WeaverletApp, SimpleRouterComponent
from dash import html

class A(WeaverletComponent):
    def get_layout(self): return html.Div("A")
class B(WeaverletComponent):
    def get_layout(self): return html.Div("B")
class NotFound(WeaverletComponent):
    def get_layout(self, pathname): return html.Div(f"404: {pathname}")

router = SimpleRouterComponent(routes={"/":A(), "/a":A(), "/b":B()},
                               not_found_page_component=NotFound())
WeaverletApp(root_component=router).app.run()
```

**Prefixing (optional):**
```python
router = SimpleRouterComponent(routes=..., not_found_page_component=NotFound(), use_prefix=True)
WeaverletApp(root_component=router, context={"prefix":"/my/app"}).app.run()
```

---

### Pattern F.1 — `keep_mounted` State Preservation
**Intent:** Multipage app where each page's React state (counters, selections, WebGL canvases) must survive navigation.

```python
from weaverlet import WeaverletComponent, WeaverletApp, Identifier, SimpleRouterComponent
from dash_extensions.enrich import Input, Output
from dash import html

class Counter(WeaverletComponent):
    btn = Identifier(); out = Identifier()
    def get_layout(self):
        return html.Div([ html.Button("Click", id=self.btn), html.Div(id=self.out) ])
    def register_callbacks(self, app):
        @app.callback(Output(self.out, "children"), Input(self.btn, "n_clicks"),
                      prevent_initial_call=True)
        def show(n): return f"clicks: {n or 0}"

class Other(WeaverletComponent):
    def get_layout(self): return html.Div("Other page")

class NF(WeaverletComponent):
    def get_layout(self): return html.Div("Not found")

# IMPORTANT: each route maps to a *distinct* instance — no aliasing under keep_mounted=True.
router = SimpleRouterComponent(
    routes={"/": Counter(), "/other": Other()},
    not_found_page_component=NF(),
    keep_mounted=True,
    preserve_path="/",   # the route whose canvas/state matters most; default = first route
)
WeaverletApp(root_component=router).app.run()
```

**Use this pattern when:**
- Pages contain `dash-leaflet` maps, `dash-sylvereye` graphs, Plotly WebGL backends, or any component whose initialization is expensive.
- Per-page `n_clicks`, dropdown selections, or scroll positions must persist across navigation.

**Avoid this pattern when:**
- Pages are heavy and you only ever want one in memory at a time.
- Two routes need to alias the same component instance (use `keep_mounted=False`).

---

### Pattern G — Auth Routing
**Intent:** Protect routes behind login.

```python
from weaverlet import (
    WeaverletComponent, WeaverletApp, Identifier,
    AuthRouterComponent, RedirectComponent,
)
from dash_extensions.enrich import Output, Trigger
from flask import session
from dash import html

class Login(WeaverletComponent):
    btn = Identifier()
    def __init__(self): super().__init__(); self.redirect=RedirectComponent()
    def get_layout(self, pathname, hash, href, search, protected_route):
        self._protected=protected_route
        return html.Div([ self.redirect(), html.Button("Login", id=self.btn) ])
    def register_callbacks(self, app):
        @app.callback(Output(self.redirect.href_id, self.redirect.href_attr), Trigger(self.btn,"n_clicks"))
        def do_login(): session["user"]="User"; return {"url": self._protected, "target":"_self"}

class Protected(WeaverletComponent):
    def get_layout(self, pathname, hash, href, search, user): return html.Div(f"Welcome {user}!")

class NF(WeaverletComponent):
    def get_layout(self, pathname): return html.Div(f"404: {pathname}")

router = AuthRouterComponent(routes={"/": {"component":Protected(),"login_required":True},
                                      "/login": {"component":Login(),"login_required":False}},
                             not_found_page_component=NF())
WeaverletApp(root_component=router).app.run()
```

---

### Pattern H — Redirect from Callback
**Intent:** Navigate programmatically after an action.

```python
from weaverlet import WeaverletComponent, Identifier, RedirectComponent
from dash_extensions.enrich import Output, Trigger
from dash import html

class Redirector(WeaverletComponent):
    btn = Identifier()
    def __init__(self): super().__init__(); self.redirect=RedirectComponent()
    def get_layout(self): return html.Div([ self.redirect(), html.Button("Go", id=self.btn) ])
    def register_callbacks(self, app):
        @app.callback(Output(self.redirect.href_id, self.redirect.href_attr), Trigger(self.btn,"n_clicks"))
        def go(): return {"url": "/target", "target": "_self"}
```

---

### Pattern I — Store Component (Persist/Merge/Clean)
**Intent:** Centralized state with explicit ops.

```python
from weaverlet import WeaverletComponent, StoreComponent, StoreComponentOp
from dash_extensions.enrich import Output
from dash import html

class StoreDemo(WeaverletComponent):
    def __init__(self): super().__init__(); self.store=StoreComponent()
    def get_layout(self): return html.Div([ self.store() ])
    def register_callbacks(self, app):
        # Elsewhere: emit to self.store.input_signal with op dicts
        pass

# To write:
# @app.callback(SignalOutput(self.store.input_signal), Trigger(...))
# def store_payload(): return {"op": StoreComponentOp.MERGE, "data": {"x": 1}}
```

---

### Pattern J — DBC Composition (Navbar + Pages)
**Intent:** Compose higher‑level GUI elements with Dash Bootstrap Components.

```python
import dash_bootstrap_components as dbc
from dash import html, dcc
from weaverlet import WeaverletApp, WeaverletComponent, SimpleRouterComponent

class Navbar(WeaverletComponent):
    def get_layout(self, brand):
        return dbc.NavbarSimple(children=[ dbc.NavItem(dbc.NavLink("Page A", href="/a")),
                                           dbc.NavItem(dbc.NavLink("Page B", href="/b")) ],
                                brand=brand, color="primary", dark=True)

class Page(WeaverletComponent):
    def __init__(self, brand, body): super().__init__(); self.nav=Navbar(); self.brand=brand; self.body=body
    def get_layout(self):
        return html.Div([ self.nav(brand=self.brand),
                          dbc.Container([ dcc.Markdown(self.body) ], fluid=True) ])

router = SimpleRouterComponent(
    routes={"/": Page("Brand", "# A"), "/a": Page("Brand", "# A"), "/b": Page("Brand", "# B")},
    not_found_page_component=Page("Brand", "# Not found"),
)
WeaverletApp(root_component=router, external_stylesheets=[dbc.themes.CYBORG]).app.run()
```

---

### Pattern J.1 — DMC + AppShell (Professional Sidebar Layout)
**Intent:** Full‑height dashboard shell using Dash Mantine Components.

```python
import dash_mantine_components as dmc
from weaverlet import WeaverletComponent, WeaverletApp, SimpleRouterComponent

class Page(WeaverletComponent):
    def __init__(self, label): super().__init__(); self.label=label
    def get_layout(self): return dmc.Card(dmc.Text(self.label),
                                          withBorder=True, padding="lg", m="md")

class NF(WeaverletComponent):
    def get_layout(self): return dmc.Alert("404", color="red", m="md")

class Shell(WeaverletComponent):
    def __init__(self):
        super().__init__()
        self.router = SimpleRouterComponent(
            routes={"/": Page("Home"), "/about": Page("About")},
            not_found_page_component=NF(),
            keep_mounted=True,
        )
    def get_layout(self):
        return dmc.MantineProvider(
            dmc.AppShell(
                [
                    dmc.AppShellHeader(dmc.Title("My Dashboard", order=3, p="md")),
                    dmc.AppShellNavbar(dmc.Stack([
                        dmc.NavLink(label="Home", href="/"),
                        dmc.NavLink(label="About", href="/about"),
                    ], p="md")),
                    dmc.AppShellMain(dmc.Container(self.router(), size="md", py="xl")),
                ],
                header={"height": 60}, navbar={"width": 240, "breakpoint": "sm"},
            ),
            theme={"primaryColor": "indigo"},
        )

WeaverletApp(root_component=Shell()).app.run()
```

---

### Pattern K — Testing Hooks (Smoke)
**Intent:** Quick sanity checks for LLM‑generated code.

```python
# test_smoke.py
def test_imports():
    import weaverlet
    from weaverlet import WeaverletComponent, WeaverletApp, SimpleRouterComponent

def test_component_contract():
    from weaverlet import WeaverletComponent
    class C(WeaverletComponent):
        def get_layout(self): return "ok"
    assert C().get_layout() == "ok"

def test_identifier_unique():
    from weaverlet import WeaverletComponent, Identifier
    class C(WeaverletComponent):
        x = Identifier()
        def get_layout(self): return None
    assert C().x != C().x
```

Run:
```
pytest -q
```

---

### Pattern L — Deployment (WSGI)
**Intent:** Serve app with gunicorn/uwsgi.

```python
# app.py
from weaverlet import WeaverletApp, WeaverletComponent
from dash import html

class Root(WeaverletComponent):
    def get_layout(self): return html.Div("Hello")

application = WeaverletApp(root_component=Root()).app.server  # WSGI entrypoint
```

Gunicorn:
```
gunicorn app:application -w 2 -b 0.0.0.0:8080
```

---

### Anti‑Patterns (Do NOT do this)
- ❌ Creating `dash.Dash()` manually or setting `app.layout` yourself.
- ❌ Hardcoded string IDs instead of `Identifier()` descriptors.
- ❌ Cross‑component communication via bare `dcc.Store` (use Signals/StoreComponent).
- ❌ Callbacks declared outside the owning component's `register_callbacks`.
- ❌ Mutating components/DOM directly inside callbacks (only update props).
- ❌ Using `wapp.app.run_server(...)` — Dash 4 removed it; use `wapp.app.run(...)`.
- ❌ Using legacy `import dash_html_components as html` / `import dash_core_components as dcc` — use `from dash import html, dcc`.
- ❌ Aliasing two `routes` keys to the same component instance with `keep_mounted=True`.

</Patterns>

# 🧵 Weaverlet — ReadMe.LLM (Part 6 : Metadata for LLMs)

## <Metadata>

This section provides **meta‑guidance** for large language models (LLMs) such as GPT‑5,
Claude Code, or Codex. It defines operational constraints, inference heuristics,
and safety boundaries when reasoning about or generating Weaverlet code.

---

### 1. Scope of Knowledge

LLMs reading this file are expected to understand:

| Domain | Description |
|:--|:--|
| **Dash 4.x Framework** | Web framework for Python, declarative callbacks, `dash.html` and `dash.dcc` components. `app.run_server` is removed in 4.x; use `app.run`. |
| **dash_extensions.enrich** | `DashProxy`, `Trigger`, `Serverside` (value wrapper), `group=` multi‑output callbacks. |
| **Flask Sessions** | Used by `AuthRouterComponent` for authentication context. |
| **Weaverlet Framework 0.3.x** | Component‑based abstraction on top of Dash, with WebGL‑safe routing via `keep_mounted=True`. |

---

### 2. Supported External Libraries

| Library | Purpose |
|:--|:--|
| `dash >= 4.1.0, < 5.0.0` | UI primitives (`html`, `dcc`) |
| `dash_extensions >= 1.0.0, < 3.0.0` | DashProxy + advanced callback primitives |
| `dash_bootstrap_components >= 2.0` | Bootstrap‑based UI styling (examples 11–13) |
| `dash_mantine_components >= 2.0` | Mantine‑based UI styling (example 14) |
| `flask` | Session management for auth routers (transitive) |
| `random` | Example payloads for signals |
| `pytest`, `pytest-playwright` | Smoke and browser tests (`pip install weaverlet[dev]`) |

Optional extras:

| Extra | Adds |
|:--|:--|
| `weaverlet[jupyter]` | `dash[jupyter] >= 4.1` (for `jupyter_mode=True`) |
| `weaverlet[examples]` | DBC + DMC for the `examples/` folder |
| `weaverlet[dev]` | pytest, pytest-playwright |

---

### 3. LLM Behavioral Rules

- Generate deterministic, minimal, **runnable** Python code.
- Follow **Rules (Part 1)** and **Patterns (Part 5)** strictly.
- Default to top‑level imports (`from weaverlet import ...`).
- Prefer *explicit imports* and *in‑module callback definitions*.
- Default `SimpleRouterComponent(keep_mounted=False)` unless the user mentions WebGL / persistent state / Sylvereye / Leaflet / Plotly WebGL.
- Use `wapp.app.run(...)` (never `run_server`).
- Preserve code indentation, triple‑quote balance, and parameter ordering.

---

### 4. Reasoning Assumptions for LLMs

When synthesizing or refactoring Weaverlet code, assume:

1. **Single root application:** there is exactly one `WeaverletApp(root_component=...)` per script.
2. **No circular component references:** component graph forms a DAG; cycles are broken via `DetachedComponentRef`.
3. **Dash callbacks** are pure; side effects occur only through returned properties.
4. **Identifiers** are globally unique via the `Identifier()` descriptor; their string form is opaque.
5. **Signals** are the canonical communication mechanism; do not improvise event buses.
6. **Context dictionary** is propagated once at app construction; treat as effectively read‑only at runtime.
7. **Multi‑page routing** is handled exclusively via `SimpleRouterComponent` or `AuthRouterComponent`.
8. **Permissive get_layout signatures:** routed pages may declare any subset of `(pathname, hash, href, search, user, protected_route)`.
9. **`keep_mounted=True` mounts every route at startup.** All `routes` entries must be distinct instances.

---

### 5. Safety and Deployment Constraints

| Category | Guidance |
|:--|:--|
| **Security** | Do not store plaintext passwords or tokens in source. Use `flask.session`. |
| **Ports** | Prefer `8050–8090` for local examples; avoid 80/443 without sudo. |
| **Data** | Examples must not rely on external datasets or internet access. |
| **Threading** | Weaverlet apps run single‑threaded by default; no multithreading assumptions. |
| **Network** | Assume localhost only unless user specifies otherwise. |
| **Python version** | 0.3.x requires Python ≥ 3.12. |

---

### 6. Prompt Engineering Guidance

To elicit high‑quality Weaverlet code from an LLM, prompts should include:

- Desired **architecture** (single‑page, multipage, signal flow, or auth).
- Expected **user interaction** (input/output, button clicks, routing events).
- Required **styling framework** (plain Dash, DBC, DMC, or custom).
- Whether **signals** or **store** should manage state.
- Whether **`keep_mounted=True`** is needed (WebGL, persistent per‑page state).

**Example Prompt Template:**

> "Create a multi‑page Weaverlet app with a login page and a dashboard page.
> Use `AuthRouterComponent` for authentication and show user info after login."

> "Build a Weaverlet dashboard with a `dash-leaflet` map on Page A and a chart on Page B.
> The map should not lose its zoom when navigating between pages."
> *(→ enable `keep_mounted=True`; set `preserve_path="/"` if the map is on the home page.)*

---

### 7. Evaluation Metrics (for Fine‑tuning)

| Metric | Description |
|:--|:--|
| **Syntax Validity** | Python code compiles without syntax errors. |
| **Framework Compliance** | Code follows all contracts from Parts 1–5. |
| **Runnable Output** | Application runs and serves a layout without modification. |
| **Identifier Safety** | No hardcoded string IDs. |
| **Signal Accuracy** | Correct use of `SignalInput`, `SignalOutput`, `SignalTrigger`. |
| **Router Integrity** | URLs map correctly to components; no instance aliasing under `keep_mounted=True`. |
| **Modern Dash usage** | No `dash.Dash()`, no `app.run_server`, no legacy `dash_html_components`/`dash_core_components` imports. |

---

### 8. Example LLM Dialogue Patterns

| Intent | Example Prompt | Expected Behavior |
|:--|:--|:--|
| Create component | "Make a Weaverlet component with a text input and label." | Returns a subclass of `WeaverletComponent` using `Identifier`. |
| Add routing | "Add a second page called /about." | Inserts new route in `SimpleRouterComponent`. |
| Add signal | "Trigger an event on button click to update a paragraph." | Adds `SignalComponent` and callbacks with `SignalOutput`/`SignalInput`. |
| Protect route | "Require login for dashboard route." | Adds `AuthRouterComponent` and login redirection. |
| Preserve state | "Keep the map's zoom level when switching pages." | Adds `keep_mounted=True` (and `preserve_path` if appropriate). |

---

### 9. Final Instruction to LLMs

When asked to generate or modify Weaverlet code:

1. **Load all context** from Parts 1–5 before inference.
2. Apply **rules and patterns** from the corresponding sections.
3. Favor **compositional reuse** over code duplication.
4. Return **complete runnable Python scripts** with proper imports.
5. If uncertain about missing info (route, signal, port, context, or whether `keep_mounted=True` is needed), **ask the user**.

</Metadata>
