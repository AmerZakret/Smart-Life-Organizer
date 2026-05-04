from django.db import models
from users.models import UserProfile


class Category(models.Model):
    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#0d9488")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = (("user", "name"),)

    def __str__(self):
        return f"{self.name} ({self.user})"


class Event(models.Model):
    CATEGORY_CHOICES = [
        ("Work", "Work"),
        ("Health", "Health"),
        ("Personal", "Personal"),
        ("Education", "Education"),
    ]
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    category = models.ForeignKey(
        "planner.Category", null=True, blank=True, on_delete=models.SET_NULL
    )
    # Recurrence: store an RFC 5545 RRULE string (e.g. "FREQ=WEEKLY;BYDAY=MO")
    rrule = models.CharField(max_length=512, null=True, blank=True)
    recurrence_end = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Habit(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    current_streak = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


class EventException(models.Model):
    """Represents an exception to a recurring Event: modification or cancellation

    - `event` is the recurring parent
    - `original_start` identifies the instance datetime being modified
    - if `is_cancelled` is True the occurrence is removed
    - otherwise override fields may replace the instance data
    """

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="exceptions"
    )
    original_start = models.DateTimeField()
    is_cancelled = models.BooleanField(default=False)

    # Optional overrides for a single instance
    override_title = models.CharField(max_length=150, null=True, blank=True)
    override_description = models.TextField(null=True, blank=True)
    override_start_time = models.DateTimeField(null=True, blank=True)
    override_end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("event", "original_start"),)

    def __str__(self):
        return f"Exception for {self.event.title} @ {self.original_start.isoformat()}"
