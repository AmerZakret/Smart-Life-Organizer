import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartlife_project.settings')
django.setup()

from planner.models import Event
from planner.utils import expand_events_for_range

now = timezone.now()
local_now = timezone.localtime(now)
print(f"UTC Now: {now}")
print(f"Local Now: {local_now}")

today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
today_end = today_start + timedelta(days=1)

print(f"Today Start: {today_start}")
print(f"Today End: {today_end}")

events_qs = Event.objects.all()
expanded = expand_events_for_range(events_qs, today_start, today_end)

print(f"Expanded events for today: {len(expanded)}")
for occ in expanded:
    print(f"- {occ['title']} at {occ['start_time']}")
