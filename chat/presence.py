from collections import defaultdict
from threading import Lock


class PresenceTracker:
    """
    Tracks active WebSocket connections for each user.

    A user can have multiple WebSocket connections,
    for example:
    - multiple browser tabs
    - multiple devices
    """

    def __init__(self):
        self.connections = defaultdict(set)
        self.lock = Lock()

    def add(self, user_id, channel_name):
        with self.lock:
            self.connections[user_id].add(channel_name)

            return len(self.connections[user_id])

    def remove(self, user_id, channel_name):
        with self.lock:
            if user_id not in self.connections:
                return 0

            self.connections[user_id].discard(channel_name)

            if not self.connections[user_id]:
                del self.connections[user_id]
                return 0

            return len(self.connections[user_id])

    def is_online(self, user_id):
        with self.lock:
            return bool(
                self.connections.get(user_id)
            )

    def connection_count(self, user_id):
        with self.lock:
            return len(
                self.connections.get(user_id, set())
            )


presence_tracker = PresenceTracker()