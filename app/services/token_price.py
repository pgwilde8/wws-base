"""
Token Price Service - Fetches current $CANDLE token price from exchange APIs.
"""
import os
from typing import Optional
import httpx


class TokenPriceService:
    """Handles fetching and caching $CANDLE token price."""
    
    # Default fallback price (used if API fails)
    DEFAULT_PRICE = 0.042  # $0.042 per $CANDLE
    
    @staticmethod
    def get_candle_price() -> float:
        """
        Get current $CANDLE token price.
        
        TODO: Implement live API fetch from:
        - CoinGecko: https://api.coingecko.com/api/v3/simple/price?ids=candle&vs_currencies=usd
        - Or your own price oracle
        
        For now, returns default price.
        
        Returns:
            Current price per $CANDLE token in USD
        """
        # TODO: Implement API fetch
        # try:
        #     async with httpx.AsyncClient() as client:
        #         response = await client.get(
        #             "https://api.coingecko.com/api/v3/simple/price",
        #             params={"ids": "candle", "vs_currencies": "usd"}
        #         )
        #         if response.status_code == 200:
        #             data = response.json()
        #             return float(data.get("candle", {}).get("usd", TokenPriceService.DEFAULT_PRICE))
        # except Exception as e:
        #     print(f"⚠️  Token price API failed: {e}")
        
        # For now, return default or check env var for override
        env_price = os.getenv("CANDLE_TOKEN_PRICE")
        if env_price:
            try:
                return float(env_price)
            except ValueError:
                pass
        
        return TokenPriceService.DEFAULT_PRICE
    
    @staticmethod
    def usd_to_candle(usd_amount: float) -> float:
        """
        Convert USD amount to $CANDLE tokens.
        
        Args:
            usd_amount: Amount in USD
        
        Returns:
            Equivalent amount in $CANDLE tokens
        """
        price = TokenPriceService.get_candle_price()
        return usd_amount / price if price > 0 else 0.0
    
    @staticmethod
    def candle_to_usd(candle_amount: float) -> float:
        """
        Convert $CANDLE tokens to USD.
        
        Args:
            candle_amount: Amount in $CANDLE tokens
        
        Returns:
            Equivalent amount in USD
        """
        price = TokenPriceService.get_candle_price()
        return candle_amount * price
    
    @staticmethod
    def get_portfolio_stats(engine, trucker_id: int) -> dict:
        """
        Calculate portfolio statistics for a trucker.
        
        Returns:
            {
                "cost_basis": float,  # Total USD value at deposit
                "current_value": float,  # Total tokens * current price
                "total_tokens": float,  # Total $CANDLE tokens
                "total_roi": float,  # Current value - cost basis
                "roi_percentage": float,  # ROI as percentage
                "most_recent_deposit": dict or None,  # Latest ledger entry with growth calc
                "gas_equivalent": float,  # Net profit converted to gallons of diesel
                "diesel_price": float  # Price per gallon used for calculation
            }
        """
        diesel_price = 4.00  # Standard diesel price
        
        if not engine or not trucker_id:
            return {
                "cost_basis": 0.0,
                "current_value": 0.0,
                "total_tokens": 0.0,
                "total_roi": 0.0,
                "roi_percentage": 0.0,
                "most_recent_deposit": None,
                "current_price": TokenPriceService.get_candle_price(),
                "gas_equivalent": 0.0,
                "diesel_price": diesel_price
            }
        
        try:
            from sqlalchemy import text
            
            with engine.begin() as conn:
                # Get MC number
                mc_row = conn.execute(
                    text("SELECT mc_number FROM webwise.trucker_profiles WHERE id = :trucker_id"),
                    {"trucker_id": trucker_id}
                ).fetchone()
                
                diesel_price = 4.00  # Standard diesel price
                
                if not mc_row or not mc_row[0]:
                    return {
                        "cost_basis": 0.0,
                        "current_value": 0.0,
                        "total_tokens": 0.0,
                        "total_roi": 0.0,
                        "roi_percentage": 0.0,
                        "most_recent_deposit": None,
                        "current_price": TokenPriceService.get_candle_price(),
                        "gas_equivalent": 0.0,
                        "diesel_price": diesel_price
                    }
                
                mc_number = mc_row[0]
                
                # Get portfolio totals
                stats = conn.execute(
                    text("""
                        SELECT 
                            COALESCE(SUM(amount_usd), 0) as cost_basis,
                            COALESCE(SUM(amount_candle), 0) as total_tokens
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                    """),
                    {"mc": mc_number}
                ).fetchone()
                
                cost_basis = float(stats[0] or 0)
                total_tokens = float(stats[1] or 0)
                
                # Calculate current value using live price
                current_price = TokenPriceService.get_candle_price()
                current_value = total_tokens * current_price
                
                # Calculate ROI
                total_roi = current_value - cost_basis
                roi_percentage = (total_roi / cost_basis * 100) if cost_basis > 0 else 0.0
                
                # Calculate Gas Savings Equivalent (Diesel ROI)
                # Standard diesel price: $4.00/gal (hardcoded for now)
                diesel_price = 4.00
                net_profit = max(0.0, total_roi)  # Only show positive profit as "free fuel"
                gas_equivalent = net_profit / diesel_price if diesel_price > 0 else 0.0
                
                # Get most recent deposit
                recent = conn.execute(
                    text("""
                        SELECT 
                            load_id,
                            amount_usd,
                            amount_candle,
                            earned_at,
                            status
                        FROM webwise.driver_savings_ledger
                        WHERE driver_mc_number = :mc
                        ORDER BY earned_at DESC
                        LIMIT 1
                    """),
                    {"mc": mc_number}
                ).fetchone()
                
                most_recent_deposit = None
                if recent:
                    deposit_usd = float(recent[1] or 0)
                    deposit_tokens = float(recent[2] or 0)
                    deposit_value_now = deposit_tokens * current_price
                    deposit_growth = deposit_value_now - deposit_usd
                    deposit_growth_pct = (deposit_growth / deposit_usd * 100) if deposit_usd > 0 else 0.0
                    
                    most_recent_deposit = {
                        "load_id": recent[0],
                        "deposit_usd": deposit_usd,
                        "deposit_tokens": deposit_tokens,
                        "deposit_value_now": deposit_value_now,
                        "deposit_growth": deposit_growth,
                        "deposit_growth_pct": deposit_growth_pct,
                        "earned_at": recent[3],
                        "status": recent[4]
                    }
                
                return {
                    "cost_basis": cost_basis,
                    "current_value": current_value,
                    "total_tokens": total_tokens,
                    "total_roi": total_roi,
                    "roi_percentage": roi_percentage,
                    "most_recent_deposit": most_recent_deposit,
                    "current_price": current_price,
                    "gas_equivalent": gas_equivalent,
                    "diesel_price": diesel_price
                }
        except Exception as e:
            print(f"Error calculating portfolio stats: {e}")
            import traceback
            traceback.print_exc()
            diesel_price = 4.00  # Standard diesel price
            return {
                "cost_basis": 0.0,
                "current_value": 0.0,
                "total_tokens": 0.0,
                "total_roi": 0.0,
                "roi_percentage": 0.0,
                "most_recent_deposit": None,
                "current_price": TokenPriceService.get_candle_price(),
                "gas_equivalent": 0.0,
                "diesel_price": diesel_price
            }
