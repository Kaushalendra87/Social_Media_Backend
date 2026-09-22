from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from .models import (
    User, 
    Follow,
    FollowRequest,                     
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying user information.
    """

    full_name = serializers.ReadOnlyField()
    profile_picture = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "profile_picture",
            "bio",
            "is_private",
            "followers_count",
            "following_count",
            "date_joined",
        ]

        read_only_fields = [
            "id",
            "email",
            "date_joined",
            "full_name",
            "is_private",
            "followers_count",
            "following_count",
        ]

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            try:
                return obj.profile_picture.url
            except Exception:
                return str(obj.profile_picture)
        return None

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj).count()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer used to register a new user.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "Password must be at least 8 characters long."},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Username cannot be empty.")
        return value

    def validate_email(self, value):
        return value.lower().strip()

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        """
        Create user using the custom UserManager.
        """

        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password = password,
            **validated_data,
        )

        return user


class EmailTokenObtainPairSerializer(
    TokenObtainPairSerializer
):
    """
    JWT serializer that authenticates using email.
    """

    username_field = "email"

    def validate(self, attrs):

        email = attrs.get("email")

        if email:
            attrs["email"] = email.lower().strip()

        data = super().validate(attrs)

        data["user"] = UserSerializer(
            self.user
        ).data

        return data


class LogoutSerializer(serializers.Serializer):
    """
    Serializer used to blacklist a refresh token.
    """

    refresh = serializers.CharField(
        write_only = True
    )

    def validate(self, attrs):
        self.token = attrs["refresh"]

        try:
            RefreshToken(
                self.token
            )
        except Exception:
            raise serializers.ValidationError(
                {
                    "refresh": (
                        "Invalid or expired refresh token."
                    )
                }
            )

        return attrs

    def save(self, **kwargs):

        try:
            token = RefreshToken(
                self.token
            )

            token.blacklist()

        except Exception:
            raise serializers.ValidationError(
                {
                    "refresh": (
                        "Unable to blacklist token."
                    )
                }
            )

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used to update the authenticated user's profile.
    """

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "bio",
            "profile_picture",
            "is_private",
        ]

    def validate_username(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Username cannot be empty."
            )

        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must contain at least 3 characters."
            )

        queryset = User.objects.filter(
            username__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "This username is already taken."
            )

        return value

    def validate_bio(self, value):
         if len(value) > 500:
             raise serializers.ValidationError(
                 "Bio cannot exceed 500 characters."
             )

         return value

    def validate_profile_picture(self, image):

        if image is None:
            return image

        max_size = 5 * 1024 * 1024

        if image.size > max_size:
            raise serializers.ValidationError(
                "Profile picture cannot exceed 5 MB."
            )

        allowed_extensions = [
            "jpg",
            "jpeg",
            "png",
            "webp",
        ]

        extension = image.name.split(".")[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG, and WEBP images are allowed."
            )

        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]

        if image.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Invalid image type."
            )

        return image

class PublicUserSerializer(serializers.ModelSerializer):
    """
    Serializer used to display a user's public profile.
    """

    full_name = serializers.ReadOnlyField()
    profile_picture = serializers.SerializerMethodField()

    followers_count = serializers.SerializerMethodField()

    following_count = serializers.SerializerMethodField()

    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "profile_picture",
            "bio",
            "is_private",
            "date_joined",
            "followers_count",
            "following_count",
            "is_following",
        ]

        read_only_fields = fields

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            try:
                return obj.profile_picture.url
            except Exception:
                return str(obj.profile_picture)
        return None

    def get_followers_count(
            self,
            obj
    ):

        return Follow.objects.filter(
            following=obj
        ).count()

    def get_following_count(
            self,
            obj
    ):

        return Follow.objects.filter(
            follower=obj
        ).count()

    def get_is_following(
        self,
        obj
    ):
        request = self.context.get(
            "request"
        )

        if not request:
            return False
        
        if not request.user.is_authenticated:
            return False

        if request.user == obj:
            return False

        return Follow.objects.filter(
            follower=request.user,
            following = obj,
        ).exists()
    

class FollowSerializer(serializers.ModelSerializer):
    """
    Serializer used to display a follow relationship.
    """

    follower = PublicUserSerializer(
        read_only = True
    )

    following = PublicUserSerializer(
        read_only = True
    )

    class Meta:
        model = Follow

        fields = [
            "id",
            "follower",
            "following",
            "created_at",
        ]

        read_only_fields = fields


class FollowUserSerializer(
    serializers.ModelSerializer
):
    """
    Lightweight serializer used for followers and following lists.
    Includes relationship_status so the frontend can render Follow/Unfollow
    buttons without making a separate API call per user.
    """

    full_name = serializers.ReadOnlyField()
    profile_picture = serializers.SerializerMethodField()
    relationship_status = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "profile_picture",
            "relationship_status",
        ]

        read_only_fields = fields

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            try:
                return obj.profile_picture.url
            except Exception:
                return str(obj.profile_picture)
        return None

    def get_relationship_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return "none"
        if request.user.id == obj.id:
            return "self"
        # Use pre-loaded sets when available (populated by FollowersListView /
        # FollowingListView to avoid N+1 queries).
        following_ids = self.context.get("viewer_following_ids")
        pending_ids = self.context.get("viewer_pending_request_ids")
        if following_ids is not None:
            if obj.id in following_ids:
                return "following"
            if pending_ids is not None and obj.id in pending_ids:
                return "pending"
            return "none"
        # Fallback: single-object detail page (no pre-loading)
        if Follow.objects.filter(follower=request.user, following=obj).exists():
            return "following"
        from .models import FollowRequest
        if FollowRequest.objects.filter(sender=request.user, receiver=obj, status="pending").exists():
            return "pending"
        return "none"




class FollowStatusSerializer(
    serializers.Serializer
):
    is_following = serializers.BooleanField()

    followers_count = serializers.IntegerField()

    following_count = serializers.IntegerField()


class UserDiscoverySerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(
        read_only=True
    )

    following_count = serializers.IntegerField(
        read_only = True
    )

    profile_picture = serializers.SerializerMethodField()
    relationship_status = serializers.SerializerMethodField()
    request_id = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture",
            "bio",
            "is_private",
            "followers_count",
            "following_count",
            "relationship_status",
            "request_id",
        ]

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            try:
                return obj.profile_picture.url
            except Exception:
                return str(obj.profile_picture)
        return None

    def get_relationship_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return "none"
        if request.user == obj:
            return "self"
        # Use pre-loaded sets when available (UserSearchView annotates these).
        following_ids = self.context.get("viewer_following_ids")
        pending_ids = self.context.get("viewer_pending_request_ids")
        if following_ids is not None:
            if obj.id in following_ids:
                return "following"
            if pending_ids is not None and obj.id in pending_ids:
                return "pending"
            return "none"
        # Fallback to per-row queries when context sets are absent.
        if Follow.objects.filter(follower=request.user, following=obj).exists():
            return "following"
        pending_req = FollowRequest.objects.filter(
            sender=request.user,
            receiver=obj,
            status=FollowRequest.STATUS_PENDING
        ).first()
        if pending_req:
            return "pending"
        return "none"

    def get_request_id(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        # Use pre-loaded pending IDs set when available.
        pending_ids = self.context.get("viewer_pending_request_ids")
        if pending_ids is not None:
            # If the id is in the pre-loaded set, we still need the actual request id.
            # Fall through to the DB query only in that case to retrieve the id.
            if obj.id not in pending_ids:
                return None
        pending_req = FollowRequest.objects.filter(
            sender=request.user,
            receiver=obj,
            status=FollowRequest.STATUS_PENDING
        ).first()
        return pending_req.id if pending_req else None

class FollowRequestSerializer(serializers.ModelSerializer):
    sender = UserDiscoverySerializer(
        read_only = True
    )

    receiver = UserDiscoverySerializer(
        read_only = True
    )

    class Meta:
        model = FollowRequest

        fields = [
            "id",
            "sender",
            "receiver",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "sender",
            "receiver",
            "status",
            "created_at",
            "updated_at",
        ]


class UserProfileSerializer(
    serializers.ModelSerializer
):
    followers_count = serializers.IntegerField(
        read_only=True
    )

    following_count = serializers.IntegerField(
        read_only=True
    )

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture",
            "bio",
            "is_private",
            "followers_count",
            "following_count",
        ]