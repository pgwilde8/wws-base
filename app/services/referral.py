from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from app.models.negotiation import Negotiation, NegotiationStatus
from app.models.user import User

class ReferralService:
    @staticmethod
    def track_otr_bounty(db: Session, trucker_id: int):
        """
        Checks if this is the driver's first 'WON' load to trigger the $100 bounty.
        """
        win_count = db.query(Negotiation).filter(
            Negotiation.trucker_id == trucker_id,
            Negotiation.status == NegotiationStatus.WON
        ).count()
        
        # If this is their first win, it flags a $100 bounty opportunity
        return 100.00 if win_count == 1 else 0.00

    @staticmethod
    def get_monthly_referral_stats(db: Session):
        """
        Aggregates total bounties and estimated residuals for the admin report.
        Tracks actual first-time wins (not just signups) for accurate bounty calculation.
        """
        # Count drivers who have exactly 1 WON load (first win = $100 bounty)
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM (
                SELECT trucker_id
                FROM webwise.negotiations
                WHERE status = 'won'
                GROUP BY trucker_id
                HAVING COUNT(*) = 1
            ) as first_winners
        """))
        row = result.first()
        first_win_count = row[0] if row else 0
        total_bounties = first_win_count * 100.00
        
        # Calculate residuals: 0.5% of all 'won' load volume
        total_volume = db.query(func.sum(Negotiation.final_rate)).filter(
            Negotiation.status == NegotiationStatus.WON
        ).scalar() or 0
        
        residuals = float(total_volume) * 0.005
        
        # Goal tracking: 20 bounties/month = $2,000
        goal_bounties = 20
        goal_amount = goal_bounties * 100.00
        progress_percent = min(100, (first_win_count / goal_bounties) * 100) if goal_bounties > 0 else 0
        
        return {
            "total_bounties": round(total_bounties, 2),
            "total_residuals": round(residuals, 2),
            "combined_otr_income": round(total_bounties + residuals, 2),
            "first_win_count": first_win_count,
            "goal_bounties": goal_bounties,
            "goal_amount": goal_amount,
            "progress_percent": round(progress_percent, 1),
            "remaining_to_goal": max(0, goal_bounties - first_win_count)
        }

    @staticmethod
    def get_referral_leaderboard(db: Session, limit: int = 10):
        """
        Shows which referral codes (and location codes) are generating the most $100 bounties.
        Tracks by referred_by code → drivers who won their first load.
        Includes location_code for truck stop attribution (e.g., LOMBARDI_01, PITCHER_02).
        """
        # Get referral codes with location codes and count how many drivers they referred who have won their first load
        leaderboard = db.execute(text("""
            SELECT 
                u.referral_code,
                u.location_code,
                COUNT(DISTINCT u2.id) as referred_count,
                COUNT(DISTINCT CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM webwise.negotiations n
                        JOIN webwise.trucker_profiles tp ON n.trucker_id = tp.id
                        WHERE tp.user_id = u2.id AND n.status = 'won'
                    ) THEN u2.id
                END) as referred_with_wins,
                COUNT(DISTINCT CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM webwise.negotiations n
                        JOIN webwise.trucker_profiles tp ON n.trucker_id = tp.id
                        WHERE tp.user_id = u2.id AND n.status = 'won'
                        GROUP BY n.trucker_id
                        HAVING COUNT(*) = 1
                    ) THEN u2.id
                END) as first_win_count
            FROM webwise.users u
            LEFT JOIN webwise.users u2 ON u2.referred_by = u.referral_code
            WHERE u.referral_code IS NOT NULL
            GROUP BY u.referral_code, u.location_code
            HAVING COUNT(DISTINCT u2.id) > 0
            ORDER BY first_win_count DESC, referred_with_wins DESC
            LIMIT :limit
        """), {"limit": limit})
        
        results = []
        for row in leaderboard:
            referral_code = row.referral_code or "N/A"
            location_code = row.location_code or None
            first_wins = row.first_win_count or 0
            bounty_total = first_wins * 100.00
            
            results.append({
                "referral_code": referral_code,
                "location_code": location_code,
                "referred_count": row.referred_count or 0,
                "referred_with_wins": row.referred_with_wins or 0,
                "first_win_count": first_wins,
                "bounty_total": round(bounty_total, 2)
            })
        
        return results