from django.db import models
from users.models import UserProfile

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('Work', 'Work'),
        ('Health', 'Health'),
        ('Personal', 'Personal'),
    ]
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
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
