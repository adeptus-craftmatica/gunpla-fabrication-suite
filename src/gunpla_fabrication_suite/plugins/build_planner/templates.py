"""Built-in build templates: starting stage lists for a new build project.

These are plain Python data, not a database table — see the module
docstring in ``__init__.py`` for why. Once a build is created, its stages
are materialized as real, per-project
:class:`~gunpla_fabrication_suite.plugins.build_planner.models.build_stage.BuildStage`
rows that the user can freely reorder, rename, add to, or remove.
"""

from __future__ import annotations

from dataclasses import dataclass

from gunpla_fabrication_suite.plugins.build_planner.errors import UnknownTemplateError


@dataclass(frozen=True, slots=True)
class BuildTemplate:
    """A named, ordered list of default stage names for a new build."""

    key: str
    label: str
    stage_names: tuple[str, ...]


_STRAIGHT = (
    "Planning",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Final Assembly",
    "Photography",
    "Completed",
)

_PANEL_LINED = (
    "Planning",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Panel Lining",
    "Final Assembly",
    "Photography",
    "Completed",
)

_FULLY_PAINTED = (
    "Planning",
    "Reference Gathering",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Seam Removal",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Masking",
    "Panel Lining",
    "Decals",
    "Top Coating",
    "Final Assembly",
    "Photography",
    "Completed",
)

_WEATHERED = (
    "Planning",
    "Reference Gathering",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Seam Removal",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Masking",
    "Panel Lining",
    "Decals",
    "Weathering",
    "Top Coating",
    "Final Assembly",
    "Photography",
    "Completed",
)

_COMPETITION = (
    "Planning",
    "Reference Gathering",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Seam-Line Planning",
    "Seam Removal",
    "Scribing",
    "Detail Modification",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Masking",
    "Panel Lining",
    "Decals",
    "Weathering",
    "Top Coating",
    "Final Assembly",
    "Photography",
    "Packaging or Display",
    "Completed",
)

_CUSTOM_CONVERSION = (
    "Planning",
    "Reference Gathering",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Detail Modification",
    "Scribing",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Panel Lining",
    "Top Coating",
    "Final Assembly",
    "Photography",
    "Completed",
)

_DIORAMA = (
    "Planning",
    "Reference Gathering",
    "Initial Assembly",
    "Detail Modification",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Weathering",
    "Final Assembly",
    "Photography",
    "Packaging or Display",
    "Completed",
)

_COMMISSION = (
    "Planning",
    "Reference Gathering",
    "Runner Inspection",
    "Parts Washing",
    "Initial Assembly",
    "Surface Preparation",
    "Priming",
    "Base Coating",
    "Detail Painting",
    "Masking",
    "Panel Lining",
    "Decals",
    "Weathering",
    "Top Coating",
    "Final Assembly",
    "Photography",
    "Packaging or Display",
    "Completed",
)

BUILTIN_TEMPLATES: tuple[BuildTemplate, ...] = (
    BuildTemplate(key="straight_build", label="Straight Build", stage_names=_STRAIGHT),
    BuildTemplate(key="panel_lined", label="Panel-Lined Build", stage_names=_PANEL_LINED),
    BuildTemplate(key="fully_painted", label="Fully Painted Build", stage_names=_FULLY_PAINTED),
    BuildTemplate(key="weathered", label="Weathered Build", stage_names=_WEATHERED),
    BuildTemplate(key="competition", label="Competition Build", stage_names=_COMPETITION),
    BuildTemplate(
        key="custom_conversion", label="Custom Conversion", stage_names=_CUSTOM_CONVERSION
    ),
    BuildTemplate(key="diorama", label="Diorama Build", stage_names=_DIORAMA),
    BuildTemplate(key="commission", label="Commission Build", stage_names=_COMMISSION),
)

_TEMPLATES_BY_KEY = {template.key: template for template in BUILTIN_TEMPLATES}


def get_template(key: str) -> BuildTemplate:
    """Look up a built-in template by its key.

    Raises:
        UnknownTemplateError: If no template is registered under ``key``.
    """
    try:
        return _TEMPLATES_BY_KEY[key]
    except KeyError:
        raise UnknownTemplateError(key) from None
