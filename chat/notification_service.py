from notifications.models import Notification


def create_message_notification(
    actor,
    recipient,
    message,
):

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type="message",
        message=(
            f"{actor.username} sent you a message."
        ),
        content_object=message,
    )