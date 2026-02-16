from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.negotiation import Negotiation, NegotiationStatus


class RevenueService:
    """Non-speculative buy pressure: 2% of WON load revenue = $CANDLE buyback."""

    @staticmethod
    def get_weekly_buyback_stats(db: Session) -> dict[str, Any]:
        """Calculate total 'Win' revenue and the 2% network fee (for Transak buyback)."""
        try:
            stats = (
                db.query(
                    func.count(Negotiation.id).label("total_wins"),
                    func.sum(Negotiation.final_rate).label("total_revenue"),
                )
                .filter(Negotiation.status == NegotiationStatus.WON)
                .one()
            )
        except Exception:
            return {
                "win_count": 0,
                "total_revenue": 0.0,
                "candle_buyback_usd": 0.0,
            }
        total_revenue = float(stats.total_revenue or 0.0)
        network_fee = total_revenue * 0.02
        return {
            "win_count": stats.total_wins or 0,
            "total_revenue": total_revenue,
            "candle_buyback_usd": round(network_fee, 2),
        }

    @staticmethod
    def get_buyback_stats_from_engine(engine: Optional[Engine]) -> dict[str, Any]:
        """Raw-SQL fallback when ORM/Session not available (e.g. negotiations in webwise)."""
        if not engine:
            return {"win_count": 0, "total_revenue": 0.0, "candle_buyback_usd": 0.0}
        try:
            with engine.begin() as conn:
                r = conn.execute(
                    text("""
                        SELECT
                            COUNT(*) AS total_wins,
                            COALESCE(SUM(final_rate), 0) AS total_revenue
                        FROM webwise.negotiations
                        WHERE status = 'won'
                    """)
                )
                row = r.one()
                total_revenue = float(row.total_revenue or 0)
                win_count = row.total_wins or 0
                candle_buyback_usd = round(total_revenue * 0.02, 2)
                return {
                    "win_count": win_count,
                    "total_revenue": total_revenue,
                    "candle_buyback_usd": candle_buyback_usd,
                }
        except Exception:
            return {"win_count": 0, "total_revenue": 0.0, "candle_buyback_usd": 0.0}

    @staticmethod
    def get_trucker_contribution(engine: Optional[Engine], trucker_id: int) -> dict[str, Any]:
        """Per-driver Green Candle contribution: wins and tier-based buyback attributed to this trucker."""
        if not engine or trucker_id is None:
            return {"win_count": 0, "total_revenue": 0.0, "candle_contribution_usd": 0.0}
        try:
            from app.services.reward_tier import RewardTierService
            
            with engine.begin() as conn:
                # Get reward tier
                tier_row = conn.execute(
                    text("SELECT reward_tier FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                reward_tier = tier_row[0] if tier_row and tier_row[0] else "STANDARD"
                
                # Get wins and revenue
                r = conn.execute(
                    text("""
                        SELECT
                            COUNT(*) AS total_wins,
                            COALESCE(SUM(final_rate), 0) AS total_revenue
                        FROM webwise.negotiations
                        WHERE status = 'won' AND trucker_id = :trucker_id
                    """),
                    {"trucker_id": trucker_id},
                )
                row = r.one()
                total_revenue = float(row.total_revenue or 0)
                win_count = row.total_wins or 0
                
                # Calculate contribution based on tier
                buyback_rate = RewardTierService.get_buyback_percentage(reward_tier)
                candle_contribution_usd = round(total_revenue * buyback_rate, 2)
                
                return {
                    "win_count": win_count,
                    "total_revenue": total_revenue,
                    "candle_contribution_usd": candle_contribution_usd,
                }
        except Exception:
            return {"win_count": 0, "total_revenue": 0.0, "candle_contribution_usd": 0.0}

    @staticmethod
    def get_all_trucker_contributions(engine: Optional[Engine], limit: int = 10) -> list[dict[str, Any]]:
        """
        Get contribution stats for all truckers (leaderboard-style).
        Returns list sorted by total revenue descending.
        """
        if not engine:
            return []
        try:
            from app.services.reward_tier import RewardTierService
            
            with engine.begin() as conn:
                r = conn.execute(
                    text("""
                        SELECT
                            tp.id,
                            tp.display_name,
                            tp.mc_number,
                            tp.carrier_name,
                            tp.reward_tier,
                            COUNT(n.id) AS win_count,
                            COALESCE(SUM(n.final_rate), 0) AS total_revenue
                        FROM webwise.trucker_profiles tp
                        LEFT JOIN webwise.negotiations n ON n.trucker_id = tp.id AND n.status = 'won'
                        GROUP BY tp.id, tp.display_name, tp.mc_number, tp.carrier_name, tp.reward_tier
                        HAVING COUNT(n.id) > 0
                        ORDER BY total_revenue DESC
                        LIMIT :limit
                    """),
                    {"limit": limit},
                )
                results = []
                for row in r:
                    reward_tier = row.reward_tier or "STANDARD"
                    total_revenue = float(row.total_revenue or 0)
                    buyback_rate = RewardTierService.get_buyback_percentage(reward_tier)
                    candle_contribution_usd = round(total_revenue * buyback_rate, 2)
                    
                    results.append({
                        "trucker_id": row.id,
                        "display_name": row.display_name,
                        "mc_number": row.mc_number or "N/A",
                        "carrier_name": row.carrier_name,
                        "win_count": row.win_count or 0,
                        "total_revenue": total_revenue,
                        "candle_contribution_usd": candle_contribution_usd,
                    })
                return results
        except Exception as e:
            print(f"Error getting trucker contributions: {e}")
            return []

    @staticmethod
    def get_fuel_leaderboard(engine: Optional[Engine], limit: int = 10) -> list[dict[str, Any]]:
        """
        Calculate fuel leaderboard based on net profit (ROI) converted to gallons of diesel.
        
        For each driver:
        - Calculate cost_basis (total USD deposited)
        - Calculate current_value (total tokens * current price)
        - Calculate net_profit = current_value - cost_basis (only positive)
        - Convert to gallons: net_profit / diesel_price
        
        Returns top drivers sorted by gallons earned descending.
        """
        if not engine:
            return []
        
        try:
            from app.services.token_price import TokenPriceService
            
            diesel_price = 4.00  # Standard diesel price
            current_price = TokenPriceService.get_candle_price()
            
            with engine.begin() as conn:
                # Get all drivers with savings ledger entries
                r = conn.execute(
                    text("""
                        SELECT 
                            tp.id AS trucker_id,
                            tp.display_name,
                            tp.mc_number,
                            tp.carrier_name,
                            COALESCE(SUM(dsl.amount_usd), 0) AS cost_basis,
                            COALESCE(SUM(dsl.amount_candle), 0) AS total_tokens
                        FROM webwise.trucker_profiles tp
                        INNER JOIN webwise.driver_savings_ledger dsl ON dsl.driver_mc_number = tp.mc_number
                        GROUP BY tp.id, tp.display_name, tp.mc_number, tp.carrier_name
                        HAVING SUM(dsl.amount_usd) > 0
                        ORDER BY total_tokens DESC
                    """)
                )
                
                results = []
                for row in r:
                    cost_basis = float(row.cost_basis or 0)
                    total_tokens = float(row.total_tokens or 0)
                    
                    # Calculate current value and net profit
                    current_value = total_tokens * current_price
                    net_profit = max(0.0, current_value - cost_basis)  # Only positive profit counts
                    
                    # Convert to gallons
                    total_gallons_earned = net_profit / diesel_price if diesel_price > 0 else 0.0
                    
                    # Only include drivers with positive gallons
                    if total_gallons_earned > 0:
                        results.append({
                            "trucker_id": row.trucker_id,
                            "display_name": row.display_name or "Unknown",
                            "mc_number": row.mc_number or "N/A",
                            "carrier_name": row.carrier_name,
                            "cost_basis": cost_basis,
                            "current_value": current_value,
                            "net_profit": net_profit,
                            "total_gallons_earned": round(total_gallons_earned, 1),
                        })
                
                # Sort by gallons descending and limit
                results.sort(key=lambda x: x["total_gallons_earned"], reverse=True)
                return results[:limit]
                
        except Exception as e:
            print(f"Error getting fuel leaderboard: {e}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def get_card_eligibility(engine: Optional[Engine], trucker_id: int) -> dict[str, Any]:
        """
        Check if a trucker is eligible to request a debit card.
        Automation Fuel model: eligible when they have Available Fuel (claimable_balance > 0).
        """
        if not engine or not trucker_id:
            return {
                "eligible": False,
                "days_until_eligible": 0,
                "oldest_reward_age_days": 0,
                "vesting_progress_pct": 0.0,
                "card_status": "NOT_STARTED"
            }
        try:
            from app.services.vesting import VestingService
            with engine.begin() as conn:
                card_row = conn.execute(
                    text("SELECT status FROM webwise.debit_cards WHERE trucker_id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
            card_status = card_row[0] if card_row else "NOT_STARTED"
            claimable = VestingService.get_claimable_balance(engine, trucker_id)
            eligible = claimable > 0 and card_status == "NOT_STARTED"
            return {
                "eligible": eligible,
                "days_until_eligible": 0,
                "oldest_reward_age_days": 0,
                "vesting_progress_pct": 100.0 if eligible else 0.0,
                "card_status": card_status
            }
                
        except Exception as e:
            print(f"Error checking card eligibility: {e}")
            import traceback
            traceback.print_exc()
            return {
                "eligible": False,
                "days_until_eligible": 180,
                "oldest_reward_age_days": 0,
                "vesting_progress_pct": 0.0,
                "card_status": "NOT_STARTED"
            }

    @staticmethod
    def transfer_to_card(engine: Optional[Engine], trucker_id: int, token_amount: float) -> dict[str, Any]:
        """
        Transfer $CANDLE tokens from vault to debit card balance.
        
        Process:
        1. Verify trucker has ACTIVE card
        2. Verify token_amount <= claimable_balance
        3. Get current token price
        4. Calculate USD amount
        5. Update card balance
        6. Create transaction record
        7. Deduct tokens from savings ledger (mark as CLAIMED)
        
        Args:
            engine: Database engine
            trucker_id: Trucker profile ID
            token_amount: Amount of $CANDLE tokens to transfer
        
        Returns:
            {
                "success": bool,
                "usd_amount": float,
                "new_card_balance": float,
                "message": str
            }
        """
        if not engine or not trucker_id or token_amount <= 0:
            return {
                "success": False,
                "usd_amount": 0.0,
                "new_card_balance": 0.0,
                "message": "Invalid parameters"
            }
        
        try:
            from app.services.token_price import TokenPriceService
            from app.services.vesting import VestingService
            
            with engine.begin() as conn:
                # 1. Verify card exists and is ACTIVE
                card_row = conn.execute(
                    text("SELECT id, current_balance_usd, status FROM webwise.debit_cards WHERE trucker_id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                
                if not card_row:
                    return {
                        "success": False,
                        "usd_amount": 0.0,
                        "new_card_balance": 0.0,
                        "message": "No debit card found. Please request a card first."
                    }
                
                if card_row.status != 'ACTIVE':
                    return {
                        "success": False,
                        "usd_amount": 0.0,
                        "new_card_balance": 0.0,
                        "message": f"Card is not active. Current status: {card_row.status}"
                    }
                
                debit_card_id = card_row.id
                current_card_balance = float(card_row.current_balance_usd or 0)
                
                # 2. Verify claimable balance
                claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
                
                if token_amount > claimable_balance:
                    return {
                        "success": False,
                        "usd_amount": 0.0,
                        "new_card_balance": current_card_balance,
                        "message": f"Insufficient balance. Available: {claimable_balance:,.2f} $CANDLE"
                    }
                
                # 3. Get current token price
                token_price = TokenPriceService.get_candle_price()
                usd_amount = token_amount * token_price
                
                # 4. Get MC number for ledger updates
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                
                if not mc_row or not mc_row[0]:
                    return {
                        "success": False,
                        "usd_amount": 0.0,
                        "new_card_balance": current_card_balance,
                        "message": "Trucker profile not found"
                    }
                
                mc_number = mc_row[0]
                
                # 5. Update card balance
                new_card_balance = current_card_balance + usd_amount
                conn.execute(
                    text("""
                        UPDATE webwise.debit_cards 
                        SET current_balance_usd = :balance,
                            updated_at = now()
                        WHERE id = :card_id
                    """),
                    {"balance": new_card_balance, "card_id": debit_card_id}
                )
                
                # 6. Create transaction record
                conn.execute(
                    text("""
                        INSERT INTO webwise.debit_card_transactions 
                        (debit_card_id, trucker_id, transaction_type, token_amount, usd_amount, token_price, status, description)
                        VALUES (:card_id, :trucker_id, 'LOAD', :token_amount, :usd_amount, :token_price, 'COMPLETED', :description)
                    """),
                    {
                        "card_id": debit_card_id,
                        "trucker_id": trucker_id,
                        "token_amount": token_amount,
                        "usd_amount": usd_amount,
                        "token_price": token_price,
                        "description": f"Transferred {token_amount:,.2f} $CANDLE to card balance"
                    }
                )
                
                # 7. Deduct tokens from savings ledger (mark vested entries as CLAIMED)
                # Mark oldest vested entries first (FIFO) until we've covered the token_amount
                remaining = token_amount
                ledger_rows = conn.execute(
                    text("""
                        SELECT id, amount_candle
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                        AND status IN ('VESTED', 'LOCKED')
                        AND unlocks_at <= now()
                        ORDER BY earned_at ASC
                    """),
                    {"mc": mc_number}
                ).fetchall()
                
                for row in ledger_rows:
                    if remaining <= 0:
                        break
                    entry_amount = float(row.amount_candle)
                    if entry_amount <= remaining:
                        # Mark entire entry as claimed
                        conn.execute(
                            text("UPDATE webwise.driver_savings_ledger SET status = 'CLAIMED', updated_at = now() WHERE id = :id"),
                            {"id": row.id}
                        )
                        remaining -= entry_amount
                    else:
                        # Partial claim - mark full entry for simplicity
                        conn.execute(
                            text("UPDATE webwise.driver_savings_ledger SET status = 'CLAIMED', updated_at = now() WHERE id = :id"),
                            {"id": row.id}
                        )
                        remaining = 0
                
                # Create notification
                conn.execute(
                    text("""
                        INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                        VALUES (:trucker_id, :message, 'SYSTEM_ALERT', false)
                    """),
                    {
                        "trucker_id": trucker_id,
                        "message": f"💳 ${usd_amount:,.2f} loaded to your GC Fuel & Fleet Card! ({token_amount:,.2f} $CANDLE @ ${token_price:.4f}/token)",
                    }
                )
                
                return {
                    "success": True,
                    "usd_amount": usd_amount,
                    "new_card_balance": new_card_balance,
                    "message": f"Successfully transferred {token_amount:,.2f} $CANDLE (${usd_amount:,.2f}) to card"
                }
                
        except Exception as e:
            print(f"Error transferring to card: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "usd_amount": 0.0,
                "new_card_balance": 0.0,
                "message": f"Transfer failed: {str(e)}"
            }
