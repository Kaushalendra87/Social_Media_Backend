from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_from_token(token):
    if not token or not isinstance(token, str):
        return AnonymousUser()

    # Clean and sanitize token string
    token = token.strip().strip('"').strip("'")
    if token.startswith("Bearer "):
        token = token[7:].strip()
    elif token.startswith("Bearer%20"):
        token = token[9:].strip()

    if not token:
        return AnonymousUser()

    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)

        if not user or not user.is_active:
            print("JWT AUTH FAILURE: User inactive or not found")
            return AnonymousUser()

        print(f"JWT AUTH SUCCESS: user={user.username} (id={user.id})")
        return user

    except (InvalidToken, TokenError) as error:
        print(f"JWT AUTH INVALID TOKEN: {error}")
        return AnonymousUser()
    except Exception as error:
        print(f"JWT AUTH EXCEPTION: {type(error).__name__} - {error}")
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Custom JWT authentication middleware for WebSocket connections.
    Extracts token from query params: ?token=<JWT>
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get("token")

        print("========================================")
        print("WEBSOCKET HANDSHAKE REQUEST")
        print("QUERY STRING:", query_string)
        print("TOKEN PRESENT:", bool(token_list))

        if token_list and token_list[0]:
            raw_token = token_list[0]
            user = await get_user_from_token(raw_token)
        else:
            print("NO TOKEN PROVIDED IN QUERY STRING")
            user = AnonymousUser()

        scope["user"] = user

        print("WEBSOCKET USER BINDING:", user)
        print("USER ID:", getattr(user, "id", None))
        print("========================================")

        return await self.inner(scope, receive, send)