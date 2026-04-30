"""Playwright browser test — verifies that `keep_mounted=True` preserves
component state across route changes in a real browser.

Marked `browser` so it can be skipped via `pytest -m "not browser"`. Skipped
automatically if Playwright (or its browser binaries) isn't installed.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def fixture_app_url():
    """Boot tests/fixtures/keep_mounted_app.py on a free port; tear down
    when the module is done."""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.fixtures.keep_mounted_app"],
        cwd=REPO_ROOT,
        env={"PORT": str(port), "PATH": str(Path("/usr/bin"))},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Wait for the ready marker (or up to 15s).
    deadline = time.time() + 15
    ready = False
    output_buf: list[str] = []
    try:
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            output_buf.append(line)
            if "WLT_FIXTURE_READY" in line or "Running on http" in line:
                ready = True
                break
        if not ready:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            pytest.skip(
                "fixture app did not start in time:\n" + "".join(output_buf)
            )
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def browser_context():
    """Module-scoped Playwright browser; skip the whole module if Chromium
    binaries aren't installed (`playwright install chromium`)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # pragma: no cover — environment-dependent
            pytest.skip(f"Chromium not available: {exc}")
        yield browser
        browser.close()


@pytest.mark.browser
def test_keep_mounted_preserves_counter_state_across_routes(
    fixture_app_url, browser_context
):
    """Click the counter on Page A three times, navigate to B, navigate
    back, and assert the counter is still at 3 — the whole point of
    `keep_mounted=True`."""
    def _click_visible(selector_text: str, role: str = "a"):
        """Click whichever of the matching elements is currently visible.
        Both pages mount their own copy at startup, so multiple matches
        exist — only one is visible at a time."""
        for el in page.locator(role, has_text=selector_text).all():
            if el.is_visible():
                el.click()
                return
        raise AssertionError(
            f"No visible {role!r} element with text {selector_text!r} found"
        )

    context = browser_context.new_context()
    page = context.new_page()
    try:
        page.goto(fixture_app_url, wait_until="networkidle")

        # Click the visible counter button three times (Page A's button).
        for _ in range(3):
            _click_visible("Click me", role="button")
        page.wait_for_selector("[data-testid='out-A']:has-text('clicks: 3')")

        # Navigate to /b via the visible "Go to B" link — SPA-style nav
        # through dcc.Location, so wrappers stay mounted (a hard page.goto()
        # would reload the whole app and destroy the React state we're
        # testing).
        _click_visible("Go to B")
        page.wait_for_url("**/b")

        # Click Page B's counter once.
        _click_visible("Click me", role="button")
        page.wait_for_selector("[data-testid='out-B']:has-text('clicks: 1')")

        # Navigate back to "/" the same SPA-style way.
        _click_visible("Go to A")
        page.wait_for_url(fixture_app_url + "/")

        # Page A's counter should STILL show "clicks: 3" — that's
        # keep_mounted=True doing its job (the component was hidden but
        # never unmounted, so React preserved its state).
        out_a_text = page.locator("[data-testid='out-A']").inner_text()
        assert "clicks: 3" in out_a_text, (
            f"Expected Page A counter to survive navigation, got: {out_a_text!r}"
        )

        # Page B's "clicks: 1" survived too (its wrapper is hidden now,
        # but inner_text still returns the DOM text content).
        out_b_text = page.locator("[data-testid='out-B']").inner_text()
        assert "clicks: 1" in out_b_text, (
            f"Expected Page B counter to survive navigation, got: {out_b_text!r}"
        )
    finally:
        context.close()
