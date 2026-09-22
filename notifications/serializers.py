from  rest_framework import serializers

from .models import Notification


class NotificationSeializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username",
        read_only = True,
    )

    actor_profile_picture = serializers.SerializerMethodField()

    notification_message = serializers.SerializerMethodField()

    post_id = serializers.IntegerField(
        source = "post.id",
        read_only = True,
        allow_null = True,
    )

    comment_id = serializers.IntegerField(
        source="comment.id",
        read_only = True,
        allow_null = True,    
    )

    reply_id = serializers.IntegerField(
        source="reply.id",
        read_only=True,
        allow_null=True,
    )

    follow_request_id = serializers.IntegerField(
        source = "follow_request.id",
        read_only = True,
        allow_null = True,
    )

    class Meta:
        model = Notification

        fields = [
            "id",
            "notification_type",
            "actor",
            "actor_username",
            "actor_profile_picture",
            "notification_message",
            "post_id",
            "comment_id",
            "reply_id",
            "follow_request_id",
            "is_read",
            "created_at",
        ]

        read_only_fields = fields

    def get_actor_profile_picture(self, obj):
        profile_picture = getattr(
            obj.actor,
            "profile_picture",
            None,
        )

        if not profile_picture:
            return None

        try:
            return profile_picture.url
        except (ValueError, AttributeError):
            return str(profile_picture)


    def get_notification_message(self, obj):
        username = obj.actor.username

        messages = {
            Notification.NotificationType.FOLLOW:
                f"{username} started following you.",

            Notification.NotificationType.FOLLOW_REQUEST:
                f"{username} sent you a follow request.",

            Notification.NotificationType.FOLLOW_ACCEPTED:
                f"{username} accepted your follow request.",

            Notification.NotificationType.LIKE:
                f"{username} liked your post.",

            Notification.NotificationType.COMMENT:
                f"{username} commented on your post.",

            Notification.NotificationType.REPLY:
                f"{username} replied to your comment.",
        }

        return messages.get(
            obj.notification_type,
            f"{username} interacteed with you.",
        )
    
        