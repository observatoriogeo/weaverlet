"""CSS style sets used by routers in `keep_mounted=True` mode.

The preserve_path wrapper stays mounted with `visibility:hidden` when not
active (so its WebGL canvas survives a route change); other route wrappers
use `display:none` which is cleaner for the document flow. Visible routes
that aren't the preserve_path render as a `position:absolute` overlay on
top of the preserve_path's reserved flow — so there's no blank gap when
the preserve_path is hidden.
"""

VISIBLE_STYLE = {
    "position": "relative",
    "visibility": "visible",
    "pointerEvents": "auto",
    "zIndex": 1,
}

HIDDEN_STYLE_PRESERVE = {
    "position": "relative",
    "visibility": "hidden",
    "pointerEvents": "none",
}

HIDDEN_STYLE_DISPLAY_NONE = {"display": "none"}

VISIBLE_STYLE_OVERLAY = {
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "zIndex": 2,
}
