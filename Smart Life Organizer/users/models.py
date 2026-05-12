from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    TONE_CHOICES = [
        ("motivational", "Motivational"),
        ("direct", "Direct"),
        ("professional", "Professional"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=50, default="UTC")
    ai_tone = models.CharField(max_length=20, choices=TONE_CHOICES, default="direct")
    # Notification preferences
    email_notifications_enabled = models.BooleanField(default=True)
    webhook_notifications_enabled = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
