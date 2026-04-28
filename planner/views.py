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
from .models import Event, Habit, Category
from .utils import expand_events_for_range
import csv
from django.http import HttpResponse
from icalendar import Calendar, Event as IcsEvent
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

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
    # category is now a FK to Category; use its name for counts
    categories = [e.category.name for e in events_today if e.category]
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
    # Show events for the next 30 days (expand recurring events)
    from django.utils import timezone
    now = timezone.now()
    window_end = now + timezone.timedelta(days=30)

    events_qs = Event.objects.filter(user=user_profile).select_related('aitip')
    occurrences = expand_events_for_range(events_qs, now, window_end)
    context = {'events': occurrences}
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

    # Optional recurrence fields
    rrule_raw = data.get('rrule') or None
    recurrence_end_raw = data.get('recurrence_end') or None

    # ── Create ────────────────────────────────────────────────────────────────
    user_profile = request.user.userprofile
    # Ensure category is a Category instance (FK)
    category_obj, _ = Category.objects.get_or_create(
        user=user_profile,
        name=category,
        defaults={'color': '#0d9488'}
    )

    event = Event.objects.create(
        user=user_profile,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        category=category_obj,
        rrule=rrule_raw,
        recurrence_end=(lambda v: (timezone.make_aware(parse_datetime(v)) if timezone.is_naive(parse_datetime(v)) else parse_datetime(v))) (recurrence_end_raw) if recurrence_end_raw else None,
    )
    logger.info("Event '%s' (id=%s) created for user '%s'.", title, event.pk, request.user.username)

    return JsonResponse({
        'success':    True,
        'id':         event.pk,
        'title':      event.title,
        'start_time': event.start_time.isoformat(),
        'end_time':   event.end_time.isoformat(),
        'category':   event.category.name if event.category else None,
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


@login_required
@require_GET
def export_csv(request):
    """Export user's Events and Habits as CSV."""
    user_profile = request.user.userprofile

    # Events
    events = Event.objects.filter(user=user_profile).order_by('start_time')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="smartlife_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['type', 'title', 'start_time', 'end_time', 'category', 'description'])
    for e in events:
        writer.writerow(['event', e.title, e.start_time.isoformat(), e.end_time.isoformat(), e.category.name if e.category else '', e.description])

    # Habits
    habits = Habit.objects.filter(user=user_profile)
    for h in habits:
        writer.writerow(['habit', h.name, '', '', '', ''])

    return response


@login_required
@require_GET
def export_ics(request):
    """Export user's events as an .ics calendar."""
    user_profile = request.user.userprofile
    events = Event.objects.filter(user=user_profile)

    cal = Calendar()
    cal.add('prodid', '-//Smart Life Organizer//')
    cal.add('version', '2.0')

    for e in events:
        comp = IcsEvent()
        comp.add('summary', e.title)
        comp.add('dtstart', e.start_time)
        comp.add('dtend', e.end_time)
        if e.rrule:
            # naive: set raw RRULE string (icalendar expects dict-like vRecur)
            for part in e.rrule.split(';'):
                if not part:
                    continue
                k, v = part.split('=')
                comp.add('rrule', {k: v})
        comp.add('description', e.description or '')
        cal.add_component(comp)

    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="smartlife_events.ics"'
    return response


@login_required
def import_events(request):
    """Simple upload handler to import CSV or ICS files."""
    user_profile = request.user.userprofile
    if request.method == 'POST':
        f = request.FILES.get('file')
        if not f:
            return JsonResponse({'success': False, 'error': 'No file uploaded.'}, status=400)

        name = f.name.lower()
        created = 0
        if name.endswith('.csv'):
            text = f.read().decode('utf-8')
            reader = csv.reader(text.splitlines())
            for row in reader:
                if not row:
                    continue
                if row[0].lower() == 'event' and len(row) >= 6:
                    title = row[1]
                    try:
                        start = timezone.datetime.fromisoformat(row[2])
                        end = timezone.datetime.fromisoformat(row[3])
                    except Exception:
                        continue
                    cat_name = row[4]
                    cat = None
                    if cat_name:
                        cat, _ = Category.objects.get_or_create(user=user_profile, name=cat_name)
                    Event.objects.create(user=user_profile, title=title, start_time=start, end_time=end, category=cat, description=row[5])
                    created += 1
                elif row[0].lower() == 'habit' and len(row) >= 2:
                    Habit.objects.get_or_create(user=user_profile, name=row[1])
                    created += 1

        elif name.endswith('.ics'):
            data = f.read()
            try:
                cal = Calendar.from_ical(data)
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid ICS file.'}, status=400)
            for component in cal.walk():
                if component.name == 'VEVENT':
                    title = str(component.get('summary'))
                    dtstart = component.get('dtstart').dt
                    dtend = component.get('dtend').dt if component.get('dtend') else (dtstart + timezone.timedelta(hours=1))
                    rrule = component.get('rrule')
                    rrule_str = None
                    if rrule:
                        # Convert vRecur dict to RFC string
                        parts = []
                        for k, v in rrule.items():
                            parts.append(f"{k}={','.join(v)}")
                        rrule_str = ';'.join(parts)
                    Event.objects.create(user=user_profile, title=title, start_time=dtstart, end_time=dtend, rrule=rrule_str)
                    created += 1
        else:
            return JsonResponse({'success': False, 'error': 'Unsupported file type.'}, status=400)

        return JsonResponse({'success': True, 'created': created})

    # GET -> render a simple upload form
    return render(request, 'planner/import_form.html')


@login_required
@require_POST
def api_create_habit(request):
    """
    POST /api/habits/create/
    Body: { "name": "Drink water" }
    Returns habit JSON.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name is required.'}, status=400)
    if len(name) > 100:
        return JsonResponse({'success': False, 'error': 'Name must be ≤ 100 characters.'}, status=400)

    user_profile = request.user.userprofile
    habit, created = Habit.objects.get_or_create(user=user_profile, name=name)

    status = 201 if created else 200
    return JsonResponse({
        'success': True,
        'id': habit.pk,
        'name': habit.name,
        'current_streak': habit.current_streak,
        'last_completed_date': str(habit.last_completed_date) if habit.last_completed_date else None,
        'created': created,
    }, status=status)


@login_required
@require_POST
def api_delete_habit(request, habit_id):
    user_profile = request.user.userprofile
    try:
        habit = Habit.objects.get(pk=habit_id, user=user_profile)
    except Habit.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Habit not found.'}, status=404)

    habit.delete()
    logger.info("Habit id=%s deleted by user %s", habit_id, request.user.username)
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_delete_event(request, event_id):
    """Delete an event or a single occurrence of a recurring event.

    POST body JSON:
      { "scope": "single"|"series", "original_start": "ISO_DATETIME" }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    scope = data.get('scope', 'series')
    original_start_raw = data.get('original_start')

    user_profile = request.user.userprofile
    try:
        event = Event.objects.get(pk=event_id, user=user_profile)
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found.'}, status=404)

    # If deleting a single occurrence of a recurring event, create an EventException
    if event.rrule and scope == 'single':
        if not original_start_raw:
            return JsonResponse({'success': False, 'error': 'original_start required for single-occurrence deletion.'}, status=400)
        from django.utils.dateparse import parse_datetime
        orig = parse_datetime(original_start_raw)
        if orig is None:
            return JsonResponse({'success': False, 'error': 'Invalid original_start datetime.'}, status=400)
        if timezone.is_naive(orig):
            orig = timezone.make_aware(orig)

        # create cancellation exception
        EventException = getattr(__import__('planner.models', fromlist=['EventException']), 'EventException')
        EventException.objects.get_or_create(event=event, original_start=orig, defaults={'is_cancelled': True})
        logger.info("Created cancellation for event id=%s occurrence %s by user %s", event_id, orig.isoformat(), request.user.username)
        return JsonResponse({'success': True, 'deleted_occurrence': True})

    # Otherwise delete the whole event/series
    event.delete()
    logger.info("Deleted event id=%s (series) by user %s", event_id, request.user.username)
    return JsonResponse({'success': True, 'deleted_occurrence': False})


@login_required
@require_POST
def api_edit_event(request, event_id):
    """Edit an event or a single occurrence.

    Body: fields same as create plus optional 'scope' and 'original_start'.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)

    scope = data.get('scope', 'series')
    original_start_raw = data.get('original_start')

    user_profile = request.user.userprofile
    try:
        event = Event.objects.get(pk=event_id, user=user_profile)
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found.'}, status=404)

    title = data.get('title')
    description = data.get('description')
    start_raw = data.get('start_time')
    end_raw = data.get('end_time')
    category_name = data.get('category')

    from django.utils.dateparse import parse_datetime

    # Editing a single occurrence: create or update an EventException override
    if event.rrule and scope == 'single':
        if not original_start_raw:
            return JsonResponse({'success': False, 'error': 'original_start required for single-occurrence edit.'}, status=400)
        orig = parse_datetime(original_start_raw)
        if orig is None:
            return JsonResponse({'success': False, 'error': 'Invalid original_start datetime.'}, status=400)
        if timezone.is_naive(orig):
            orig = timezone.make_aware(orig)

        ex_model = getattr(__import__('planner.models', fromlist=['EventException']), 'EventException')
        ex, created = ex_model.objects.get_or_create(event=event, original_start=orig)
        if title is not None:
            ex.override_title = title
        if description is not None:
            ex.override_description = description
        if start_raw:
            sdt = parse_datetime(start_raw)
            if timezone.is_naive(sdt):
                sdt = timezone.make_aware(sdt)
            ex.override_start_time = sdt
        if end_raw:
            edt = parse_datetime(end_raw)
            if timezone.is_naive(edt):
                edt = timezone.make_aware(edt)
            ex.override_end_time = edt
        ex.is_cancelled = False
        ex.save()
        return JsonResponse({'success': True, 'updated_occurrence': True})

    # Series edit — update event fields
    if title is not None:
        event.title = title
    if description is not None:
        event.description = description
    if start_raw:
        sdt = parse_datetime(start_raw)
        if timezone.is_naive(sdt):
            sdt = timezone.make_aware(sdt)
        event.start_time = sdt
    if end_raw:
        edt = parse_datetime(end_raw)
        if timezone.is_naive(edt):
            edt = timezone.make_aware(edt)
        event.end_time = edt
    if category_name is not None:
        cat_obj, _ = Category.objects.get_or_create(user=user_profile, name=category_name)
        event.category = cat_obj

    event.save()
    return JsonResponse({'success': True, 'updated_occurrence': False})
