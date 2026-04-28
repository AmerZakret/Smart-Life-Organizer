import json
import logging
from datetime import timedelta

import plotly.express as px
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_engine.models import AITip
from .models import Event, Habit

logger = logging.getLogger(__name__)


# ── Page views ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user_profile = request.user.userprofile
    today = timezone.now().date()

    events_today = Event.objects.filter(
        user=user_profile,
        start_time__date=today,
    ).order_by('start_time')

    habits = Habit.objects.filter(user=user_profile)

    active_tip = AITip.objects.filter(
        event__user=user_profile,
        event__start_time__gte=timezone.now(),
        is_notified=False,
    ).select_related('event').first()

    # Plotly pie chart
    categories = [e.category for e in events_today]
    if categories:
        cat_counts = {c: categories.count(c) for c in set(categories)}
        fig = px.pie(
            names=list(cat_counts.keys()),
            values=list(cat_counts.values()),
            title="Today's Events by Category",
            color_discrete_sequence=['#0d9488', '#0ea5e9', '#a855f7'],
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter, sans-serif', size=12),
        )
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        chart_html = ""

    context = {
        'events_today': events_today,
        'habits': habits,
        'active_tip': active_tip,
        'chart_html': chart_html,
    }
    return render(request, 'planner/dashboard.html', context)


@login_required
def calendar(request):
    user_profile = request.user.userprofile
    events = (
        Event.objects
        .filter(user=user_profile)
        .select_related('aitip')
        .order_by('start_time')
    )
    context = {'events': events}
    return render(request, 'planner/calendar.html', context)


@login_required
def settings_view(request):
    user_profile = request.user.userprofile
    if request.method == 'POST':
        user_profile.timezone = request.POST.get('timezone', 'UTC')
        user_profile.ai_tone = request.POST.get('ai_tone', 'direct')
        user_profile.save()
        return redirect('dashboard')

    context = {
        'profile': user_profile,
        'tones': user_profile.TONE_CHOICES,
    }
    return render(request, 'planner/settings.html', context)


# ── AJAX API endpoints ────────────────────────────────────────────────────────

@login_required
@require_POST
def api_create_event(request):
    """
    POST /api/events/create/
    ─────────────────────────
    Accepts a JSON body with event fields, creates the Event row, and returns
    a JSON response.  The post_save signal in ai_engine will asynchronously
    generate an AITip in the background.

    Request body (JSON)
    -------------------
    {
        "title":       str  (required, max 150 chars)
        "description": str  (optional)
        "start_time":  str  ISO 8601 datetime-local format "YYYY-MM-DDTHH:MM"
        "end_time":    str  ISO 8601 datetime-local format "YYYY-MM-DDTHH:MM"
        "category":    str  "Work" | "Health" | "Personal"
    }

    Response 200 (success)
    ----------------------
    {"success": true, "title": ..., "start_time": ..., "end_time": ..., "category": ...}

    Response 400 (validation error)
    --------------------------------
    {"success": false, "error": "..."}
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)

    title      = data.get('title', '').strip()
    description = data.get('description', '').strip()
    start_raw  = data.get('start_time', '').strip()
    end_raw    = data.get('end_time', '').strip()
    category   = data.get('category', '').strip()

    # ── Validation ────────────────────────────────────────────────────────────
    if not title:
        return JsonResponse({'success': False, 'error': 'Title is required.'}, status=400)
    if len(title) > 150:
        return JsonResponse({'success': False, 'error': 'Title must be ≤ 150 characters.'}, status=400)
    if not start_raw or not end_raw:
        return JsonResponse({'success': False, 'error': 'Start and end times are required.'}, status=400)
    if category not in ('Work', 'Health', 'Personal'):
        return JsonResponse({'success': False, 'error': 'Invalid category.'}, status=400)

    # Parse datetime-local strings (HTML format: "YYYY-MM-DDTHH:MM")
    from django.utils.dateparse import parse_datetime
    start_time = parse_datetime(start_raw)
    end_time   = parse_datetime(end_raw)

    if start_time is None or end_time is None:
        return JsonResponse({'success': False, 'error': 'Invalid datetime format.'}, status=400)

    # Make datetimes timezone-aware using Django's current timezone
    if timezone.is_naive(start_time):
        start_time = timezone.make_aware(start_time)
    if timezone.is_naive(end_time):
        end_time = timezone.make_aware(end_time)

    if end_time <= start_time:
        return JsonResponse({'success': False, 'error': 'End time must be after start time.'}, status=400)

    # ── Create ────────────────────────────────────────────────────────────────
    user_profile = request.user.userprofile
    event = Event.objects.create(
        user=user_profile,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        category=category,
    )
    logger.info("Event '%s' (id=%s) created for user '%s'.", title, event.pk, request.user.username)

    return JsonResponse({
        'success':    True,
        'id':         event.pk,
        'title':      event.title,
        'start_time': event.start_time.isoformat(),
        'end_time':   event.end_time.isoformat(),
        'category':   event.category,
    }, status=201)


@login_required
@require_POST
def api_toggle_habit(request, habit_id):
    """
    POST /api/habits/<id>/toggle/
    ──────────────────────────────
    Marks today as the last completed date for the given habit and increments
    the streak counter by 1.  Idempotent: toggling twice on the same day does
    not double-count.

    Response 200
    ------------
    {"success": true, "new_streak": int, "last_completed": "YYYY-MM-DD"}

    Response 400 / 404
    ------------------
    {"success": false, "error": "..."}
    """
    user_profile = request.user.userprofile

    try:
        habit = Habit.objects.get(pk=habit_id, user=user_profile)
    except Habit.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Habit not found.'}, status=404)

    today = timezone.now().date()

    # Idempotency: don't increment if already toggled today
    if habit.last_completed_date == today:
        return JsonResponse({
            'success':        True,
            'new_streak':     habit.current_streak,
            'last_completed': str(today),
            'already_done':   True,
        })

    habit.current_streak      += 1
    habit.last_completed_date  = today
    habit.save(update_fields=['current_streak', 'last_completed_date'])

    logger.info(
        "Habit '%s' (id=%s) toggled for user '%s'. New streak: %s.",
        habit.name, habit.pk, request.user.username, habit.current_streak,
    )

    return JsonResponse({
        'success':        True,
        'new_streak':     habit.current_streak,
        'last_completed': str(today),
        'already_done':   False,
    })
