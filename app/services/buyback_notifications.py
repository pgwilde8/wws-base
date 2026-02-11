"""
Buyback Notification Service - Sends community-visible notifications when loads are won.
This is the "Proof of Freight" mechanism that shows real-world buyback pressure.
"""
import os
import httpx
from typing import Optional, Dict, Any


class BuybackNotificationService:
    """Handles sending buyback notifications to Slack/Discord when loads are won."""
    
    @staticmethod
    async def send_buyback_notification(
        final_rate: float,
        buyback_amount: float,
        trucker_name: Optional[str] = None,
        mc_number: Optional[str] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send buyback notification to configured webhooks (Slack/Discord).
        This is the "community-visible" trigger that shows real freight generating buyback pressure.
        
        Returns dict with status of each webhook attempt.
        """
        results = {}
        
        # Slack webhook
        slack_webhook = os.getenv("SLACK_BUYBACK_WEBHOOK")
        if slack_webhook:
            results["slack"] = await BuybackNotificationService._send_slack_notification(
                slack_webhook, final_rate, buyback_amount, trucker_name, mc_number, origin, destination
            )
        
        # Discord webhook
        discord_webhook = os.getenv("DISCORD_BUYBACK_WEBHOOK")
        if discord_webhook:
            results["discord"] = await BuybackNotificationService._send_discord_notification(
                discord_webhook, final_rate, buyback_amount, trucker_name, mc_number, origin, destination
            )
        
        return results
    
    @staticmethod
    async def _send_slack_notification(
        webhook_url: str,
        final_rate: float,
        buyback_amount: float,
        trucker_name: Optional[str],
        mc_number: Optional[str],
        origin: Optional[str],
        destination: Optional[str],
    ) -> Dict[str, Any]:
        """Send formatted message to Slack webhook."""
        try:
            route_info = ""
            if origin and destination:
                route_info = f" | {origin} → {destination}"
            
            driver_info = ""
            if trucker_name:
                driver_info = f" by {trucker_name}"
                if mc_number:
                    driver_info += f" ({mc_number})"
            
            payload = {
                "text": "🕯️ **Green Candle Buyback Triggered**",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🕯️ Green Candle Buyback Triggered"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Load Value:*\n${final_rate:,.2f}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Buyback Amount:*\n${buyback_amount:,.2f}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Driver:*\n{trucker_name or 'N/A'}{f' ({mc_number})' if mc_number else ''}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Route:*\n{origin or 'N/A'} → {destination or 'N/A'}"
                            }
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=5.0)
                response.raise_for_status()
                return {"status": "success", "message": "Slack notification sent"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    async def _send_discord_notification(
        webhook_url: str,
        final_rate: float,
        buyback_amount: float,
        trucker_name: Optional[str],
        mc_number: Optional[str],
        origin: Optional[str],
        destination: Optional[str],
    ) -> Dict[str, Any]:
        """Send formatted embed to Discord webhook."""
        try:
            route_info = ""
            if origin and destination:
                route_info = f"{origin} → {destination}"
            
            driver_info = trucker_name or "N/A"
            if mc_number:
                driver_info += f" ({mc_number})"
            
            embed = {
                "title": "🕯️ Green Candle Buyback Triggered",
                "color": 0x00ff00,  # Green
                "fields": [
                    {"name": "Load Value", "value": f"${final_rate:,.2f}", "inline": True},
                    {"name": "Buyback Amount", "value": f"${buyback_amount:,.2f}", "inline": True},
                    {"name": "Driver", "value": driver_info, "inline": True},
                    {"name": "Route", "value": route_info or "N/A", "inline": True},
                ],
                "timestamp": None,  # Discord will add timestamp
            }
            
            payload = {"embeds": [embed]}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=5.0)
                response.raise_for_status()
                return {"status": "success", "message": "Discord notification sent"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
