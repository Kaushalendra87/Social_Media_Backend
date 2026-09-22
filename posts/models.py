from django.conf import settings
from django.db import models
from cloudinary.models import CloudinaryField

# Create your models here.

class Post(models.Model):
    """
    Represents a social media post.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    caption = models.TextField(
        max_length=5000,
        blank = True,
    )

    image = CloudinaryField(
        "image",
        folder="social_media/posts",
        blank = True,
        null = True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]


        indexes = [
            models.Index(
                fields=[
                    "author",
                    "-created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"Post {self.id} "
            f"by {self.author.username}"
        )


    def save(
        self,
        *args,
        **kwargs
    ):

        if self.pk:

            old_post = (
                Post.objects
                .filter(pk=self.pk)
                .first()
            )

            if old_post:

                old_image = (
                    old_post.image
                )

                new_image = (
                    self.image
                )

                if (
                    old_image
                    and old_image != new_image
                ):

                    old_image.delete(
                        save=False
                    )

        super().save(
            *args,
            **kwargs
        )
    

    def delete(
        self,
        *args,
        **kwargs
    ):

        if self.image:

            self.image.delete(
                save=False
            )

        super().delete(
            *args,
            **kwargs
        )


class Like(models.Model):
    """
    Represents a user's like a post.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_likes",
    )

    post = models.ForeignKey(
        Post,
        on_delete = models.CASCADE,
        related_name="likes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "post",
                ],
                name = "unique_user_post_like",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "post",
                    "-created_at",
                ],
                name="like_post_created_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "-created_at",
                ],
                name="like_user_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.username} "
            f"liked Post { self.post.id}"
        )


class Comment(models.Model):
    """
    Represents a comment made by a user on a post.
    """

    post = models.ForeignKey(
        "Post",
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    content = models.TextField(
        max_length=1000,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["post", "-created_at"]
            ),
            models.Index(
                fields=["author", "-created_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.author} commented "
            f"on Post {self.post_id}"
        )

class Reply(models.Model):
    """
    Represents a reply made by auser to a comment.
    """

    comment = models.ForeignKey(
        "Comment",
        on_delete=models.CASCADE,
        related_name="replies",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    content = models.TextField(
        max_length=1000,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["comment", "created_at"]
            ),
            models.Index(
                fields=["author", "-created_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.author} replied "
            f"to Comment {self.comment_id}"
        )
    
    