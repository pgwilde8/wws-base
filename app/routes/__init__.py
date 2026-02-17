from app.routes.public import router as public_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.admin_burn import router as admin_burn_router
from app.routes.admin_beta import router as admin_beta_router
from app.routes.beta_apply import router as beta_apply_router
from app.routes.client import router as client_router
from app.routes.legal import router as legal_router
from app.routes.ingest import router as ingest_router
from app.routes.api import router as api_router
from app.routes.ops_treasury import router as ops_treasury_router
from app.routes.webhooks import router as webhooks_router

__all__ = [
    "public_router",
    "auth_router",
    "admin_router",
    "admin_burn_router",
    "admin_beta_router",
    "beta_apply_router",
    "client_router",
    "legal_router",
    "ingest_router",
    "api_router",
    "ops_treasury_router",
    "webhooks_router",
]
