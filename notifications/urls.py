from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    NotificationDeleteView,
    NotificationListView,
    NotificationMarkReadView,
    UnreadNotificationCountView,
)


urlpatterns = [
    # ============================================================
    # NOTIFICATION LIST
    # GET /api/notifications/
    # Returns all notifications for the authenticated user
    # ============================================================
    path(
        "",
        NotificationListView.as_view(),
        name="notification-list",
    ),

    # ============================================================
    # UNREAD NOTIFICATION COUNT
    # GET /api/notifications/unread-count/
    # Returns the number of unread notifications
    # ============================================================
    path(
        "unread-count/",
        UnreadNotificationCountView.as_view(),
        name="notification-unread-count",
    ),

    # ============================================================
    # MARK ALL NOTIFICATIONS AS READ
    # PATCH /api/notifications/mark-all-read/
    # Marks all notifications as read
    # ============================================================
    path(
        "mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="notification-mark-all-read",
    ),

    # ============================================================
    # MARK SINGLE NOTIFICATION AS READ
    # PATCH /api/notifications/<id>/read/
    # Marks a specific notification as read
    # ============================================================
    path(
        "<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),

    # ============================================================
    # DELETE SINGLE NOTIFICATION
    # DELETE /api/notifications/<id>/
    # Deletes a specific notification
    # ============================================================
    path(
        "<int:pk>/",
        NotificationDeleteView.as_view(),
        name="notification-delete",
    ),
]
