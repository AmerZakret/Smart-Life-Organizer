from django.db import models
from planner.models import Event


class AITip(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    tip_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"Tip for {self.event.title}"
