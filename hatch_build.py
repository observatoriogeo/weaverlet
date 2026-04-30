"""Hatchling metadata hook — rewrites README.md image paths to absolute URLs
when building the PyPI artifacts.

Why this exists:
- README.md uses a *relative* image path so GitHub renders the logo natively
  with full PNG transparency (GitHub serves repo-local files directly,
  bypassing the camo image proxy that otherwise adds a backdrop).
- PyPI renders the package description as a standalone HTML page and has no
  context for relative paths, so a relative `<img src="logo.png">` shows
  broken on the PyPI project page.
- This hook reads README.md at build time, substitutes the relative image
  path with an absolute jsDelivr CDN URL pointing at the same file in the
  GitHub repo, and exposes the result as the package's PyPI long-description
  via `[project] dynamic = ["readme"]`.

The README.md committed to git stays GitHub-friendly; PyPI sees the
transformed version. Single source of truth, no second README to keep in
sync.
"""
from __future__ import annotations

from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface

# Relative paths in the README that need to become absolute jsDelivr URLs
# for PyPI. Keyed on the path string as it appears in README.md.
_REPO_OWNER_AND_NAME = "observatoriogeo/weaverlet"
_BRANCH = "main"
_PYPI_URL_REWRITES: dict[str, str] = {
    # Logo image — rendered <img src="..."> in the README.
    "FullLogo_Transparent_NoBuffer.png": (
        f"https://cdn.jsdelivr.net/gh/{_REPO_OWNER_AND_NAME}@{_BRANCH}/"
        "FullLogo_Transparent_NoBuffer.png"
    ),
}


class WeaverletReadmeHook(MetadataHookInterface):
    """Replace `dynamic = ["readme"]` with the transformed README content."""

    def update(self, metadata: dict) -> None:
        readme_path = Path(self.root) / "README.md"
        text = readme_path.read_text(encoding="utf-8")
        for relative, absolute in _PYPI_URL_REWRITES.items():
            text = text.replace(f'src="{relative}"', f'src="{absolute}"')
            text = text.replace(f"]({relative})", f"]({absolute})")
        metadata["readme"] = {
            "content-type": "text/markdown",
            "text": text,
        }
