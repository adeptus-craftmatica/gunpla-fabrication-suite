"""pytest-qt tests for the Photography UI: gallery, lightbox, and the library page."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.plugins.photography.ui.lightbox_dialog import LightboxDialog
from gunpla_fabrication_suite.plugins.photography.ui.photo_gallery_widget import (
    PhotoGalleryWidget,
)
from gunpla_fabrication_suite.plugins.photography.ui.photo_library_page import PhotoLibraryPage

_ENTITY_TYPE = "build_planner.build"


def _make_jpeg(path: Path, *, color: tuple[int, int, int] = (10, 120, 200)) -> Path:
    Image.new("RGB", (400, 300), color=color).save(path, "JPEG")
    return path


def _import_and_wait(qtbot, gallery_or_page, paths: list[Path]) -> None:
    gallery_or_page._import_paths(paths)
    qtbot.waitUntil(lambda: gallery_or_page._pending_job_id is None, timeout=5000)


def test_gallery_starts_with_empty_state(qtbot, photo_service, jobs) -> None:
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)

    assert gallery._stack.currentWidget() is gallery._empty_state
    assert gallery._compare_button.isEnabled() is False


def test_importing_a_photo_populates_the_grid(qtbot, photo_service, jobs, tmp_path) -> None:
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)

    _import_and_wait(qtbot, gallery, [_make_jpeg(tmp_path / "wip.jpg")])

    assert len(gallery._photos) == 1
    assert gallery._stack.currentWidget() is gallery._scroll
    assert gallery._grid.count() == 1


def test_importing_two_photos_enables_compare_button(qtbot, photo_service, jobs, tmp_path) -> None:
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)

    _import_and_wait(
        qtbot,
        gallery,
        [
            _make_jpeg(tmp_path / "one.jpg", color=(10, 10, 10)),
            _make_jpeg(tmp_path / "two.jpg", color=(220, 220, 220)),
        ],
    )

    assert gallery._compare_button.isEnabled() is True


def test_set_hero_updates_the_gallery(qtbot, photo_service, jobs, tmp_path) -> None:
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)
    _import_and_wait(qtbot, gallery, [_make_jpeg(tmp_path / "wip.jpg")])

    gallery._set_hero(gallery._photos[0])

    assert gallery._photos[0].is_hero is True


def test_detach_removes_the_photo_from_this_gallery_but_not_the_library(
    qtbot, photo_service, jobs, tmp_path, monkeypatch
) -> None:
    import gunpla_fabrication_suite.plugins.photography.ui.photo_gallery_widget as gallery_module

    monkeypatch.setattr(gallery_module, "confirm_destructive_action", lambda *a, **k: True)
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)
    _import_and_wait(qtbot, gallery, [_make_jpeg(tmp_path / "wip.jpg")])
    photo_id = gallery._photos[0].photo.id

    gallery._detach(gallery._photos[0])

    assert gallery._photos == []
    assert photo_service.get_photo(photo_id) is not None


def test_delete_removes_the_photo_permanently(
    qtbot, photo_service, jobs, tmp_path, monkeypatch
) -> None:
    import gunpla_fabrication_suite.plugins.photography.ui.photo_gallery_widget as gallery_module

    monkeypatch.setattr(gallery_module, "confirm_destructive_action", lambda *a, **k: True)
    gallery = PhotoGalleryWidget(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        entity_type=_ENTITY_TYPE,
        entity_id="build-1",
    )
    qtbot.addWidget(gallery)
    _import_and_wait(qtbot, gallery, [_make_jpeg(tmp_path / "wip.jpg")])
    photo_id = gallery._photos[0].photo.id

    gallery._delete(gallery._photos[0])

    assert gallery._photos == []
    from gunpla_fabrication_suite.plugins.photography.errors import PhotoNotFoundError

    try:
        photo_service.get_photo(photo_id)
    except PhotoNotFoundError:
        pass
    else:
        raise AssertionError("expected PhotoNotFoundError after permanent delete")


def test_library_page_starts_with_empty_state(qtbot, photo_service, jobs, layout_manager) -> None:
    page = PhotoLibraryPage(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
    )
    qtbot.addWidget(page)

    assert page._stack.currentWidget() is page._empty_state


def test_library_page_shows_photos_from_every_build(
    qtbot, photo_service, jobs, layout_manager, tmp_path
) -> None:
    page = PhotoLibraryPage(
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
    )
    qtbot.addWidget(page)

    photo_service.attach(
        photo_service.import_photo(_make_jpeg(tmp_path / "a.jpg", color=(1, 2, 3))).id,
        _ENTITY_TYPE,
        "build-1",
    )
    photo_service.attach(
        photo_service.import_photo(_make_jpeg(tmp_path / "b.jpg", color=(9, 8, 7))).id,
        _ENTITY_TYPE,
        "build-2",
    )
    page.refresh()

    assert len(page._photos) == 2
    assert page._stack.currentWidget() is page._scroll


def test_lightbox_navigates_between_photos(qtbot, photo_service, tmp_path) -> None:
    first = photo_service.import_photo(_make_jpeg(tmp_path / "a.jpg", color=(1, 2, 3)))
    second = photo_service.import_photo(_make_jpeg(tmp_path / "b.jpg", color=(9, 8, 7)))

    dialog = LightboxDialog(
        [first, second], 0, photo_service, NotificationCenter(), on_changed=lambda: None
    )
    qtbot.addWidget(dialog)

    assert dialog._prev_button.isEnabled() is False
    assert dialog._next_button.isEnabled() is True

    dialog._show_next()

    assert dialog._index == 1
    assert dialog._prev_button.isEnabled() is True
    assert dialog._next_button.isEnabled() is False


def test_lightbox_save_button_is_the_dialogs_default_action(qtbot, photo_service, tmp_path) -> None:
    """Regression test: with only one photo, Previous starts disabled and Qt moves
    initial focus to the next focusable button — without ``setAutoDefault(False)``
    on the nav/rotate buttons, that focused button visually steals the "default"
    action from Save (see lightbox_dialog.py's ``nav_row`` construction)."""
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "a.jpg"))

    dialog = LightboxDialog(
        [photo], 0, photo_service, NotificationCenter(), on_changed=lambda: None
    )
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    assert dialog._prev_button.isEnabled() is False
    assert dialog._save_button.isDefault() is True
    for button in (
        dialog._prev_button,
        dialog._next_button,
        dialog._rotate_left_button,
        dialog._rotate_right_button,
    ):
        assert button.autoDefault() is False
        assert button.isDefault() is False


def test_lightbox_rotate_persists_through_the_service(qtbot, photo_service, tmp_path) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "a.jpg"))

    dialog = LightboxDialog(
        [photo], 0, photo_service, NotificationCenter(), on_changed=lambda: None
    )
    qtbot.addWidget(dialog)

    dialog._rotate(90)

    assert photo_service.get_photo(photo.id).rotation_degrees == 90


def test_lightbox_delete_calls_on_changed_and_closes_when_last_photo(
    qtbot, photo_service, tmp_path, monkeypatch
) -> None:
    import gunpla_fabrication_suite.plugins.photography.ui.lightbox_dialog as lightbox_module

    monkeypatch.setattr(lightbox_module, "confirm_destructive_action", lambda *a, **k: True)
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "a.jpg"))
    changed_calls = []

    dialog = LightboxDialog(
        [photo], 0, photo_service, NotificationCenter(), on_changed=lambda: changed_calls.append(1)
    )
    qtbot.addWidget(dialog)

    dialog._delete()

    assert changed_calls == [1]
