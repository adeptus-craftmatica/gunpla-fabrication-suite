"""An explicit service registry used for dependency injection.

There is no reflection-based auto-wiring here on purpose: every service is
registered explicitly by the code that owns it (core bootstrap or a plugin's
``register`` step), and every consumer asks for it explicitly by type. This
keeps dependency graphs traceable without a "magic" DI framework.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_Factory = Callable[[], object]


class ServiceNotRegisteredError(KeyError):
    """Raised when a service is requested that no one has registered."""

    def __init__(self, service_type: type) -> None:
        super().__init__(f"No service registered for {service_type!r}")
        self.service_type = service_type


class ServiceContainer:
    """A typed registry mapping service interfaces to instances or factories."""

    def __init__(self) -> None:
        self._instances: dict[type, object] = {}
        self._factories: dict[type, _Factory] = {}

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """Register a concrete, already-constructed singleton instance."""
        self._instances[service_type] = instance

    def register_factory(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """Register a factory invoked lazily the first time the service is resolved."""
        self._factories[service_type] = factory

    def resolve(self, service_type: type[T]) -> T:
        """Return the registered instance for ``service_type``.

        Raises:
            ServiceNotRegisteredError: If nothing was registered for the type.
        """
        if service_type in self._instances:
            return self._instances[service_type]  # type: ignore[return-value]

        if service_type in self._factories:
            instance = self._factories[service_type]()
            self._instances[service_type] = instance
            return instance  # type: ignore[return-value]

        raise ServiceNotRegisteredError(service_type)

    def try_resolve(self, service_type: type[T]) -> T | None:
        """Return the registered instance for ``service_type``, or ``None``."""
        try:
            return self.resolve(service_type)
        except ServiceNotRegisteredError:
            return None

    def is_registered(self, service_type: type) -> bool:
        """Return whether ``service_type`` has an instance or factory registered."""
        return service_type in self._instances or service_type in self._factories
