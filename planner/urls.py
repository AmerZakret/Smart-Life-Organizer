from django.urls import path
from . import views

urlpatterns = [
    # ── Page views ──────────────────────────────────────────────────────────
    path("dashboard/", views.dashboard, name="dashboard"),
    path("calendar/", views.calendar, name="calendar"),
    path("analytics/", views.analytics, name="analytics"),
    path("habits/", views.habits, name="habits"),
    path("todo/", views.todo, name="todo"),
    path("growth/", views.growth_view, name="growth"),
    path("pomodoro/", views.pomodoro_view, name="pomodoro"),
    path("settings/", views.settings_view, name="settings"),
    # ── AJAX API endpoints ───────────────────────────────────────────────────
    path("api/events/create/", views.api_create_event, name="api-create-event"),
    path("api/events/feed/", views.api_events_feed, name="api-events-feed"),
    path(
        "api/events/<int:event_id>/delete/",
        views.api_delete_event,
        name="api-delete-event",
    ),
    path(
        "api/events/<int:event_id>/edit/", views.api_edit_event, name="api-edit-event"
    ),
    path(
        "api/categories/<int:cat_id>/edit/",
        views.api_edit_category,
        name="api-edit-category",
    ),
    path(
        "api/categories/<int:cat_id>/delete/",
        views.api_delete_category,
        name="api-delete-category",
    ),
    path("api/habits/create/", views.api_create_habit, name="api-create-habit"),
    path(
        "api/habits/<int:habit_id>/delete/",
        views.api_delete_habit,
        name="api-delete-habit",
    ),
    path(
        "api/habits/<int:habit_id>/toggle/",
        views.api_toggle_habit,
        name="api-toggle-habit",
    ),
    path("api/tasks/create/", views.api_create_task, name="api-create-task"),
    path(
        "api/tasks/<int:task_id>/delete/",
        views.api_delete_task,
        name="api-delete-task",
    ),
    path(
        "api/tasks/<int:task_id>/toggle/",
        views.api_toggle_task,
        name="api-toggle-task",
    ),
    path(
        "api/pomodoro/complete/",
        views.api_complete_pomodoro,
        name="api-complete-pomodoro",
    ),
    path("export/csv/", views.export_csv, name="export-csv"),
    path("export/ics/", views.export_ics, name="export-ics"),
    path("import/", views.import_events, name="import-events"),
]
