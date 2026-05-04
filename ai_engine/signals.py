"""
ai_engine/signals.py
─────────────────────
Django signal handlers that trigger AI tip generation whenever a new
Event is saved for the first time (created=True).

Design decisions
────────────────
* **Thread-based async**: The Gemini API call is offloaded to a daemon
  thread so the request/response cycle that created the event is never
  blocked waiting for the external API.  This is the lightweight async
  approach mandated by the plan ("asynchronously if possible").

* **One-tip-per-event guard**: The handler checks for an existing AITip
  via `get_or_create` logic — the OneToOneField on AITip ensures only
  one tip can exist per event at the DB level.  The signal only fires
  the API call for newly created events, not subsequent saves.

* **Silent failure**: If the service returns None (API error, missing
  key, etc.) no AITip row is created and no exception propagates to
  the caller.
"""

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _generate_and_cache_tip(event_id: int, event_title: str, start_time) -> None:
    """
    Worker function executed in a background thread.
    """
    import time
    from ai_engine.models import AITip
    from ai_engine.services import generate_event_tip
    from planner.models import Event

    # Small delay to ensure DB transaction is committed
    time.sleep(1.5)

    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return

    # Guard: don't overwrite an existing tip
    if AITip.objects.filter(event=event).exists():
        return

    # Retry logic (up to 3 attempts with exponential backoff)
    max_retries = 3
    for attempt in range(max_retries):
        tip_text = generate_event_tip(event_title, start_time)
        if tip_text:
            AITip.objects.create(event=event, tip_text=tip_text)
            logger.info("AITip cached for event '%s' (id=%s) on attempt %s.", event_title, event_id, attempt+1)
            return
        
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 15  # 15s, 30s
            logger.debug("Tip generation failed for event %s. Retrying in %ss...", event_id, wait_time)
            time.sleep(wait_time)

    logger.warning("Failed to generate AI tip for event '%s' after %s attempts.", event_title, max_retries)


@receiver(post_save, sender="planner.Event")
def trigger_ai_tip_on_event_create(sender, instance, created, **kwargs):
    """
    Fires after a new Event row is committed to the database.

    Only acts on *creation* (created=True).  Updates to existing events
    (e.g. marking is_completed=True) do not re-trigger the API call.
    """
    if not created:
        return

    thread = threading.Thread(
        target=_generate_and_cache_tip,
        args=(instance.pk, instance.title, instance.start_time),
        daemon=True,   # dies with the main process — no orphan threads
        name=f"ai-tip-event-{instance.pk}",
    )
    thread.start()
    logger.debug(
        "AI tip thread started for new event '%s' (id=%s).",
        instance.title,
        instance.pk,
    )
