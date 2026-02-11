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
        """Per-driver Green Candle contribution: wins and 2% attributed to this trucker."""
        if not engine or trucker_id is None:
            return {"win_count": 0, "total_revenue": 0.0, "candle_contribution_usd": 0.0}
        try:
            with engine.begin() as conn:
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
                candle_contribution_usd = round(total_revenue * 0.02, 2)
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
            with engine.begin() as conn:
                r = conn.execute(
                    text("""
                        SELECT
                            tp.id,
                            tp.display_name,
                            tp.mc_number,
                            tp.carrier_name,
                            COUNT(n.id) AS win_count,
                            COALESCE(SUM(n.final_rate), 0) AS total_revenue,
                            COALESCE(SUM(n.final_rate), 0) * 0.02 AS candle_contribution_usd
                        FROM webwise.trucker_profiles tp
                        LEFT JOIN webwise.negotiations n ON n.trucker_id = tp.id AND n.status = 'won'
                        GROUP BY tp.id, tp.display_name, tp.mc_number, tp.carrier_name
                        HAVING COUNT(n.id) > 0
                        ORDER BY total_revenue DESC
                        LIMIT :limit
                    """),
                    {"limit": limit},
                )
                results = []
                for row in r:
                    results.append({
                        "trucker_id": row.id,
                        "display_name": row.display_name,
                        "mc_number": row.mc_number or "N/A",
                        "carrier_name": row.carrier_name,
                        "win_count": row.win_count or 0,
                        "total_revenue": float(row.total_revenue or 0),
                        "candle_contribution_usd": round(float(row.candle_contribution_usd or 0), 2),
                    })
                return results
        except Exception as e:
            print(f"Error getting trucker contributions: {e}")
            return []
