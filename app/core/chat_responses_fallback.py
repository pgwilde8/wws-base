"""
Fallback chat service using OpenAI Chat Completions API.
Use this if Responses API is not yet available.
This simulates conversation threading by storing messages in memory or a simple cache.
"""
import os
from typing import Optional, Dict
from fastapi import HTTPException, status
from openai import OpenAI
from app.core.chat_responses import _load_system_prompt

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Simple in-memory conversation store (use Redis or DB in production)
_conversations: Dict[str, list] = {}

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")  # Use cheaper model for chat


def run_chat_completions(
    message: str,
    conversation_id: Optional[str] = None,
    greeting: bool = False
) -> Dict:
    """
    Chat using Chat Completions API (fallback for Responses API).
    
    Args:
        message: User's message
        conversation_id: Conversation ID for threading (None for new conversation)
        greeting: If True, send greeting instead
    
    Returns:
        Dict with reply, conversation_id
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
            detail="Message too long"
        )
    
    # Get or create conversation history
    if conversation_id and conversation_id in _conversations:
        messages = _conversations[conversation_id]
    else:
        # New conversation: start with system prompt
        system_prompt = _load_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        # Generate conversation ID (simple hash or UUID)
        import hashlib
        import time
        conversation_id = hashlib.md5(
            f"{time.time()}{message}".encode()
        ).hexdigest()[:16]
    
    # Add user message or greeting
    if greeting:
        messages.append({
            "role": "user",
            "content": "Introduce yourself and ask how you can help. Be friendly and mention we're Green Candle Dispatch—AI dispatch for truckers."
        })
    else:
        messages.append({"role": "user", "content": message.strip()})
    
    try:
        # Call Chat Completions API
        # Debug: log what we're sending
        # print(f"Sending to OpenAI: model={CHAT_MODEL}, messages_count={len(messages)}")
        
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        # Debug: log response structure
        # print(f"Response received: type={type(response)}, choices_count={len(response.choices) if hasattr(response, 'choices') else 0}")
        
        # Extract message content - handle both string and object types
        try:
            # Debug: log response structure if needed
            # print(f"Response type: {type(response)}")
            # print(f"Choices type: {type(response.choices)}")
            # print(f"Message type: {type(response.choices[0].message)}")
            
            message_obj = response.choices[0].message
            content = message_obj.content
            
            # Debug: log content type
            # print(f"Content type: {type(content)}, value: {content}")
            
            if content is None:
                assistant_message = "Sorry, I didn't get a response. Can you try asking again?"
            elif isinstance(content, str):
                assistant_message = content.strip()
            else:
                # Handle ResponseTextConfig or other object types
                # Try to get text attribute if it exists
                if hasattr(content, 'text'):
                    assistant_message = str(content.text).strip()
                elif hasattr(content, '__str__'):
                    assistant_message = str(content).strip()
                else:
                    # Last resort: convert to string
                    assistant_message = str(content).strip()
                    
            # Ensure we have a valid message
            if not assistant_message or len(assistant_message) == 0:
                assistant_message = "Sorry, I didn't get a response. Can you try asking again?"
                
        except Exception as parse_error:
            # If we can't parse the response, return a helpful error
            import traceback
            print(f"Error parsing response: {parse_error}")
            print(traceback.format_exc())
            # Don't save failed responses to history
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse API response: {str(parse_error)}"
            )
        
        # Save assistant response to history
        messages.append({"role": "assistant", "content": assistant_message})
        
        # Keep only last 10 messages to avoid token limits
        if len(messages) > 10:
            # Keep system prompt + last 9 messages
            messages = [messages[0]] + messages[-9:]
        
        _conversations[conversation_id] = messages
        
        result = {
            "reply": assistant_message,
            "response_id": conversation_id,  # Use same field name as Responses API
            "conversation_id": conversation_id  # Also include for clarity
        }
        
        if greeting:
            result["greeting"] = True
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Log full error for debugging (remove in production or use proper logging)
        print(f"Chat error: {error_type}: {error_msg}")
        print(traceback.format_exc())
        
        if "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again."
            )
        
        # More specific error messages
        if "ResponseTextConfig" in error_msg or "object has no attribute 'strip'" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chat service configuration error. Please contact support."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {error_msg}"
        )


def get_greeting() -> Dict:
    """Get greeting message."""
    return run_chat_completions(message="", greeting=True)
