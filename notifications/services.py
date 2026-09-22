from .models import Notification

def create_notification(
        *,
        recipient,
        actor,
        notification_type,
        post=None,
        comment=None,
        reply=None,
        follow_request=None,
):
    if recipient == actor:
        return None

    return Notification.objects.create(
        recipient = recipient,
        actor = actor,
        notification_type = notification_type,
        post = post,
        comment = comment,
        reply=reply,
        follow_request = follow_request,
    )

