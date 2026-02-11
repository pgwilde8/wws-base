from fastapi import APIRouter, Request, Depends, HTTPException, status, Body
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy import text

from app.core.deps import templates, engine, require_admin, get_db
from app.services.payments import RevenueService
from app.services.referral import ReferralService
from app.services.email import send_negotiation_email, parse_broker_reply
from app.services.buyback_notifications import BuybackNotificationService
from sqlalchemy.orm import Session

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
async def mark_negotiation_won(negotiation_id: int, body: dict = Body(...)):
    """
    Broker said yes at this price → WON. 
    This is the critical trigger for the 2% buyback (Transak/Slack/Discord notification).
    """
    final_rate = body.get("final_rate")
    if final_rate is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="final_rate required")
    try:
        final_rate = float(final_rate)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="final_rate must be a number")
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    
    # Get negotiation details including trucker info
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'won', final_rate = :final_rate, updated_at = now()
                WHERE id = :id
                RETURNING id, trucker_id, origin, destination
            """),
            {"id": negotiation_id, "final_rate": final_rate},
        )
        row = r.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negotiation not found")
        
        negotiation_id_db, trucker_id, origin, destination = row
        
        # Get trucker info for notification
        trucker_name = None
        mc_number = None
        if trucker_id:
            trucker_row = conn.execute(
                text("SELECT display_name, mc_number FROM webwise.trucker_profiles WHERE id = :id"),
                {"id": trucker_id}
            ).fetchone()
            if trucker_row:
                trucker_name, mc_number = trucker_row[0], trucker_row[1]
            
            # Create driver notification (will appear via HTMX polling within 30s)
            route_info = ""
            if origin and destination:
                route_info = f" ({origin} → {destination})"
            
            buyback_amount = round(final_rate * 0.02, 2)
            conn.execute(
                text("""
                    INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                    VALUES (:trucker_id, :message, 'LOAD_WON', false)
                """),
                {
                    "trucker_id": trucker_id,
                    "message": f"💰 WIN! ${final_rate:,.2f} load secured{route_info}. ${buyback_amount:,.2f} added to $CANDLE buyback pool.",
                },
            )
    
    buyback_accrued = round(final_rate * 0.02, 2)
    
    # Send community-visible buyback notification (Slack/Discord)
    # This is the "Proof of Freight" mechanism
    try:
        await BuybackNotificationService.send_buyback_notification(
            final_rate=final_rate,
            buyback_amount=buyback_accrued,
            trucker_name=trucker_name,
            mc_number=mc_number,
            origin=origin,
            destination=destination,
        )
    except Exception as e:
        # Don't fail the request if webhook fails, but log it
        print(f"⚠️  Buyback notification failed: {e}")
    
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


@router.get("/admin/referral-stats", dependencies=[Depends(require_admin)])
def admin_referral_stats(request: Request, db: Session = Depends(get_db)):
    """
    HTMX: Returns Referral Stats widget showing monthly OTR bounties, residuals, and goal progress.
    Also includes referral leaderboard showing which codes generate the most $100 bounties.
    """
    stats = ReferralService.get_monthly_referral_stats(db)
    leaderboard = ReferralService.get_referral_leaderboard(db, limit=5)
    
    return templates.TemplateResponse(
        "partials/referral_stats_widget.html",
        {
            "request": request,
            "stats": stats,
            "leaderboard": leaderboard
        }
    )


@router.get("/admin/trucker-leaderboard", dependencies=[Depends(require_admin)])
def trucker_leaderboard(request: Request):
    """Admin view: Top truckers by Green Candle contribution (wins and revenue)."""
    if not engine:
        return templates.TemplateResponse(
            "partials/trucker_leaderboard_widget.html",
            {"request": request, "truckers": []}
        )
    
    from app.services.payments import RevenueService
    truckers = RevenueService.get_all_trucker_contributions(engine, limit=10)
    
    return templates.TemplateResponse(
        "partials/trucker_leaderboard_widget.html",
        {"request": request, "truckers": truckers}
    )


@router.get("/admin/network-health", dependencies=[Depends(require_admin)])
def network_health(request: Request):
    """Network Health widget showing email connectivity and broker reply status."""
    if not engine:
        return templates.TemplateResponse(
            "partials/network_health_widget.html",
            {"request": request, "email_configured": False, "pending_replies": 0}
        )
    
    from app.services.email import MXROUTE_SMTP_USER, MXROUTE_SMTP_PASSWORD
    
    email_configured = bool(MXROUTE_SMTP_USER and MXROUTE_SMTP_PASSWORD)
    
    # Count negotiations waiting for broker reply
    with engine.begin() as conn:
        pending_count = conn.execute(
            text("""
                SELECT COUNT(*) 
                FROM webwise.negotiations 
                WHERE status IN ('sent', 'pending') 
                AND created_at > now() - interval '7 days'
            """)
        ).scalar() or 0
    
    return templates.TemplateResponse(
        "partials/network_health_widget.html",
        {
            "request": request,
            "email_configured": email_configured,
            "pending_replies": pending_count
        }
    )


@router.get("/admin/usage-stats", dependencies=[Depends(require_admin)])
def admin_usage_stats(request: Request):
    """
    HTMX: Returns Usage Monitor widget showing OpenAI token usage per MC number.
    Flags high-cost users (many negotiations, few wins).
    """
    if not engine:
        return templates.TemplateResponse(
            "partials/usage_monitor_widget.html",
            {"request": request, "usage_data": [], "error": "Database not configured"}
        )
    
    with engine.begin() as conn:
        # Get usage stats per MC number (via trucker_profiles)
        rows = conn.execute(text("""
            SELECT 
                tp.mc_number,
                tp.display_name,
                tp.carrier_name,
                COUNT(n.id) as negotiation_count,
                COALESCE(SUM(n.ai_total_tokens), 0) as total_tokens,
                COALESCE(SUM(CASE WHEN n.status = 'won' THEN 1 ELSE 0 END), 0) as wins_count,
                CASE 
                    WHEN COUNT(n.id) > 0 THEN 
                        ROUND(COUNT(n.id)::numeric / NULLIF(SUM(CASE WHEN n.status = 'won' THEN 1 ELSE 0 END), 0), 2)
                    ELSE 0
                END as negotiations_per_win
            FROM webwise.trucker_profiles tp
            LEFT JOIN webwise.negotiations n ON n.trucker_id = tp.id
            WHERE tp.mc_number IS NOT NULL
            GROUP BY tp.id, tp.mc_number, tp.display_name, tp.carrier_name
            HAVING COUNT(n.id) > 0
            ORDER BY total_tokens DESC, negotiation_count DESC
            LIMIT 10
        """))
        
        usage_data = []
        for row in rows:
            mc = row.mc_number or "N/A"
            negotiations = row.negotiation_count or 0
            tokens = row.total_tokens or 0
            wins = row.wins_count or 0
            ratio = float(row.negotiations_per_win or 0)
            
            # Flag high-cost users: >50 negotiations with <2 wins (ratio > 25)
            is_high_cost = negotiations > 50 and wins < 2
            
            usage_data.append({
                "mc_number": mc,
                "display_name": row.display_name or "Unknown",
                "carrier_name": row.carrier_name or "",
                "negotiation_count": negotiations,
                "total_tokens": tokens,
                "wins_count": wins,
                "negotiations_per_win": ratio,
                "is_high_cost": is_high_cost,
                "estimated_cost_usd": round(tokens * 0.00001, 2)  # Rough estimate: $0.00001 per token
            })
    
    return templates.TemplateResponse(
        "partials/usage_monitor_widget.html",
        {"request": request, "usage_data": usage_data}
    )


@router.get("/admin/leads", response_class=HTMLResponse)
def view_leads_dashboard(request: Request):
    """
    The 'Money Board': Shows all users who need factoring or have it.
    Displays OTR requests (commission opportunities) and existing clients (switching opportunities).
    """
    # Check authentication and redirect if needed
    from app.core.deps import current_user
    user = current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not engine:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    
    with engine.begin() as conn:
        # Fetch all users with referral status (not 'NONE' and not NULL)
        rows = conn.execute(text("""
            SELECT 
                u.id,
                u.email,
                u.referral_status,
                u.factoring_company,
                u.created_at,
                tp.mc_number,
                tp.display_name,
                tp.carrier_name
            FROM webwise.users u
            LEFT JOIN webwise.trucker_profiles tp ON u.id = tp.user_id
            WHERE u.referral_status IS NOT NULL 
              AND u.referral_status != 'NONE'
            ORDER BY u.created_at DESC
        """))
        
        leads = []
        for row in rows:
            leads.append({
                "id": row.id,
                "email": row.email,
                "referral_status": row.referral_status or "NONE",
                "factoring_company": row.factoring_company,
                "created_at": row.created_at,
                "mc_number": row.mc_number,
                "display_name": row.display_name,
                "carrier_name": row.carrier_name
            })
        
        # Calculate stats
        total_requested = sum(1 for lead in leads if lead["referral_status"] == "OTR_REQUESTED")
        total_existing = sum(1 for lead in leads if lead["referral_status"] == "EXISTING_CLIENT")
    
    return templates.TemplateResponse(
        "admin/leads.html",
        {
            "request": request,
            "leads": leads,
            "stats": {
                "requested": total_requested,
                "existing": total_existing,
                "total": len(leads)
            }
        }
    )
