"""Shared spacing and typography tokens.

Every page repeated its own slightly different literal for "page title"
styling (22px here, 20px there, 18px somewhere else). This constant is the
single source of truth so pages read as one cohesive application instead of
a collection of separately-styled screens.

Color-bearing text styles (secondary text, section titles, captions) live
in ``shared_ui/labels.py``'s role system instead of here, since a plain
string constant baked once at import time can't react to a live theme
switch — see ``labels.py``'s docstring.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Spacing:
    """A consistent spacing scale, in pixels."""

    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24


SPACING = Spacing()

#: A page's main `<h1>`-equivalent title (one per page, top-left). No color
#: override needed — it inherits the theme's primary text color already.
PAGE_TITLE = "font-size: 22px; font-weight: 600;"
