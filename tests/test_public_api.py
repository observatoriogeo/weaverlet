"""Top-level re-exports + version string."""
from __future__ import annotations

import re

import weaverlet


def test_version_matches_semver_format():
    assert re.match(r"^\d+\.\d+\.\d+$", weaverlet.__version__) is not None


def test_top_level_reexports_present():
    expected = {
        "WeaverletComponent",
        "WeaverletApp",
        "Identifier",
        "RouterComponent",
        "WeaverletException",
        "DetachedComponentRef",
        "DetatchedComponentRef",
        "ComponentsDict",
        "ComponentsList",
        "ComponentsOrderedDict",
        "SignalInput",
        "SignalOutput",
        "SignalState",
        "SignalTrigger",
        "SignalGroup",
        "ServersideSignalOutput",
        "Serverside",
        "SimpleRouterComponent",
        "AuthRouterComponent",
        "RedirectComponent",
        "SignalComponent",
        "DivSignalComponent",
        "EmptyLayoutComponent",
        "StoreComponent",
        "StoreComponentOp",
        "DEFAULT_COMPONENT_NAME",
    }
    missing = expected - set(dir(weaverlet))
    assert not missing, f"missing public exports: {missing}"


def test_all_lists_only_existing_names():
    for name in weaverlet.__all__:
        assert hasattr(weaverlet, name), f"__all__ lists {name!r} but module has no such attr"


def test_legacy_base_imports_still_work():
    """Existing user code that imports from weaverlet.base must keep working."""
    from weaverlet.base import (  # noqa: F401
        WeaverletApp,
        WeaverletComponent,
        Identifier,
        RouterComponent,
        WeaverletException,
        SignalInput,
        SignalOutput,
        SignalTrigger,
        SignalState,
        SignalGroup,
        ServersideSignalOutput,
    )


def test_legacy_components_imports_still_work():
    from weaverlet.components import (  # noqa: F401
        AuthRouterComponent,
        DivSignalComponent,
        EmptyLayoutComponent,
        RedirectComponent,
        SignalComponent,
        SimpleRouterComponent,
        StoreComponent,
        StoreComponentOp,
    )
