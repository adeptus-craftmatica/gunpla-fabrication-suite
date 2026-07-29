"""pytest-qt tests for the Build Planner UI: list, detail, dialogs, and the timer."""

from __future__ import annotations

from PySide6.QtCore import Qt

from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.build_planner.ui.build_detail_view import BuildDetailView
from gunpla_fabrication_suite.plugins.build_planner.ui.build_list_view import BuildListView
from gunpla_fabrication_suite.plugins.build_planner.ui.build_planner_page import BuildPlannerPage
from gunpla_fabrication_suite.plugins.build_planner.ui.new_build_dialog import NewBuildDialog
from gunpla_fabrication_suite.plugins.build_planner.ui.stage_tree_widget import StageTreeWidget


def _create_build(build_service, existing_kit, title="Test Build", template_key="straight_build"):
    return build_service.create_build(
        BuildProjectCreate(kit_id=existing_kit.id, title=title, template_key=template_key)
    )


def test_new_build_dialog_populates_kits_and_templates(qtbot, kit_service, existing_kit) -> None:
    dialog = NewBuildDialog(kit_service)
    qtbot.addWidget(dialog)

    assert dialog._kit_combo.count() == 1
    assert dialog._template_combo.count() >= 8
    assert dialog._title_edit.text() == existing_kit.name


def test_new_build_dialog_accept_produces_create_payload(qtbot, kit_service, existing_kit) -> None:
    dialog = NewBuildDialog(kit_service)
    qtbot.addWidget(dialog)

    dialog._on_accept()

    data = dialog.result_data()
    assert data is not None
    assert data.kit_id == existing_kit.id
    assert data.title == existing_kit.name


def test_new_build_dialog_with_no_kits_disables_combo(qtbot, kit_service) -> None:
    dialog = NewBuildDialog(kit_service)
    qtbot.addWidget(dialog)

    assert dialog._kit_combo.isEnabled() is False


def test_stage_tree_widget_shows_template_stages(qtbot, build_service, existing_kit) -> None:
    build = _create_build(build_service, existing_kit, template_key="panel_lined")
    tree = StageTreeWidget(build_service, build.id, on_changed=lambda: None)
    qtbot.addWidget(tree)

    assert tree._tree.topLevelItemCount() == 8
    assert tree._tree.topLevelItem(0).text(0).startswith("Planning")


def test_stage_tree_widget_checkbox_toggles_stage_completion(
    qtbot, build_service, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    changed_calls = []
    tree = StageTreeWidget(build_service, build.id, on_changed=lambda: changed_calls.append(1))
    qtbot.addWidget(tree)

    item = tree._tree.topLevelItem(0)
    item.setCheckState(0, Qt.CheckState.Checked)

    stages = build_service.list_stages(build.id)
    assert stages[0].is_completed is True

    qtbot.waitUntil(lambda: len(changed_calls) >= 1)


def test_stage_tree_widget_add_and_remove_stage(qtbot, build_service, existing_kit) -> None:
    build = _create_build(build_service, existing_kit)
    tree = StageTreeWidget(build_service, build.id, on_changed=lambda: None)
    qtbot.addWidget(tree)
    initial_count = tree._tree.topLevelItemCount()

    new_stage = build_service.add_stage(build.id, "Extra Stage")
    tree.refresh()
    assert tree._tree.topLevelItemCount() == initial_count + 1

    build_service.remove_stage(new_stage.id)
    tree.refresh()
    assert tree._tree.topLevelItemCount() == initial_count


def test_build_list_view_shows_empty_state_with_no_builds(
    qtbot, build_service, kit_service
) -> None:
    view = BuildListView(build_service, kit_service, on_select=lambda _id: None)
    qtbot.addWidget(view)

    assert view._stack.currentWidget() is view._empty_state


def test_build_list_view_shows_created_builds_in_table(
    qtbot, build_service, kit_service, existing_kit
) -> None:
    _create_build(build_service, existing_kit, title="Gundam Build")
    view = BuildListView(build_service, kit_service, on_select=lambda _id: None)
    qtbot.addWidget(view)

    assert view._stack.currentWidget() is view._table
    assert view._table.rowCount() == 1
    assert view._table.item(0, 0).text() == "Gundam Build"


def test_build_list_view_kanban_toggle_shows_columns(
    qtbot, build_service, kit_service, existing_kit
) -> None:
    _create_build(build_service, existing_kit)
    view = BuildListView(build_service, kit_service, on_select=lambda _id: None)
    qtbot.addWidget(view)

    view._kanban_checkbox.setChecked(True)

    assert view._stack.currentWidget() is view._kanban_scroll


def test_build_list_view_selecting_row_invokes_callback(
    qtbot, build_service, kit_service, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    selected = []
    view = BuildListView(build_service, kit_service, on_select=selected.append)
    qtbot.addWidget(view)

    view._on_table_row_activated(view._table.item(0, 0))

    assert selected == [build.id]


def test_build_detail_view_shows_title_and_progress(
    qtbot, build_service, work_session_service, journal_service, kit_service, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    view = BuildDetailView(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        notifications=NotificationCenter(),
        build_id=build.id,
        on_back=lambda: None,
    )
    qtbot.addWidget(view)

    assert view._title_label.text() == build.title
    assert view._progress_bar.value() == 0


def test_build_detail_view_start_action_updates_status(
    qtbot, build_service, work_session_service, journal_service, kit_service, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    view = BuildDetailView(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        notifications=NotificationCenter(),
        build_id=build.id,
        on_back=lambda: None,
    )
    qtbot.addWidget(view)

    view._on_start()

    assert build_service.get_build(build.id).status == "in_progress"
    assert "In Progress" in view._status_label.text()


def test_build_detail_view_archive_calls_on_back(
    qtbot,
    monkeypatch,
    build_service,
    work_session_service,
    journal_service,
    kit_service,
    existing_kit,
) -> None:
    import gunpla_fabrication_suite.plugins.build_planner.ui.build_detail_view as detail_module

    monkeypatch.setattr(detail_module, "confirm_destructive_action", lambda *a, **k: True)
    build = _create_build(build_service, existing_kit)
    went_back = []
    view = BuildDetailView(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        notifications=NotificationCenter(),
        build_id=build.id,
        on_back=lambda: went_back.append(1),
    )
    qtbot.addWidget(view)

    view._on_archive()

    assert went_back == [1]
    assert build_service.get_build(build.id).is_deleted is True


def test_build_planner_page_navigates_between_list_and_detail(
    qtbot, build_service, work_session_service, journal_service, kit_service, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    page = BuildPlannerPage(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        notifications=NotificationCenter(),
    )
    qtbot.addWidget(page)

    page.show_build(build.id)
    assert page._detail_view is not None
    assert page._stack.currentWidget() is page._detail_view

    page.show_list()
    assert page._stack.currentWidget() is page._list_view
    assert page._detail_view is None


def test_timer_widget_start_and_stop_flow(
    qtbot, work_session_service, build_service, existing_kit
) -> None:
    from gunpla_fabrication_suite.plugins.build_planner.ui.timer_widget import TimerWidget

    build = _create_build(build_service, existing_kit)
    widget = TimerWidget(
        work_session_service, build.id, NotificationCenter(), on_changed=lambda: None
    )
    qtbot.addWidget(widget)

    widget._on_start()
    assert work_session_service.get_active_session() is not None
    assert widget._stop_button.isEnabled() is True

    active = work_session_service.get_active_session()
    work_session_service.stop_timer(active.id)
    widget.refresh()

    assert work_session_service.get_active_session() is None
    assert widget._start_button.isEnabled() is True
