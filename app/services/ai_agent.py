import asyncio
from typing import Any

from app.core.deps import openai_client


class AIAgentService:
    @staticmethod
    async def draft_negotiation_email(
        load_data: dict[str, Any],
        driver_current_location: str = "10 miles away",
    ) -> str:
        """Draft a short broker negotiation email. Returns subject + body text."""
        prompt = f"""
        Role: Senior Freight Dispatcher for Green Candle Dispatch.
        Context: Negotiating a {load_data.get('type', 'freight')} load from {load_data.get('origin', 'Origin')} to {load_data.get('destination', 'Destination')}.
        Target Price: ${load_data.get('price', 0) + 300} (Current offer: ${load_data.get('price', 0)}).
        Driver Status: {driver_current_location}.

        Task: Write a professional, punchy email to the broker.
        Ask if the load is still available and if they can meet the target price.
        Format: Subject line and Body only. Keep it under 100 words.
        """
        if not openai_client:
            return "OpenAI not configured. Set OPENAI_API_KEY to enable AI draft."

        def _call_openai() -> str:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional logistics negotiator."},
                    {"role": "user", "content": prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()

        return await asyncio.to_thread(_call_openai)
