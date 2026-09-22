from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AcceptFollowRequestView,
    CancelFollowRequestView,
    CurrentUserView,
    EmailTokenObtainPairView,
    FollowRequestListView,
    FollowStatusView,
    FollowUserView,
    FollowersListView,
    FollowingListView,
    LogoutView,
    ProfileUpdateView,
    PublicProfileView,
    RegisterView,
    RejectFollowRequestView,
    RemoveProfilePictureView,
    SendFollowRequestView,
    UserRelationshipView,
    UserSearchView,
)


urlpatterns = [
    # Authentication
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Current user and profile settings
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/update/", ProfileUpdateView.as_view(), name="profile-update"),
    path("me/profile-picture/", RemoveProfilePictureView.as_view(), name="remove-profile-picture"),

    # Discovery and relationship state
    path("search/", UserSearchView.as_view(), name="user-search"),
    path("follow-requests/", FollowRequestListView.as_view(), name="follow-request-list"),
    path("follow-requests/<int:request_id>/accept/", AcceptFollowRequestView.as_view(), name="accept-follow-request"),
    path("follow-requests/<int:request_id>/reject/", RejectFollowRequestView.as_view(), name="reject-follow-request"),
    path("follow-requests/<int:request_id>/cancel/", CancelFollowRequestView.as_view(), name="cancel-follow-request"),
    path("<int:user_id>/follow-request/", SendFollowRequestView.as_view(), name="send-follow-request"),
    path("<int:user_id>/relationship/", UserRelationshipView.as_view(), name="user-relationship"),

    # Username-based follow and profile routes
    path("<str:username>/follow/", FollowUserView.as_view(), name="follow-user"),
    path("<str:username>/followers/", FollowersListView.as_view(), name="followers"),
    path("<str:username>/following/", FollowingListView.as_view(), name="following"),
    path("<str:username>/follow-status/", FollowStatusView.as_view(), name="follow-status"),
    path("<str:username>/", PublicProfileView.as_view(), name="public-profile"),
]