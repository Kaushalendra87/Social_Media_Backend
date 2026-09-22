from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from notifications.models import Notification
from notifications.services import create_notification


from rest_framework import generics
from rest_framework import status

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from rest_framework.response import Response

from rest_framework.views import APIView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

from .models import (
    User, 
    Follow,
    FollowRequest,
)


from .serializers import (
    FollowRequestSerializer,
    RegisterSerializer,
    UserDiscoverySerializer,
    UserSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    PublicUserSerializer,
    FollowSerializer,
    FollowUserSerializer,
)

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for registering a new user
    """

    queryset = User.objects.all()

    serializer_class = RegisterSerializer

    permission_classes = [
        AllowAny,
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data = request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        response_serializer = UserSerializer(
            user
        )

        return Response(
            {
                "message": "User registered successfully.",
                "user": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class EmailTokenObtainPairView(
    TokenObtainPairView
):
    """
    Login using email and password 
    """

    serializer_class = (
        EmailTokenObtainPairSerializer
    )


class LogoutView(APIView):
    """
    Logout the authenticated user by blaclisting the refresh token
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):

        serializer = LogoutSerializer(
            data = request.data
        )

        serializer.is_valid(
            raise_exception= True
        )

        serializer.save()

        return Response(
            {
                "message": "Logout successful"
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserView(generics.RetrieveAPIView):
    """
    Return the currently authenticated user.
    """

    serializer_class = UserSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_object(self):
        return self.request.user


class ProfileUpdateView(
    generics.UpdateAPIView
):
    """
    Update the currently authenticated user's profile.
    """

    serializer_class = ProfileUpdateSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    http_method_names = [
        "patch",
        "put",
    ]

    def get_object(self):
        return self.request.user



class RemoveProfilePictureView(
    APIView
):
    """
    Remove the authenticated user's
    profile picture.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def delete(self, request):

        user = request.user

        if not user.profile_picture:
            return Response(
                {
                    "message": (
                        "No profile picture exists."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.profile_picture.delete(
            save=False
        )

        user.profile_picture = None

        user.save(
            update_fields=[
                "profile_picture",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": (
                    "Profile picture removed successfully."
                )
            },
            status=status.HTTP_200_OK,
        )


class PublicProfileView(
    generics.RetrieveAPIView
):
    """
    Retrieve a user's public profile.
    """

    serializer_class = PublicUserSerializer

    permission_classes = [
        AllowAny,
    ]

    lookup_field = "username"

    look_up_kwarg = "username"

    queryset = User.objects.filter(
        is_active = True
    )



class FollowUserView(APIView):
    """
    Follow another user.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
            self,
            request,
            username
    ):

        follower = request.user

        try:

            following = User.objects.get(
                username = username,
                is_active = True,
            )

        except User.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "User not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ----------------------------------------------
        # Prevent self-follow
        # ----------------------------------------------

        if follower == following:

            return Response(
                {
                    "detail": (
                        "You cannot follow yourself."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------
        # Check existing relationship
        # ----------------------------------------------

        follow =  Follow.objects.filter(
            follower=follower,
            following=following,
        ).first()

        if follow:

            return Response(
                {
                    "detail": (
                        "You are already following "
                        "this user."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------
        # Create relationship
        # ----------------------------------------------

        follow = Follow.objects.create(
            follower=follower,
            following=following,
        )

        create_notification(
            recipient=following,
            actor=follower,
            notification_type=(
                Notification.NotificationType.FOLLOW
            ),
        )

        return Response(
            {
                "message": (
                    f"You are now following "
                    f"{following.username}."
                ),
                "follow": FollowSerializer(
                    follow
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(
            self,
            request,
            username
    ):

        follower = request.user

        try:

            following = User.objects.get(
                username=username,
                is_active=True,
            )

        except User.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "User not found. "
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if follower == following:

            return Response(
                {
                    "detail": (
                        "You cannot unfollow yourself."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = Follow.objects.filter(
            follower=follower,
            following=following,
        ).delete()

        if deleted_count == 0:

            return Response(
                {
                    "detail": (
                        "You are not following "
                        "this user."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    f"You unfollowed "
                    f"{following.username}."
                )
            },
            status=status.HTTP_200_OK,
        )


class FollowersListView(
    generics.ListAPIView
):
    """
    Return the followers of a given user.
    Followers = users who have a Follow row where Follow.following == user.
    These rows are reached via user.follower_relationships (following FK reverse).
    """

    serializer_class = FollowUserSerializer

    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        username = self.kwargs.get("username") or self.kwargs.get("user_id")

        try:
            if isinstance(username, int) or (isinstance(username, str) and username.isdigit()):
                user = User.objects.get(id=int(username), is_active=True)
            else:
                user = User.objects.get(username=username, is_active=True)

        except User.DoesNotExist:
            return User.objects.none()

        if user.is_private:
            req_user = self.request.user
            is_owner = req_user.is_authenticated and req_user == user
            is_follower = req_user.is_authenticated and Follow.objects.filter(follower=req_user, following=user).exists()
            if not (is_owner or is_follower):
                raise PermissionDenied("This account is private. Follow this user to view their followers.")

        # Followers of `user` = users who follow `user`
        # = Follow rows where following=user  →  reached via user.follower_relationships (following FK reverse)
        # Then get the follower users via following_relationships (follower FK reverse)
        return User.objects.filter(
            following_relationships__following=user,
            is_active=True,
        ).order_by(
            "-following_relationships__created_at"
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        req_user = self.request.user
        if req_user.is_authenticated:
            # Bulk-load viewer's follows & pending requests so the serializer
            # doesn't hit the DB once per list row.
            context["viewer_following_ids"] = set(
                Follow.objects.filter(follower=req_user)
                .values_list("following_id", flat=True)
            )
            context["viewer_pending_request_ids"] = set(
                FollowRequest.objects.filter(
                    sender=req_user,
                    status=FollowRequest.STATUS_PENDING,
                ).values_list("receiver_id", flat=True)
            )
        return context


class FollowingListView(
    generics.ListAPIView
):
    """
    Return the users that a given user follows.
    Following = users who have a Follow row where Follow.follower == user.
    These rows are reached via user.following_relationships (follower FK reverse).
    """

    serializer_class = FollowUserSerializer

    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        username = self.kwargs.get("username") or self.kwargs.get("user_id")

        try:
            if isinstance(username, int) or (isinstance(username, str) and username.isdigit()):
                user = User.objects.get(id=int(username), is_active=True)
            else:
                user = User.objects.get(username=username, is_active=True)

        except User.DoesNotExist:
            return User.objects.none()

        if user.is_private:
            req_user = self.request.user
            is_owner = req_user.is_authenticated and req_user == user
            is_follower = req_user.is_authenticated and Follow.objects.filter(follower=req_user, following=user).exists()
            if not (is_owner or is_follower):
                raise PermissionDenied("This account is private. Follow this user to view their following list.")

        # Following of `user` = users that `user` follows
        # = Follow rows where follower=user  →  reached via user.following_relationships (follower FK reverse)
        # Then get the following users via follower_relationships (following FK reverse)
        return User.objects.filter(
            follower_relationships__follower=user,
            is_active=True,
        ).order_by(
            "-follower_relationships__created_at"
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        req_user = self.request.user
        if req_user.is_authenticated:
            context["viewer_following_ids"] = set(
                Follow.objects.filter(follower=req_user)
                .values_list("following_id", flat=True)
            )
            context["viewer_pending_request_ids"] = set(
                FollowRequest.objects.filter(
                    sender=req_user,
                    status=FollowRequest.STATUS_PENDING,
                ).values_list("receiver_id", flat=True)
            )
        return context


class FollowStatusView(APIView):
    """
    Return follow status and counts for a specific user.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        username
    ):

        try:

            user = User.objects.get(
                username=username,
                is_active=True,
            )

        except User.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "User not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        is_following = Follow.objects.filter(
            follower = request.user,
            following = user,
        ).exists()

        followers_count = (
            Follow.objects.filter(
                following=user
            ).count()
        )

        following_count = (
            Follow.objects.filter(
                follower=user
            ).count()
        )

        return Response(
            {
                "is_following": is_following,
                "followers_count": followers_count,
                "following_count": following_count,
            },
            status=status.HTTP_200_OK,
        )


class UserSearchView(generics.ListAPIView):
    """
    Search users by username, first_name or last_name.
    """

    serializer_class = UserDiscoverySerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        query = (
            self.request.query_params
            .get("q", "")
            .strip()
        )

        queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )

        from django.db.models import Count
        return queryset.annotate(
            followers_count=Count("follower_relationships", distinct=True),
            following_count=Count("following_relationships", distinct=True),
        ).order_by("username")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        req_user = self.request.user
        if req_user.is_authenticated:
            context["viewer_following_ids"] = set(
                Follow.objects.filter(follower=req_user)
                .values_list("following_id", flat=True)
            )
            context["viewer_pending_request_ids"] = set(
                FollowRequest.objects.filter(
                    sender=req_user,
                    status=FollowRequest.STATUS_PENDING,
                ).values_list("receiver_id", flat=True)
            )
        return context

class SendFollowRequestView(
    generics.CreateAPIView
):
    """
    Send a follow request to another user.
    """

    serializer_class = FollowRequestSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        sender = request.user

        receiver = get_object_or_404(
            User,
            id=self.kwargs["user_id"],
        )

        if sender == receiver:
            return Response(
                {
                    "detail": (
                        "You cannot follow yourself."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        #Already Following
        if Follow.objects.filter(
            follower=sender,
            following = receiver,
        ).exists():

            return Response(
                {
                    "detail": (
                        "You are alreeady following "
                        "this user."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        #PUBLIC ACCOUNT
        if not receiver.is_private:

            follow = Follow.objects.create(
                follower = sender,
                following = receiver,
            )

            # ----------------------------------------------
            # Create follow notification
            # ----------------------------------------------
            create_notification(
                recipient=receiver,
                actor=sender,
                notification_type=(
                    Notification.NotificationType.FOLLOW
                ),
            )

            return Response(
                {
                    "detail": (
                        "You are now following "
                        "this user."
                    ),
                    "status": "following",
                    "follow_id": follow.id,
                },
                status=status.HTTP_201_CREATED,
            )

        #PRIVATE ACCOUNT

        follow_request = (
            FollowRequest.objects.filter(
                sender = sender,
                receiver = receiver,
            )
            .first()
        )

        if follow_request:

            if (
                follow_request.status
                == FollowRequest.STATUS_PENDING
            ):
                return Response (
                    {
                        "detail": (
                            "Follow request already "
                            "exists."
                        ),
                        "status": "pending",
                        "request_id": (
                            follow_request.id
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            follow_request.status = FollowRequest.STATUS_PENDING

            follow_request.save(
                update_fields = [
                    "status",
                    "updated_at",
                ]
            )

            create_notification(
                recipient=receiver,
                actor=sender,
                notification_type=(
                    Notification.NotificationType.FOLLOW_REQUEST
                ),
                follow_request=follow_request,
            )

            serializer = self.get_serializer(follow_request)
            return Response(
                {
                    "detail": "Follow request sent.",
                    "status": "pending",
                    "request_id": follow_request.id,
                    "request": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        else:

            follow_request = (
                FollowRequest.objects.create(
                    sender = sender,
                    receiver = receiver,
                    status= (
                        FollowRequest.STATUS_PENDING
                    ),
                )
            )

            # ----------------------------------------------
            # Create follow request notification
            # 
            
            create_notification(
                recipient=receiver,
                actor=sender,
                notification_type=(
                    Notification.NotificationType.FOLLOW_REQUEST
                ),
                follow_request=follow_request,
            )

            serializer = self.get_serializer(
                follow_request
            )

            return Response(
                {
                    "detail": (
                        "Follow request sent."
                    ),
                    "status": "pending",
                    "request_id": follow_request.id,
                    "request": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

class FollowRequestListView(
    generics.ListAPIView
):
    """
    List pending follow requests received
    by the authenticated user.
    """

    serializer_class = FollowRequestSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            FollowRequest.objects
            .filter(
                receiver=self.request.user,
                status=FollowRequest.STATUS_PENDING,
            )
            .select_related(
                "sender",
                "receiver",
            )
            .order_by(
                "-created_at"
            )
        )


class AcceptFollowRequestView(
    generics.GenericAPIView
):
    """
    Accept a pending follow request.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        follow_request = get_object_or_404(
            FollowRequest,
            id=self.kwargs["request_id"],
            receiver=request.user,
        )

        if (
            follow_request.status
            != FollowRequest.STATUS_PENDING
        ):
            return Response(
                {
                    "detail": (
                        "This request is no longer "
                        "pending."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        Follow.objects.get_or_create(
            follower=follow_request.sender,
            following=follow_request.receiver,
        )

        follow_request.status = (
            FollowRequest.STATUS_ACCEPTED
        )

        follow_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        create_notification(
            recipient=follow_request.sender,
            actor=request.user,
            notification_type=(
                Notification.NotificationType.FOLLOW_ACCEPTED
            ),
            follow_request=follow_request,
        )

        return Response(
            {
                "detail": (
                    "Follow request accepted."
                ),
                "status": "following",
            },
            status=status.HTTP_200_OK,
        )


class RejectFollowRequestView(
    generics.GenericAPIView
):
    """
    Reject a pending follow request.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, *args, **kwargs):

        follow_request = get_object_or_404(
            FollowRequest,
            id=self.kwargs["request_id"],
            receiver=request.user,
        )

        if (
            follow_request.status
            != FollowRequest.STATUS_PENDING
        ):
            return Response(
                {
                    "detail": (
                        "This request is no longer "
                        "pending."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow_request.status = (
            FollowRequest.STATUS_REJECTED
        )

        follow_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return Response(
            {
                "detail": (
                    "Follow request rejected."
                ),
                "status": "rejected",
            },
            status=status.HTTP_200_OK,
        )

class CancelFollowRequestView(
    generics.GenericAPIView
):
    """
    Cancel a follow request sent by the authenticated user.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def delete(self, request, *args, **kwargs):
        follow_request = get_object_or_404(
            FollowRequest,
            id=self.kwargs["request_id"],
            sender=request.user,
            status=FollowRequest.STATUS_PENDING,
        )

        follow_request.delete()

        return Response(
            {
                "detail": "Follow request cancelled.",
                "status": "none",
            },
            status=status.HTTP_200_OK,
        )


class UserRelationshipView(
    generics.GenericAPIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):

        current_user = request.user

        target_user = get_object_or_404(
            User,
            id=self.kwargs["user_id"],
        )

        if current_user == target_user:
            return Response(
                {
                    "status": "self",
                }
            )

        if Follow.objects.filter(
            follower=current_user,
            following=target_user,
        ).exists():

            return Response(
                {
                    "status": "following",
                }
            )

        pending_request = (
            FollowRequest.objects.filter(
                sender=current_user,
                receiver=target_user,
                status=(
                    FollowRequest.STATUS_PENDING
                ),
            )
            .first()
        )

        if pending_request:

            return Response(
                {
                    "status": "pending",
                    "request_id": (
                        pending_request.id
                    ),
                }
            )

        return Response(
            {
                "status": "none",
            }
        )