"""
Vesting Service - Available Automation Fuel (service credits).
No vesting/lock: all credits are immediately available for platform actions.
"""
from typing import Optional, Dict, Any
from sqlalchemy.engine import Engine
from sqlalchemy import text


class VestingService:
    """Available Automation Fuel—$CANDLE credits for AI agents."""

    @staticmethod
    def get_claimable_balance(engine: Optional[Engine], trucker_id: int) -> float:
        """Available $CANDLE balance for automation. Alias for get_available_service_balance."""
        return VestingService.get_available_service_balance(engine, trucker_id)

    @staticmethod
    def get_available_service_balance(engine: Optional[Engine], trucker_id: int) -> float:
        """
        Total Available Fuel: sum of CREDITED (positive) + CONSUMED (negative).
        All earned credits are immediately available—no lock or maturity period.
        """
        if not engine or not trucker_id:
            return 0.0
        try:
            with engine.begin() as conn:
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                if not mc_row or not mc_row[0]:
                    return 0.0
                mc_number = mc_row[0]
                # CREDITED = positive. CONSUMED = negative. Sum = available.
                # LEGACY: VESTED/LOCKED statuses removed - credits are immediate-use only
                result = conn.execute(
                    text("""
                        SELECT COALESCE(SUM(amount_candle), 0) as balance
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                          AND status IN ('CREDITED', 'CONSUMED')
                    """),
                    {"mc": mc_number}
                ).fetchone()
                return float(result[0] or 0.0)
        except Exception as e:
            print(f"Error calculating available balance: {e}")
            return 0.0

    @staticmethod
    def get_vesting_stats(engine: Optional[Engine], trucker_id: int) -> Dict[str, Any]:
        """
        Service credit stats for Automation Fuel model.
        Returns: total_candle_balance, claimable_balance, consumed_balance.
        """
        if not engine or not trucker_id:
            return {
                "total_candle_balance": 0.0,
                "claimable_balance": 0.0,
                "consumed_balance": 0.0,
            }
        try:
            with engine.begin() as conn:
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                if not mc_row or not mc_row[0]:
                    return {"total_candle_balance": 0.0, "claimable_balance": 0.0, "consumed_balance": 0.0}
                mc_number = mc_row[0]
                stats = conn.execute(
                    text("""
                        SELECT
                            COALESCE(SUM(CASE WHEN amount_candle > 0 THEN amount_candle ELSE 0 END), 0) as total_credits,
                            COALESCE(SUM(CASE WHEN status = 'CONSUMED' THEN ABS(amount_candle) ELSE 0 END), 0) as consumed_balance,
                            COALESCE(SUM(amount_candle), 0) as available_balance
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                          AND status IN ('CREDITED', 'CONSUMED')
                    """),
                    {"mc": mc_number}
                ).fetchone()
                total_credits = float(stats[0] or 0)
                consumed = float(stats[1] or 0)
                available = float(stats[2] or 0)
                return {
                    "total_candle_balance": total_credits,
                    "claimable_balance": available,
                    "available_service_balance": available,
                    "consumed_balance": consumed,
                }
        except Exception as e:
            print(f"Error getting fuel stats: {e}")
            return {"total_candle_balance": 0.0, "claimable_balance": 0.0, "consumed_balance": 0.0}

    @staticmethod
    def mark_vested_entries(engine: Optional[Engine], mc_number: str) -> int:
        """No-op: vesting removed. Kept for API compatibility."""
        return 0
