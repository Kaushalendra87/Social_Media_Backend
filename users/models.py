from django.contrib.auth.models import (
    AbstractBaseUser, 
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

from .managers import UserManager

from cloudinary.models import CloudinaryField

# Create your models here.

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for the social media platform.

    Authentication:
        email + password

    Public identity:
        username
    """


    username = models.CharField(
        max_length=30,
        unique = True,
        db_index = True,
    )

    email = models.EmailField(
        unique =True,
        db_index=True,
    )

    first_name = models.CharField(
        max_length=100,
        blank = True,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    profile_picture = CloudinaryField(
        "profile_picture",
        folder="social_media/profile_pictures",
        blank=True,
        null=True,
    )

    bio = models.TextField(
        max_length=500,
        blank = True,
    )

    is_online =models.BooleanField(
        default=False,
    )

    last_seen = models.DateTimeField(
        null =True,
        blank = True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_private = models.BooleanField(
        default=False,
        help_text="Whether this account requires follow requests."
    )

    is_staff = models.BooleanField(
        default= False,
    )

    date_joined = models.DateTimeField(
        default = timezone.now,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "username",
    ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return (
            f"{self.first_name} { self.last_name}"
            ).strip()

class Follow(models.Model):
    """
    Represents a relationship where one user follows another user.
    """

    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )

    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "follower",
                    "following",
                ],
                name="unique_user_follow",
            ),

            models.CheckConstraint(
                condition=~models.Q(
                    follower=models.F("following")
                ),
                name="prevent_self_follow",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "follower",
                    "created_at",
                ]
            ),

            models.Index(
                fields=[
                    "following",
                    "created_at",
                ]
            ),
        ]

        ordering = [
            "-created_at",
        ]


class FollowRequest(models.Model):
    """
    Represents a request from one user to follow another user.
    """

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    sender = models.ForeignKey(
        User,
        on_delete = models.CASCADE,
        related_name="sent_follow_requests",
    )

    receiver = models.ForeignKey(
        User,
        on_delete = models.CASCADE,
        related_name = "recieved_follow_requests",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    created_at = models.DateTimeField(
        auto_now_add = True,
    )

    updated_at = models.DateTimeField(
        auto_now = True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
            fields=[
                "receiver",
                "status",
            ]
        ),
        models.Index(
            fields=[
                "sender",
                "status",
            ]
        ),
    ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sender",
                    "receiver",
                ],
                name="unique_follow_request",
            ),

            models.CheckConstraint(
                condition=~models.Q(
                    sender=models.F("receiver")
                ),
                name="prevent_self_follow_request",
            ),
        ]

        def __str__(self):
            return (
                f"{self.sender.username } ->"
                f"{self.receiver.username} "
                f"({self.status})"

            )
        
    