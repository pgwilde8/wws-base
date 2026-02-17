"""
Chat service using OpenAI Responses API for frontend chat widget.
Handles conversation threading and includes system prompt for Green Candle Dispatch.
"""
import os
from pathlib import Path
from typing import Optional, Dict
from fastapi import HTTPException, status
from openai import OpenAI

# Load system prompt from file
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_SYSTEM_PROMPT_PATH = _BASE_DIR / "docs" / "chat-agent-system-prompt-responses-api.md"

def _load_system_prompt() -> str:
    """Load the system prompt from the markdown file."""
    try:
        if _SYSTEM_PROMPT_PATH.exists():
            content = _SYSTEM_PROMPT_PATH.read_text()
            # Extract just the system prompt section (skip markdown headers)
            lines = content.split("\n")
            in_prompt = False
            prompt_lines = []
            for line in lines:
                if "## System Prompt" in line:
                    in_prompt = True
                    continue
                if in_prompt and line.startswith("##"):
                    break
                if in_prompt:
                    prompt_lines.append(line)
            return "\n".join(prompt_lines).strip()
    except Exception:
        pass
    
    # Fallback: return a minimal prompt if file not found
    return """You are a friendly assistant for Green Candle Dispatch—AI dispatch for owner-operators. 
Help drivers understand the service: AI scans load boards 24/7, negotiates rates, handles paperwork. 
Flat 2% fee only after funding. Guide drivers to sign up at /beta/apply or /register. 
Be friendly, direct, trucker-focused. Don't oversell."""

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Model to use (update when Responses API model name is confirmed)
RESPONSES_MODEL = os.getenv("RESPONSES_MODEL", "gpt-4o")  # Update to "gpt-5" when available


def run_responses_chat(
    message: str,
    response_id: Optional[str] = None,
    greeting: bool = False,
    use_fallback: bool = True
) -> Dict:
    """
    Send a message to OpenAI Responses API and get a reply.
    
    Args:
        message: User's message (empty string for greeting)
        response_id: Previous response ID for conversation threading (None for new conversation)
        greeting: If True, send a greeting message instead of user message
    
    Returns:
        Dict with:
            - reply: Assistant's response text
            - response_id: Response ID for threading (use in next call)
            - greeting: Optional greeting message if this was a greeting request
    """
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI client not configured"
        )
    
    if not message and not greeting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message required"
        )
    
    if len(message) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message too long (max 2000 characters)"
        )
    
    # Load system prompt
    system_prompt = _load_system_prompt()
    
    # Build input messages
    input_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]
    
    # Add greeting or user message
    if greeting:
        # For greeting, ask the AI to introduce itself
        input_messages.append({
            "role": "user",
            "content": "Introduce yourself and ask how you can help. Be friendly and mention we're Green Candle Dispatch—AI dispatch for truckers."
        })
    else:
        input_messages.append({
            "role": "user",
            "content": message.strip()
        })
    
    # Always use fallback for now (Responses API not available yet)
    # When Responses API is available, remove this and uncomment the API call below
    if use_fallback:
        from app.core.chat_responses_fallback import run_chat_completions
        # Map response_id to conversation_id for fallback
        return run_chat_completions(
            message=message,
            conversation_id=response_id,  # Fallback uses conversation_id
            greeting=greeting
        )
    
    # TODO: Uncomment when Responses API is available
    # When Responses API is ready, uncomment the code below and remove the fallback above
    #
    # try:
    #     # Call Responses API
    #     # Note: Update API call when Responses API is officially released
    #     # This is based on the expected structure from OpenAI documentation
    #     response = openai_client.responses.create(
    #         model=RESPONSES_MODEL,
    #         store=True,  # Remember conversation
    #         input=input_messages,
    #         previous_response_id=response_id  # Thread the conversation
    #     )
    #     
    #     # Extract reply from response
    #     # Response structure may vary - adjust based on actual API response
    #     reply_text = ""
    #     if hasattr(response, "output") and response.output:
    #         # Handle different response formats
    #         if isinstance(response.output, str):
    #             reply_text = response.output
    #         elif isinstance(response.output, list):
    #             for item in response.output:
    #                 if isinstance(item, dict) and item.get("role") == "assistant":
    #                     content = item.get("content", "")
    #                     if isinstance(content, str):
    #                         reply_text = content
    #                     elif isinstance(content, list):
    #                         # Handle content blocks
    #                         for block in content:
    #                             if isinstance(block, dict) and block.get("type") == "text":
    #                                 reply_text += block.get("text", "")
    #                     break
    #     
    #     # Fallback: try common response attributes
    #     if not reply_text:
    #         if hasattr(response, "text"):
    #             reply_text = response.text
    #         elif hasattr(response, "content"):
    #             reply_text = str(response.content)
    #         else:
    #             reply_text = str(response)
    #     
    #     reply_text = reply_text.strip()
    #     
    #     if not reply_text:
    #         reply_text = "Sorry, I didn't get a response. Can you try asking again?"
    #     
    #     result = {
    #         "reply": reply_text,
    #         "response_id": getattr(response, "id", response_id)  # Use response.id for threading
    #     }
    #     
    #     # Add greeting flag if this was a greeting request
    #     if greeting:
    #         result["greeting"] = True
    #     
    #     return result
    #     
    # except Exception as e:
    #     # Handle API errors gracefully
    #     error_msg = str(e)
    #     if "rate limit" in error_msg.lower():
    #         raise HTTPException(
    #             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #             detail="Too many requests. Please try again in a moment."
    #         )
    #     elif "invalid" in error_msg.lower() or "not found" in error_msg.lower():
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"Invalid request: {error_msg}"
    #         )
    #     else:
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Chat service error: {error_msg}"
    #         )
    
    # This should never be reached since fallback always returns
    # But keeping as safety net
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Chat service temporarily unavailable. Please try again."
    )


def get_greeting(use_fallback: bool = True) -> Dict:
    """
    Get a greeting message for new chat sessions.
    
    Returns:
        Dict with greeting message and response_id for threading
    """
    return run_responses_chat(message="", greeting=True, use_fallback=use_fallback)
