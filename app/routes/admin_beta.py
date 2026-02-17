# app/routes/admin_beta.py
# application_id is UUID string. users.id and trucker_profiles.id are INTEGER.

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

from passlib.context import CryptContext

from app.core.deps import get_engine, require_admin
from app.services.beta_activation import display_stage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/admin/beta", tags=["admin-beta"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


class BetaApproveIn(BaseModel):
    application_id: str = Field(..., description="UUID string from /beta/apply")
    temp_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class BetaApproveOut(BaseModel):
    application_id: str
    user_id: int
    trucker_profile_id: int
    email: str
    mc_number: str
    temp_password: str
    approved_at: datetime


@router.post("/approve", response_model=BetaApproveOut, dependencies=[Depends(require_admin)])
def approve_beta_driver(payload: BetaApproveIn, engine: Engine = Depends(get_engine)):

    # Validate UUID early so we return 400 instead of a DB error
    try:
        app_id = str(UUID(payload.application_id))
    except Exception:
        raise HTTPException(status_code=400, detail="application_id must be a valid UUID.")

    temp_password = payload.temp_password or secrets.token_urlsafe(10)
    password_hash = hash_password(temp_password)

    with engine.begin() as conn:

        # 1) Fetch PENDING application and lock it
        app = conn.execute(
            text(
                """
                SELECT id, full_name, email, phone, mc_number, carrier_name, factoring_company, billing_method
                FROM webwise.beta_driver_applications
                WHERE id = :id AND status = 'PENDING'
                FOR UPDATE;
                """
            ),
            {"id": app_id},
        ).mappings().one_or_none()

        if not app:
            raise HTTPException(status_code=404, detail="Pending beta application not found.")

        # 2) Ensure email not already used in users (unique constraint exists)
        exists = conn.execute(
            text("SELECT id FROM webwise.users WHERE email = :email LIMIT 1;"),
            {"email": app["email"].lower().strip()},
        ).mappings().one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="A user with this email already exists.")

        # 3) Create user (INTEGER id)
        user = conn.execute(
            text(
                """
                INSERT INTO webwise.users
                (email, password_hash, role, is_active, factoring_company)
                VALUES
                (:email, :password_hash, 'client', true, :factoring_company)
                RETURNING id, email;
                """
            ),
            {
                "email": app["email"].lower().strip(),
                "password_hash": password_hash,
                "factoring_company": app["factoring_company"],
            },
        ).mappings().one()

        user_id = int(user["id"])

        # 4) Create trucker profile (INTEGER id) with is_beta=true and billing_method from application
        profile = conn.execute(
            text(
                """
                INSERT INTO webwise.trucker_profiles
                (user_id, display_name, carrier_name, mc_number, is_beta, billing_method)
                VALUES
                (:user_id, :display_name, :carrier_name, :mc_number, true, :billing_method)
                RETURNING id;
                """
            ),
            {
                "user_id": user_id,
                "display_name": app["full_name"],
                "carrier_name": app["carrier_name"],
                "mc_number": app["mc_number"],
                "billing_method": app.get("billing_method"),
            },
        ).mappings().one()

        profile_id = int(profile["id"])

        # 5) Mark application approved + link created ids
        conn.execute(
            text(
                """
                UPDATE webwise.beta_driver_applications
                SET status = 'APPROVED',
                    decided_at = NOW(),
                    created_user_id = :user_id,
                    created_trucker_profile_id = :profile_id
                WHERE id = :id;
                """
            ),
            {"user_id": user_id, "profile_id": profile_id, "id": app_id},
        )

    return BetaApproveOut(
        application_id=app_id,
        user_id=user_id,
        trucker_profile_id=profile_id,
        email=user["email"],
        mc_number=app["mc_number"],
        temp_password=temp_password,
        approved_at=datetime.utcnow(),
    )


@router.get("/applications", dependencies=[Depends(require_admin)])
def list_beta_applications(
    status: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING",
    limit: int = 50,
    engine: Engine = Depends(get_engine),
):
    limit = max(1, min(limit, 200))

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    id, full_name, email, phone, mc_number, carrier_name,
                    truck_type, preferred_lanes, factoring_company,
                    status, created_at, decided_at,
                    created_user_id, created_trucker_profile_id
                FROM webwise.beta_driver_applications
                WHERE status = :status
                ORDER BY created_at DESC
                LIMIT :limit;
                """
            ),
            {"status": status, "limit": limit},
        ).mappings().all()

    # stringify UUID id for JSON; Row._mapping for dict conversion (SQLAlchemy 2)
    return [{**r._mapping, "id": str(r["id"])} for r in rows]


class BetaRejectIn(BaseModel):
    application_id: str
    reason: Optional[str] = Field(default=None, max_length=500)


@router.post("/reject", dependencies=[Depends(require_admin)])
def reject_beta_application(payload: BetaRejectIn, engine: Engine = Depends(get_engine)):
    try:
        app_id = str(UUID(payload.application_id))
    except Exception:
        raise HTTPException(status_code=400, detail="application_id must be a valid UUID.")

    with engine.begin() as conn:
        updated = conn.execute(
            text(
                """
                UPDATE webwise.beta_driver_applications
                SET status = 'REJECTED',
                    decided_at = NOW()
                WHERE id = :id AND status = 'PENDING'
                RETURNING id;
                """
            ),
            {"id": app_id},
        ).mappings().one_or_none()

        if not updated:
            raise HTTPException(status_code=404, detail="Pending beta application not found.")

    return {"application_id": app_id, "status": "REJECTED"}


class BetaResetPasswordIn(BaseModel):
    email: EmailStr = Field(..., description="Beta driver email")
    temp_password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    beta_only: bool = Field(default=True, description="If True, only allow reset for is_beta accounts")


@router.post("/reset-password", dependencies=[Depends(require_admin)])
def reset_beta_driver_password(payload: BetaResetPasswordIn, engine: Engine = Depends(get_engine)):
    """
    Admin-only: set a new password for a beta driver (by email).
    Use for "I forgot my password" — no email flow required. Returns temp_password so you can text it.
    """
    temp_pw = payload.temp_password or secrets.token_urlsafe(10)
    pw_hash = hash_password(temp_pw)
    email_clean = payload.email.lower().strip()

    with engine.begin() as conn:
        user = conn.execute(
            text("""
                SELECT u.id, u.email, u.role, tp.is_beta
                FROM webwise.users u
                LEFT JOIN webwise.trucker_profiles tp ON tp.user_id = u.id
                WHERE LOWER(u.email) = :email
                LIMIT 1
            """),
            {"email": email_clean},
        ).mappings().one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Auth uses 'client' for drivers; allow 'trucker' for legacy/approve-created accounts
        if user["role"] not in ("client", "trucker"):
            raise HTTPException(status_code=409, detail="User is not a driver")

        if payload.beta_only and not user.get("is_beta"):
            raise HTTPException(status_code=409, detail="User is not a beta driver; set beta_only=false to reset any driver.")

        conn.execute(
            text("UPDATE webwise.users SET password_hash = :pw WHERE id = :id"),
            {"pw": pw_hash, "id": user["id"]},
        )

    return {"email": user["email"], "temp_password": temp_pw}


@router.get("/activation", dependencies=[Depends(require_admin)])
def list_beta_activation(engine: Engine = Depends(get_engine)):
    """
    Admin: beta driver activation state for operational visibility.
    Who is approved, who logged in, who ran scout, who won/funded.
    """
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text("""
                    SELECT
                        tp.mc_number,
                        u.email,
                        tp.beta_activation_stage AS stage,
                        tp.beta_last_activity_at AS last_activity,
                        tp.beta_onboarded_at AS onboarded_at,
                        tp.created_at
                    FROM webwise.trucker_profiles tp
                    JOIN webwise.users u ON u.id = tp.user_id
                    WHERE tp.is_beta = true
                    ORDER BY tp.beta_last_activity_at DESC NULLS LAST
                """),
            ).mappings().all()
    except Exception:
        return []
    out = []
    for r in rows:
        stage = r.get("stage") or "APPROVED"
        last_activity = r.get("last_activity")
        item = {
            "mc_number": r.get("mc_number"),
            "email": r.get("email"),
            "stage": stage,
            "display_stage": display_stage(stage, last_activity),
        }
        if last_activity:
            item["last_activity"] = last_activity.isoformat() if hasattr(last_activity, "isoformat") else str(last_activity)
        else:
            item["last_activity"] = None
        if r.get("onboarded_at"):
            item["onboarded_at"] = r["onboarded_at"].isoformat() if hasattr(r["onboarded_at"], "isoformat") else str(r["onboarded_at"])
        out.append(item)
    return out
