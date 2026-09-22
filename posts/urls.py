from django.urls import path

from .views import (
    FeedView,
    PostCreateView,
    PostListView,
    PostDetailView,
    UserPostsListView,
    LikePostView,
    PostLikesListView,
    PostCommentListCreateView,
    CommentDetailView,
    CommentReplyListCreateView,
    ReplyDetailView,
)


urlpatterns = [

    # ==================================================
    # POSTS
    # ==================================================

    path(
        "",
        PostListView.as_view(),
        name="post-list",
    ),


    # ==================================================
    # USER FEED
    # ==================================================

    path(
        "feed/",
        FeedView.as_view(),
        name="feed",
    ),

    path(
        "create/",
        PostCreateView.as_view(),
        name="post-create",
    ),

    path(
        "<int:id>/",
        PostDetailView.as_view(),
        name="post-detail",
    ),

    # ==================================================
    # USER POSTS
    # ==================================================

    path(
        "user/<str:username>/",
        UserPostsListView.as_view(),
        name="user-posts",
    ),

    path(
        "<int:post_id>/like/",
        LikePostView.as_view(),
        name="post-like",
    ),

    path(
        "<int:post_id>/likes/",
        PostLikesListView.as_view(),
        name="post-likes",
    ),

    # ==================================================
    # USER COMMENTS
    # ==================================================

    path(
        "<int:post_id>/comments/",
        PostCommentListCreateView.as_view(),
        name="post-comments",
    ),

    path(
        "comments/<int:pk>/",
        CommentDetailView.as_view(),
        name="comment-detail",
    ),

    path(
        "comments/<int:comment_id>/replies/",
        CommentReplyListCreateView.as_view(),
        name="comment-replies",
    ),

    path(
        "replies/<int:pk>/",
        ReplyDetailView.as_view(),
        name="reply-detail",
    ),


]