# Chat Responses API Setup Guide

This guide explains how to use the new Responses API integration for the frontend chat widget.

## Files Created

1. **`app/core/chat_responses.py`** - Main Responses API implementation
2. **`app/core/chat_responses_fallback.py`** - Fallback using Chat Completions API
3. **`app/routes/public.py`** - Updated `/api/chat` endpoint
4. **`app/templates/layout/base.html`** - Updated frontend JavaScript

## How It Works

### Current Implementation (Fallback Mode)

Right now, the code uses **Chat Completions API** as a fallback because Responses API may not be available yet. It:
- Stores conversation history in memory (simple dict)
- Uses `conversation_id` as `response_id` for compatibility
- Works with `gpt-4o-mini` or `gpt-4o` models

### When Responses API is Available

Update `app/core/chat_responses.py`:

1. **Update the API call** - Replace the `responses.create()` call with the actual API structure
2. **Update model name** - Change `RESPONSES_MODEL` to the correct model (e.g., `"gpt-5"`)
3. **Set `use_fallback=False`** - Or remove fallback logic entirely

## Environment Variables

Add to your `.env`:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-...

# Model selection
RESPONSES_MODEL=gpt-4o  # For Responses API (update when available)
CHAT_MODEL=gpt-4o-mini   # For fallback Chat Completions
```

## API Endpoints

### `POST /api/chat`

Send a message and get a reply.

**Request:**
```json
{
  "message": "How much does this cost?",
  "response_id": "abc123"  // Optional: for conversation threading
}
```

**Response:**
```json
{
  "reply": "Flat 2% dispatch fee only after you get funded...",
  "response_id": "xyz789"  // Use this in next request
}
```

### `GET /api/chat/greeting`

Get a greeting message for new chat sessions.

**Response:**
```json
{
  "reply": "Hey! I'm the Green Candle AI...",
  "response_id": "conv_123",
  "greeting": true
}
```

## Frontend Features

The updated JavaScript:
- ✅ Uses `response_id` instead of `thread_id`
- ✅ Shows greeting when chat opens
- ✅ Makes sign-up links clickable (`/beta/apply`, `/register`, etc.)
- ✅ Handles conversation threading automatically

## Testing

1. **Test greeting:**
   ```bash
   curl http://localhost:8990/api/chat/greeting
   ```

2. **Test chat:**
   ```bash
   curl -X POST http://localhost:8990/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "How much does this cost?"}'
   ```

3. **Test threading:**
   ```bash
   # First message
   RESPONSE_ID=$(curl -X POST http://localhost:8990/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me more"}' | jq -r '.response_id')
   
   # Follow-up using response_id
   curl -X POST http://localhost:8990/api/chat \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"What about factoring?\", \"response_id\": \"$RESPONSE_ID\"}"
   ```

## Migration from Old Assistants API

If you were using the old `run_assistant_message()` function:

1. **Old code** used `thread_id` → **New code** uses `response_id`
2. **Old code** used Assistants API → **New code** uses Responses API (or fallback)
3. **Frontend** automatically updated to use `response_id`

The old endpoint still works but uses the new implementation.

## Production Considerations

### Conversation Storage

The fallback uses in-memory storage (`_conversations` dict). For production:

1. **Use Redis** for conversation storage:
   ```python
   import redis
   redis_client = redis.Redis(host='localhost', port=6379, db=0)
   
   # Store messages
   redis_client.setex(
       f"chat:{conversation_id}",
       3600,  # 1 hour TTL
       json.dumps(messages)
   )
   ```

2. **Or use database** - Store in `webwise.chat_conversations` table

### Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter
limiter = Limiter(key_func=lambda: request.client.host)

@router.post("/api/chat")
@limiter.limit("10/minute")
async def chat_api(...):
    ...
```

### Error Handling

The code includes basic error handling. Consider:
- Logging errors to monitoring service
- Retry logic for transient failures
- User-friendly error messages

## System Prompt

The system prompt is loaded from:
- `docs/chat-agent-system-prompt-responses-api.md`

Update this file to change the AI's behavior. The prompt is loaded automatically.

## Troubleshooting

**"OpenAI client not configured"**
- Check `OPENAI_API_KEY` is set in `.env`

**"Chat service error"**
- Check OpenAI API key is valid
- Check you have API credits
- Check model name is correct

**Conversation not threading**
- Make sure you're sending `response_id` in requests
- Check that `response_id` is being returned and stored

**Greeting not showing**
- Check `/api/chat/greeting` endpoint works
- Check browser console for JavaScript errors

## Next Steps

1. ✅ Code is ready to use with fallback (Chat Completions)
2. ⏳ When Responses API is available, update `chat_responses.py`
3. ⏳ Add Redis/database for conversation storage in production
4. ⏳ Add rate limiting
5. ⏳ Monitor usage and costs
