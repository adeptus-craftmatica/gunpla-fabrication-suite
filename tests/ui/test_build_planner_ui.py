"""pytest-qt tests for the Build Planner UI: list, detail, dialogs, and the timer."""

from __future__ import annotations

from PySide6.QtCore import Qt

from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.build_planner.ui.build_detail_view import BuildDetailView
from gunpla_fabrication_suite.plugins.build_planner.ui.build_list_view import BuildListView
from gunpla_fabrication_suite.plugins.build_planner.ui.build_planner_page import BuildPlannerPage
from gunpla_fabrication_suite.plugins.build_planner.ui.continue_building_widget import (
    ContinueBuildingWidget,
)
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
    qtbot, build_service, kit_service, layout_manager
) -> None:
    view = BuildListView(build_service, kit_service, layout_manager, on_select=lambda _id: None)
    qtbot.addWidget(view)

    assert view._stack.currentWidget() is view._empty_state


def test_build_list_view_shows_created_builds_in_table(
    qtbot, build_service, kit_service, layout_manager, existing_kit
) -> None:
    _create_build(build_service, existing_kit, title="Gundam Build")
    view = BuildListView(build_service, kit_service, layout_manager, on_select=lambda _id: None)
    qtbot.addWidget(view)

    assert view._stack.currentWidget() is view._table
    assert view._table.rowCount() == 1
    assert view._table.item(0, 0).text() == "Gundam Build"


def test_build_list_view_kanban_toggle_shows_columns(
    qtbot, build_service, kit_service, layout_manager, existing_kit
) -> None:
    _create_build(build_service, existing_kit)
    view = BuildListView(build_service, kit_service, layout_manager, on_select=lambda _id: None)
    qtbot.addWidget(view)

    view._kanban_checkbox.setChecked(True)

    assert view._stack.currentWidget() is view._kanban_scroll


def test_build_list_view_selecting_row_invokes_callback(
    qtbot, build_service, kit_service, layout_manager, existing_kit
) -> None:
    build = _create_build(build_service, existing_kit)
    selected = []
    view = BuildListView(build_service, kit_service, layout_manager, on_select=selected.append)
    qtbot.addWidget(view)

    view._on_table_row_activated(view._table.item(0, 0))

    assert selected == [build.id]


def test_build_detail_view_shows_title_and_progress(
    qtbot,
    build_service,
    work_session_service,
    journal_service,
    kit_service,
    photo_service,
    jobs,
    layout_manager,
    existing_kit,
) -> None:
    build = _create_build(build_service, existing_kit)
    view = BuildDetailView(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
        build_id=build.id,
        on_back=lambda: None,
    )
    qtbot.addWidget(view)

    assert view._title_label.text() == build.title
    assert view._progress_bar.value() == 0


def test_build_detail_view_start_action_updates_status(
    qtbot,
    build_service,
    work_session_service,
    journal_service,
    kit_service,
    photo_service,
    jobs,
    layout_manager,
    existing_kit,
) -> None:
    build = _create_build(build_service, existing_kit)
    view = BuildDetailView(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
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
    photo_service,
    jobs,
    layout_manager,
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
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
        build_id=build.id,
        on_back=lambda: went_back.append(1),
    )
    qtbot.addWidget(view)

    view._on_archive()

    assert went_back == [1]
    assert build_service.get_build(build.id).is_deleted is True


def test_build_planner_page_navigates_between_list_and_detail(
    qtbot,
    build_service,
    work_session_service,
    journal_service,
    kit_service,
    photo_service,
    jobs,
    layout_manager,
    existing_kit,
) -> None:
    build = _create_build(build_service, existing_kit)
    page = BuildPlannerPage(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
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


def test_journal_widget_refresh_twice_in_a_row_leaves_no_stale_widget(
    qtbot, build_service, journal_service, existing_kit
) -> None:
    """Regression: calling refresh() again before a prior deleteLater() completes
    used to leave two overlapping empty-state widgets visible at once.
    Removing a widget from the layout (``takeAt``) only stops the layout from
    managing it — it stays a visible child of the parent, rendering right on
    top of the new one, until ``deleteLater()``'s deferred deletion actually
    runs. ``takeAt`` alone also makes ``_feed_layout.count()`` look correct
    immediately, which is why this needs to check parentage, not count.
    """
    from gunpla_fabrication_suite.plugins.build_planner.ui.journal_widget import JournalWidget

    build = _create_build(build_service, existing_kit)
    widget = JournalWidget(journal_service, build.id)
    qtbot.addWidget(widget)

    # __init__ already called refresh() once; grab that first empty-state
    # widget, then call refresh() again immediately — simulating
    # BuildDetailView's own refresh() running right after JournalWidget's
    # constructor already self-populated — before any event loop turn could
    # process a deferred deletion.
    first_empty_state = widget._feed_layout.itemAt(0).widget()
    widget.refresh()

    assert widget._feed_layout.count() == 1
    # The old widget must be detached immediately (parent is None), not
    # merely scheduled for deletion — otherwise it stays visible, briefly
    # overlapping the new one, until the event loop gets around to it.
    assert first_empty_state.parent() is None


def test_resume_navigates_to_the_build_planner_page_and_opens_the_build(
    qtbot,
    build_service,
    work_session_service,
    journal_service,
    kit_service,
    photo_service,
    jobs,
    navigator,
    layout_manager,
    existing_kit,
) -> None:
    """Regression test: clicking Resume must actually switch the shell to the
    Build Planner page with that build open, not just prepare the page and
    leave the user to find it themselves (see continue_building_widget.py)."""
    build = _create_build(build_service, existing_kit)
    build_service.start_build(build.id)

    page = BuildPlannerPage(
        build_service=build_service,
        work_session_service=work_session_service,
        journal_service=journal_service,
        kit_service=kit_service,
        photo_service=photo_service,
        jobs=jobs,
        notifications=NotificationCenter(),
        layout_manager=layout_manager,
    )
    qtbot.addWidget(page)

    navigated_to = []
    navigator.navigate_requested.connect(navigated_to.append)

    widget = ContinueBuildingWidget(build_service, kit_service, page, navigator)
    qtbot.addWidget(widget)

    widget._on_resume(page, navigator, build.id)

    assert navigated_to == ["build_planner"]
    assert page._detail_view is not None
    assert page._detail_view._build_id == build.id
    assert page._stack.currentWidget() is page._detail_view
