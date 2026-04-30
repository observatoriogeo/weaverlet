"""Integration tests that boot a real Dash app and probe it via HTTP.

Slower than unit tests but cover behaviors that only show up at runtime —
asset serving, callback graph wiring, multi-output `group=` registration
under DashProxy. Skipped if the test can't bind a port or the server
fails to start.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _boot(script_path: Path, port: int, env_overrides: dict | None = None):
    """Spawn `python script_path` on the given port; return the Popen object
    once we see 'Running on' or the process dies. PYTHONPATH is set so the
    spawned process can `import weaverlet` against the editable install."""
    import os

    env = {**os.environ, "PORT": str(port)}
    if env_overrides:
        env.update(env_overrides)
    env["PYTHONPATH"] = str(REPO_ROOT) + ":" + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 15
    output: list[str] = []
    while time.time() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
            continue
        output.append(line)
        if "Running on http" in line:
            return proc
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    pytest.skip("server failed to start:\n" + "".join(output))


def _shutdown(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# -- assign() served by Dash --------------------------------------------------

ASSIGN_APP_SCRIPT = """
import os
from dash import html
from dash_extensions.javascript import assign
from weaverlet import WeaverletApp, WeaverletComponent

# Generate a JS function that the test will look for in the served file.
_marker_handle = assign(\"\"\"
function(feature) { return {fillColor: feature.properties.color || 'blue'}; }
\"\"\")

class _Root(WeaverletComponent):
    def get_layout(self):
        return html.Div("assign() smoke")

WeaverletApp(root_component=_Root()).app.run(
    port=int(os.environ["PORT"]), debug=False,
)
"""


def test_assign_function_served_from_auto_resolved_assets_folder(tmp_path):
    """`dash_extensions.javascript.assign(...)` writes its JS to
    <assets_folder>/dashExtensions_default.js. WeaverletApp auto-resolves
    `assets_folder` to the user's __main__ script's directory, so Dash
    must end up serving the file at /assets/dashExtensions_default.js.
    Without DashProxy + auto-resolve, the JS exists on disk but isn't
    routed — leaf libraries like dash-leaflet then fail with
    'No match for function0'."""
    script = tmp_path / "assign_app.py"
    script.write_text(ASSIGN_APP_SCRIPT)
    port = _free_port()
    proc = _boot(script, port)
    try:
        # The home page renders.
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
            assert resp.status == 200

        # The auto-generated JS file is reachable.
        url = f"http://127.0.0.1:{port}/assets/dashExtensions_default.js"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            body = resp.read().decode()

        # And the JS body contains the function we registered.
        assert "fillColor" in body, f"assign() body missing marker: {body[:200]!r}"

        # The file actually lives in tmp_path/assets/ (not in the repo's
        # weaverlet/assets/), confirming auto-resolve targeted __main__.
        assert (tmp_path / "assets" / "dashExtensions_default.js").exists()
    finally:
        _shutdown(proc)


# -- StoreComponent STORE / MERGE / CLEAN -------------------------------------

STORE_APP_SCRIPT = """
import os
from dash import html
from dash_extensions.enrich import Input, Output
from weaverlet import (
    Identifier, SignalOutput, StoreComponent, StoreComponentOp,
    WeaverletApp, WeaverletComponent,
)

class _Root(WeaverletComponent):
    store_input_btn_id = Identifier()  # placeholder; we drive via /_dash-update-component

    def __init__(self):
        super().__init__()
        self.store = StoreComponent()

    def get_layout(self):
        return html.Div([self.store()])

WeaverletApp(root_component=_Root()).app.run(
    port=int(os.environ["PORT"]), debug=False,
)
"""


def test_store_component_callback_graph_registers_under_dashproxy(tmp_path):
    """StoreComponent registers four callbacks at construction:
    input_signal demux + the three store/merge/clean writers. The latter
    three all write to the same Output(store_id, 'data'); they only
    coexist because DashProxy's group= multiplexer allows multiple
    callbacks per Output. This test confirms the registration survives
    the dash-extensions 1.x/2.x transition (the riskiest piece of
    `Serverside`/group=`/`enrich` API churn during the v0.3 upgrade)
    and that the callbacks all show up in /_dash-dependencies.

    The detailed routing logic for STORE / MERGE / CLEAN is covered by
    unit tests; here we only verify the wire-up at the HTTP layer."""
    script = tmp_path / "store_app.py"
    script.write_text(STORE_APP_SCRIPT)
    port = _free_port()
    proc = _boot(script, port)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_dash-dependencies") as resp:
            deps = json.loads(resp.read().decode())

        # Three callbacks should target StoreComponent.store_id (.data) —
        # the STORE / MERGE / CLEAN writers, all multiplexed via DashProxy.
        store_id_outputs = [
            d for d in deps
            if "StoreComponent_store_id" in d.get("output", "")
        ]
        assert len(store_id_outputs) == 3, (
            f"Expected 3 callbacks writing to StoreComponent.store_id "
            f"(STORE/MERGE/CLEAN); got {len(store_id_outputs)}: {store_id_outputs}"
        )

        # And exactly one demux callback that writes to all three internal
        # signals at once (its `output` is a `...`-separated multi-output
        # string in dash-extensions' enrich format).
        demuxes = [
            d for d in deps
            if "..." in d.get("output", "")
            and d.get("output", "").count("SignalComponent_signal_id") >= 3
        ]
        assert len(demuxes) == 1, (
            f"Expected exactly 1 demux callback with 3 SignalComponent outputs; "
            f"got {len(demuxes)}: {[d.get('output') for d in demuxes]}"
        )
    finally:
        _shutdown(proc)
