from django.utils import timezone

from users.models import User

def set_user_online(user_id):
    """
    Mark a user aas online.
    """

    User.objects.filter(id=user_id).update(
        is_online = True,
    )


def set_user_offline(user_id):
    """
    Mark a user as offline.
    """    

    User.objects.filter(id=user_id).update(
        is_online=False,
        last_seen=timezone.now(),
    )

def get_user_presence(user_id):
    """
    return the current presence information of a user.
    """

    try:
        user = User.objects.get(id=user_id)
        return {
            "id": user.id,
            "is_online": user.is_online,
            "last_seen": user.last_seen,
        }

    except User.DoesNotExist:
        return None

    