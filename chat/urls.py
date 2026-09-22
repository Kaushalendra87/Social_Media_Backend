from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    MarkMessagesReadView,
    MessageListCreateView,
    UnreadMessageCountView,
    MessageUpdateDeleteView,
    ConversationDeleteView,
    ToggleConversationMuteView,
    UserChatStatusView,
)


urlpatterns = [

    # API 1: List/Create Conversations
    path(
        "conversations/",
        ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),

    # API 2: Conversation Detail
    path(
        "conversations/<int:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),

    # API 3: List/Create Messages
    path(
        "conversations/<int:conversation_id>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create",
    ),

    # API 4: Mark Messages as Read
    path(
        "conversations/<int:conversation_id>/messages/read/",
        MarkMessagesReadView.as_view(),
        name="mark-messages-read",
    ),

    # API 5: Unread Message Count
    path(
        "unread-count/",
        UnreadMessageCountView.as_view(),
        name="unread-message-count",
    ),

    # API 6: Message Update / Delete
    path(
        "messages/<int:message_id>/",
        MessageUpdateDeleteView.as_view(),
        name="message-update-delete",
    ),

    # API 7: Delete a Conversation
    path(
        "conversations/<int:conversation_id>/delete/",
        ConversationDeleteView.as_view(),
        name="conversation-delete",
    ),

    # API 8: Toggle Conversation mute
    path(
        "conversations/<int:conversation_id>/mute/",
        ToggleConversationMuteView.as_view(),
        name="conversation-mute",
    ),

    # API 9:  Get User Chat Status
    path(
        "users/<int:user_id>/status/",
        UserChatStatusView.as_view(),
        name="user-chat-status",
    ),

]