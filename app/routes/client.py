from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.deps import templates, current_user, engine, get_db
from app.services.ai_agent import AIAgentService
from app.services.payments import RevenueService
from app.services.storage import upload_bol
from app.services.factoring import push_invoice_to_factor
from app.services.tokenomics import credit_driver_savings
from app.schemas.load import LoadResponse, LoadStatus

router = APIRouter()


@router.get("/clients/dashboard")
def client_dashboard(request: Request, user: Optional[Dict] = Depends(current_user)):
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    return templates.TemplateResponse("clients/dashboard.html", {"request": request, "user": user})


@router.get("/clients/my-contribution")
def my_contribution(request: Request, user: Optional[Dict] = Depends(current_user)):
    """Per-driver Green Candle contribution. Returns HTML partial for HTMX, JSON otherwise."""
    if not user or user.get("role") != "client":
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "clients/partials/contribution_stats.html",
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
        return templates.TemplateResponse(
            "clients/partials/contribution_stats.html",
            {"request": request, "stats": stats},
        )
    return stats


@router.get("/clients/notifications/poll", response_class=HTMLResponse)
def poll_notifications(request: Request, user: Optional[Dict] = Depends(current_user)):
    """HTMX: every 30s. Returns all unread toasts (replace container so no duplicates)."""
    if not user or user.get("role") != "client" or not engine:
        return HTMLResponse(content="")
    trucker_id = None
    with engine.begin() as conn:
        r = conn.execute(text("SELECT id FROM webwise.trucker_profiles WHERE user_id = :uid"), {"uid": user.get("id")})
        row = r.first()
        trucker_id = row.id if row else None
    if not trucker_id:
        return HTMLResponse(content="")
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                SELECT id, message, notif_type, created_at
                FROM webwise.notifications
                WHERE trucker_id = :trucker_id AND is_read = false
                ORDER BY created_at DESC
                LIMIT 10
            """),
            {"trucker_id": trucker_id},
        )
        rows = r.fetchall()
    notifications = [{"id": row[0], "message": row[1], "notif_type": row[2], "created_at": row[3]} for row in rows]
    if not notifications:
        return HTMLResponse(content="")
    resp = templates.TemplateResponse(
        "clients/partials/notification_list.html",
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


@router.post("/negotiate/{load_id}")
async def start_negotiation(load_id: int):
    # 1. Fetch load details (In V1, from your Mock service)
    load_data = {"id": load_id, "origin": "Elizabeth, NJ", "price": 2800, "type": "Dry Van"}
    
    # 2. AI drafts the email
    email_draft = await AIAgentService.draft_negotiation_email(load_data)
    
    # 3. TODO: Send via SendGrid or save to DB for driver approval
    return {"status": "Draft Created", "preview": email_draft}


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
    
    # Get the driver's MC number from their profile
    mc_number = None
    if engine:
        with engine.begin() as conn:
            r = conn.execute(
                text("""
                    SELECT tp.mc_number 
                    FROM webwise.trucker_profiles tp
                    WHERE tp.user_id = :uid
                """),
                {"uid": user.get("id")},
            )
            row = r.first()
            mc_number = row.mc_number if row else None
    
    if not mc_number:
        # No MC number found - show empty state or redirect
        return templates.TemplateResponse(
            "clients/savings.html",
            {
                "request": request,
                "user": user,
                "error": "No MC number found. Please complete your profile.",
                "savings_data": None
            }
        )
    
    # Fetch savings data using the same logic as the API endpoint
    # Use engine directly (consistent with other routes in this file)
    if not engine:
        return templates.TemplateResponse(
            "clients/savings.html",
            {
                "request": request,
                "user": user,
                "error": "Database not available.",
                "savings_data": None
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

        savings_data = {
            "mc_number": mc_number,
            "total_candle_balance": total_balance,
            "locked_balance": locked_balance,
            "unlocked_balance": unlocked_balance,
            "next_vesting_date": next_vesting_date.isoformat() if next_vesting_date else None,
            "days_until_unlock": days_until_unlock,
            "recent_transactions": recent_transactions,
            "transaction_count": len(recent_transactions)
        }
    
    return templates.TemplateResponse(
        "clients/savings.html",
        {
            "request": request,
            "user": user,
            "savings_data": savings_data
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