import csv
import json
import logging
from datetime import timedelta

import plotly.express as px
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from icalendar import Calendar, Event as IcsEvent

from ai_engine.models import AITip
from ai_engine.services import generate_dashboard_insight
from .models import Category, Event, Habit, Task, PomodoroSession
from .utils import expand_events_for_range

logger = logging.getLogger(__name__)


# ── Page views ────────────────────────────────────────────────────────────────


_FALLBACK_QUOTES = [
    "Consistency is the key to success. Start by completing your first task today!",
    "Small daily improvements lead to staggering long-term results. Keep going!",
    "The secret of getting ahead is getting started. You've got this!",
    "Focus on progress, not perfection. Every step counts.",
    "Your future self will thank you for the effort you put in today.",
]


@login_required
def dashboard(request):
    import random
    user_profile = request.user.userprofile
    today = timezone.now().date()
    now = timezone.now()

    events_today = Event.objects.filter(
        user=user_profile,
        start_time__date=today,
    ).order_by("start_time")

    habits = Habit.objects.filter(user=user_profile).order_by("-id")
    all_tasks = Task.objects.filter(user=user_profile)
    pending_tasks = all_tasks.filter(is_completed=False)
    tasks = pending_tasks.order_by("-id")[:5]
    pending_tasks_count = pending_tasks.count()

    # Best habit streak for context
    best_streak_habit = habits.order_by("-current_streak").first()

    # Fetch next 48h events for the personalized tip
    next_48h = now + timedelta(hours=48)
    upcoming_events = Event.objects.filter(
        user=user_profile,
        start_time__gte=now,
        start_time__lte=next_48h
    ).order_by("start_time")[:5]

    # Generate personalized dashboard insight via Gemini
    dashboard_tip = generate_dashboard_insight(
        username=request.user.first_name or request.user.username,
        events=list(upcoming_events),
        habits=list(habits),
        tone=user_profile.ai_tone,
        pending_tasks_count=pending_tasks_count,
    )

    # Fallback: if Gemini is unavailable, provide a motivational quote
    if not dashboard_tip:
        dashboard_tip = random.choice(_FALLBACK_QUOTES)

    context = {
        "events_today": events_today,
        "habits": habits,
        "tasks": tasks,
        "dashboard_tip": dashboard_tip,
        "pending_tasks_count": pending_tasks_count,
        "best_streak_habit": best_streak_habit,
        "categories": Category.objects.filter(user=user_profile).order_by("name"),
    }
    return render(request, "planner/dashboard.html", context)

@login_required
def analytics(request):
    user_profile = request.user.userprofile
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)

    # All events for today
    events_today = Event.objects.filter(
        user=user_profile,
        start_time__date=today,
    ).order_by("start_time")

    # Category counts for today's chart
    cat_counts = {}
    cat_colors = {}
    categories_objects = [e.category for e in events_today if e.category]
    for cat in categories_objects:
        cat_counts[cat.name] = cat_counts.get(cat.name, 0) + 1
        if cat.color:
            cat_colors[cat.name] = cat.color

    if cat_counts:
        names = list(cat_counts.keys())
        values = list(cat_counts.values())
        fig = px.pie(
            names=names,
            values=values,
            color=names,
            color_discrete_map=cat_colors,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12),
            title_text=""
        )
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    else:
        chart_html = ""

    # Top Categories (Full dataset)
    all_categories = Category.objects.filter(user=user_profile)
    top_categories_data = []
    total_events = Event.objects.filter(user=user_profile).count()
    
    for cat in all_categories:
        count = Event.objects.filter(user=user_profile, category=cat).count()
        if count > 0:
            percentage = (count / total_events * 100) if total_events > 0 else 0
            top_categories_data.append({
                "name": cat.name,
                "count": count,
                "percentage": int(percentage),
                "color": cat.color
            })
    top_categories_data = sorted(top_categories_data, key=lambda x: x["count"], reverse=True)[:5]

    # Weekly Activity (Heatmap data)
    weekly_activity = []
    for i in range(7):
        day = today - timedelta(days=i)
        count = Event.objects.filter(user=user_profile, start_time__date=day).count()
        weekly_activity.append({
            "day": day.strftime("%a"),
            "date": day,
            "count": count
        })
    weekly_activity.reverse()

    context = {
        "chart_html": chart_html,
        "events_today_count": events_today.count(),
        "top_categories": top_categories_data,
        "weekly_activity": weekly_activity,
        "max_activity": max([d["count"] for d in weekly_activity]) if weekly_activity else 0
    }
    return render(request, "planner/analytics.html", context)


@login_required
def growth_view(request):
    user_profile = request.user.userprofile
    habits = Habit.objects.filter(user=user_profile).order_by("-id")
    tasks = Task.objects.filter(user=user_profile).order_by("-id")
    return render(request, "planner/growth.html", {
        "habits": habits,
        "tasks": tasks,
        "categories": Category.objects.filter(user=user_profile).order_by("name"),
    })

@login_required
def habits(request):
    return redirect("growth")

@login_required
def todo(request):
    return redirect("growth")

@login_required
def pomodoro_view(request):
    user_profile = request.user.userprofile
    today = timezone.now().date()
    sessions = PomodoroSession.objects.filter(
        user=user_profile,
        completed_at__date=today
    ).order_by("-completed_at")
    
    return render(request, "planner/pomodoro.html", {
        "sessions": sessions,
        "sessions_count": sessions.count()
    })

@login_required
@require_POST
def api_complete_pomodoro(request):
    user_profile = request.user.userprofile
    PomodoroSession.objects.create(user=user_profile, duration_minutes=25)
    return JsonResponse({"success": True})


@login_required
def calendar(request):
    user_profile = request.user.userprofile

    # provide user's categories to the template for dynamic select & legend
    categories = Category.objects.filter(user=user_profile).order_by("name")
    categories_json = json.dumps(
        [{"name": c.name, "color": c.color} for c in categories]
    )

    # AI tips for the sidebar
    ai_tips = (
        AITip.objects.filter(
            event__user=user_profile,
            event__start_time__gte=timezone.now(),
        )
        .select_related("event", "event__category")
        .order_by("event__start_time")[:8]
    )

    context = {
        "categories": categories,
        "categories_json": categories_json,
        "ai_tips": ai_tips,
    }
    return render(request, "planner/calendar.html", context)


@login_required
@require_GET
def api_events_feed(request):
    """GET /api/events/feed/?start=...&end=...

    Returns events in FullCalendar-compatible JSON format.
    FullCalendar automatically appends `start` and `end` ISO date params.
    """
    user_profile = request.user.userprofile

    start_raw = request.GET.get("start", "")
    end_raw = request.GET.get("end", "")

    from django.utils.dateparse import parse_datetime, parse_date

    start_dt = None
    end_dt = None

    # FullCalendar sends ISO dates like "2026-05-01" or datetimes
    if start_raw:
        start_dt = parse_datetime(start_raw) or (
            timezone.make_aware(timezone.datetime.combine(parse_date(start_raw), timezone.datetime.min.time()))
            if parse_date(start_raw)
            else None
        )
    if end_raw:
        end_dt = parse_datetime(end_raw) or (
            timezone.make_aware(timezone.datetime.combine(parse_date(end_raw), timezone.datetime.max.time()))
            if parse_date(end_raw)
            else None
        )

    if not start_dt or not end_dt:
        now = timezone.now()
        start_dt = start_dt or (now - timedelta(days=30))
        end_dt = end_dt or (now + timedelta(days=60))

    if timezone.is_naive(start_dt):
        start_dt = timezone.make_aware(start_dt)
    if timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)

    events_qs = Event.objects.filter(user=user_profile).select_related("category")
    occurrences = expand_events_for_range(events_qs, start_dt, end_dt)

    fc_events = []
    for occ in occurrences:
        cat = occ.get("category")
        color = cat.color if cat and cat.color else "#94a3b8"
        fc_events.append(
            {
                "id": occ["event"].pk,
                "title": occ["title"],
                "start": occ["start_time"].isoformat(),
                "end": occ["end_time"].isoformat(),
                "color": color,
                "textColor": "#ffffff",
                "extendedProps": {
                    "category": cat.name if cat else "",
                    "categoryColor": color,
                    "description": occ.get("description", ""),
                    "isRecurring": bool(occ["event"].rrule),
                    "originalStart": (
                        occ["original_start"].isoformat()
                        if occ.get("original_start")
                        else None
                    ),
                    "isCompleted": occ["event"].is_completed,
                },
            }
        )

    # Add Tasks that have due dates to the Calendar
    tasks_qs = Task.objects.filter(
        user=user_profile, 
        due_date__isnull=False,
        due_date__gte=start_dt,
        due_date__lt=end_dt
    )
    for task in tasks_qs:
        fc_events.append(
            {
                "id": f"task_{task.id}",
                "title": f"📝 {task.title}",
                "start": task.due_date.isoformat(),
                "allDay": True,
                "color": "#f59e0b",  # Amber/Yellow for tasks
                "textColor": "#ffffff",
                "extendedProps": {
                    "isTask": True,
                    "isCompleted": task.is_completed,
                },
            }
        )

    return JsonResponse(fc_events, safe=False)


@login_required
def settings_view(request):
    user_profile = request.user.userprofile
    if request.method == "POST":
        user_profile.timezone = request.POST.get("timezone", "UTC")
        user_profile.ai_tone = request.POST.get("ai_tone", "direct")
        user_profile.save()
        return redirect("dashboard")

    context = {
        "profile": user_profile,
        "tones": user_profile.TONE_CHOICES,
        "categories": Category.objects.filter(user=user_profile).order_by("name"),
    }
    return render(request, "planner/settings.html", context)


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
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body."}, status=400
        )

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    start_raw = data.get("start_time", "").strip()
    end_raw = data.get("end_time", "").strip()
    category = data.get("category", "").strip()
    category_color = data.get("category_color") or "#0d9488"

    # ── Validation ────────────────────────────────────────────────────────────
    if not title:
        return JsonResponse(
            {"success": False, "error": "Title is required."}, status=400
        )
    if len(title) > 150:
        return JsonResponse(
            {"success": False, "error": "Title must be ≤ 150 characters."}, status=400
        )
    if not start_raw or not end_raw:
        return JsonResponse(
            {"success": False, "error": "Start and end times are required."}, status=400
        )
    # allow arbitrary category names (created on demand) but require non-empty and limit length
    if not category:
        return JsonResponse(
            {"success": False, "error": "Category is required."}, status=400
        )
    if category == "__new__":
        return JsonResponse(
            {"success": False, "error": "Invalid category selection."}, status=400
        )
    if len(category) > 50:
        return JsonResponse(
            {"success": False, "error": "Category must be ≤ 50 characters."}, status=400
        )

    # Parse datetime-local strings (HTML format: "YYYY-MM-DDTHH:MM")
    from django.utils.dateparse import parse_datetime

    start_time = parse_datetime(start_raw)
    end_time = parse_datetime(end_raw)

    if start_time is None or end_time is None:
        return JsonResponse(
            {"success": False, "error": "Invalid datetime format."}, status=400
        )

    # Make datetimes timezone-aware using Django's current timezone
    if timezone.is_naive(start_time):
        start_time = timezone.make_aware(start_time)
    if timezone.is_naive(end_time):
        end_time = timezone.make_aware(end_time)

    if end_time <= start_time:
        return JsonResponse(
            {"success": False, "error": "End time must be after start time."},
            status=400,
        )

    # Optional recurrence fields
    rrule_raw = data.get("rrule") or None
    recurrence_end_raw = data.get("recurrence_end") or None

    # ── Create ────────────────────────────────────────────────────────────────
    user_profile = request.user.userprofile
    # Ensure category is a Category instance (FK)
    category_obj, created = Category.objects.get_or_create(
        user=user_profile, name=category, defaults={"color": category_color}
    )
    # Update color on existing category if user picked a custom color
    if not created and category_color and category_color != "#0d9488":
        category_obj.color = category_color
        category_obj.save(update_fields=["color"])

    event = Event.objects.create(
        user=user_profile,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        category=category_obj,
        rrule=rrule_raw,
        recurrence_end=(
            (
                lambda v: (
                    timezone.make_aware(parse_datetime(v))
                    if timezone.is_naive(parse_datetime(v))
                    else parse_datetime(v)
                )
            )(recurrence_end_raw)
            if recurrence_end_raw
            else None
        ),
    )
    logger.info(
        "Event '%s' (id=%s) created for user '%s'.",
        title,
        event.pk,
        request.user.username,
    )

    return JsonResponse(
        {
            "success": True,
            "id": event.pk,
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "category": event.category.name if event.category else None,
            "category_color": event.category.color if event.category else None,
            "category_created": created,
        },
        status=201,
    )


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
        return JsonResponse({"success": False, "error": "Habit not found."}, status=404)

    today = timezone.now().date()

    # Idempotency: don't increment if already toggled today
    if habit.last_completed_date == today:
        return JsonResponse(
            {
                "success": True,
                "new_streak": habit.current_streak,
                "last_completed": str(today),
                "already_done": True,
            }
        )

    habit.current_streak += 1
    habit.last_completed_date = today
    habit.save(update_fields=["current_streak", "last_completed_date"])

    logger.info(
        "Habit '%s' (id=%s) toggled for user '%s'. New streak: %s.",
        habit.name,
        habit.pk,
        request.user.username,
        habit.current_streak,
    )

    return JsonResponse(
        {
            "success": True,
            "new_streak": habit.current_streak,
            "last_completed": str(today),
            "already_done": False,
        }
    )


@require_POST
def api_edit_category(request, cat_id):
    """Edit a category's name and color."""
    user_profile = request.user.userprofile
    try:
        data = json.loads(request.body)
        cat = Category.objects.get(pk=cat_id, user=user_profile)

        name = data.get("name", "").strip()
        color = data.get("color", "").strip()

        if name:
            cat.name = name
        if color:
            cat.color = color
        cat.save()

        return JsonResponse({"success": True, "name": cat.name, "color": cat.color})
    except Category.DoesNotExist:
        return JsonResponse({"success": False, "error": "Category not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def api_delete_category(request, cat_id):
    """Delete a category and explicitly confirm deletion of its events."""
    user_profile = request.user.userprofile
    try:
        cat = Category.objects.get(pk=cat_id, user=user_profile)
        # We can perform the delete directly. Django CASCADE will delete the associated events if defined.
        # But we will do it explicitly just to be safe and confirm it.
        cat.delete()
        return JsonResponse({"success": True})
    except Category.DoesNotExist:
        return JsonResponse({"success": False, "error": "Category not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_GET
def export_csv(request):
    """Export user's Events and Habits as CSV."""
    user_profile = request.user.userprofile

    # Events
    events = Event.objects.filter(user=user_profile).order_by("start_time")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="smartlife_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["type", "title", "start_time", "end_time", "category", "description"]
    )
    for e in events:
        writer.writerow(
            [
                "event",
                e.title,
                e.start_time.isoformat(),
                e.end_time.isoformat(),
                e.category.name if e.category else "",
                e.description,
            ]
        )

    # Habits
    habits = Habit.objects.filter(user=user_profile)
    for h in habits:
        writer.writerow(["habit", h.name, "", "", "", ""])

    return response


@login_required
@require_GET
def export_ics(request):
    """Export user's events as an .ics calendar."""
    user_profile = request.user.userprofile
    events = Event.objects.filter(user=user_profile)

    cal = Calendar()
    cal.add("prodid", "-//Smart Life Organizer//")
    cal.add("version", "2.0")

    for e in events:
        comp = IcsEvent()
        comp.add("summary", e.title)
        comp.add("dtstart", e.start_time)
        comp.add("dtend", e.end_time)
        if e.rrule:
            # naive: set raw RRULE string (icalendar expects dict-like vRecur)
            for part in e.rrule.split(";"):
                if not part:
                    continue
                k, v = part.split("=")
                comp.add("rrule", {k: v})
        comp.add("description", e.description or "")
        cal.add_component(comp)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = 'attachment; filename="smartlife_events.ics"'
    return response


@login_required
def import_events(request):
    """Simple upload handler to import CSV or ICS files."""
    user_profile = request.user.userprofile
    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            return JsonResponse(
                {"success": False, "error": "No file uploaded."}, status=400
            )

        name = f.name.lower()
        created = 0
        if name.endswith(".csv"):
            text = f.read().decode("utf-8")
            reader = csv.reader(text.splitlines())
            for row in reader:
                if not row:
                    continue
                if row[0].lower() == "event" and len(row) >= 6:
                    title = row[1]
                    try:
                        start = timezone.datetime.fromisoformat(row[2])
                        end = timezone.datetime.fromisoformat(row[3])
                    except Exception:
                        continue
                    cat_name = row[4]
                    cat = None
                    if cat_name:
                        cat, _ = Category.objects.get_or_create(
                            user=user_profile, name=cat_name
                        )
                    Event.objects.create(
                        user=user_profile,
                        title=title,
                        start_time=start,
                        end_time=end,
                        category=cat,
                        description=row[5],
                    )
                    created += 1
                elif row[0].lower() == "habit" and len(row) >= 2:
                    Habit.objects.get_or_create(user=user_profile, name=row[1])
                    created += 1

        elif name.endswith(".ics"):
            data = f.read()
            try:
                cal = Calendar.from_ical(data)
            except Exception:
                return JsonResponse(
                    {"success": False, "error": "Invalid ICS file."}, status=400
                )
            for component in cal.walk():
                if component.name == "VEVENT":
                    title = str(component.get("summary"))
                    dtstart = component.get("dtstart").dt
                    dtend = (
                        component.get("dtend").dt
                        if component.get("dtend")
                        else (dtstart + timezone.timedelta(hours=1))
                    )
                    rrule = component.get("rrule")
                    rrule_str = None
                    if rrule:
                        # Convert vRecur dict to RFC string
                        parts = []
                        for k, v in rrule.items():
                            parts.append(f"{k}={','.join(v)}")
                        rrule_str = ";".join(parts)
                    Event.objects.create(
                        user=user_profile,
                        title=title,
                        start_time=dtstart,
                        end_time=dtend,
                        rrule=rrule_str,
                    )
                    created += 1
        else:
            return JsonResponse(
                {"success": False, "error": "Unsupported file type."}, status=400
            )

        return JsonResponse({"success": True, "created": created})

    # GET -> render a simple upload form
    return render(request, "planner/import_form.html")


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
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body."}, status=400
        )

    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse(
            {"success": False, "error": "Name is required."}, status=400
        )
    if len(name) > 100:
        return JsonResponse(
            {"success": False, "error": "Name must be ≤ 100 characters."}, status=400
        )

    user_profile = request.user.userprofile
    habit, created = Habit.objects.get_or_create(user=user_profile, name=name)

    status = 201 if created else 200
    return JsonResponse(
        {
            "success": True,
            "id": habit.pk,
            "name": habit.name,
            "current_streak": habit.current_streak,
            "last_completed_date": (
                str(habit.last_completed_date) if habit.last_completed_date else None
            ),
            "created": created,
        },
        status=status,
    )


@login_required
@require_POST
def api_delete_habit(request, habit_id):
    user_profile = request.user.userprofile
    try:
        habit = Habit.objects.get(pk=habit_id, user=user_profile)
    except Habit.DoesNotExist:
        return JsonResponse({"success": False, "error": "Habit not found."}, status=404)

    habit.delete()
    logger.info("Habit id=%s deleted by user %s", habit_id, request.user.username)
    return JsonResponse({"success": True})


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

    scope = data.get("scope", "series")
    original_start_raw = data.get("original_start")

    user_profile = request.user.userprofile
    try:
        event = Event.objects.get(pk=event_id, user=user_profile)
    except Event.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found."}, status=404)

    # If deleting a single occurrence of a recurring event, create an EventException
    if event.rrule and scope == "single":
        if not original_start_raw:
            return JsonResponse(
                {
                    "success": False,
                    "error": "original_start required for single-occurrence deletion.",
                },
                status=400,
            )
        from django.utils.dateparse import parse_datetime

        orig = parse_datetime(original_start_raw)
        if orig is None:
            return JsonResponse(
                {"success": False, "error": "Invalid original_start datetime."},
                status=400,
            )
        if timezone.is_naive(orig):
            orig = timezone.make_aware(orig)

        # create cancellation exception
        EventException = getattr(
            __import__("planner.models", fromlist=["EventException"]), "EventException"
        )
        EventException.objects.get_or_create(
            event=event, original_start=orig, defaults={"is_cancelled": True}
        )
        logger.info(
            "Created cancellation for event id=%s occurrence %s by user %s",
            event_id,
            orig.isoformat(),
            request.user.username,
        )
        return JsonResponse({"success": True, "deleted_occurrence": True})

    # Otherwise delete the whole event/series
    event.delete()
    logger.info(
        "Deleted event id=%s (series) by user %s", event_id, request.user.username
    )
    return JsonResponse({"success": True, "deleted_occurrence": False})


@login_required
@require_POST
def api_edit_event(request, event_id):
    """Edit an event or a single occurrence.

    Body: fields same as create plus optional 'scope' and 'original_start'.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "Invalid JSON body."}, status=400
        )

    scope = data.get("scope", "series")
    original_start_raw = data.get("original_start")

    user_profile = request.user.userprofile
    try:
        event = Event.objects.get(pk=event_id, user=user_profile)
    except Event.DoesNotExist:
        return JsonResponse({"success": False, "error": "Event not found."}, status=404)

    title = data.get("title")
    description = data.get("description")
    start_raw = data.get("start_time")
    end_raw = data.get("end_time")
    category_name = data.get("category")

    from django.utils.dateparse import parse_datetime

    # Editing a single occurrence: create or update an EventException override
    if event.rrule and scope == "single":
        if not original_start_raw:
            return JsonResponse(
                {
                    "success": False,
                    "error": "original_start required for single-occurrence edit.",
                },
                status=400,
            )
        orig = parse_datetime(original_start_raw)
        if orig is None:
            return JsonResponse(
                {"success": False, "error": "Invalid original_start datetime."},
                status=400,
            )
        if timezone.is_naive(orig):
            orig = timezone.make_aware(orig)

        ex_model = getattr(
            __import__("planner.models", fromlist=["EventException"]), "EventException"
        )
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
        return JsonResponse({"success": True, "updated_occurrence": True})

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
        cat_obj, _ = Category.objects.get_or_create(
            user=user_profile, name=category_name
        )
        event.category = cat_obj

    event.save()
    return JsonResponse({"success": True, "updated_occurrence": False})


@require_POST
@login_required
def api_create_task(request):
    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        due_date_raw = data.get("due_date", "")
        if not title:
            return JsonResponse({"success": False, "error": "Title required."})
            
        due_date = None
        if due_date_raw:
            from django.utils.dateparse import parse_datetime, parse_date
            due_date = parse_datetime(due_date_raw) or (
                timezone.make_aware(timezone.datetime.combine(parse_date(due_date_raw), timezone.datetime.min.time()))
                if parse_date(due_date_raw)
                else None
            )
            if due_date and timezone.is_naive(due_date):
                due_date = timezone.make_aware(due_date)

        task = Task.objects.create(
            user=request.user.userprofile,
            title=title,
            due_date=due_date
        )
        return JsonResponse({
            "success": True, 
            "id": task.id, 
            "title": task.title,
            "is_completed": task.is_completed,
            "due_date": task.due_date.isoformat() if task.due_date else None
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@require_POST
@login_required
def api_toggle_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id, user=request.user.userprofile)
        task.is_completed = not task.is_completed
        task.save()
        return JsonResponse({"success": True, "is_completed": task.is_completed})
    except Task.DoesNotExist:
        return JsonResponse({"success": False, "error": "Task not found."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@require_POST
@login_required
def api_delete_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id, user=request.user.userprofile)
        task.delete()
        return JsonResponse({"success": True})
    except Task.DoesNotExist:
        return JsonResponse({"success": False, "error": "Task not found."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
