from django.urls import path
from . import views

urlpatterns = [
    # ── Page views ──────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard,      name='dashboard'),
    path('calendar/',  views.calendar,       name='calendar'),
    path('settings/',  views.settings_view,  name='settings'),

    # ── AJAX API endpoints ───────────────────────────────────────────────────
    path('api/events/create/',        views.api_create_event,  name='api-create-event'),
    path('api/habits/<int:habit_id>/toggle/', views.api_toggle_habit,   name='api-toggle-habit'),
]
