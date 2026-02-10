from fastapi import APIRouter, Request, Depends, HTTPException, status, Body
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import text

from app.core.deps import templates, engine, require_admin
from app.services.payments import RevenueService

router = APIRouter()


@router.get("/admin/dashboard", dependencies=[Depends(require_admin)])
def admin_dashboard(request: Request):
    stats = {
        "projects": 0,
        "published": 0,
        "pending": 0,
        "uptime": "99.9%",
    }
    pending = []
    if engine:
        with engine.begin() as conn:
            stats["projects"] = conn.execute(text("SELECT COUNT(*) FROM webwise.projects;")).scalar() or 0
            r = conn.execute(text("SELECT COUNT(*) FROM webwise.testimonials WHERE is_approved = true;"))
            stats["published"] = r.scalar() or 0
            r = conn.execute(text("SELECT COUNT(*) FROM webwise.testimonials WHERE is_approved = false;"))
            stats["pending"] = r.scalar() or 0
            rows = conn.execute(text("""
                SELECT id, client_name, event_type, rating, testimonial_text, created_at
                FROM webwise.testimonials
                WHERE is_approved = false
                ORDER BY created_at DESC
                LIMIT 5
            """))
            pending = [dict(r._mapping) for r in rows]
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "stats": stats, "pending": pending})


@router.get("/admin/revenue-stats", dependencies=[Depends(require_admin)])
def admin_revenue_stats(request: Request):
    """HTMX: returns the Buyback Engine widget (RevenueService: 2% of WON loads)."""
    stats = RevenueService.get_buyback_stats_from_engine(engine)
    return templates.TemplateResponse(
        "partials/revenue_stats_widget.html",
        {
            "request": request,
            "pending_buyback": stats["candle_buyback_usd"],
            "win_count": stats["win_count"],
            "total_revenue": stats["total_revenue"],
        },
    )


@router.post("/admin/testimonials/{testimonial_id}/approve", dependencies=[Depends(require_admin)])
def approve_testimonial(testimonial_id: int):
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE webwise.testimonials
            SET is_approved = true
            WHERE id = :id
        """), {"id": testimonial_id})
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/testimonials/{testimonial_id}/reject", dependencies=[Depends(require_admin)])
def reject_testimonial(testimonial_id: int):
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM webwise.testimonials
            WHERE id = :id
        """), {"id": testimonial_id})
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/negotiations/{negotiation_id}/mark-replied", dependencies=[Depends(require_admin)])
def mark_negotiation_replied(negotiation_id: int, body: dict | None = Body(None)):
    """When a broker replies (email/webhook or manual), set status to REPLIED so the AI can follow up."""
    broker_reply = (body or {}).get("broker_reply", "") or ""
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'replied', broker_reply = :broker_reply, updated_at = now()
                WHERE id = :id
                RETURNING id
            """),
            {"id": negotiation_id, "broker_reply": broker_reply or None},
        )
        if r.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negotiation not found")
    return {"status": "replied", "negotiation_id": negotiation_id}


@router.post("/admin/negotiations/{negotiation_id}/mark-won", dependencies=[Depends(require_admin)])
def mark_negotiation_won(negotiation_id: int, body: dict = Body(...)):
    """Broker said yes at this price → WON. This is the trigger for the 2% buyback (Transak/Slack notification)."""
    final_rate = body.get("final_rate")
    if final_rate is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="final_rate required")
    try:
        final_rate = float(final_rate)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="final_rate must be a number")
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'won', final_rate = :final_rate, updated_at = now()
                WHERE id = :id
                RETURNING id, trucker_id
            """),
            {"id": negotiation_id, "final_rate": final_rate},
        )
        row = r.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negotiation not found")
        trucker_id = row[1]
        if trucker_id:
            conn.execute(
                text("""
                    INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                    VALUES (:trucker_id, :message, 'LOAD_WON', false)
                """),
                {
                    "trucker_id": trucker_id,
                    "message": f"💰 WIN! ${final_rate:,.2f} load secured. ${final_rate * 0.02:,.2f} added to $CANDLE buyback pool.",
                },
            )
    buyback_accrued = round(final_rate * 0.02, 2)
    # So driver dashboards (HTMX) can refresh "My Contribution" when admin marks a load won
    return JSONResponse(
        content={
            "status": "won",
            "negotiation_id": negotiation_id,
            "final_rate": final_rate,
            "buyback_accrued": buyback_accrued,
        },
        headers={"HX-Trigger": "contributionUpdated"},
    )
