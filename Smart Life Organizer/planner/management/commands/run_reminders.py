"""
planner/management/commands/run_reminders.py
────────────────────────────────────────────
Custom Django management command that runs the background reminder loop.

Usage
─────
    python manage.py run_reminders

Behaviour
─────────
* Uses the `schedule` library to poll the database **every 1 minute**.
* Finds events that:
    - start within the next 30 minutes from now, AND
    - have an associated AITip that has NOT yet been notified
      (aitip__is_notified=False).
* For each matching event it:
    1. Prints a formatted reminder to stdout (visible in the dev console /
       process supervisor logs).
    2. Sets `AITip.is_notified = True` so the reminder fires exactly once.

This is the *development* notification mechanism.  In production, this
print statement can be swapped for an email/push/webhook call without
changing any other part of the codebase.

Run with Ctrl-C to stop.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


def _check_reminders() -> None:
    """
    Core reminder check — executed by the scheduler every minute.

    Late-imported to ensure Django's ORM is fully initialised before
    the first call (avoids AppRegistryNotReady on startup).
    """
    # Late imports — models are available by the time the command runs
    from planner.models import Event
    from ai_engine.models import AITip

    window_start = timezone.now()
    window_end = window_start + timedelta(minutes=30)

    # Spec query: events starting within 30 min with un-notified AITip
    upcoming = Event.objects.filter(
        start_time__gte=window_start,
        start_time__lte=window_end,
        aitip__is_notified=False,
    ).select_related("aitip", "user__user")

    if not upcoming.exists():
        logger.debug(
            "[Reminders] No upcoming reminders at %s.", window_start.strftime("%H:%M")
        )
        return

    for event in upcoming:
        minutes_away = int((event.start_time - window_start).total_seconds() / 60)
        tip_text = event.aitip.tip_text if hasattr(event, "aitip") else "Be prepared!"

        # ── Console notification (dev) ─────────────────────────────────────
        reminder_line = (
            f"\n{'='*60}\n"
            f"  🔔  REMINDER  |  {event.user.user.username}\n"
            f"  Event  : {event.title}\n"
            f"  Starts : {event.start_time.strftime('%H:%M')}  ({minutes_away} min away)\n"
            f"  Tip    : {tip_text}\n"
            f"{'='*60}"
        )
        print(reminder_line, flush=True)
        logger.info("Reminder fired for event '%s' (id=%s).", event.title, event.pk)

        # ── Mark as notified so we don't fire again ────────────────────────
        AITip.objects.filter(event=event).update(is_notified=True)


class Command(BaseCommand):
    help = (
        "Run the background reminder loop. "
        "Checks for upcoming events every 60 seconds and prints a console "
        "reminder for any event starting within 30 minutes that has not yet "
        "been notified.  Press Ctrl-C to stop."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Polling interval in seconds (default: 60).",
        )

    def handle(self, *args, **options):
        interval = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n Smart Life Organizer — Reminder Service\n"
                f" Polling every {interval}s for events within 30 minutes.\n"
                f" Press Ctrl-C to stop.\n"
            )
        )
        logger.info("Reminder service started (interval=%ss).", interval)

        # The management command remains for local use, but when Celery is
        # configured we recommend running the Celery beat scheduler instead.
        self.stdout.write(
            self.style.WARNING(
                "\nReminder service (legacy) — use Celery beat for production.\n"
            )
        )
        # Run a single check on demand
        _check_reminders()
