"""The Photography plugin: managed progress-photo storage, galleries, and comparisons.

Scope for this milestone, deliberately: photos attach to any entity via a
polymorphic ``PhotoRelationship`` (``entity_type`` + ``entity_id``, no SQL
foreign key into another plugin's tables — the same decoupling pattern used
by Build Planner's ``kit_id`` reference). Cropping, basic annotations, and
per-stage/per-journal-entry attachment granularity are not implemented yet;
Build Planner attaches photos at the whole-build level for now. Full-
resolution images are never stored in SQLite — only paths into the managed
``media/`` directory (see ``core.paths.ApplicationPaths``).

Image processing (hashing, thumbnail/preview generation) always runs off
the Qt UI thread through the core ``BackgroundJobManager`` — see
``services/media_processor.py``.
"""

from __future__ import annotations
