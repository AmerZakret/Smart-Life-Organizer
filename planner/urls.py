from django.urls import path
from . import views

urlpatterns = [
    # ── Page views ──────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard,      name='dashboard'),
    path('calendar/',  views.calendar,       name='calendar'),
    path('settings/',  views.settings_view,  name='settings'),

    # ── AJAX API endpoints ───────────────────────────────────────────────────
    path('api/events/create/',        views.api_create_event,  name='api-create-event'),
    path('api/habits/create/',        views.api_create_habit,  name='api-create-habit'),
    path('api/habits/<int:habit_id>/toggle/', views.api_toggle_habit,   name='api-toggle-habit'),
    path('export/csv/', views.export_csv, name='export-csv'),
    path('export/ics/', views.export_ics, name='export-ics'),
    path('import/', views.import_events, name='import-events'),
]
