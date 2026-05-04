import pytest
import json
from django.contrib.auth.models import User
from django.utils import timezone
from planner.models import Event, Habit
from datetime import timedelta


@pytest.fixture
def authenticated_client(client):
    user = User.objects.create_user(username="planneruser", password="password123")
    client.login(username="planneruser", password="password123")
    return client, user


@pytest.mark.django_db
def test_dashboard_access_denied_anonymous(client):
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "login" in response.url


@pytest.mark.django_db
def test_api_create_event(authenticated_client):
    client, user = authenticated_client
    start_time = (timezone.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    end_time = (timezone.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

    data = {
        "title": "Test Event",
        "description": "Test Description",
        "start_time": start_time,
        "end_time": end_time,
        "category": "Work",
    }

    response = client.post(
        "/api/events/create/", data=json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 201
    assert Event.objects.filter(title="Test Event", user=user.userprofile).exists()


@pytest.mark.django_db
def test_api_toggle_habit(authenticated_client):
    client, user = authenticated_client
    habit = Habit.objects.create(
        user=user.userprofile, name="Read 10 mins", current_streak=5
    )

    response = client.post(f"/api/habits/{habit.id}/toggle/")

    assert response.status_code == 200
    habit.refresh_from_db()
    assert habit.current_streak == 6
    assert habit.last_completed_date == timezone.now().date()

    # Test idempotency (toggling again today shouldn't increment)
    response = client.post(f"/api/habits/{habit.id}/toggle/")
    habit.refresh_from_db()
    assert habit.current_streak == 6
