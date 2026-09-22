from rest_framework.permissions import (
    BasePermission,
)

from .models import Conversation

class IsConversationParticipant(
    BasePermission
):
    """
    Allows access only to users who are participants 
    in the conversation.
    """

    def has_object_permission(self, request, view, obj):
        if not isinstance(
            obj,
            Conversation,
        ):
            return False

        return (
            obj.participant_one == request.user
            or
            obj.participant_two == request.user
        )