from rest_framework import serializers

from .models import (
    Post,
    Like,
    Comment,
    Reply,
)

class PostAuthorSerializer(
    serializers.Serializer
):
    """
    Lightweight representation of the post.
    """

    id = serializers.IntegerField(
        read_only = True
    )

    username = serializers.CharField(
        read_only = True 
    )

    first_name = serializers.CharField(
        read_only = True
    )

    last_name = serializers.CharField(
        read_only = True
    )

    full_name = serializers.CharField(
        read_only = True
    )

    profile_picture = serializers.CharField(
        read_only = True,
        allow_null = True,
    )


class PostSerializer(
    serializers.ModelSerializer
):
    """
    Serializer used for displaying posts.
    """

    author = serializers.SerializerMethodField()

    like_count = serializers.SerializerMethodField()

    is_liked = serializers.SerializerMethodField()

    comment_count = serializers.SerializerMethodField()

    class Meta:

        model = Post

        fields = [
            "id",
            "author",
            "caption",
            "image",
            "created_at",
            "updated_at",
            "like_count",
            "comment_count",
            "is_liked",
        ]

        read_only_fields = [
            "id",
            "author",
            "created_at",
            "updated_at",
            "like_count",
            "comment_count",
            "is_liked",
        ]


    def get_author(
            self,
            obj,
    ):
        user = obj.author
        profile_picture = None

        if getattr(user, "profile_picture", None):
            try:
                profile_picture = user.profile_picture.url
            except Exception:
                profile_picture = str(user.profile_picture) if user.profile_picture else None

        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": (
                f"{user.first_name} "
                f"{user.last_name}"
            ).strip(),
            "profile_picture": profile_picture,
        }

    def get_like_count(
            self,
            obj,
    ):
        if hasattr(obj, "like_count"):
            return obj.like_count
        return obj.likes.count()

    def get_is_liked(
            self,
            obj,
    ):
        if hasattr(obj, "is_liked"):
            return bool(obj.is_liked)

        request = self.context.get(
            "request"
        )

        if not request:
            return False

        if not request.user.is_authenticated:
            return False

        return obj.likes.filter(
            user = request.user
        ).exists()

    def get_comment_count(self, obj):
        if hasattr(obj, "comment_count"):
            return obj.comment_count
        return obj.comments.count()
    


class PostCreateUpdateSerializer(
    serializers.ModelSerializer
):
    """
    Serializer used when creating or updating a post.
    """

    class Meta:
        model = Post

        fields = [
            "caption",
            "image",
        ]

    def validate(
            self,
            attrs,
    ):

        caption = attrs.get(
            "caption",
            ""
        )

        image = attrs.get(
            "image"
        )

        caption = (
            caption.strip()
            if caption
            else ""
        )

        if not caption and not image:

            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        (
                            "A post must contain "
                            "a caption or an image."
                        )
                    ]
                }
            )

        if image:

            max_size = (
                10 * 1024 *1024
            )

            if image.size > max_size:

                raise serializers.ValidationError(
                    {
                        "image": (
                            "Imgae size cannot "
                            "exceed 1- MB."
                        )
                    }
                )

            attrs["caption"] = caption

            return attrs


class LikeSerializer(
    serializers.ModelSerializer
):
    """
    Serializers used when returning information about a like.
    """

    username = serializers.CharField(
        source = "user.username",
        read_only=True,
    )

    class Meta:
        model = Like

        fields = [
            "id",
            "username",
            "post",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "created_at",
        ]


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for post comments.
    """

    author = serializers.SerializerMethodField()

    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment

        fields = [
            "id",
            "post",
            "author",
            "content",
            "created_at",
            "updated_at",
            "reply_count",
        ]

        read_only_fields = [
            "id",
            "post",
            "author",
            "created_at",
            "updated_at",
            "reply_count",
        ]

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Comment cannot be empty."
            )

        return value

    def get_reply_count(self, obj):
        if hasattr(obj, "reply_count"):
            return obj.reply_count
        return obj.replies.count()

    def get_author(self, obj):
        user = obj.author
        profile_picture = None

        if getattr(user, "profile_picture", None):
            try:
                profile_picture = user.profile_picture.url
            except Exception:
                profile_picture = str(user.profile_picture) if user.profile_picture else None

        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_picture,
        }

class ReplySerializer(serializers.ModelSerializer):
    """
    Serializer for replies to comments.
    """

    author = serializers.SerializerMethodField()

    class Meta:
        model = Reply

        fields = [
            "id",
            "comment",
            "author",
            "content",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "comment",
            "author",
            "created_at",
            "updated_at",
        ]

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Reply cannot be empty."
            )

        return value

    def get_author(self, obj):
        user = obj.author
        profile_picture = None

        if getattr(user, "profile_picture", None):
            try:
                profile_picture = user.profile_picture.url
            except Exception:
                profile_picture = str(user.profile_picture) if user.profile_picture else None

        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_picture,
        }

  