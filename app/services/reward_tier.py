"""
Reward Tier Service - Calculates buyback amounts based on driver reward tier.

STANDARD tier: 2.5% of final_rate (25% of fee burned)
INCENTIVE tier: 0.8% of final_rate (10% of fee burned)
"""
from typing import Optional


class RewardTierService:
    """Handles reward tier-based buyback calculations."""
    
    STANDARD_BUYBACK_RATE = 0.025  # 2.5% of final_rate
    INCENTIVE_BUYBACK_RATE = 0.01   # 1% of final_rate (10% of 2.5% fee)
    
    @staticmethod
    def calculate_buyback_amount(final_rate: float, reward_tier: Optional[str] = "STANDARD") -> float:
        """
        Calculate buyback amount based on reward tier.
        
        Args:
            final_rate: The final rate of the load
            reward_tier: 'STANDARD' or 'INCENTIVE' (defaults to 'STANDARD')
        
        Returns:
            Buyback amount in USD
        """
        if reward_tier == "INCENTIVE":
            return round(final_rate * RewardTierService.INCENTIVE_BUYBACK_RATE, 2)
        else:
            # Default to STANDARD
            return round(final_rate * RewardTierService.STANDARD_BUYBACK_RATE, 2)
    
    @staticmethod
    def get_buyback_percentage(reward_tier: Optional[str] = "STANDARD") -> float:
        """Get the buyback percentage for a given tier."""
        if reward_tier == "INCENTIVE":
            return RewardTierService.INCENTIVE_BUYBACK_RATE
        return RewardTierService.STANDARD_BUYBACK_RATE
    
    @staticmethod
    def calculate_finders_fee(final_rate: float) -> float:
        """
        Calculate Finder's Fee for the Scout who discovered the load.
        
        Finder's Fee = 5% of the 2.5% platform fee
        Example: $3000 load → $60 platform fee → $3 Finder's Fee
        
        Args:
            final_rate: The final rate of the load
        
        Returns:
            Finder's fee amount in USD
        """
        platform_fee = final_rate * 0.025  # 2.5% platform fee
        finders_fee = platform_fee * 0.05  # 5% of platform fee
        return round(finders_fee, 2)
