from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(
    admin.ModelAdmin
):

    list_display = [
        "id",
        "participant_one",
        "participant_two",
        "created_at",
        "updated_at",
    ]

    search_fields = [
        "participant_one__username",
        "participant_two__username",
    ]

    ordering = [
        "-updated_at"
    ]


@admin.register(Message)
class MessageAdmin(
    admin.ModelAdmin
):

    list_display = [
        "id",
        "conversation",
        "sender",
        "content",
        "is_read",
        "created_at",
    ]

    list_filter = [
        "is_read",
        "created_at",
    ]

    search_fields = [
        "sender__username",
        "content",
    ]

    ordering = [
        "-created_at"
    ]