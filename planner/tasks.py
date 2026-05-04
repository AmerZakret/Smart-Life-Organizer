from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
import requests
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_reminders():
    """Find events starting within 30 minutes and send reminders.

    This replaces the old `run_reminders` management command when running
    under Celery + Beat.
    """
    from planner.models import Event
    from ai_engine.models import AITip

    window_start = timezone.now()
    window_end = window_start + timedelta(minutes=30)

    upcoming = Event.objects.filter(
        start_time__gte=window_start,
        start_time__lte=window_end,
        aitip__is_notified=False,
    ).select_related("aitip", "user__user")

    if not upcoming.exists():
        logger.debug(
            "[Celery Reminders] No upcoming reminders at %s.",
            window_start.strftime("%H:%M"),
        )
        return

    for event in upcoming:
        minutes_away = int((event.start_time - window_start).total_seconds() / 60)
        tip_text = event.aitip.tip_text if hasattr(event, "aitip") else "Be prepared!"
        user_profile = getattr(event, "user", None)
        sent_any = False

        # Email notification
        try:
            if getattr(user_profile, "email_notifications_enabled", False):
                recipient = event.user.user.email
                if recipient:
                    subject = f"Reminder: {event.title} in {minutes_away} minutes"
                    message = f"Event: {event.title}\nStarts: {event.start_time.strftime('%Y-%m-%d %H:%M')}\nTip: {tip_text}"
                    send_mail(subject, message, None, [recipient], fail_silently=False)
                    logger.info(
                        "Sent reminder email to %s for event %s", recipient, event.pk
                    )
                    sent_any = True
        except Exception as exc:
            logger.exception(
                "Failed to send reminder email for event %s: %s", event.pk, exc
            )

        # Webhook notification
        try:
            if getattr(
                user_profile, "webhook_notifications_enabled", False
            ) and getattr(user_profile, "webhook_url", None):
                payload = {
                    "event_id": event.pk,
                    "title": event.title,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "tip": tip_text,
                }
                try:
                    resp = requests.post(
                        user_profile.webhook_url, json=payload, timeout=5
                    )
                    resp.raise_for_status()
                    logger.info(
                        "Sent webhook to %s for event %s",
                        user_profile.webhook_url,
                        event.pk,
                    )
                    sent_any = True
                except Exception as exc:
                    logger.exception(
                        "Failed to POST webhook for event %s to %s: %s",
                        event.pk,
                        user_profile.webhook_url,
                        exc,
                    )
        except Exception:
            # guard against attribute errors when profiles are missing
            pass

        # Mark notified if we sent at least one notification or user has notifications disabled
        if sent_any or not (
            getattr(user_profile, "email_notifications_enabled", False)
            or getattr(user_profile, "webhook_notifications_enabled", False)
        ):
            AITip.objects.filter(event=event).update(is_notified=True)
