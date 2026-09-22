import json
from threading import Lock

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message

from .services import (
    get_other_participant,
    get_unread_message_count,
    mark_messages_delivered,
    mark_messages_seen,
)

from users.models import User


class PresenceTracker:
    """Track active WebSocket connections per user."""

    def __init__(self):
        self.connections = {}
        self.lock = Lock()

    def add(self, user_id, channel_name):
        with self.lock:
            connections = self.connections.setdefault(
                user_id,
                set(),
            )
            connections.add(channel_name)
            return len(connections)

    def remove(self, user_id, channel_name):
        with self.lock:
            connections = self.connections.get(user_id)

            if not connections:
                return 0

            connections.discard(channel_name)

            if not connections:
                self.connections.pop(user_id, None)
                return 0

            return len(connections)

    def is_online(self, user_id):
        with self.lock:
            return bool(self.connections.get(user_id))

    def connection_count(self, user_id):
        with self.lock:
            return len(self.connections.get(user_id, set()))


presence_tracker = PresenceTracker()

class UserChatConsumer(AsyncWebsocketConsumer):
    """
    Handles user-level real-time events across the application
    (such as new conversation creation, conversation deletion, and user messages).
    """

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close(code=4401)
            return

        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )
        await self.accept()

        # Track this WebSocket connection. A user is considered online
        # while at least one WebSocket connection remains active.
        connection_count = presence_tracker.add(
            self.user.id,
            self.channel_name,
        )

        if connection_count == 1:
            await self.set_user_online()
            await self.broadcast_presence_to_contacts(
                is_online=True
            )

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection",
                    "status": "connected",
                    "user_id": self.user.id,
                    "is_online": True,
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user") and self.user and not self.user.is_anonymous:
            remaining_connections = presence_tracker.remove(
                self.user.id,
                self.channel_name,
            )

            if remaining_connections == 0:
                await self.set_user_offline()
                await self.broadcast_presence_to_contacts(
                    is_online=False
                )

        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
                if data.get("type") == "ping":
                    await self.send(text_data=json.dumps({"type": "pong"}))
            except Exception:
                pass

    @database_sync_to_async
    def set_user_online(self):
        User.objects.filter(id=self.user.id).update(
            is_online=True
        )

    @database_sync_to_async
    def set_user_offline(self):
        User.objects.filter(id=self.user.id).update(
            is_online=False,
            last_seen=timezone.now(),
        )

    @database_sync_to_async
    def get_presence_contact_ids(self):
        """Return users sharing a conversation with this user."""
        return list(
            Conversation.objects.filter(
                Q(participant_one_id=self.user.id)
                | Q(participant_two_id=self.user.id)
            ).values_list(
                "participant_one_id",
                "participant_two_id",
            )
        )

    @database_sync_to_async
    def get_current_presence(self):
        try:
            user = User.objects.get(id=self.user.id)
        except User.DoesNotExist:
            return None

        return {
            "is_online": user.is_online,
            "last_seen": (
                user.last_seen.isoformat()
                if user.last_seen
                else None
            ),
        }

    async def broadcast_presence_to_contacts(self, is_online):
        """Notify users who share a conversation with this user."""
        rows = await self.get_presence_contact_ids()
        contact_ids = set()
        presence = await self.get_current_presence()

        if not presence:
            return

        for participant_one_id, participant_two_id in rows:
            if participant_one_id != self.user.id:
                contact_ids.add(participant_one_id)
            if participant_two_id != self.user.id:
                contact_ids.add(participant_two_id)

        for contact_id in contact_ids:
            await self.channel_layer.group_send(
                f"user_{contact_id}",
                {
                    "type": "presence_update",
                    "user_id": self.user.id,
                    "is_online": is_online,
                    "last_seen": presence["last_seen"],
                },
            )

    async def presence_update(self, event):
        if event["user_id"] == self.user.id:
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "is_online": event["is_online"],
                    "last_seen": event["last_seen"],
                }
            )
        )

    async def conversation_created(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "conversation_created",
                    "conversation": event["conversation"],
                }
            )
        )

    async def conversation_deleted(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "conversation_deleted",
                    "conversation_id": event["conversation_id"],
                }
            )
        )

    async def user_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_message",
                    "message": event["message"],
                }
            )
        )


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time communication for a single conversation.

    Every participant connected to the same conversation joins
    the same channel group.
    """

    # ==================================================
    # CONNECT
    # ==================================================

    async def connect(self):

        self.user = self.scope.get("user")

        self.conversation_id = (
            self.scope["url_route"]["kwargs"]["conversation_id"]
        )

        self.room_group_name = (
            f"chat_conversation_{self.conversation_id}"
        )

        print("========================================")
        print("WEBSOCKET CONNECT")
        print("USER:", self.user)
        print("USER ID:", getattr(self.user, "id", None))
        print("CONVERSATION:", self.conversation_id)
        print("GROUP:", self.room_group_name)
        print("========================================")

        # --------------------------------------------------
        # Authentication
        # --------------------------------------------------

        if not self.user or self.user.is_anonymous:

            print("Authentication failed.")

            await self.close(code=4401)

            return

        # --------------------------------------------------
        # Conversation authorization
        # --------------------------------------------------

        allowed = await self.user_can_access_conversation()

        print("CONVERSATION ACCESS:", allowed)

        if not allowed:

            print(
                f"User {self.user.id} is not a participant "
                f"of conversation {self.conversation_id}"
            )

            await self.close(code=4403)

            return

        # --------------------------------------------------
        # Join channel group
        # --------------------------------------------------

        print("Adding channel to Redis group...")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        print("Successfully added to Redis group.")

        # --------------------------------------------------
        # Accept WebSocket
        # --------------------------------------------------

        await self.accept()

        print("WebSocket accepted.")

        # --------------------------------------------------
        # Presence connection tracking
        # --------------------------------------------------

        connection_count = presence_tracker.add(
            self.user.id,
            self.channel_name,
        )

        print(
            f"USER {self.user.id} ACTIVE CONNECTIONS:",
            connection_count,
        )

        if connection_count == 1:
            await self.set_user_online()
            await self.broadcast_presence(is_online=True)

        # --------------------------------------------------
        # Connection confirmation
        # --------------------------------------------------

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection",
                    "status": "connected",
                    "conversation_id": self.conversation_id,
                    "user_id": self.user.id,
                    "is_online": True,
                }
            )
        )

        # Send the current presence of the other participant
        # immediately after the conversation WebSocket connects.
        other_user_id = await self.get_other_user_id()

        if other_user_id:
            other_presence = await self.get_user_presence(
                other_user_id
            )

            if other_presence:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "presence",
                            "user_id": other_presence["user_id"],
                            "is_online": other_presence["is_online"],
                            "last_seen": other_presence["last_seen"],
                        }
                    )
                )

    # ==================================================
    # DISCONNECT
    # ==================================================

    async def disconnect(self, close_code):

        print(
            f"WebSocket DISCONNECT "
            f"/ws/chat/{getattr(self, 'conversation_id', None)}/ "
            f"[user={getattr(self.user, 'id', None)}] "
            f"[code={close_code}]"
        )

        if (
            getattr(self, "user", None)
            and not self.user.is_anonymous
        ):
            remaining_connections = presence_tracker.remove(
                self.user.id,
                self.channel_name,
            )

            print(
                f"USER {self.user.id} REMAINING CONNECTIONS:",
                remaining_connections,
            )

            if remaining_connections == 0:
                await self.set_user_offline()
                await self.broadcast_presence(is_online=False)

        if hasattr(self, "room_group_name"):

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    # ==================================================
    # RECEIVE
    # ==================================================

    async def receive(
        self,
        text_data=None,
        bytes_data=None,
    ):

        if not text_data:

            await self.send_error(
                "WebSocket message cannot be empty."
            )

            return

        try:

            data = json.loads(text_data)

        except (json.JSONDecodeError, TypeError):

            await self.send_error(
                "Invalid JSON."
            )

            return

        if not isinstance(data, dict):

            await self.send_error(
                "WebSocket data must be a JSON object."
            )

            return

        event_type = data.get("type")

        print(
            f"WEBSOCKET EVENT "
            f"user={self.user.id} "
            f"type={event_type} "
            f"data={data}"
        )

        if event_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        # --------------------------------------------------
        # Message
        # --------------------------------------------------

        if event_type == "message":

            await self.handle_message(data)

        # --------------------------------------------------
        # Typing
        # --------------------------------------------------

        elif event_type == "typing":

            await self.handle_typing(data)

        # --------------------------------------------------
        # Read
        # --------------------------------------------------

        elif event_type == "read":

            await self.handle_read()

        # --------------------------------------------------
        # Edit
        # --------------------------------------------------

        elif event_type == "edit_message":

            await self.handle_edit_message(data)

        # --------------------------------------------------
        # Delete
        # --------------------------------------------------

        elif event_type == "delete_message":

            await self.handle_delete_message(data)

        else:

            await self.send_error(
                "Unknown event type."
            )

    # ==================================================
    # MESSAGE
    # ==================================================

    async def handle_message(self, data):

        content = data.get("content")

        # --------------------------------------------------
        # Validate content
        # --------------------------------------------------

        if not isinstance(content, str):

            await self.send_error(
                "Message content must be a string."
            )

            return

        content = content.strip()

        if not content:

            await self.send_error(
                "Message cannot be empty."
            )

            return

        if len(content) > 5000:

            await self.send_error(
                "Message cannot exceed 5000 characters."
            )

            return

        # --------------------------------------------------
        # Create message
        # --------------------------------------------------

        message = await self.create_message(content)

        if not message:

            await self.send_error(
                "Unable to create message."
            )

            return

        print(
            "MESSAGE CREATED:",
            message
        )

        # --------------------------------------------------
        # Broadcast message
        # --------------------------------------------------

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            },
        )

    # ==================================================
    # CHAT MESSAGE EVENT
    # ==================================================

    async def chat_message(self, event):

        print(
            "SENDING MESSAGE TO WEBSOCKET:",
            event["message"]
        )

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message": event["message"],
                }
            )
        )

    # ==================================================
    # PRESENCE
    # ==================================================

    async def broadcast_presence(self, is_online):

        other_user_id = await self.get_other_user_id()

        if not other_user_id:
            return

        presence = await self.get_user_presence(
            self.user.id
        )

        if not presence:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence_update",
                "user_id": self.user.id,
                "is_online": is_online,
                "last_seen": presence["last_seen"],
            },
        )

    async def presence_update(self, event):

        if event["user_id"] == self.user.id:
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "is_online": event["is_online"],
                    "last_seen": event["last_seen"],
                }
            )
        )

    # ==================================================
    # TYPING
    # ==================================================

    async def handle_typing(self, data):

        is_typing = bool(
            data.get(
                "is_typing",
                False,
            )
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_event",
                "user_id": self.user.id,
                "username": self.user.username,
                "is_typing": is_typing,
            },
        )

    async def typing_event(self, event):

        # Do not send typing event back to sender

        if event["user_id"] == self.user.id:

            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    # ==================================================
    # READ RECEIPT
    # ==================================================

    async def handle_read(self):

        updated_count = await self.mark_message_read()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_event",
                "user_id": self.user.id,
                "updated_count": updated_count,
            },
        )

    async def read_event(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "read",
                    "user_id": event["user_id"],
                    "updated_count": event["updated_count"],
                }
            )
        )

    # ==================================================
    # EDIT MESSAGE
    # ==================================================

    async def handle_edit_message(self, data):

        message_id = data.get("message_id")

        content = data.get("content")

        # --------------------------------------------------
        # Validate message ID
        # --------------------------------------------------

        if not message_id:

            await self.send_error(
                "message_id is required."
            )

            return

        try:

            message_id = int(message_id)

        except (TypeError, ValueError):

            await self.send_error(
                "message_id must be a valid integer."
            )

            return

        # --------------------------------------------------
        # Validate content
        # --------------------------------------------------

        if not isinstance(content, str):

            await self.send_error(
                "Message content must be a string."
            )

            return

        content = content.strip()

        if not content:

            await self.send_error(
                "Message cannot be empty."
            )

            return

        if len(content) > 5000:

            await self.send_error(
                "Message cannot exceed 5000 characters."
            )

            return

        # --------------------------------------------------
        # Update message
        # --------------------------------------------------

        message = await self.edit_message(
            message_id,
            content,
        )

        if not message:

            await self.send_error(
                "Message not found or you are not allowed to edit this message."
            )

            return

        print(
            "MESSAGE EDITED:",
            message
        )

        # --------------------------------------------------
        # Broadcast edited message
        # --------------------------------------------------

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_edited",
                "message": message,
            },
        )

    async def message_edited(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edited",
                    "message": event["message"],
                }
            )
        )

    # ==================================================
    # DELETE MESSAGE
    # ==================================================

    async def handle_delete_message(self, data):

        message_id = data.get("message_id")

        # --------------------------------------------------
        # Validate message ID
        # --------------------------------------------------

        if not message_id:

            await self.send_error(
                "message_id is required."
            )

            return

        try:

            message_id = int(message_id)

        except (TypeError, ValueError):

            await self.send_error(
                "message_id must be a valid integer."
            )

            return

        # --------------------------------------------------
        # Delete message
        # --------------------------------------------------

        message = await self.delete_message(
            message_id
        )

        if not message:

            await self.send_error(
                "Message not found or you are not allowed to delete it."
            )

            return

        print(
            "MESSAGE DELETED:",
            message
        )

        # --------------------------------------------------
        # Broadcast deletion
        # --------------------------------------------------

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_deleted",
                "message_id": message["id"],
                "deleted_at": message["deleted_at"],
            },
        )

    async def message_deleted(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_deleted",
                    "message_id": event["message_id"],
                    "deleted_at": event["deleted_at"],
                }
            )
        )

    # ==================================================
    # CONVERSATION DELETED EVENT
    # ==================================================

    async def conversation_deleted(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "conversation_deleted",
                    "conversation_id": event["conversation_id"],
                }
            )
        )

    # ==================================================
    # ERROR
    # ==================================================

    async def send_error(self, message):

        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": message,
                }
            )
        )

    # ==================================================
    # DATABASE METHODS
    # ==================================================

    @database_sync_to_async
    def user_can_access_conversation(self):

        return Conversation.objects.filter(
            id=self.conversation_id,
        ).filter(
            Q(participant_one=self.user)
            |
            Q(participant_two=self.user)
        ).exists()

    @database_sync_to_async
    def set_user_online(self):
        User.objects.filter(id=self.user.id).update(
            is_online=True
        )

    @database_sync_to_async
    def set_user_offline(self):
        User.objects.filter(id=self.user.id).update(
            is_online=False,
            last_seen=timezone.now(),
        )

    @database_sync_to_async
    def get_user_presence(self, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        return {
            "user_id": user.id,
            "is_online": user.is_online,
            "last_seen": (
                user.last_seen.isoformat()
                if user.last_seen
                else None
            ),
        }

    @database_sync_to_async
    def get_other_user_id(self):
        try:
            conversation = Conversation.objects.get(
                id=self.conversation_id
            )
        except Conversation.DoesNotExist:
            return None

        if conversation.participant_one_id == self.user.id:
            return conversation.participant_two_id

        if conversation.participant_two_id == self.user.id:
            return conversation.participant_one_id

        return None

    # ==================================================
    # CREATE MESSAGE
    # ==================================================

    @database_sync_to_async
    def create_message(self, content):

        try:

            conversation = (
                Conversation.objects
                .filter(
                    id=self.conversation_id,
                )
                .filter(
                    Q(participant_one=self.user)
                    |
                    Q(participant_two=self.user)
                )
                .first()
            )

            if not conversation:

                return None

            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
            )

            # Update conversation timestamp

            conversation.updated_at = timezone.now()

            conversation.save(
                update_fields=[
                    "updated_at"
                ]
            )

            # --------------------------------------------------
            # IMPORTANT:
            # Convert datetime objects to strings BEFORE
            # sending data through Redis.
            # --------------------------------------------------

            profile_picture = getattr(self.user, "profile_picture", None)
            sender_profile_picture = None
            if profile_picture:
                try:
                    sender_profile_picture = profile_picture.url
                except Exception:
                    sender_profile_picture = str(profile_picture)

            return {
                "id": message.id,
                "conversation": self.conversation_id,
                "sender": self.user.id,
                "sender_username": self.user.username,
                "sender_profile_picture": sender_profile_picture,
                "content": message.content,
                "is_read": message.is_read,
                "is_deleted": message.is_deleted,

                "edited_at": (
                    message.edited_at.isoformat()
                    if message.edited_at
                    else None
                ),

                "deleted_at": (
                    message.deleted_at.isoformat()
                    if message.deleted_at
                    else None
                ),

                "created_at": (
                    message.created_at.isoformat()
                    if message.created_at
                    else None
                ),

                "updated_at": (
                    message.updated_at.isoformat()
                    if message.updated_at
                    else None
                ),
            }

        except Exception as error:

            print(
                "CREATE MESSAGE ERROR:",
                error
            )

            return None

    # ==================================================
    # MARK MESSAGE AS READ
    # ==================================================

    @database_sync_to_async
    def mark_message_read(self):

        return (
            Message.objects
            .filter(
                conversation_id=self.conversation_id,
                is_read=False,
                is_deleted=False,
            )
            .exclude(
                sender=self.user
            )
            .update(
                is_read=True
            )
        )

    # ==================================================
    # EDIT MESSAGE
    # ==================================================

    @database_sync_to_async
    def edit_message(
        self,
        message_id,
        content,
    ):

        try:

            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user,
                is_deleted=False,
            )

        except Message.DoesNotExist:

            return None

        message.content = content

        message.edited_at = timezone.now()

        message.save(
            update_fields=[
                "content",
                "edited_at",
                "updated_at",
            ]
        )

        return {
            "id": message.id,
            "conversation": self.conversation_id,
            "sender": self.user.id,
            "sender_username": self.user.username,
            "content": message.content,

            "edited_at": (
                message.edited_at.isoformat()
                if message.edited_at
                else None
            ),

            "updated_at": (
                message.updated_at.isoformat()
                if message.updated_at
                else None
            ),
        }

    # ==================================================
    # DELETE MESSAGE
    # ==================================================

    @database_sync_to_async
    def delete_message(self, message_id):

        try:

            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user,
                is_deleted=False,
            )

        except Message.DoesNotExist:

            return None

        message.is_deleted = True

        message.deleted_at = timezone.now()

        message.content = ""

        message.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "content",
                "updated_at",
            ]
        )

        return {
            "id": message.id,

            "deleted_at": (
                message.deleted_at.isoformat()
                if message.deleted_at
                else None
            ),
        }
