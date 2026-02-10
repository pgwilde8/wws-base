from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import text

from app.core.deps import templates, current_user, engine
from app.services.ai_agent import AIAgentService
from app.services.payments import RevenueService

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