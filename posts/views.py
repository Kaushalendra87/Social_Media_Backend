from django.db.models import Q, Count, Exists, OuterRef

from notifications.models import Notification
from notifications.services import create_notification

from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from rest_framework.response import Response
from .models import (
    Post,
    Like,
    Comment,
    Reply,
)


def get_optimized_post_queryset(user, base_queryset=None):
    if base_queryset is None:
        base_queryset = Post.objects.all()

    qs = base_queryset.select_related("author").annotate(
        like_count=Count("likes", distinct=True),
        comment_count=Count("comments", distinct=True),
    )

    if user and user.is_authenticated:
        qs = qs.annotate(
            is_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user))
        )

    return qs

from .serializers import (
    PostSerializer,
    PostCreateUpdateSerializer,
    LikeSerializer,
    CommentSerializer,
    ReplySerializer,
)


from django.shortcuts import render

# Create your views here.

class PostCreateView(
    generics.CreateAPIView
):
    """
    Create a new post.
    """

    serializer_class = (
        PostCreateUpdateSerializer
    )

    permission_classes = [
        IsAuthenticated,
    ]

    def create(
            self,
            request,
            *args,
            **kwargs,
    ):

        serializer = self.get_serializer(
            data = request.data
        )

        serializer.is_valid(
            raise_exception = True
        )

        post = serializer.save(
            author = request.user
        )

        response_serializer = PostSerializer(
            post,
            context = {
                "request" : request
            }
        )

        return Response(
            {
                "message": (
                    "Post created successfully."
                ),
                "post": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class PostListView(
    generics.ListAPIView
):
    """
    Return all discoverable posts.
    Posts from private accounts are only visible if the requesting user is the post author or follows the private author.
    """

    serializer_class = PostSerializer

    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        from users.models import Follow

        user = self.request.user

        if user.is_authenticated:
            following_user_ids = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
            base_qs = Post.objects.filter(
                Q(author__is_private=False) |
                Q(author=user) |
                Q(author_id__in=following_user_ids)
            )
        else:
            base_qs = Post.objects.filter(author__is_private=False)

        return get_optimized_post_queryset(user, base_qs).order_by("-created_at")


class PostDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete a post.
    """

    queryset = (
        Post.objects
        .select_related("author")
        .all()
    )

    permission_classes = [
        IsAuthenticated,
    ]

    lookup_field = "id"

    def get_serializer_class(
            self
    ):
        if self.request.method in [
            "PATCH",
            "PUT",
        ]:

            return PostCreateUpdateSerializer

        return PostSerializer

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        author = post.author
        from users.models import Follow

        if author.is_private:
            is_owner = request.user.is_authenticated and request.user == author
            is_follower = request.user.is_authenticated and Follow.objects.filter(follower=request.user, following=author).exists()

            if not (is_owner or is_follower):
                return Response(
                    {"detail": "This post belongs to a private account. Follow this user to view their post."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(post)
        return Response(serializer.data)

    def update(
            self,
            request,
            *args,
            **kwargs
    ):

        post = self.get_object()

        if post.author != request.user:

            return Response(
                {
                    "detail": (
                        "You can only update "
                        "your own posts."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        partial = kwargs.pop(
            "partial",
            False,
        )

        serializer = (
            self.get_serializer(
                post,
                data = request.data,
                partial = partial,
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        post = serializer.save()

        response_serializer = PostSerializer(
            post,
            context = {
                "request": request
            }
        )

        return Response(
            {
                "message": (
                    "Post updated successfully."
                ),
                "post": (
                    response_serializer.data
                ),
            },
            status=status.HTTP_200_OK,
        )

    def destroy(
            self,
            request,
            *args, 
            **kwargs
    ):

        post = self.get_object()

        if post.author != request.user:

            return Response(
                {
                    "detail": (
                        "You can only delete "
                        "your own posts."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        post.delete()

        return Response(
            {
                "message": (
                    "Post deleted successfully."
                )
            },
            status=status.HTTP_200_OK,
        )

        
class UserPostsListView(
    generics.ListAPIView
):

    """
    Return posts created by a specific user.
    If the target user account is private, posts are only accessible to approved followers or the account owner.
    """

    serializer_class = PostSerializer

    permission_classes = [
        AllowAny,
    ]

    def list(self, request, *args, **kwargs):
        username = self.kwargs["username"]
        from users.models import User, Follow
        from rest_framework.exceptions import PermissionDenied

        target_user = get_object_or_404(User, username=username, is_active=True)

        if target_user.is_private:
            is_owner = request.user.is_authenticated and request.user == target_user
            is_follower = request.user.is_authenticated and Follow.objects.filter(follower=request.user, following=target_user).exists()

            if not (is_owner or is_follower):
                return Response(
                    {"detail": "This account is private. Follow this user to see their posts."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return super().list(request, *args, **kwargs)

    def get_queryset(
            self
    ):

        username = self.kwargs[
            "username"
        ]

        return (
            Post.objects
            .select_related("author")
            .filter(
                author__username = username,
                author__is_active = True,
            )
        )

def check_post_access(user, post):
    """
    Verify if `user` has permission to view/interact with `post`.
    If the author's account is private, user must be the author or an approved follower.
    """
    author = post.author
    if author.is_private:
        from users.models import Follow
        is_owner = user.is_authenticated and user == author
        is_follower = user.is_authenticated and Follow.objects.filter(follower=user, following=author).exists()
        if not (is_owner or is_follower):
            raise PermissionDenied("This post belongs to a private account. Follow this user to interact with their post.")


class LikePostView(APIView):
    """
    Like or unlike a post.

    POST   /api/posts/<post_id>/like/  -> Like
    DELETE /api/posts/<post_id>/like/  -> Unlike
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        post_id,
    ):

        post = get_object_or_404(
            Post,
            id=post_id,
        )

        check_post_access(request.user, post)

        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post,
        )

        like_count = Like.objects.filter(
            post=post
        ).count()

        if not created:

            return Response(
                {
                    "message": (
                        "You have already "
                        "liked this post."
                    ),
                    "liked": True,
                    "post_id": post.id,
                    "like_count": like_count,
                },
                status=status.HTTP_200_OK,
            )

        # ------------------------------------------------
        # CREATE LIKE NOTIFICATION
        # ------------------------------------------------
        create_notification(
            recipient=post.author,
            actor=request.user,
            notification_type=(
                Notification.NotificationType.LIKE
            ),
            post=post,
        )

        return Response(
            {
                "message": (
                    "Post liked successfully."
                ),
                "liked": True,
                "post_id": post.id,
                "like_count": like_count,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(
        self,
        request,
        post_id,
    ):

        post = get_object_or_404(
            Post,
            id=post_id,
        )

        check_post_access(request.user, post)

        deleted_count, _ = Like.objects.filter(
            user=request.user,
            post=post,
        ).delete()

        like_count = Like.objects.filter(
            post=post
        ).count()

        if deleted_count == 0:

            return Response(
                {
                    "message": (
                        "You have not "
                        "liked this post."
                    ),
                    "liked": False,
                    "post_id": post.id,
                    "like_count": like_count,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": (
                    "Post unliked successfully."
                ),
                "liked": False,
                "post_id": post.id,
                "like_count": like_count,
            },
            status=status.HTTP_200_OK,
        )


class PostLikesListView(APIView):
    """
    List users who liked a post.

    GET /api/posts/<post_id>/likes/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        post_id,
    ):

        post = get_object_or_404(
            Post,
            id=post_id,
        )

        check_post_access(request.user, post)

        likes = (
            Like.objects
            .filter(
                post=post
            )
            .select_related(
                "user"
            )
        )

        serializer = LikeSerializer(
            likes,
            many=True,
        )

        return Response(
            {
                "count": likes.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PostCommentListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List comments for a post.

    POST:
        Create a comment on a post.
    """

    serializer_class = CommentSerializer

    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly
    ]

    def get_queryset(self):
        post_id = self.kwargs["post_id"]
        post = get_object_or_404(Post, id=post_id)
        check_post_access(self.request.user, post)

        return (
            Comment.objects
            .filter(post_id=post_id)
            .select_related("author", "post")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        post_id = self.kwargs["post_id"]

        post = generics.get_object_or_404(
            Post,
            id=post_id,
        )
        check_post_access(self.request.user, post)

        comment = serializer.save(
            author=self.request.user,
            post=post,
        )

        # ------------------------------------------------
        # CREATE COMMENT NOTIFICATION
        # ------------------------------------------------
        create_notification(
            recipient=post.author,
            actor=self.request.user,
            notification_type=(
                Notification.NotificationType.COMMENT
            ),
            post=post,
            comment=comment,
        )


class CommentDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete a comment.
    """

    queryset = (
        Comment.objects
        .select_related("author", "post", "post__author")
    )

    serializer_class = CommentSerializer

    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly
    ]

    def get_object(self):
        comment = super().get_object()
        check_post_access(self.request.user, comment.post)
        return comment

    def perform_update(self, serializer):
        comment = self.get_object()

        if comment.author != self.request.user:
            raise PermissionDenied(
                "You can only edit your own comments."
            )

        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied(
                "You can only delete your own comments."
            )

        instance.delete()


class CommentReplyListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List replies for a comment.

    POST:
        Create a reply to a comment.
    """

    serializer_class = ReplySerializer

    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly
    ]

    def get_queryset(self):
        comment_id = self.kwargs["comment_id"]
        comment = get_object_or_404(Comment.objects.select_related("post", "post__author"), id=comment_id)
        check_post_access(self.request.user, comment.post)

        return (
            Reply.objects
            .filter(comment_id=comment_id)
            .select_related(
                "author",
                "comment",
                "comment__post",
            )
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        comment_id = self.kwargs["comment_id"]

        comment = get_object_or_404(
            Comment.objects.select_related("post", "post__author"),
            id=comment_id,
        )
        check_post_access(self.request.user, comment.post)

        reply = serializer.save(
            author=self.request.user,
            comment=comment,
        )

        # ------------------------------------------------
        # CREATE REPLY NOTIFICATION
        # ------------------------------------------------
        create_notification(
            recipient=comment.author,
            actor=self.request.user,
            notification_type=(
                Notification.NotificationType.REPLY
            ),
            post=comment.post,
            comment=comment,
            reply=reply,
        )

class ReplyDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete a reply.
    """

    queryset = (
        Reply.objects
        .select_related(
            "author",
            "comment",
            "comment__post",
            "comment__post__author",
        )
    )

    serializer_class = ReplySerializer

    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly
    ]

    def get_object(self):
        reply = super().get_object()
        check_post_access(self.request.user, reply.comment.post)
        return reply

    def perform_update(self, serializer):
        reply = self.get_object()

        if reply.author != self.request.user:
            raise PermissionDenied(
                "You can only edit your own replies."
            )

        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied(
                "You can only delete your own replies."
            )

        instance.delete()


class FeedView(generics.ListAPIView):
    """
    Returns posts created by the authenticated user and 
    users that the authenticated user follows.
    """

    serializer_class = PostSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        user = self.request.user

        following_user_ids = user.following_relationships.values_list(
            "following_id",
            flat = True,
        )

        return (
            Post.objects
            .filter(
                Q(author=user) |
                Q(author_id__in = following_user_ids)
            )
            .select_related("author")
            .order_by("-created_at")
        )

    