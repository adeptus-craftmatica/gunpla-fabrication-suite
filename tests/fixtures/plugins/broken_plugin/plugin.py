"""A fixture plugin that always fails during registration, used to test failure isolation."""

from __future__ import annotations


class BrokenPlugin:
    plugin_id = "test.plugin.broken"

    def register(self, context) -> None:
        raise RuntimeError("this plugin is intentionally broken")

    def initialize(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
