# app/routes/beta_apply.py
# beta_driver_applications.id is UUID. Returns application_id as UUID string.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.deps import get_engine, templates

router = APIRouter(tags=["beta"])


@router.get("/beta/apply")
def beta_apply_page(request: Request):
    """Render the beta application form (weekly invoicing checkbox, etc.)."""
    return templates.TemplateResponse("public/beta_apply.html", {"request": request})


class BetaApplyIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)

    mc_number: str = Field(min_length=2, max_length=50)
    carrier_name: str | None = Field(default=None, max_length=255)
    truck_type: str | None = Field(default=None, max_length=100)
    preferred_lanes: str | None = Field(default=None, max_length=400)
    factoring_company: str | None = Field(default=None, max_length=200)

    agree_weekly_invoice: bool = Field(
        default=False,
        description="I agree to weekly invoicing for the 2.5% dispatch fee after loads are completed.",
    )


@router.post("/beta/apply")
def beta_apply(payload: BetaApplyIn, engine: Engine = Depends(get_engine)):
    billing_method = "WEEKLY_INVOICE" if payload.agree_weekly_invoice else None

    sql = text(
        """
        INSERT INTO webwise.beta_driver_applications
        (full_name, email, phone, mc_number, carrier_name, truck_type, preferred_lanes, factoring_company, billing_method)
        VALUES
        (:full_name, :email, :phone, :mc_number, :carrier_name, :truck_type, :preferred_lanes, :factoring_company, :billing_method)
        RETURNING id, status;
        """
    )

    try:
        with engine.begin() as conn:
            row = conn.execute(
                sql,
                {
                    "full_name": payload.full_name.strip(),
                    "email": payload.email.lower().strip(),
                    "phone": payload.phone.strip(),
                    "mc_number": payload.mc_number.strip(),
                    "carrier_name": payload.carrier_name,
                    "truck_type": payload.truck_type,
                    "preferred_lanes": payload.preferred_lanes,
                    "factoring_company": payload.factoring_company,
                    "billing_method": billing_method,
                },
            ).mappings().one()

        return {"application_id": str(row["id"]), "status": row["status"]}

    except Exception as e:
        msg = str(e).lower()
        # These names match the partial unique indexes in the migration
        if "uq_beta_driver_app_email_pending" in msg or "uq_beta_driver_app_mc_pending" in msg:
            raise HTTPException(status_code=409, detail="An application is already pending for this email or MC number.")
        raise HTTPException(status_code=500, detail="Failed to submit beta application.")
