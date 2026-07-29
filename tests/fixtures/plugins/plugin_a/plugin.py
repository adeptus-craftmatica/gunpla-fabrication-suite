"""A fixture plugin with no dependencies, used to test plugin load ordering."""

from __future__ import annotations


class PluginA:
    plugin_id = "test.plugin.a"

    def register(self, context) -> None:
        self._context = context

    def initialize(self) -> None:
        pass

    def start(self) -> None:
        log_path = self._context.paths.root / "load_order.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{self.plugin_id}\n")

    def stop(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
