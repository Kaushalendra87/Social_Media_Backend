from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Conversation(models.Model):
    """
    Represents a private conversation between two users.
    """

    participant_one = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations_as_participant_one",
    )

    participant_two = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations_as_participant_two",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "participant_one",
                    "participant_two",
                ],
                name="unique_conversation_pair",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "participant_one",
                    "updated_at",
                ]
            ),
            models.Index(
                fields=[
                    "participant_two",
                    "updated_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"Conversation "
            f"{self.participant_one} - "
            f"{self.participant_two}"
        )

    def get_other_participant(self, user):
        """
        Return the other participant in the conversation.
        """

        if user == self.participant_one:
            return self.participant_two

        return self.participant_one

    def has_participant(self, user):
        return (
            self.participant_one == user
            or self.participant_two == user
        )

class ConversationParticipant(models.Model):
    """
    Stores per user settings for a conversation.

    This allows each participant to independently mute/unmute a conversation.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participant_settings",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversation_settings",
    )

    is_muted = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "conversation",
                    "user",
                ],
                name="unique_conversation_participant",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "is_muted",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.conversation_id}"
        )


class Message(models.Model):
    """
    Represents a message sent inside a conversation.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    content = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    is_deleted = models.BooleanField(
        default=False
    )

    delivered_at = models.DateTimeField(
        null =True,
        blank = True,
    )

    seen_at = models.DateTimeField(
        null=True,
        blank = True,
    )

    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank = True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=[
                    "conversation",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "conversation",
                    "is_read",
                ]
            ),
            models.Index(
                fields=[
                    "conversation",
                    "is_deleted",
                ]
            ),
            models.Index(
                fields=[
                    "sender",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "conversation",
                    "is_deleted",
                    "-created_at",
                ],
                name="msg_conv_del_created_idx",
            ),
            models.Index(
                fields=[
                    "conversation",
                    "is_read",
                    "is_deleted",
                ],
                name="msg_conv_read_del_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.sender} - "
            f"{self.conversation_id} - "
            f"{self.created_at}"
        )