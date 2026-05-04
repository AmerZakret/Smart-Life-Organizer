import pytest
from unittest.mock import patch
from django.contrib.auth.models import User
from django.utils import timezone
from planner.models import Event
from ai_engine.models import AITip
from datetime import timedelta


@pytest.mark.django_db(transaction=True)
def test_ai_tip_creation_signal():
    """Test that creating an event triggers the AI tip creation thread (mocked)."""
    user = User.objects.create_user(username="aiuser", password="password123")

    # We mock the generate_event_tip function to return a fixed string
    with patch("ai_engine.services.generate_event_tip") as mocked_tip:
        mocked_tip.return_value = "Mocked AI Tip: Stay focused."

        from planner.models import Category
        category = Category.objects.create(name="Work", user=user.userprofile)

        # Creating an event should trigger the signal
        event = Event.objects.create(
            user=user.userprofile,
            title="AI Test Meeting",
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
            category=category,
        )

        # Since it's in a thread, we might need a tiny sleep or just join the threads
        # in a real complex test, but for this simple mock, the signal handler
        # starts a thread. In tests, we can often just wait for a second.
        import time

        time.sleep(3)

        assert AITip.objects.filter(event=event).exists()
        tip = AITip.objects.get(event=event)
        assert tip.tip_text == "Mocked AI Tip: Stay focused."
