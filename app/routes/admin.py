from fastapi import APIRouter, Request, Depends, HTTPException, status, Body
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy import text
import logging

from app.core.deps import templates, engine, require_admin, get_db
from app.services.payments import RevenueService
from app.services.beta_activation import update_beta_activity, STAGE_FIRST_LOAD_WON
from app.services.referral import ReferralService
from app.services.email import send_negotiation_email, parse_broker_reply
from app.services.buyback_notifications import BuybackNotificationService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
    
    # Get negotiation details including trucker info and load_id
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'won', final_rate = :final_rate, updated_at = now()
                WHERE id = :id
                RETURNING id, trucker_id, origin, destination, load_id
            """),
            {"id": negotiation_id, "final_rate": final_rate},
        )
        row = r.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negotiation not found")
        
        negotiation_id_db, trucker_id, origin, destination, load_id = row
        if trucker_id:
            update_beta_activity(engine, trucker_id=trucker_id, new_stage=STAGE_FIRST_LOAD_WON)
        
        # Get trucker info and reward tier for dynamic buyback calculation
        trucker_name = None
        mc_number = None
        reward_tier = "STANDARD"
        if trucker_id:
            trucker_row = conn.execute(
                text("SELECT display_name, mc_number, reward_tier FROM webwise.trucker_profiles WHERE id = :id"),
                {"id": trucker_id}
            ).fetchone()
            if trucker_row:
                trucker_name, mc_number, reward_tier = trucker_row[0], trucker_row[1], (trucker_row[2] or "STANDARD")
            
            # Create driver notification (will appear via HTMX polling within 30s)
            route_info = ""
            if origin and destination:
                route_info = f" ({origin} → {destination})"
            
            # Calculate buyback based on reward tier
            from app.services.reward_tier import RewardTierService
            buyback_amount = RewardTierService.calculate_buyback_amount(final_rate, reward_tier)
            
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
            
            # Check for Finder's Fee: If load was discovered by someone else, credit them
            if load_id and str(load_id).strip():
                # Look up the Load by ref_id (negotiations.load_id matches loads.ref_id)
                load_row = conn.execute(
                    text("SELECT discovered_by_id FROM webwise.loads WHERE ref_id = :load_id"),
                    {"load_id": str(load_id).strip()}
                ).fetchone()
                
                if load_row and load_row.discovered_by_id and load_row.discovered_by_id != trucker_id:
                    # This load was discovered by a different driver - credit Finder's Fee
                    discoverer_id = load_row.discovered_by_id
                    
                    # Get discoverer's MC number
                    discoverer_row = conn.execute(
                        text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :id"),
                        {"id": discoverer_id}
                    ).fetchone()
                    
                    if discoverer_row and discoverer_row.mc_number:
                        from app.services.reward_tier import RewardTierService
                        from app.services.token_price import TokenPriceService
                        
                        finders_fee_usd = RewardTierService.calculate_finders_fee(final_rate)
                        
                        # Credit Finder's Fee to discoverer's Automation Fuel (immediate)
                        current_price = TokenPriceService.get_candle_price()
                        tokens_earned = finders_fee_usd / current_price if current_price > 0 else 0.0
                        conn.execute(
                            text("""
                                INSERT INTO webwise.driver_savings_ledger 
                                (driver_mc_number, load_id, amount_usd, amount_candle, unlocks_at, status)
                                VALUES (:mc, :load, :usd, :tokens, now(), 'CREDITED')
                            """),
                            {
                                "mc": discoverer_row.mc_number,
                                "load": f"FINDERS_FEE-{load_id}",
                                "usd": finders_fee_usd,
                                "tokens": tokens_earned,
                            }
                        )
                        
                        # Create notification for discoverer
                        conn.execute(
                            text("""
                                INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                                VALUES (:trucker_id, :message, 'SYSTEM_ALERT', false)
                            """),
                            {
                                "trucker_id": discoverer_id,
                                "message": f"🎯 SCOUT BONUS: A load you discovered ({origin} → {destination}) was just booked! You've earned ${finders_fee_usd:,.2f} Finder's Fee ({tokens_earned:,.2f} $CANDLE).",
                            }
                        )
                        
                        logger.info(f"🎯 FINDERS FEE: Credited ${finders_fee_usd} to discoverer trucker_id={discoverer_id} for load {load_id}")
    
    # Platform treasury: record dispatch fee revenue (burn-eligible)
    from decimal import Decimal
    from app.services.burn import record_revenue
    from app.models.treasury import RevenueSourceType

    platform_fee = (Decimal(str(final_rate)) * Decimal("0.02")).quantize(Decimal("0.01"))
    if platform_fee > 0 and engine:
        try:
            record_revenue(
                engine,
                source_type=RevenueSourceType.DISPATCH_FEE,
                gross_amount_usd=platform_fee,
                source_ref=f"dispatch-{negotiation_id}",
                load_id=str(load_id) if load_id else None,
                driver_mc_number=mc_number,
                burn_eligible=False,  # true only after factoring settlement (confirm_dispatch_settlement)
            )
        except Exception as e:
            logger.warning("platform_revenue_ledger insert failed (idempotent?): %s", e)
    
    # Calculate buyback based on reward tier (use same calculation as above)
    from app.services.reward_tier import RewardTierService
    buyback_accrued = RewardTierService.calculate_buyback_amount(final_rate, reward_tier)
    
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


@router.get("/admin/drivers", dependencies=[Depends(require_admin)])
def drivers_management(request: Request):
    """Admin view: Manage drivers and their reward tiers."""
    if not engine:
        return templates.TemplateResponse(
            "admin/drivers.html",
            {"request": request, "drivers": []}
        )
    
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT 
                tp.id,
                tp.display_name,
                tp.mc_number,
                tp.carrier_name,
                tp.reward_tier,
                u.email,
                u.created_at,
                COUNT(n.id) FILTER (WHERE n.status = 'won') as win_count,
                COALESCE(SUM(n.final_rate) FILTER (WHERE n.status = 'won'), 0) as total_revenue
            FROM webwise.trucker_profiles tp
            LEFT JOIN webwise.users u ON tp.user_id = u.id
            LEFT JOIN webwise.negotiations n ON n.trucker_id = tp.id
            GROUP BY tp.id, tp.display_name, tp.mc_number, tp.carrier_name, tp.reward_tier, u.email, u.created_at
            ORDER BY tp.created_at DESC
        """))
        
        drivers = []
        for row in rows:
            drivers.append({
                "id": row.id,
                "display_name": row.display_name or "Unknown",
                "mc_number": row.mc_number or "N/A",
                "carrier_name": row.carrier_name or "",
                "reward_tier": row.reward_tier or "STANDARD",
                "email": row.email or "N/A",
                "created_at": row.created_at,
                "win_count": row.win_count or 0,
                "total_revenue": float(row.total_revenue or 0)
            })
    
    return templates.TemplateResponse(
        "admin/drivers.html",
        {"request": request, "drivers": drivers}
    )


@router.patch("/admin/drivers/{driver_id}/update-tier", dependencies=[Depends(require_admin)])
async def update_driver_tier(driver_id: int, request: Request):
    """Update a driver's reward tier via HTMX."""
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Get tier from form data (HTMX sends form-encoded)
    form_data = await request.form()
    tier = form_data.get('tier') or request.query_params.get('tier')
    
    if not tier or tier not in ['STANDARD', 'INCENTIVE']:
        raise HTTPException(status_code=400, detail="Invalid tier. Must be 'STANDARD' or 'INCENTIVE'")
    
    with engine.begin() as conn:
        # Verify driver exists and get current tier
        check = conn.execute(
            text("SELECT id, display_name, reward_tier FROM webwise.trucker_profiles WHERE id = :id"),
            {"id": driver_id}
        ).fetchone()
        
        if not check:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        old_tier = check.reward_tier or "STANDARD"
        
        # Update tier
        conn.execute(
            text("""
                UPDATE webwise.trucker_profiles 
                SET reward_tier = :tier, updated_at = now()
                WHERE id = :id
            """),
            {"tier": tier, "id": driver_id}
        )
        
        # If upgraded to INCENTIVE, send VIP notification
        if tier == "INCENTIVE" and old_tier != "INCENTIVE":
            conn.execute(
                text("""
                    INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                    VALUES (:trucker_id, :message, 'SYSTEM_ALERT', false)
                """),
                {
                    "trucker_id": driver_id,
                    "message": "🚀 VIP UPGRADE: Your account is now on the 90% Incentive Tier! Enjoy maximized rewards.",
                }
            )
    
    # Return the select dropdown with updated selection (HTMX will swap it)
    tier_label = "75/25 (Standard)" if tier == "STANDARD" else "90/10 (Incentive)"
    return HTMLResponse(
        content=f'''
        <select 
          hx-patch="/admin/drivers/{driver_id}/update-tier" 
          hx-trigger="change"
          hx-include="[name='tier']"
          hx-target="closest td"
          hx-swap="innerHTML"
          name="tier"
          class="bg-slate-800 text-xs text-white border border-slate-700 rounded px-2 py-1 focus:ring-green-500 focus:border-green-500">
          <option value="STANDARD" {'selected' if tier == 'STANDARD' else ''}>
            75/25 (Standard)
          </option>
          <option value="INCENTIVE" {'selected' if tier == 'INCENTIVE' else ''}>
            90/10 (Incentive)
          </option>
        </select>
        ''',
        headers={"HX-Trigger": "tierUpdated"}
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


@router.get("/admin/broker", dependencies=[Depends(require_admin)])
def broker_lookup(request: Request, mc: str | None = None):
    """Lookup broker by MC number. Shows all contact info and emails."""
    broker = None
    emails = []
    error = None
    mc_clean = None

    if mc:
        mc_clean = "".join(c for c in str(mc).strip() if c.isdigit())
        if not mc_clean:
            error = "Please enter a valid MC number (digits only)."
        elif not engine:
            error = "Database not configured."
        else:
            with engine.begin() as conn:
                row = conn.execute(
                    text("""
                        SELECT mc_number, dot_number, company_name, dba_name, website,
                               primary_email, primary_phone, secondary_phone, fax,
                               phy_street, phy_city, phy_state, phy_zip,
                               source, preferred_contact_method, created_at, updated_at
                        FROM webwise.brokers WHERE mc_number = :mc
                    """),
                    {"mc": mc_clean},
                ).fetchone()
                if row:
                    broker = dict(row._mapping)
                    em_rows = conn.execute(
                        text("""
                            SELECT email, source, confidence, evidence
                            FROM webwise.broker_emails WHERE mc_number = :mc
                            ORDER BY confidence DESC
                        """),
                        {"mc": mc_clean},
                    )
                    emails = [dict(r._mapping) for r in em_rows]

    return templates.TemplateResponse(
        "admin/broker.html",
        {
            "request": request,
            "mc": mc.strip() if mc else None,
            "mc_clean": mc_clean,
            "broker": broker,
            "emails": emails,
            "error": error,
        },
    )


@router.get("/admin/cards", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
def card_fulfillment_queue(request: Request):
    """Admin view: Card fulfillment queue showing REQUESTED and SHIPPED cards."""
    if not engine:
        return templates.TemplateResponse(
            "admin/cards.html",
            {"request": request, "requests": [], "pending_count": 0}
        )
    
    with engine.begin() as conn:
        # Get all card requests (REQUESTED and SHIPPED status)
        rows = conn.execute(text("""
            SELECT 
                dc.id,
                dc.trucker_id,
                dc.status,
                dc.card_last_four,
                dc.requested_at,
                dc.shipped_at,
                tp.mc_number,
                tp.display_name,
                tp.address_line1,
                tp.address_line2,
                tp.city,
                tp.state,
                tp.zip_code
            FROM webwise.debit_cards dc
            INNER JOIN webwise.trucker_profiles tp ON dc.trucker_id = tp.id
            WHERE dc.status IN ('REQUESTED', 'SHIPPED')
            ORDER BY 
                CASE dc.status 
                    WHEN 'REQUESTED' THEN 1 
                    WHEN 'SHIPPED' THEN 2 
                    ELSE 3 
                END,
                dc.requested_at DESC
        """))
        
        requests = []
        pending_count = 0
        for row in rows:
            if row.status == 'REQUESTED':
                pending_count += 1
            requests.append({
                "id": row.id,
                "trucker_id": row.trucker_id,
                "status": row.status,
                "card_last_four": row.card_last_four,
                "requested_at": row.requested_at,
                "shipped_at": row.shipped_at,
                "trucker_mc": row.mc_number or "N/A",
                "display_name": row.display_name or "Unknown",
                "address_line1": row.address_line1,
                "address_line2": row.address_line2,
                "city": row.city,
                "state": row.state,
                "zip": row.zip_code
            })
    
    return templates.TemplateResponse(
        "admin/cards.html",
        {"request": request, "requests": requests, "pending_count": pending_count}
    )


@router.post("/admin/cards/ship/{card_id}", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
async def ship_card(card_id: int, request: Request):
    """Mark a card as shipped with last 4 digits."""
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    form_data = await request.form()
    last_four = form_data.get("last_four", "").strip()
    
    if not last_four or len(last_four) != 4 or not last_four.isdigit():
        return HTMLResponse(
            content='<td colspan="5" class="px-6 py-4 text-red-400">Invalid card number. Must be 4 digits.</td>',
            status_code=400
        )
    
    with engine.begin() as conn:
        # Verify card exists and is in REQUESTED status
        check = conn.execute(
            text("SELECT trucker_id, status FROM webwise.debit_cards WHERE id = :card_id"),
            {"card_id": card_id}
        ).fetchone()
        
        if not check:
            return HTMLResponse(
                content='<td colspan="5" class="px-6 py-4 text-red-400">Card not found.</td>',
                status_code=404
            )
        
        if check.status != 'REQUESTED':
            return HTMLResponse(
                content=f'<td colspan="5" class="px-6 py-4 text-yellow-400">Card already {check.status.lower()}.</td>',
                status_code=400
            )
        
        trucker_id = check.trucker_id
        
        # Update card status
        conn.execute(
            text("""
                UPDATE webwise.debit_cards 
                SET status = 'SHIPPED',
                    card_last_four = :last_four,
                    shipped_at = now(),
                    updated_at = now()
                WHERE id = :card_id
            """),
            {"card_id": card_id, "last_four": last_four}
        )
        
        # Create notification for driver
        conn.execute(
            text("""
                INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                VALUES (:trucker_id, :message, 'SYSTEM_ALERT', false)
            """),
            {
                "trucker_id": trucker_id,
                "message": "📦 YOUR CARD IS ON THE WAY! Watch your mail for your GC Fuel & Fleet Card. You'll be able to activate it once it arrives.",
            }
        )
        
        # Get updated card info for display
        updated = conn.execute(
            text("""
                SELECT 
                    dc.id,
                    dc.status,
                    dc.card_last_four,
                    dc.requested_at,
                    tp.mc_number,
                    tp.address_line1,
                    tp.address_line2,
                    tp.city,
                    tp.state,
                    tp.zip_code
                FROM webwise.debit_cards dc
                INNER JOIN webwise.trucker_profiles tp ON dc.trucker_id = tp.id
                WHERE dc.id = :card_id
            """),
            {"card_id": card_id}
        ).fetchone()
        
        # Return updated row HTML
        return HTMLResponse(
            content=f'''
            <tr id="card-row-{updated.id}" class="bg-blue-900/20">
                <td class="px-6 py-4 text-white font-mono">{updated.mc_number or 'N/A'}</td>
                <td class="px-6 py-4 text-slate-400">
                    {updated.address_line1 or ''}{f', {updated.address_line2}' if updated.address_line2 else ''}<br>
                    {updated.city or ''}, {updated.state or ''} {updated.zip_code or ''}
                </td>
                <td class="px-6 py-4 text-slate-400">
                    {updated.requested_at.strftime('%m/%d/%Y') if updated.requested_at else 'N/A'}
                </td>
                <td class="px-6 py-4">
                    <span class="text-indigo-400 font-mono">{updated.card_last_four or 'N/A'}</span>
                </td>
                <td class="px-6 py-4 text-right">
                    <span class="text-blue-400 text-xs font-bold">SHIPPED</span>
                </td>
            </tr>
            ''',
            headers={"HX-Trigger": "cardShipped"}
        )
