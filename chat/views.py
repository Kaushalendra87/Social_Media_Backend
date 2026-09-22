from django.db.models import Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Conversation, 
    ConversationParticipant,
    Message,
)
from users.models import User

from .permissions import IsConversationParticipant
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
)


class ConversationListCreateView(
    generics.ListCreateAPIView
):
    """
    List conversations belonging to the authenticated user
    and create a new conversation.

    Supports conversation search using:

        ?search=username
    """

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Annotate unread count per conversation using a subquery so we
        # avoid N+1 counting in the serializer.
        unread_subquery = (
            Message.objects.filter(
                conversation=OuterRef("pk"),
                is_read=False,
                is_deleted=False,
            )
            .exclude(sender=user)
            .values("conversation")
            .annotate(cnt=Coalesce(Q(pk__isnull=False), 0))
            .values("cnt")
        )

        queryset = (
            Conversation.objects
            .filter(
                Q(participant_one=user)
                |
                Q(participant_two=user)
            )
            .select_related(
                "participant_one",
                "participant_two",
            )
            .prefetch_related(
                "participant_settings",
                "messages__sender",
            )
            .order_by("-updated_at")
        )

        search = self.request.query_params.get("search")
        if search:
            search = search.strip()
            if search:
                queryset = queryset.filter(
                    Q(participant_one__username__icontains=search)
                    | Q(participant_two__username__icontains=search)
                    | Q(participant_one__first_name__icontains=search)
                    | Q(participant_two__first_name__icontains=search)
                    | Q(participant_one__last_name__icontains=search)
                    | Q(participant_two__last_name__icontains=search)
                    | Q(participant_one__email__icontains=search)
                    | Q(participant_two__email__icontains=search)
                )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        user = request.user
        other_user_id = request.data.get("user_id")
        username = request.data.get("username")

        if not other_user_id and not username:
            return Response(
                {"detail": "user_id or username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        if other_user_id:
            other_user = get_object_or_404(User, id=other_user_id)
        else:
            other_user = get_object_or_404(User, username=username)

        if str(other_user.id) == str(user.id):
            return Response(
                {"detail": "You cannot create a conversation with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.id < other_user.id:
            participant_one = user
            participant_two = other_user
        else:
            participant_one = other_user
            participant_two = user

        conversation, created = Conversation.objects.get_or_create(
            participant_one=participant_one,
            participant_two=participant_two,
        )

        if created:
            ConversationParticipant.objects.bulk_create(
                [
                    ConversationParticipant(
                        conversation=conversation,
                        user=participant_one,
                    ),
                    ConversationParticipant(
                        conversation=conversation,
                        user=participant_two,
                    ),
                ]
            )

        serializer = self.get_serializer(conversation)
        serialized_data = serializer.data

        # Broadcast new conversation to BOTH participants in real time via user-level channel
        if created:
            channel_layer = get_channel_layer()
            if channel_layer:
                # Build JSON-safe payload (no datetime objects)
                conv_payload = self._make_json_safe(serialized_data)

                for participant in [participant_one, participant_two]:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{participant.id}",
                        {
                            "type": "conversation_created",
                            "conversation": conv_payload,
                        },
                    )

        return Response(
            serialized_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _make_json_safe(self, data):
        """Recursively convert non-serializable values (datetime, etc.) to strings."""
        import datetime
        if isinstance(data, dict):
            return {k: self._make_json_safe(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._make_json_safe(i) for i in data]
        if isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        return data


class ConversationDetailView(generics.RetrieveAPIView):
    """
    Retrieve a conversation.
    Only participants can access it.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    lookup_url_kwarg = "conversation_id"

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(
                Q(participant_one=user) | Q(participant_two=user)
            )
            .select_related("participant_one", "participant_two")
            .prefetch_related("messages")
        )


class ConversationDeleteView(generics.DestroyAPIView):
    """
    Delete a conversation.
    Only participants can delete it. Broadcasts conversation_deleted to channel layer first.
    """
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "conversation_id"

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(
                Q(participant_one=user) | Q(participant_two=user)
            )
            .select_related("participant_one", "participant_two")
            .prefetch_related("messages__sender")
            .order_by("-updated_at")
        )

    def perform_destroy(self, instance):
        conversation_id = instance.id
        participant_one_id = instance.participant_one_id
        participant_two_id = instance.participant_two_id
        channel_layer = get_channel_layer()
        if channel_layer:
            event = {
                "type": "conversation_deleted",
                "conversation_id": conversation_id,
            }
            # Notify the conversation WebSocket channel (for open chat windows)
            async_to_sync(channel_layer.group_send)(
                f"chat_conversation_{conversation_id}",
                event,
            )
            # Also notify BOTH user-level channels (for sidebar / users not in chat window)
            for uid in [participant_one_id, participant_two_id]:
                async_to_sync(channel_layer.group_send)(
                    f"user_{uid}",
                    event,
                )
        instance.delete()


class MessageListCreateView(generics.ListCreateAPIView):
    """
    GET: List messages from a conversation.
    POST: Send a message.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]

    def get_conversation(self):
        return get_object_or_404(
            Conversation.objects.filter(
                Q(participant_one=self.request.user)
                | Q(participant_two=self.request.user)
            ),
            id=self.kwargs["conversation_id"],
        )

    def get_queryset(self):
        conversation = self.get_conversation()
        return (
            Message.objects.filter(conversation=conversation)
            .select_related("sender")
            .order_by("created_at")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        conversation = self.get_conversation()
        content = request.data.get("content")

        if not content or not content.strip():
            return Response(
                {"detail": "Message content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content.strip(),
        )

        conversation.save(update_fields=["updated_at"])
        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update or delete a message.
    Only the sender can edit or delete their own message.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "message_id"

    def get_queryset(self):
        user = self.request.user
        return (
            Message.objects.filter(
                sender=user,
                is_deleted=False,
            )
            .filter(
                Q(conversation__participant_one=user)
                | Q(conversation__participant_two=user)
            )
        )

    def perform_update(self, serializer):
        serializer.save(edited_at=timezone.now())

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.content = ""
        instance.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "content",
                "updated_at",
            ]
        )


class MarkMessagesReadView(generics.GenericAPIView):
    """
    Mark messages received by the current user as read.
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]

    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation.objects.filter(
                Q(participant_one=request.user)
                | Q(participant_two=request.user)
            ),
            id=self.kwargs["conversation_id"],
        )

        updated_count = (
            Message.objects.filter(
                conversation=conversation,
                is_read=False,
            )
            .exclude(sender=request.user)
            .update(is_read=True)
        )

        return Response(
            {
                "message": "Messages marked as read.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class UnreadMessageCountView(generics.GenericAPIView):
    """
    Return the total number of unread messages received by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        unread_count = (
            Message.objects.filter(
                Q(conversation__participant_one=user)
                | Q(conversation__participant_two=user),
                is_read=False,
                is_deleted=False,
            )
            .exclude(sender=user)
            .count()
        )

        return Response(
            {"unread_count": unread_count},
            status=status.HTTP_200_OK,
        )


class ToggleConversationMuteView(generics.GenericAPIView):
    """
    Toggle mute state for the authenticated user in a conversation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation,
            id=self.kwargs["conversation_id"],
        )

        if not conversation.has_participant(request.user):
            return Response(
                {"detail": "You are not a participant of this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        participant_setting, created = ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=request.user,
        )

        participant_setting.is_muted = not participant_setting.is_muted
        participant_setting.save(update_fields=["is_muted", "updated_at"])

        return Response(
            {
                "conversation_id": conversation.id,
                "is_muted": participant_setting.is_muted,
            },
            status=status.HTTP_200_OK,
        )

class UserChatStatusView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]

    def get(
            self,
            request,
            user_id,
    ):

        try:
            user = User.objects.get(
                id = user_id,
                is_active = True,
            )

        except User.DoesNotExist:
            return Response(
                {
                    "detail": "User not found."
                },
                status = status.HTTP_404_NOT_FOUND,
            )

        # Allow presence check if user is self, shares a conversation, or follows target user
        if request.user.id != user.id:
            from users.models import Follow
            shares_conversation = Conversation.objects.filter(
                (Q(participant_one=request.user) & Q(participant_two=user)) |
                (Q(participant_one=user) & Q(participant_two=request.user))
            ).exists()
            is_follower = Follow.objects.filter(follower=request.user, following=user).exists()
            
            if not (shares_conversation or is_follower):
                return Response(
                    {"detail": "You do not have permission to view this user's online status."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return Response(
            {
                "user_id": user_id,
                "username": user.username,
                "is_online": user.is_online,
                "last_seen": user.last_seen,
            }
        )