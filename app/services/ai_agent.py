import asyncio
from typing import Any, Dict, Optional

from app.core.deps import openai_client


class AIAgentService:
    @staticmethod
    async def draft_negotiation_email(
        load_data: dict[str, Any],
        driver_current_location: str = "10 miles away",
    ) -> Dict[str, Any]:
        """
        Draft a short broker negotiation email. Returns dict with draft text and usage stats.
        Returns: {"draft": str, "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}}
        """
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
            return {
                "draft": "OpenAI not configured. Set OPENAI_API_KEY to enable AI draft.",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }

        def _call_openai() -> Dict[str, Any]:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional logistics negotiator."},
                    {"role": "user", "content": prompt},
                ],
            )
            draft_text = (response.choices[0].message.content or "").strip()
            
            # Parse subject and body from draft (format: "Subject: ...\n\nBody: ...")
            subject = ""
            body = draft_text
            if "Subject:" in draft_text:
                parts = draft_text.split("Subject:", 1)
                if len(parts) > 1:
                    subject_body = parts[1].split("Body:", 1) if "Body:" in parts[1] else parts[1].split("\n\n", 1)
                    subject = subject_body[0].strip()
                    body = subject_body[1].strip() if len(subject_body) > 1 else draft_text
            elif "\n\n" in draft_text:
                # Fallback: first line is subject, rest is body
                lines = draft_text.split("\n\n", 1)
                subject = lines[0].replace("Subject:", "").strip()
                body = lines[1] if len(lines) > 1 else draft_text
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
            return {
                "draft": draft_text,  # Full draft for display
                "subject": subject or f"Load Inquiry: {load_data.get('origin', 'Origin')} to {load_data.get('destination', 'Destination')}",
                "body": body,
                "usage": usage
            }

        return await asyncio.to_thread(_call_openai)
