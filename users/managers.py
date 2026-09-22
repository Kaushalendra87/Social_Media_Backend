from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    """
    Custom manager for the User model.

    Handles creation of normal users and superusers.
    """

    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a normal user.
        """

        if not email:
            raise ValueError("Email address is required.")

        if not username:
            raise ValueError("Username is required.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            username = username,
            **extra_fields,
        )

        user.set_password(password)

        user.save(using = self.db)

        return user

    def create_superuser(
            self,
            email,
            username,
            password = None,
            **extra_fields,
    ):
        """
        Create and save a superuser.
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff = True"
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True"
            )

        return self.create_user(
            email = email,
            username = username,
            password=password,
            **extra_fields,
        )