"""Tests for the explicit dependency-injection service container."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.core.services.container import ServiceNotRegisteredError


class _Greeter:
    def greet(self) -> str:
        return "hello"


def test_resolve_returns_registered_instance() -> None:
    container = ServiceContainer()
    instance = _Greeter()
    container.register_instance(_Greeter, instance)

    assert container.resolve(_Greeter) is instance


def test_resolve_raises_for_unregistered_type() -> None:
    container = ServiceContainer()

    with pytest.raises(ServiceNotRegisteredError):
        container.resolve(_Greeter)


def test_try_resolve_returns_none_for_unregistered_type() -> None:
    container = ServiceContainer()

    assert container.try_resolve(_Greeter) is None


def test_factory_is_invoked_lazily_and_only_once() -> None:
    container = ServiceContainer()
    call_count = 0

    def factory() -> _Greeter:
        nonlocal call_count
        call_count += 1
        return _Greeter()

    container.register_factory(_Greeter, factory)
    assert call_count == 0

    first = container.resolve(_Greeter)
    second = container.resolve(_Greeter)

    assert call_count == 1
    assert first is second


def test_is_registered_reflects_instances_and_factories() -> None:
    container = ServiceContainer()
    assert container.is_registered(_Greeter) is False

    container.register_instance(_Greeter, _Greeter())
    assert container.is_registered(_Greeter) is True
