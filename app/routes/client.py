from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.deps import templates, current_user, engine, get_db
from app.services.ai_agent import AIAgentService
from app.services.negotiation import save_negotiation
from app.services.payments import RevenueService
from app.services.storage import upload_bol
from app.services.factoring import push_invoice_to_factor
from app.services.tokenomics import credit_driver_savings
from app.services.buyback_notifications import BuybackNotificationService
from app.schemas.load import LoadResponse, LoadStatus

router = APIRouter()


@router.get("/clients/dashboard")
def client_dashboard(request: Request, user: Optional[Dict] = Depends(current_user)):
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    return templates.TemplateResponse("drivers/dashboard.html", {"request": request, "user": user})


@router.get("/clients/active-load", response_class=HTMLResponse)
def active_load(request: Request, user: Optional[Dict] = Depends(current_user)):
    """
    Returns the driver's current active load (most recent WON negotiation).
    Returns empty HTML if no active load exists.
    """
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"), {"uid": user.get("id")})
        row = r.first()
        trucker_id = row.id if row else None
    
    if not trucker_id:
        return HTMLResponse(content="")
    
    # Get most recent WON negotiation (active load)
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                SELECT 
                    id, origin, destination, final_rate, created_at
                FROM webwise.negotiations
                WHERE trucker_id = :trucker_id 
                AND status = 'won'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"trucker_id": trucker_id}
        )
        row = r.first()
        
        if not row:
            # No active load - return placeholder
            if request.headers.get("HX-Request"):
                return templates.TemplateResponse(
                    "drivers/partials/no_active_load.html",
                    {"request": request}
                )
            return {"active": False}
        
        active_load_data = {
            "id": row.id,
            "origin": row.origin or "Unknown",
            "destination": row.destination or "Unknown",
            "final_rate": float(row.final_rate) if row.final_rate else 0.0,
            "created_at": row.created_at
        }
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "drivers/partials/active_load_card.html",
            {"request": request, "load": active_load_data}
        )
    return active_load_data


@router.get("/clients/my-contribution")
def my_contribution(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Per-driver Green Candle contribution. Returns HTML partial for HTMX, JSON otherwise."""
    if not user or user.get("role") != "client":
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "drivers/partials/contribution_stats.html",
                {"request": request, "stats": {"win_count": 0, "total_revenue": 0.0, "candle_contribution_usd": 0.0}},
            )
        return RedirectResponse(url="/login/client", status_code=303)
    trucker_id = None
    if engine:
        with engine.begin() as conn:
            r = conn.execute(
                text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
                {"uid": user.get("id")},
            )
            row = r.first()
            trucker_id = row.id if row else None
    stats = RevenueService.get_trucker_contribution(engine, trucker_id) if trucker_id else {
        "win_count": 0, "total_revenue": 0.0, "candle_contribution_usd": 0.0
    }
    if request.headers.get("HX-Request"):
        resp = templates.TemplateResponse(
            "drivers/partials/contribution_stats.html",
            {"request": request, "stats": stats},
        )
        # Add HTMX trigger so other widgets can listen for updates
        resp.headers["HX-Trigger"] = "contributionStatsLoaded"
        return resp
    return stats


@router.get("/clients/notifications/poll", response_class=HTMLResponse)
def poll_notifications(request: Request, user: Optional[Dict] = Depends(current_user)):
    """
    HTMX polling endpoint: checks every 30s for new unread notifications.
    Returns only NEW notifications (not already shown) to prevent duplicates.
    Uses beforeend swap to append new toasts to the notification container.
    """
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"), {"uid": user.get("id")})
        row = r.first()
        trucker_id = row.id if row else None
    if not trucker_id:
        return HTMLResponse(content="")
    
    # Get the timestamp of the last notification we've shown (from request header or use current time - 30s)
    # For V1, we'll return only notifications created in the last 30 seconds to avoid duplicates
    with engine.begin() as conn:
        # Get notifications created in the last 30 seconds (to match polling interval)
        r = conn.execute(
            text("""
                SELECT 
                    n.id, 
                    n.message, 
                    n.notif_type, 
                    n.created_at
                FROM webwise.notifications n
                WHERE n.trucker_id = :trucker_id 
                AND n.is_read = false
                AND n.created_at > now() - interval '35 seconds'
                ORDER BY n.created_at DESC
            """),
            {"trucker_id": trucker_id},
        )
        rows = r.fetchall()
        
        # Parse negotiation_id from PENDING_APPROVAL notifications (format: "NEG_ID:123|message")
        notifications_with_neg = []
        for row in rows:
            message = row[1]
            negotiation_id = None
            display_message = message
            
            if row[2] == "PENDING_APPROVAL" and "NEG_ID:" in message:
                # Extract negotiation_id from message format: "NEG_ID:123|message"
                import re
                match = re.search(r'NEG_ID:(\d+)\|', message)
                if match:
                    negotiation_id = int(match.group(1))
                    # Remove the ID prefix from display message
                    display_message = re.sub(r'NEG_ID:\d+\|', '', message)
            
            notif_data = {
                "id": row[0],
                "message": display_message,  # Clean message without ID prefix
                "notif_type": row[2],
                "created_at": row[3],
                "negotiation_id": negotiation_id
            }
            notifications_with_neg.append(notif_data)
    
    notifications = notifications_with_neg
    if not notifications:
        return HTMLResponse(content="")
    
    # Return notification list (will be appended via beforeend)
    resp = templates.TemplateResponse(
        "drivers/partials/notification_list.html",
        {"request": request, "notifications": notifications},
    )
    # Dash-mounted phone: play sound when new alerts arrive (browsers may block until user has interacted)
    resp.headers["HX-Trigger"] = "playNotificationSound"
    return resp


@router.post("/clients/notifications/{notification_id}/read", response_class=HTMLResponse)
def mark_notification_read(notification_id: int, user: Optional[Dict] = Depends(current_user)):
    """Mark read and return empty so HTMX removes the toast (outerHTML swap)."""
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                UPDATE webwise.notifications n
                SET is_read = true
                FROM webwise.trucker_profiles t
                WHERE n.trucker_id = t.id AND t.user_id = :uid AND n.id = :nid
                RETURNING n.id
            """),
            {"uid": user.get("id"), "nid": notification_id},
        )
        if r.fetchone() is None:
            return HTMLResponse(content="")
    return HTMLResponse(content="")


@router.post("/clients/negotiations/{negotiation_id}/confirm", response_class=HTMLResponse)
async def confirm_negotiation(negotiation_id: int, request: Request, user: Optional[Dict] = Depends(current_user), db: Session = Depends(get_db)):
    """
    Driver confirms a PENDING_APPROVAL negotiation → marks as WON.
    This is the "Final Click" that gives drivers control and prevents AI from accepting bad loads.
    """
    if not user or user.get("role") != "client":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify this negotiation belongs to the logged-in driver
    trucker_id = None
    if engine:
        with engine.begin() as conn:
            r = conn.execute(text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"), {"uid": user.get("id")})
            row = r.first()
            trucker_id = row.id if row else None
    
    if not trucker_id:
        raise HTTPException(status_code=403, detail="Trucker profile not found")
    
    # Verify negotiation belongs to this driver and is PENDING_APPROVAL
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    with engine.begin() as conn:
        # Check negotiation ownership and status
        neg = conn.execute(
            text("""
                SELECT n.id, n.trucker_id, n.status, n.final_rate, n.origin, n.destination, n.load_id
                FROM webwise.negotiations n
                WHERE n.id = :id AND n.trucker_id = :trucker_id
            """),
            {"id": negotiation_id, "trucker_id": trucker_id}
        ).fetchone()
        
        if not neg:
            raise HTTPException(status_code=404, detail="Negotiation not found or access denied")
        
        if neg.status != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Negotiation is not pending approval (current status: {neg.status})")
        
        final_rate = neg.final_rate
        if not final_rate:
            raise HTTPException(status_code=400, detail="No rate found in negotiation")
        
        # Get reward tier for dynamic buyback calculation
        tier_row = conn.execute(
            text("SELECT reward_tier FROM webwise.trucker_profiles WHERE id = :id"),
            {"id": trucker_id}
        ).fetchone()
        reward_tier = tier_row[0] if tier_row and tier_row[0] else "STANDARD"
        
        # Mark as WON
        conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'won', updated_at = now()
                WHERE id = :id
            """),
            {"id": negotiation_id}
        )
        
        # Calculate buyback based on reward tier
        from app.services.reward_tier import RewardTierService
        buyback_amount = RewardTierService.calculate_buyback_amount(final_rate, reward_tier)
        
        route_info = ""
        if neg.origin and neg.destination:
            route_info = f" ({neg.origin} → {neg.destination})"
        
        conn.execute(
            text("""
                INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                VALUES (:trucker_id, :message, 'LOAD_WON', false)
            """),
            {
                "trucker_id": trucker_id,
                "message": f"✅ CONFIRMED! ${final_rate:,.2f} load secured{route_info}. ${buyback_amount:,.2f} added to $CANDLE buyback pool.",
            },
        )
        
        # Check for Finder's Fee: If load was discovered by someone else, credit them
        load_id = neg.load_id if hasattr(neg, 'load_id') else None
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
                    
                    # Credit Finder's Fee to discoverer's savings ledger
                    from datetime import datetime, timedelta
                    current_price = TokenPriceService.get_candle_price()
                    tokens_earned = finders_fee_usd / current_price if current_price > 0 else 0.0
                    unlock_date = datetime.now() + timedelta(days=180)
                    
                    conn.execute(
                        text("""
                            INSERT INTO webwise.driver_savings_ledger 
                            (driver_mc_number, load_id, amount_usd, amount_candle, unlocks_at, status)
                            VALUES (:mc, :load, :usd, :tokens, :unlock, 'LOCKED')
                        """),
                        {
                            "mc": discoverer_row.mc_number,
                            "load": f"FINDERS_FEE-{load_id}",
                            "usd": finders_fee_usd,
                            "tokens": tokens_earned,
                            "unlock": unlock_date
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
                            "message": f"🎯 SCOUT BONUS: A load you discovered ({neg.origin} → {neg.destination}) was just booked! You've earned ${finders_fee_usd:,.2f} Finder's Fee ({tokens_earned:,.2f} $CANDLE).",
                        }
                    )
        
        # Get trucker info for buyback notification
        trucker_row = conn.execute(
            text("SELECT display_name, mc_number FROM webwise.trucker_profiles WHERE id = :id"),
            {"id": trucker_id}
        ).fetchone()
        trucker_name = trucker_row[0] if trucker_row else None
        mc_number = trucker_row[1] if trucker_row else None
        
        # Trigger buyback notification (community-visible)
        try:
            await BuybackNotificationService.send_buyback_notification(
                final_rate=final_rate,
                buyback_amount=buyback_amount,
                trucker_name=trucker_name,
                mc_number=mc_number,
                origin=neg.origin,
                destination=neg.destination,
            )
        except Exception as e:
            print(f"⚠️  Buyback notification failed: {e}")
    
    # Return success response with HTMX trigger
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content='<div class="text-green-400 font-bold">✅ Load confirmed! Buyback triggered.</div>',
            headers={"HX-Trigger": "contributionUpdated,negotiationUpdated"}
        )
    return {"status": "confirmed", "negotiation_id": negotiation_id}


@router.post("/clients/negotiations/{negotiation_id}/reject", response_class=HTMLResponse)
async def reject_negotiation(negotiation_id: int, request: Request, user: Optional[Dict] = Depends(current_user), db: Session = Depends(get_db)):
    """
    Driver rejects a PENDING_APPROVAL negotiation → marks as LOST.
    """
    if not user or user.get("role") != "client":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify this negotiation belongs to the logged-in driver
    trucker_id = None
    if engine:
        with engine.begin() as conn:
            r = conn.execute(text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"), {"uid": user.get("id")})
            row = r.first()
            trucker_id = row.id if row else None
    
    if not trucker_id:
        raise HTTPException(status_code=403, detail="Trucker profile not found")
    
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    with engine.begin() as conn:
        # Check negotiation ownership and status
        neg = conn.execute(
            text("""
                SELECT n.id, n.trucker_id, n.status
                FROM webwise.negotiations n
                WHERE n.id = :id AND n.trucker_id = :trucker_id
            """),
            {"id": negotiation_id, "trucker_id": trucker_id}
        ).fetchone()
        
        if not neg:
            raise HTTPException(status_code=404, detail="Negotiation not found or access denied")
        
        if neg.status != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Negotiation is not pending approval (current status: {neg.status})")
        
        # Mark as LOST
        conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = 'lost', updated_at = now()
                WHERE id = :id
            """),
            {"id": negotiation_id}
        )
        
        # Create rejection notification
        conn.execute(
            text("""
                INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                VALUES (:trucker_id, :message, 'LOAD_REJECTED', false)
            """),
            {
                "trucker_id": trucker_id,
                "message": "❌ Load rejected. The broker has been notified.",
            },
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content='<div class="text-gray-400">❌ Load rejected.</div>',
            headers={"HX-Trigger": "negotiationUpdated"}
        )
    return {"status": "rejected", "negotiation_id": negotiation_id}


@router.post("/negotiate/{load_id}", response_class=HTMLResponse)
async def start_negotiation(load_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Agent Negotiate: Uses OpenAI to draft a broker negotiation email.
    Returns HTML partial for HTMX to swap into the load card.
    """
    # 1. Get logged-in user and their trucker profile
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get trucker_id from profile
    trucker_result = db.execute(text("""
        SELECT id FROM webwise.trucker_profiles WHERE user_id = :user_id LIMIT 1
    """), {"user_id": user.get("id")})
    trucker_row = trucker_result.first()
    trucker_id = trucker_row[0] if trucker_row else None
    
    # 2. Fetch load details (In V1, from your Mock service or DB)
    # TODO: Replace with actual load lookup from database
    load_data = {
        "id": load_id, 
        "origin": "Elizabeth, NJ", 
        "destination": "Charlotte, NC",
        "price": 2800, 
        "type": "Dry Van"
    }
    
    # 3. AI drafts the email (returns dict with draft, subject, body, and usage)
    result = await AIAgentService.draft_negotiation_email(load_data)
    draft_dict = {
        "subject": result.get("subject", ""),
        "body": result.get("body", result.get("draft", "")),
        "draft": result.get("draft", "")  # Full draft for display
    }
    usage = result.get("usage", {})
    
    # 4. Save to DB using helper function (ORM + token tracking)
    negotiation = save_negotiation(
        db=db,
        load_data=load_data,
        draft=draft_dict,
        trucker_id=trucker_id,
        usage=usage
    )
    
    # 5. Return HTML partial for HTMX (replaces the load card with draft preview)
    return templates.TemplateResponse(
        "public/partials/negotiation_result.html",
        {
            "request": request,
            "draft": draft_dict.get("draft", ""),
            "subject": draft_dict.get("subject", ""),
            "body": draft_dict.get("body", ""),
            "usage": usage,
            "load_id": load_id,
            "negotiation_id": negotiation.id
        }
    )


@router.post("/loads/upload-bol", response_model=LoadResponse)
async def upload_proof_of_delivery(
    load_id: str = Form(...),
    mc_number: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Fetch Load from DB (Pseudo-code: replace 'LoadModel' with your actual DB model)
    # load = db.query(LoadModel).filter(LoadModel.load_board_id == load_id).first()
    # if not load: raise HTTPException(404, "Load not found")

    # 2. Upload to DigitalOcean
    try:
        bol_url = await upload_bol(file, mc_number, load_id)
        if not bol_url:
            raise HTTPException(status_code=500, detail="Failed to upload BOL: upload_bol returned None. Check server logs.")
    except Exception as e:
        import traceback
        error_detail = f"Upload failed: {str(e)}"
        print(f"BOL Upload Error: {error_detail}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_detail)

    # 3. Calculate the 2% Fee (The Green Candle Logic)
    # final_rate = load.final_rate 
    final_rate = 3000.00 # Placeholder until you connect DB
    dispatch_fee = final_rate * 0.02

    # 4. Update DB Records
    # load.bol_url = bol_url
    # load.dispatch_fee_amount = dispatch_fee
    # load.status = LoadStatus.READY_FOR_FUNDING
    # db.commit()

    print(f"✅ BOL Uploaded. Fee Calculated: ${dispatch_fee}")
    
    # ---------------------------------------------------------
    # 3. NEW STEP: Push to Factoring Company
    # ---------------------------------------------------------
    
    # Prepare the data dictionary
    load_data_dict = {
        "load_board_id": load_id,
        "broker_name": "TQL",
        "origin": "NJ",
        "destination": "FL",
        "final_rate": final_rate,
        "dispatch_fee_amount": dispatch_fee
    }
    
    # Send it to the bank
    bank_response = push_invoice_to_factor(load_data_dict, bol_url)
    
    print(f"🏦 BANK SAYS: {bank_response['message']}")
    
    # 4. Credit the Savings Account (The "Golden Handcuffs")
    # Only credit if bank confirms funding
    if bank_response.get('status') == 'success':
        credit_result = credit_driver_savings(db, load_id=load_id, mc_number=mc_number, fee_usd=dispatch_fee)
        if not credit_result:
            print(f"⚠️  WARNING: Failed to credit savings for {mc_number} / {load_id}")
    # ---------------------------------------------------------
    
    # Return mock response for now to test
    return {
        "load_board_id": load_id,
        "mc_number": mc_number,
        "broker_name": "TQL",
        "origin": "NJ",
        "destination": "FL",
        "final_rate": final_rate,
        "id": 1,
        "status": LoadStatus.READY_FOR_FUNDING,
        "bol_url": bol_url,
        "dispatch_fee_amount": dispatch_fee,
        "token_buyback_amount": dispatch_fee,
        "created_at": "2026-02-10T08:00:00",
        "bank_status": bank_response['message']  # Return the bank's confirmation
    }


@router.get("/savings/dashboard/{mc_number}")
def get_driver_savings(mc_number: str, db: Session = Depends(get_db)):
    """
    Returns the 'Bank Account' view for the driver.
    Shows total balance, next unlock date, and recent transaction history.
    """
    # 1. Get the Total Balance (Locked + Unlocked)
    total_query = text("""
        SELECT COALESCE(SUM(amount_candle), 0) as total
        FROM webwise.driver_savings_ledger
        WHERE driver_mc_number = :mc
    """)
    total_result = db.execute(total_query, {"mc": mc_number}).first()
    total_balance = float(total_result.total) if total_result else 0.0

    # 2. Get the 'Next Unlock' date (The carrot on the stick)
    next_unlock_query = text("""
        SELECT unlocks_at
        FROM webwise.driver_savings_ledger
        WHERE driver_mc_number = :mc
          AND status = 'LOCKED'
        ORDER BY unlocks_at ASC
        LIMIT 1
    """)
    next_unlock_result = db.execute(next_unlock_query, {"mc": mc_number}).first()
    next_vesting_date = next_unlock_result.unlocks_at if next_unlock_result else None

    # 3. Calculate days until next unlock (for the countdown)
    days_until_unlock = None
    if next_vesting_date:
        delta = next_vesting_date - datetime.now(next_vesting_date.tzinfo)
        days_until_unlock = max(0, delta.days) if delta.total_seconds() > 0 else 0

    # 4. Get locked vs unlocked breakdown
    locked_query = text("""
        SELECT COALESCE(SUM(amount_candle), 0) as locked_total
        FROM webwise.driver_savings_ledger
        WHERE driver_mc_number = :mc
          AND status = 'LOCKED'
    """)
    locked_result = db.execute(locked_query, {"mc": mc_number}).first()
    locked_balance = float(locked_result.locked_total) if locked_result else 0.0

    unlocked_query = text("""
        SELECT COALESCE(SUM(amount_candle), 0) as unlocked_total
        FROM webwise.driver_savings_ledger
        WHERE driver_mc_number = :mc
          AND status IN ('VESTED', 'CLAIMED')
    """)
    unlocked_result = db.execute(unlocked_query, {"mc": mc_number}).first()
    unlocked_balance = float(unlocked_result.unlocked_total) if unlocked_result else 0.0

    # 5. Get the Transaction History (The proof)
    history_query = text("""
        SELECT 
            id,
            load_id,
            amount_usd,
            amount_candle,
            earned_at,
            unlocks_at,
            status,
            tx_hash
        FROM webwise.driver_savings_ledger
        WHERE driver_mc_number = :mc
        ORDER BY earned_at DESC
        LIMIT 10
    """)
    history_rows = db.execute(history_query, {"mc": mc_number}).fetchall()

    recent_transactions = [
        {
            "load_id": row.load_id,
            "amount_usd": float(row.amount_usd),
            "amount_candle": float(row.amount_candle),
            "earned_date": row.earned_at.isoformat() if row.earned_at else None,
            "unlocks_date": row.unlocks_at.isoformat() if row.unlocks_at else None,
            "status": row.status,
            "tx_hash": row.tx_hash
        }
        for row in history_rows
    ]

    return {
        "mc_number": mc_number,
        "total_candle_balance": total_balance,
        "locked_balance": locked_balance,
        "unlocked_balance": unlocked_balance,
        "next_vesting_date": next_vesting_date.isoformat() if next_vesting_date else None,
        "days_until_unlock": days_until_unlock,
        "recent_transactions": recent_transactions,
        "transaction_count": len(recent_transactions)
    }    

@router.get("/savings-view", response_class=HTMLResponse)
def view_savings_page(request: Request, user: Optional[Dict] = Depends(current_user)):
    """
    Display the driver's savings dashboard page.
    Fetches savings data and renders the HTML template.
    """
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    
    # Get the driver's MC number, reward tier, and wallet address from their profile
    mc_number = None
    dot_number = None
    authority_type = "MC"
    reward_tier = "STANDARD"
    trucker_id = None
    wallet_address = None
    if engine:
        with engine.begin() as conn:
            r = conn.execute(
                text("""
                    SELECT tp.id, tp.mc_number, tp.dot_number, tp.authority_type, tp.reward_tier, tp.wallet_address
                    FROM webwise.trucker_profiles tp
                    WHERE tp.user_id = :uid
                """),
                {"uid": user.get("id")},
            )
            row = r.first()
            if row:
                trucker_id = row.id
                mc_number = row.mc_number
                dot_number = row.dot_number
                authority_type = row.authority_type or "MC"
                reward_tier = row.reward_tier or "STANDARD"
                wallet_address = row.wallet_address
    
    # Initialize portfolio stats (will be empty if no MC or engine)
    from app.services.token_price import TokenPriceService
    portfolio_stats = {
        "cost_basis": 0.0,
        "current_value": 0.0,
        "total_tokens": 0.0,
        "total_roi": 0.0,
        "roi_percentage": 0.0,
        "most_recent_deposit": None,
        "current_price": TokenPriceService.get_candle_price(),
        "gas_equivalent": 0.0,
        "diesel_price": 4.00
    }
    
    # Initialize card eligibility
    from app.services.payments import RevenueService
    card_eligibility = {
        "eligible": False,
        "days_until_eligible": 180,
        "oldest_reward_age_days": 0,
        "vesting_progress_pct": 0.0,
        "card_status": "NOT_STARTED",
        "current_balance_usd": 0.0,
        "card_last_four": None
    }
    
    if not mc_number:
        # No MC number found - show empty state or redirect
        return templates.TemplateResponse(
            "drivers/savings.html",
            {
                "request": request,
                "user": user,
                "error": "No MC number found. Please complete your profile.",
                "savings_data": None,
                "mc_number": None,
                "dot_number": dot_number,
                "authority_type": authority_type,
                "reward_tier": reward_tier,
                "portfolio_stats": portfolio_stats,
                "card_eligibility": card_eligibility
            }
        )
    
    # Fetch savings data using the same logic as the API endpoint
    # Use engine directly (consistent with other routes in this file)
    if not engine:
        return templates.TemplateResponse(
            "drivers/savings.html",
            {
                "request": request,
                "user": user,
                "error": "Database not available.",
                "savings_data": None,
                "mc_number": mc_number,
                "dot_number": dot_number,
                "authority_type": authority_type,
                "portfolio_stats": portfolio_stats,
                "card_eligibility": card_eligibility
            }
        )
    
    with engine.begin() as conn:
        # Get total balance
        total_query = text("""
            SELECT COALESCE(SUM(amount_candle), 0) as total
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
        """)
        total_result = conn.execute(total_query, {"mc": mc_number}).first()
        total_balance = float(total_result.total) if total_result else 0.0

        # Get next unlock date
        next_unlock_query = text("""
            SELECT unlocks_at
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
              AND status = 'LOCKED'
            ORDER BY unlocks_at ASC
            LIMIT 1
        """)
        next_unlock_result = conn.execute(next_unlock_query, {"mc": mc_number}).first()
        next_vesting_date = next_unlock_result.unlocks_at if next_unlock_result else None

        # Calculate days until unlock
        days_until_unlock = None
        if next_vesting_date:
            delta = next_vesting_date - datetime.now(next_vesting_date.tzinfo)
            days_until_unlock = max(0, delta.days) if delta.total_seconds() > 0 else 0

        # Get locked vs unlocked breakdown
        locked_query = text("""
            SELECT COALESCE(SUM(amount_candle), 0) as locked_total
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
              AND status = 'LOCKED'
        """)
        locked_result = conn.execute(locked_query, {"mc": mc_number}).first()
        locked_balance = float(locked_result.locked_total) if locked_result else 0.0

        unlocked_query = text("""
            SELECT COALESCE(SUM(amount_candle), 0) as unlocked_total
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
              AND status IN ('VESTED', 'CLAIMED')
        """)
        unlocked_result = conn.execute(unlocked_query, {"mc": mc_number}).first()
        unlocked_balance = float(unlocked_result.unlocked_total) if unlocked_result else 0.0

        # Get recent transactions
        history_query = text("""
            SELECT 
                id,
                load_id,
                amount_usd,
                amount_candle,
                earned_at,
                unlocks_at,
                status,
                tx_hash
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
            ORDER BY earned_at DESC
            LIMIT 10
        """)
        history_rows = conn.execute(history_query, {"mc": mc_number}).fetchall()

        recent_transactions = [
            {
                "load_id": row.load_id,
                "amount_usd": float(row.amount_usd),
                "amount_candle": float(row.amount_candle),
                "earned_date": row.earned_at.isoformat() if row.earned_at else None,
                "unlocks_date": row.unlocks_at.isoformat() if row.unlocks_at else None,
                "status": row.status,
                "tx_hash": row.tx_hash
            }
            for row in history_rows
        ]

        # Get claimable balance using VestingService
        from app.services.vesting import VestingService
        claimable_balance = VestingService.get_claimable_balance(engine, trucker_id) if trucker_id else 0.0
        
        # Get portfolio stats (cost basis, current value, ROI)
        from app.services.token_price import TokenPriceService
        portfolio_stats = TokenPriceService.get_portfolio_stats(engine, trucker_id) if trucker_id else {
            "cost_basis": 0.0,
            "current_value": 0.0,
            "total_tokens": 0.0,
            "total_roi": 0.0,
            "roi_percentage": 0.0,
            "most_recent_deposit": None,
            "current_price": TokenPriceService.get_candle_price(),
            "gas_equivalent": 0.0,
            "diesel_price": 4.00
        }
        
        # Get card eligibility status
        from app.services.payments import RevenueService
        card_eligibility = RevenueService.get_card_eligibility(engine, trucker_id) if trucker_id else {
            "eligible": False,
            "days_until_eligible": 180,
            "oldest_reward_age_days": 0,
            "vesting_progress_pct": 0.0,
            "card_status": "NOT_STARTED",
            "current_balance_usd": 0.0
        }
        
        # Get current balance and card details if card is active
        if card_eligibility["card_status"] == "ACTIVE" and engine:
            with engine.begin() as conn:
                card_row = conn.execute(
                    text("SELECT current_balance_usd, card_last_four FROM webwise.debit_cards WHERE trucker_id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                if card_row:
                    card_eligibility["current_balance_usd"] = float(card_row[0] or 0)
                    card_eligibility["card_last_four"] = card_row[1]
        
        savings_data = {
            "mc_number": mc_number,
            "total_candle_balance": total_balance,
            "locked_balance": locked_balance,
            "unlocked_balance": unlocked_balance,
            "claimable_balance": claimable_balance,
            "next_vesting_date": next_vesting_date.isoformat() if next_vesting_date else None,
            "days_until_unlock": days_until_unlock,
            "recent_transactions": recent_transactions,
            "transaction_count": len(recent_transactions)
        }
    
    return templates.TemplateResponse(
        "drivers/savings.html",
        {
            "request": request,
            "user": user,
            "savings_data": savings_data,
            "mc_number": mc_number,
            "dot_number": dot_number,
            "authority_type": authority_type,
            "reward_tier": reward_tier,
            "wallet_address": wallet_address,
            "trucker_id": trucker_id,
            "portfolio_stats": portfolio_stats,
            "card_eligibility": card_eligibility
        }
    )


@router.get("/clients/claim/modal", response_class=HTMLResponse)
def claim_modal(request: Request, user: Optional[Dict] = Depends(current_user)):
    """HTMX endpoint: Returns the claim tokens modal."""
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    
    trucker_id = None
    wallet_address = None
    mc_number = None
    claimable_balance = 0.0
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id, mc_number, wallet_address FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        if r:
            trucker_id = r.id
            mc_number = r.mc_number
            wallet_address = r.wallet_address
    
    if trucker_id:
        from app.services.vesting import VestingService
        claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
    
    # Get savings data for display
    savings_data = {"claimable_balance": claimable_balance}
    
    return templates.TemplateResponse(
        "drivers/partials/claim_modal.html",
        {
            "request": request, 
            "savings_data": {"claimable_balance": claimable_balance}, 
            "wallet_address": wallet_address
        }
    )


@router.get("/clients/wallet/setup-modal", response_class=HTMLResponse)
def wallet_setup_modal(request: Request, user: Optional[Dict] = Depends(current_user)):
    """HTMX endpoint: Returns the wallet setup modal."""
    if not user or user.get("role") != "client":
        return HTMLResponse(content="")
    
    return templates.TemplateResponse(
        "drivers/partials/wallet_setup_modal.html",
        {"request": request}
    )


@router.post("/clients/wallet/setup", response_class=HTMLResponse)
async def setup_wallet(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Save wallet address to trucker profile."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    form_data = await request.form()
    wallet_address = form_data.get("wallet_address", "").strip()
    
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    
    # Basic validation (Ethereum or Solana format)
    import re
    eth_pattern = r"^0x[a-fA-F0-9]{40}$"
    solana_pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
    
    if not (re.match(eth_pattern, wallet_address) or re.match(solana_pattern, wallet_address)):
        raise HTTPException(status_code=400, detail="Invalid wallet address format")
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        conn.execute(
            text("""
                UPDATE webwise.trucker_profiles 
                SET wallet_address = :wallet, updated_at = now()
                WHERE id = :id
            """),
            {"wallet": wallet_address, "id": r.id}
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content='<div class="text-green-400 text-sm font-bold p-4">✅ Wallet address saved!</div>',
            headers={"HX-Trigger": "walletUpdated"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.post("/clients/claim/request", response_class=HTMLResponse)
async def submit_claim_request(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Submit a claim request for vested tokens."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    form_data = await request.form()
    wallet_address = form_data.get("wallet_address", "").strip()
    
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    
    trucker_id = None
    mc_number = None
    claimable_balance = 0.0
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id, mc_number FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
        mc_number = r.mc_number
        
        # Get claimable balance
        from app.services.vesting import VestingService
        claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
        
        if claimable_balance <= 0:
            raise HTTPException(status_code=400, detail="No tokens available to claim")
        
        # Create claim request
        conn.execute(
            text("""
                INSERT INTO webwise.claim_requests 
                (trucker_id, amount_candle, wallet_address, status, requested_at)
                VALUES (:trucker_id, :amount, :wallet, 'pending', now())
            """),
            {
                "trucker_id": trucker_id,
                "amount": claimable_balance,
                "wallet": wallet_address
            }
        )
        
        # Update wallet address in profile if different
        conn.execute(
            text("""
                UPDATE webwise.trucker_profiles 
                SET wallet_address = :wallet, updated_at = now()
                WHERE id = :id
            """),
            {"wallet": wallet_address, "id": trucker_id}
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'''
            <div class="bg-green-900/40 border border-green-500 rounded-xl p-6 text-center">
                <div class="text-green-400 text-4xl mb-3">✅</div>
                <div class="text-white font-bold text-lg mb-2">Claim Request Submitted!</div>
                <div class="text-slate-400 text-sm mb-4">
                    Requested: {claimable_balance:,.2f} $CANDLE<br>
                    Wallet: {wallet_address[:10]}...{wallet_address[-8:]}
                </div>
                <div class="text-[10px] text-slate-500">
                    Your request is pending admin approval. You'll be notified when processed.
                </div>
            </div>
            ''',
            headers={"HX-Trigger": "claimSubmitted"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.post("/clients/claim/reinvest", response_class=HTMLResponse)
async def reinvest_tokens(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Re-invest claimable tokens for +5% bonus (extends vesting by 3 months)."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    trucker_id = None
    mc_number = None
    claimable_balance = 0.0
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id, mc_number FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
        mc_number = r.mc_number
        
        # Get claimable balance
        from app.services.vesting import VestingService
        claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
        
        if claimable_balance <= 0:
            raise HTTPException(status_code=400, detail="No tokens available to re-invest")
        
        # Calculate bonus (5% increase)
        bonus_amount = claimable_balance * 0.05
        total_reinvested = claimable_balance + bonus_amount
        
        # Extend vesting by 3 months for all vested entries
        from datetime import timedelta
        conn.execute(
            text("""
                UPDATE webwise.driver_savings_ledger
                SET unlocks_at = unlocks_at + INTERVAL '3 months',
                    amount_candle = amount_candle * 1.05,
                    status = 'LOCKED',
                    updated_at = now()
                WHERE driver_mc_number = :mc
                AND (status = 'VESTED' OR (status = 'LOCKED' AND unlocks_at <= now()))
                AND status != 'CLAIMED'
            """),
            {"mc": mc_number}
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'''
            <div class="bg-gradient-to-r from-amber-900/40 to-yellow-900/40 border border-amber-500 rounded-xl p-6 text-center">
                <div class="text-amber-400 text-4xl mb-3">💎</div>
                <div class="text-white font-bold text-lg mb-2">Diamond Hands! Re-investment Complete</div>
                <div class="text-slate-300 text-sm mb-4">
                    Re-invested: {claimable_balance:,.2f} $CANDLE<br>
                    Bonus Added: +{bonus_amount:,.2f} $CANDLE (+5%)<br>
                    <span class="text-amber-400 font-bold">New Total: {total_reinvested:,.2f} $CANDLE</span>
                </div>
                <div class="text-[10px] text-slate-500">
                    Tokens locked for additional 3 months. Your patience pays off!
                </div>
            </div>
            ''',
            headers={"HX-Trigger": "reinvestComplete"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.get("/clients/leaderboard", response_class=HTMLResponse)
def get_fuel_leaderboard(request: Request, user: Optional[Dict] = Depends(current_user)):
    """HTMX endpoint: Returns the fuel leaderboard partial."""
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    
    from app.services.payments import RevenueService
    leaderboard_data = RevenueService.get_fuel_leaderboard(engine, limit=10)
    
    return templates.TemplateResponse(
        "drivers/partials/leaderboard.html",
        {
            "request": request,
            "leaderboard": leaderboard_data
        }
    )


@router.post("/clients/debit-card/request", response_class=HTMLResponse)
async def request_debit_card(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Request a GC Fuel & Fleet Card (Month 5 feature)."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    trucker_id = None
    mc_number = None
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id, mc_number FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
        mc_number = r.mc_number
    
    # Check eligibility
    from app.services.payments import RevenueService
    eligibility = RevenueService.get_card_eligibility(engine, trucker_id)
    
    if not eligibility["eligible"]:
        return HTMLResponse(
            content=f'''
            <div class="bg-red-900/40 border border-red-500 rounded-xl p-4 text-center">
                <div class="text-red-400 font-bold mb-2">Not Eligible Yet</div>
                <div class="text-slate-300 text-sm">
                    You need {eligibility["days_until_eligible"]} more days to request a card.
                </div>
            </div>
            ''',
            status_code=400
        )
    
    # Check if already requested
    if eligibility["card_status"] in ["REQUESTED", "SHIPPED", "ACTIVE"]:
        return HTMLResponse(
            content=f'''
            <div class="bg-blue-900/40 border border-blue-500 rounded-xl p-4 text-center">
                <div class="text-blue-400 font-bold mb-2">Card Already Requested</div>
                <div class="text-slate-300 text-sm">Status: {eligibility["card_status"]}</div>
            </div>
            ''',
            status_code=400
        )
    
    # Create/update card request
    with engine.begin() as conn:
        # Insert or update card record
        conn.execute(
            text("""
                INSERT INTO webwise.debit_cards (trucker_id, status, requested_at)
                VALUES (:trucker_id, 'REQUESTED', now())
                ON CONFLICT (trucker_id) 
                DO UPDATE SET status = 'REQUESTED', requested_at = now(), updated_at = now()
            """),
            {"trucker_id": trucker_id}
        )
        
        # Create admin notification (for admin dashboard)
        # Note: Admin notifications would typically go to a separate admin_notifications table
        # For now, we'll log it and could send to Slack/Discord webhook
        print(f"🔔 CARD REQUEST: Trucker {trucker_id} (MC: {mc_number}) requested GC Fuel & Fleet Card")
    
    # Return success message
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'''
            <div class="bg-gradient-to-r from-indigo-900/40 to-blue-900/40 border border-indigo-500 rounded-xl p-6 text-center">
                <div class="text-indigo-400 text-4xl mb-3">💳</div>
                <div class="text-white font-bold text-lg mb-2">Card Request Submitted!</div>
                <div class="text-slate-300 text-sm mb-4">
                    Your GC Fuel & Fleet Card request has been received.<br>
                    We'll process your application and ship your card soon.
                </div>
                <div class="text-[10px] text-slate-500">
                    You'll receive a notification when your card ships.
                </div>
            </div>
            ''',
            headers={"HX-Trigger": "cardRequested"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.post("/clients/cards/activate", response_class=HTMLResponse)
async def activate_card(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Activate a shipped card (driver confirms receipt)."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
        
        # Check if card exists and is SHIPPED
        card_check = conn.execute(
            text("SELECT id, status FROM webwise.debit_cards WHERE trucker_id = :trucker_id"),
            {"trucker_id": trucker_id}
        ).fetchone()
        
        if not card_check:
            return HTMLResponse(
                content='<div class="bg-red-900/40 border border-red-500 rounded-xl p-4 text-center text-red-400">No card found.</div>',
                status_code=404
            )
        
        if card_check.status != 'SHIPPED':
            return HTMLResponse(
                content=f'<div class="bg-yellow-900/40 border border-yellow-500 rounded-xl p-4 text-center text-yellow-400">Card is already {card_check.status.lower()}.</div>',
                status_code=400
            )
        
        # Activate the card
        conn.execute(
            text("""
                UPDATE webwise.debit_cards 
                SET status = 'ACTIVE',
                    activated_at = now(),
                    updated_at = now()
                WHERE trucker_id = :trucker_id
            """),
            {"trucker_id": trucker_id}
        )
        
        # Create success notification
        conn.execute(
            text("""
                INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                VALUES (:trucker_id, :message, 'SYSTEM_ALERT', false)
            """),
            {
                "trucker_id": trucker_id,
                "message": "💳 CARD ACTIVATED! Your GC Fuel & Fleet Card is now active and ready to use.",
            }
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content='''
            <div class="bg-gradient-to-r from-green-900/40 to-emerald-900/40 border border-green-500 rounded-xl p-6 text-center">
                <div class="text-green-400 text-4xl mb-3">💳</div>
                <div class="text-white font-bold text-lg mb-2">Card Activated!</div>
                <div class="text-slate-300 text-sm mb-4">
                    Your GC Fuel & Fleet Card is now active and ready to use.
                </div>
                <div class="text-[10px] text-slate-500">
                    You can now transfer tokens to your card balance.
                </div>
            </div>
            ''',
            headers={"HX-Trigger": "cardActivated"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.get("/clients/cards/transfer-modal", response_class=HTMLResponse)
def transfer_modal(request: Request, user: Optional[Dict] = Depends(current_user)):
    """HTMX endpoint: Returns the transfer tokens to card modal."""
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    
    trucker_id = None
    claimable_balance = 0.0
    card_balance = 0.0
    
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if r:
            trucker_id = r.id
            
            # Get claimable balance
            from app.services.vesting import VestingService
            claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
            
            # Get card balance
            card_row = conn.execute(
                text("SELECT current_balance_usd FROM webwise.debit_cards WHERE trucker_id = :trucker_id AND status = 'ACTIVE'"),
                {"trucker_id": trucker_id}
            ).fetchone()
            
            if card_row:
                card_balance = float(card_row[0] or 0)
    
    from app.services.token_price import TokenPriceService
    token_price = TokenPriceService.get_candle_price()
    
    return templates.TemplateResponse(
        "drivers/partials/transfer_modal.html",
        {
            "request": request,
            "claimable_balance": claimable_balance,
            "card_balance": card_balance,
            "token_price": token_price
        }
    )


@router.post("/clients/cards/transfer", response_class=HTMLResponse)
async def transfer_to_card(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Transfer tokens from vault to debit card."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    form_data = await request.form()
    token_amount_str = form_data.get("token_amount", "").strip()
    
    try:
        token_amount = float(token_amount_str)
    except ValueError:
        return HTMLResponse(
            content='<div class="bg-red-900/40 border border-red-500 rounded-xl p-4 text-center text-red-400">Invalid amount. Please enter a number.</div>',
            status_code=400
        )
    
    if token_amount <= 0:
        return HTMLResponse(
            content='<div class="bg-red-900/40 border border-red-500 rounded-xl p-4 text-center text-red-400">Amount must be greater than 0.</div>',
            status_code=400
        )
    
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
    
    # Execute transfer
    from app.services.payments import RevenueService
    result = RevenueService.transfer_to_card(engine, trucker_id, token_amount)
    
    if not result["success"]:
        return HTMLResponse(
            content=f'<div class="bg-red-900/40 border border-red-500 rounded-xl p-4 text-center text-red-400">{result["message"]}</div>',
            status_code=400
        )
    
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=f'''
            <div class="bg-gradient-to-r from-green-900/40 to-emerald-900/40 border border-green-500 rounded-xl p-6 text-center">
                <div class="text-green-400 text-4xl mb-3">💳</div>
                <div class="text-white font-bold text-lg mb-2">Transfer Complete!</div>
                <div class="text-slate-300 text-sm mb-4">
                    {result["message"]}<br>
                    <span class="text-green-400 font-bold">New Card Balance: ${result["new_card_balance"]:,.2f}</span>
                </div>
                <div class="text-[10px] text-slate-500">
                    Your tokens have been converted to USD and loaded to your card.
                </div>
            </div>
            ''',
            headers={"HX-Trigger": "cardBalanceUpdated"}
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.get("/clients/scout-config", response_class=HTMLResponse)
def scout_config(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Scout Extension configuration page - shows API key and setup instructions."""
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    
    trucker_id = None
    api_key = None
    mc_number = None
    dot_number = None
    authority_type = "MC"
    active_identifier = None
    
    if engine:
        with engine.begin() as conn:
            r = conn.execute(
                text("""
                    SELECT id, scout_api_key, mc_number, dot_number, authority_type 
                    FROM webwise.trucker_profiles 
                    WHERE user_id = :uid
                """),
                {"uid": user.get("id")}
            ).fetchone()
            
            if r:
                trucker_id = r.id
                api_key = r.scout_api_key
                mc_number = r.mc_number
                dot_number = r.dot_number
                authority_type = r.authority_type or "MC"
                
                # Determine active identifier for display
                if authority_type == "DOT" and dot_number:
                    active_identifier = f"DOT: {dot_number}"
                elif mc_number:
                    active_identifier = f"MC: {mc_number}"
                elif dot_number:
                    active_identifier = f"DOT: {dot_number}"
                else:
                    active_identifier = "Not configured"
    
    return templates.TemplateResponse(
        "drivers/partials/scout_config.html",
        {
            "request": request,
            "api_key": api_key,
            "trucker_id": trucker_id,
            "mc_number": mc_number,
            "dot_number": dot_number,
            "authority_type": authority_type,
            "active_identifier": active_identifier
        }
    )


@router.post("/clients/scout/generate-api-key", response_class=HTMLResponse)
async def generate_api_key(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Generate or regenerate API key for Scout Extension."""
    if not user or user.get("role") != "client" or not engine:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    import secrets
    
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"),
            {"uid": user.get("id")}
        ).fetchone()
        
        if not r:
            raise HTTPException(status_code=404, detail="Trucker profile not found")
        
        trucker_id = r.id
        
        # Generate new API key (64 character hex string)
        new_api_key = secrets.token_hex(32)
        
        # Update trucker profile
        conn.execute(
            text("""
                UPDATE webwise.trucker_profiles 
                SET scout_api_key = :api_key, updated_at = now()
                WHERE id = :trucker_id
            """),
            {"api_key": new_api_key, "trucker_id": trucker_id}
        )
    
    # Fetch updated profile info for display
    mc_number = None
    dot_number = None
    authority_type = "MC"
    active_identifier = None
    
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                SELECT mc_number, dot_number, authority_type 
                FROM webwise.trucker_profiles 
                WHERE id = :trucker_id
            """),
            {"trucker_id": trucker_id}
        ).fetchone()
        
        if r:
            mc_number = r.mc_number
            dot_number = r.dot_number
            authority_type = r.authority_type or "MC"
            
            if authority_type == "DOT" and dot_number:
                active_identifier = f"DOT: {dot_number}"
            elif mc_number:
                active_identifier = f"MC: {mc_number}"
            elif dot_number:
                active_identifier = f"DOT: {dot_number}"
            else:
                active_identifier = "Not configured"
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "drivers/partials/scout_config.html",
            {
                "request": request,
                "api_key": new_api_key,
                "trucker_id": trucker_id,
                "mc_number": mc_number,
                "dot_number": dot_number,
                "authority_type": authority_type,
                "active_identifier": active_identifier,
                "message": "API key generated successfully!"
            }
        )
    
    return RedirectResponse(url="/savings-view", status_code=303)


@router.get("/clients/referrals", response_class=HTMLResponse)
def referrals_page(request: Request, user: Optional[Dict] = Depends(current_user)):
    """
    Fleet Builder page - Shows referral rewards in $CANDLE tokens.
    Uses dynamic exchange rate to calculate token amounts.
    """
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    
    # Get current token price (dynamic, can fetch from API)
    from app.services.token_price import TokenPriceService
    token_price = TokenPriceService.get_candle_price()
    
    # Calculate referral token amount based on $75 USD reward
    referral_reward_usd = 75.0
    referral_token_amount = TokenPriceService.usd_to_candle(referral_reward_usd)
    
    referrals = []
    monthly_earnings = 0.0
    monthly_earnings_candle = 0.0
    
    if engine:
        with engine.begin() as conn:
            # Get user's referral code
            referral_code = user.get("referral_code")
            
            if referral_code:
                # Get all users referred by this user
                rows = conn.execute(
                    text("""
                        SELECT 
                            u.id,
                            u.email,
                            u.created_at,
                            u.factoring_company,
                            tp.mc_number,
                            tp.display_name
                        FROM webwise.users u
                        LEFT JOIN webwise.trucker_profiles tp ON u.id = tp.user_id
                        WHERE u.referred_by = :ref_code
                        ORDER BY u.created_at DESC
                    """),
                    {"ref_code": referral_code}
                ).fetchall()
                
                for row in rows:
                    # Determine if active (has factoring company set)
                    factoring_status = "ACTIVE" if row.factoring_company else "PENDING"
                    
                    referrals.append({
                        "mc_number": row.mc_number or row.email.split("@")[0],
                        "created_at": row.created_at,
                        "factoring_status": factoring_status
                    })
                    
                    # Calculate monthly earnings (only count ACTIVE referrals)
                    if factoring_status == "ACTIVE":
                        monthly_earnings += referral_reward_usd
                        monthly_earnings_candle += referral_token_amount
    
    return templates.TemplateResponse(
        "drivers/referrals.html",
        {
            "request": request,
            "user": user,
            "referrals": referrals,
            "monthly_earnings": monthly_earnings,
            "monthly_earnings_candle": monthly_earnings_candle,
            "referral_token_amount": referral_token_amount,  # Tokens per referral (e.g., 1,785)
            "token_price": token_price,  # Current $CANDLE price
            "referral_reward_usd": referral_reward_usd  # $75 per referral
        }
    )


@router.get("/savings-test")
def savings_test_endpoint(mc_number: str = "MC_998877"):
    """
    Test endpoint for savings dashboard - no auth required.
    Useful for quick testing without login.
    """
    if not engine:
        return {"error": "Database not available"}
    
    with engine.begin() as conn:
        # Get total balance
        total_query = text("""
            SELECT COALESCE(SUM(amount_candle), 0) as total
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
        """)
        total_result = conn.execute(total_query, {"mc": mc_number}).first()
        total_balance = float(total_result.total) if total_result else 0.0

        # Get next unlock date
        next_unlock_query = text("""
            SELECT unlocks_at
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
              AND status = 'LOCKED'
            ORDER BY unlocks_at ASC
            LIMIT 1
        """)
        next_unlock_result = conn.execute(next_unlock_query, {"mc": mc_number}).first()
        next_vesting_date = next_unlock_result.unlocks_at if next_unlock_result else None

        # Calculate days until unlock
        days_until_unlock = None
        if next_vesting_date:
            delta = next_vesting_date - datetime.now(next_vesting_date.tzinfo)
            days_until_unlock = max(0, delta.days) if delta.total_seconds() > 0 else 0

        # Get recent transactions
        history_query = text("""
            SELECT 
                load_id,
                amount_usd,
                amount_candle,
                earned_at,
                unlocks_at,
                status
            FROM webwise.driver_savings_ledger
            WHERE driver_mc_number = :mc
            ORDER BY earned_at DESC
            LIMIT 5
        """)
        history_rows = conn.execute(history_query, {"mc": mc_number}).fetchall()

        recent_transactions = [
            {
                "load_id": row.load_id,
                "amount_usd": float(row.amount_usd),
                "amount_candle": float(row.amount_candle),
                "earned_date": row.earned_at.isoformat() if row.earned_at else None,
                "unlocks_date": row.unlocks_at.isoformat() if row.unlocks_at else None,
                "status": row.status,
            }
            for row in history_rows
        ]

    return {
        "mc_number": mc_number,
        "total_candle_balance": total_balance,
        "next_vesting_date": next_vesting_date.isoformat() if next_vesting_date else None,
        "days_until_unlock": days_until_unlock,
        "recent_transactions": recent_transactions,
        "note": "Test endpoint - use ?mc_number=MC_XXXXX to test different drivers"
    }