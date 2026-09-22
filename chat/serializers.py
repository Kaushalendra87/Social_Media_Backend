from rest_framework import serializers

from .models import (
    Conversation,
    ConversationParticipant,
    Message,
)


class ConversationParticipantSerializer(
    serializers.Serializer
):
    id = serializers.IntegerField(
        read_only=True,
    )

    username = serializers.CharField(
        read_only=True,
    )

    first_name = serializers.CharField(
        read_only=True,
    )

    last_name = serializers.CharField(
        read_only=True,
    )

    is_online = serializers.BooleanField(
        read_only=True,
        default=False,
    )

    last_seen = serializers.DateTimeField(
        read_only=True,
        default=None,
    )

    profile_picture = serializers.SerializerMethodField()

    def get_profile_picture(self, obj):
        profile_picture = getattr(
            obj,
            "profile_picture",
            None,
        )

        if not profile_picture:
            return None

        try:
            return profile_picture.url
        except (
            ValueError,
            AttributeError,
        ):
            return str(profile_picture)


class ConversationSerializer(
    serializers.ModelSerializer
):
    other_participant = serializers.SerializerMethodField()

    last_message = serializers.SerializerMethodField()

    unread_count = serializers.SerializerMethodField()

    is_muted = serializers.SerializerMethodField()

    latest_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation

        fields = [
            "id",
            "other_participant",
            "last_message",
            "unread_count",
            "is_muted",
            "created_at",
            "updated_at",
            "latest_message",
        ]

        read_only_fields = fields

    def get_other_participant(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        user = request.user

        other_user = obj.get_other_participant(user)

        if not other_user:
            return None

        return ConversationParticipantSerializer(
            other_user
        ).data

    def get_last_message(self, obj):
        message = (
            obj.messages
            .filter(
                is_deleted=False
            )
            .select_related("sender")
            .order_by("-created_at")
            .first()
        )

        if not message:
            return None

        return {
            "id": message.id,
            "sender_id": message.sender_id,
            "sender_username": message.sender.username,
            "content": message.content,
            "is_read": message.is_read,
            "edited_at": message.edited_at,
            "created_at": message.created_at,
        }

    def get_unread_count(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return 0

        return (
            obj.messages
            .filter(
                is_read=False,
                is_deleted=False,
                seen_at__isnull=True,
            )
            .exclude(
                sender=request.user
            )
            .count()
        )

    def get_is_muted(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        setting = (
            obj.participant_settings
            .filter(
                user=request.user
            )
            .first()
        )

        if not setting:
            return False

        return setting.is_muted

    def get_latest_message(
            self,
            obj,
    ):
        message = (
            obj.messages
            .filter(
                is_deleted = False
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        if not message:
            return None

        return {
            "id": message.id,
            "sender_id": message.sender.id,
            "content": message.content,
            "created_at": message.created_at,
            "read_at": message.is_read,
            "delivered_at": (
                message.delivered_at
            ),
            "seen_at": (
                message.seen_at
            ),
        }


class MessageSerializer(
    serializers.ModelSerializer
):
    sender_username = serializers.CharField(
        source="sender.username",
        read_only=True,
    )

    sender_profile_picture = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Message

        fields = [
            "id",
            "conversation",
            "sender",
            "sender_username",
            "sender_profile_picture",
            "content",
            "is_read",
            "is_deleted",
            "delivered_at",
            "seen_at",
            "edited_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "conversation",
            "sender",
            "sender_username",
            "sender_profile_picture",
            "is_read",
            "is_deleted",
            "delivered_at",
            "seen_at",
            "edited_at",
            "deleted_at",
            "created_at",
            "updated_at",
        ]

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Message cannot be empty."
            )

        if len(value) > 5000:
            raise serializers.ValidationError(
                "Message cannot exceed 5000 characters."
            )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = (
                "This message has been deleted."
            )

        return data

    def get_sender_profile_picture(self, obj):
        profile_picture = getattr(
            obj.sender,
            "profile_picture",
            None,
        )

        if not profile_picture:
            return None

        try:
            return profile_picture.url
        except (
            ValueError,
            AttributeError,
        ):
            return str(profile_picture)