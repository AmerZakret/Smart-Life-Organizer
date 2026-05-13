import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartlife_project.settings')
django.setup()

from planner.models import Event

now = timezone.now()
local_now = timezone.localtime(now)
print(f"UTC Now: {now}")
print(f"Local Now: {local_now}")

today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
today_end = today_start + timedelta(days=1)

print(f"Today Start (Local): {today_start}")
print(f"Today End (Local): {today_end}")

events = Event.objects.all()
print(f"Total events in DB: {events.count()}")
for e in events:
    print(f"- {e.title}: {e.start_time}")
