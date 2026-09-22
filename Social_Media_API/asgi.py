import os
from channels.routing import (
    ProtocolTypeRouter,
    URLRouter,
)
from channels.security.websocket import (
    AllowedHostsOriginValidator,
)
from django.core.asgi import (
    get_asgi_application,
)

# 1. Set environment variable first
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "Social_Media_API.settings",
)

# 2. Initialize Django ASGI application to setup apps and models
django_asgi_app = (
    get_asgi_application()
)

# 3. Import middleware and routing AFTER Django is initialized
from chat.middleware import (
    JWTAuthMiddleware,
)
from chat.routing import (
    websocket_urlpatterns,
)

application = ProtocolTypeRouter(
    {
        # ----------------------------------
        # Normal HTTP requests
        # ----------------------------------
        "http": django_asgi_app,

        # ----------------------------------
        # WebSocket requests
        # ----------------------------------
        "websocket": (
            JWTAuthMiddleware(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        ),
    }
)