from app.routes.public import router as public_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.client import router as client_router

__all__ = ["public_router", "auth_router", "admin_router", "client_router"]
