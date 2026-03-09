"""ASGI config for Ase project — Django Channels WebSocket support."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ase_project.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing code that may trigger ORM queries.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

# Import WebSocket URL patterns from each app that registers consumers.
# These modules are imported lazily (after Django setup) to avoid AppRegistry errors.
from agents.routing import websocket_urlpatterns as agents_ws  # noqa: E402

application = ProtocolTypeRouter(
    {
        # HTTP requests are handled by the standard Django ASGI app.
        "http": django_asgi_app,
        # WebSocket handshake is validated against ALLOWED_HOSTS, then
        # authenticated via Django session middleware.
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    agents_ws,
                )
            )
        ),
    }
)
