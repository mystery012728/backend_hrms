from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    image = models.ImageField(
        upload_to='notifications/',
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} for {self.user.username}"
