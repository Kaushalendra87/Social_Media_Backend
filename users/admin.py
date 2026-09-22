from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Django admin configuration for the custom User model.
    """

    # --------------------------------------------------
    # LIST DISPLAY
    # --------------------------------------------------

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
    )

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
    )

    # --------------------------------------------------
    # DEFAULT ORDERING
    # --------------------------------------------------

    ordering = (
        "-date_joined",
    )

    # --------------------------------------------------
    # READONLY FIELDS
    # --------------------------------------------------

    readonly_fields = (
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
    )

    # --------------------------------------------------
    # EDIT USER
    # --------------------------------------------------

    fieldsets = (
        (
            "Authentication",
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),

        (
            "Personal Information",
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "profile_picture",
                    "bio",
                )
            },
        ),

        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),

        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # --------------------------------------------------
    # ADD USER
    # --------------------------------------------------

    add_fieldsets = (
        (
            "Create User",
            {
                "classes": (
                    "wide",
                ),

                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
    )