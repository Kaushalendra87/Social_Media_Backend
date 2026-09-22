from django.conf import settings
from django.db import models

# Create your models here.


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        FOLLOW =  "FOLLOW", "Follow"
        FOLLOW_REQUEST = "FOLLOW_REQUEST", "Follow Request"
        FOLLOW_ACCEPTED = "FOLLOW_ACCEPTED", "Follow Accepted"
        LIKE = "LIKE", "Like"
        COMMENT ="COMMENT", "Comment"
        REPLY = "REPLY", "Reply"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices = NotificationType.choices,
    )

    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        null = True,
        blank = True,
        related_name = "notifications",
    )

    comment = models.ForeignKey(
        "posts.Comment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    reply = models.ForeignKey(
        "posts.Reply",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    follow_request = models.ForeignKey(
        "users.FollowRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["recipient", "is_read"],
            ),
            models.Index(
                fields=["recipient", "created_at"],
            ),
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recip_read_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.actor.username} -> "
            f"{self.receipient.username} -> "
            f"{self.notification_type} -> "
        )
