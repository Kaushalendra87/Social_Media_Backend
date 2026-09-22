from django.db.models import Q

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSeializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSeializer
    permission_classes = [ IsAuthenticated ]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(
                recipient = self.request.user
            )
            .select_related(
                "actor",
                "post",
                "comment",
                "reply",
                "follow_request",
            )
            .order_by("-created_at")
        )


class UnreadNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_count = Notification.objects.filter(
            recipient = request.user,
            is_read = False,
        ).count()

        return Response(
            {
                "unread_count": unread_count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch (self, request, pk):
        try:
            notification = Notification.objects.get(\
                id=pk,
                recipient =request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {
                    "detail": "Notification not found."
                },
                status=status.HTTP_404_NOT_FOUND,            
            )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(
            {
                "detail": "Notification marked as read."
            },
            status=status.HTTP_200_OK,        
        )


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(
            is_read=True
        )

        return Response(
            {
                "detail": "All notifications marked as read.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient = request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {
                    "detail": "Notication not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

    