from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message

def get_other_participant(
        conversation,
        user
):

    if conversation.participant_one_id == user.id:
        return conversation.participant_two

    if conversation.participant_two_id == user.id:
        return conversation.participant_one

    return None

def mark_messages_delivered(
        conversation_id,
        user,
):
    now = timezone.now()

    messages = (
        Message.objects
        .filter(
            conversation_id = conversation_id,
            is_deleted = False,
            delivered_at__isnull = True,
        )
        .exclude(
            sender = user
        )
    )

    updated_count = messages.update(
        delivered_at = now
    )

    return updated_count


def mark_messages_seen(
        conversation_id,
        user,
):
    now = timezone.now()

    messages = (
        Message.objects
        .filter(
            conversation_id = conversation_id,
            is_deleted = False,
            seen_at__isnull = True,
        )
        .exclude(
            sender = user
        )
    )

    updated_count = messages.update(
        seen_at = now,
        is_read = True,
    )

    return updated_count

def get_unread_message_count(
        conversation_id,
        user,
):

    return (
        Message.objects
        .filter(
            conversation_id = conversation_id,
            is_deleted = False,
            seen_at__isnull = True,
        )
        .exclude(
            sender = user
        )
        .count()
    )

def users_can_view_presence(user, target_user_id):
    """
    Determine whether `user` is allowed to see
    the presence of `target_user_id`.

    Users can see each other's presence if they
    participate in the same conversation.
    """

    if not user or not user.is_authenticated:
        return False

    if user.id == target_user_id:
        return True

    return Conversation.objects.filter(
        Q(
            participant_one_id=user.id,
            participant_two_id=target_user_id,
        )
        |
        Q(
            participant_one_id=target_user_id,
            participant_two_id=user.id,
        )
    ).exists()


def get_user_presence_data(user_id):
    """
    Return serialized presence information.
    """

    from users.models import User

    try:
        user = User.objects.get(id=user_id)

        return {
            "user_id": user.id,
            "is_online": user.is_online,
            "last_seen": (
                user.last_seen.isoformat()
                if user.last_seen
                else None
            ),
        }

    except User.DoesNotExist:
        return None