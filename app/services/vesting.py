"""
Vesting Service - Calculates claimable balances and manages vesting logic.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.engine import Engine
from sqlalchemy import text


class VestingService:
    """Handles vesting period calculations and claimable balance logic."""
    
    @staticmethod
    def get_claimable_balance(engine: Optional[Engine], trucker_id: int) -> float:
        """
        Calculate the total amount of $CANDLE that is ready to claim.
        
        Criteria:
        - Status is 'VESTED' (unlock date has passed)
        - OR status is 'LOCKED' but unlocks_at <= now()
        
        Args:
            engine: Database engine
            trucker_id: The trucker profile ID
        
        Returns:
            Total claimable balance in $CANDLE tokens
        """
        if not engine or not trucker_id:
            return 0.0
        
        try:
            with engine.begin() as conn:
                # Get MC number from trucker profile
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                
                if not mc_row or not mc_row[0]:
                    return 0.0
                
                mc_number = mc_row[0]
                
                # Calculate claimable balance: VESTED entries + LOCKED entries where unlock date has passed
                result = conn.execute(
                    text("""
                        SELECT COALESCE(SUM(amount_candle), 0) as claimable
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                        AND (
                            status = 'VESTED'
                            OR (status = 'LOCKED' AND unlocks_at <= now())
                        )
                        AND status != 'CLAIMED'
                    """),
                    {"mc": mc_number}
                ).fetchone()
                
                return float(result[0] or 0.0)
        except Exception as e:
            print(f"Error calculating claimable balance: {e}")
            return 0.0
    
    @staticmethod
    def get_vesting_stats(engine: Optional[Engine], trucker_id: int) -> Dict[str, Any]:
        """
        Get comprehensive vesting statistics for a trucker.
        
        Returns:
            {
                "total_earned": float,
                "locked_balance": float,
                "vested_balance": float,
                "claimable_balance": float,
                "claimed_balance": float
            }
        """
        if not engine or not trucker_id:
            return {
                "total_earned": 0.0,
                "locked_balance": 0.0,
                "vested_balance": 0.0,
                "claimable_balance": 0.0,
                "claimed_balance": 0.0
            }
        
        try:
            with engine.begin() as conn:
                # Get MC number
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                
                if not mc_row or not mc_row[0]:
                    return {
                        "total_earned": 0.0,
                        "locked_balance": 0.0,
                        "vested_balance": 0.0,
                        "claimable_balance": 0.0,
                        "claimed_balance": 0.0
                    }
                
                mc_number = mc_row[0]
                
                # Get all balances
                stats = conn.execute(
                    text("""
                        SELECT 
                            COALESCE(SUM(amount_candle), 0) as total_earned,
                            COALESCE(SUM(CASE WHEN status = 'LOCKED' AND unlocks_at > now() THEN amount_candle ELSE 0 END), 0) as locked_balance,
                            COALESCE(SUM(CASE WHEN status = 'VESTED' OR (status = 'LOCKED' AND unlocks_at <= now()) THEN amount_candle ELSE 0 END), 0) as vested_balance,
                            COALESCE(SUM(CASE WHEN status = 'CLAIMED' THEN amount_candle ELSE 0 END), 0) as claimed_balance
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                    """),
                    {"mc": mc_number}
                ).fetchone()
                
                total_earned = float(stats[0] or 0)
                locked_balance = float(stats[1] or 0)
                vested_balance = float(stats[2] or 0)
                claimed_balance = float(stats[3] or 0)
                
                # Claimable = vested but not yet claimed
                claimable_balance = VestingService.get_claimable_balance(engine, trucker_id)
                
                return {
                    "total_earned": total_earned,
                    "locked_balance": locked_balance,
                    "vested_balance": vested_balance,
                    "claimable_balance": claimable_balance,
                    "claimed_balance": claimed_balance
                }
        except Exception as e:
            print(f"Error getting vesting stats: {e}")
            return {
                "total_earned": 0.0,
                "locked_balance": 0.0,
                "vested_balance": 0.0,
                "claimable_balance": 0.0,
                "claimed_balance": 0.0
            }
    
    @staticmethod
    def mark_vested_entries(engine: Optional[Engine], mc_number: str) -> int:
        """
        Auto-update LOCKED entries to VESTED when unlock date passes.
        This should be called periodically (cron job or background task).
        
        Returns:
            Number of entries updated
        """
        if not engine:
            return 0
        
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        UPDATE webwise.driver_savings_ledger
                        SET status = 'VESTED'
                        WHERE driver_mc_number = :mc
                        AND status = 'LOCKED'
                        AND unlocks_at <= now()
                    """),
                    {"mc": mc_number}
                )
                return result.rowcount
        except Exception as e:
            print(f"Error marking vested entries: {e}")
            return 0
