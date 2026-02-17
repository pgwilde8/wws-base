# OpenAI Agent Deployment Guide

This document explains how we deploy OpenAI chat agents to the Green Candle Dispatch website, including the migration from Assistants API to Responses API (and fallback to Chat Completions).

---

## Architecture Overview

### Three-Layer Approach

1. **Frontend (JavaScript)** - Chat widget in browser
2. **Backend API (FastAPI)** - Routes that handle chat requests
3. **OpenAI Service Layer** - Abstracts OpenAI API calls

```
Browser → FastAPI Route → Chat Service → OpenAI API
```

---

## File Structure

### Core Chat Files

```
app/
├── core/
│   ├── chat_responses.py              # Main Responses API implementation
│   └── chat_responses_fallback.py    # Chat Completions fallback (currently active)
├── routes/
│   └── public.py                      # API endpoints (/api/chat, /api/chat/greeting)
└── templates/
    └── layout/
        └── base.html                  # Frontend chat widget JavaScript

docs/
├── chat-agent-system-prompt.md                    # Full system prompt (long version)
├── chat-agent-system-prompt-responses-api.md      # Short system prompt (Responses API)
└── openai-agent-deployment.md                     # This file
```

---

## Key Files Explained

### 1. `app/core/chat_responses.py`

**Purpose:** Main implementation for Responses API (future-ready)

**Key Functions:**
- `run_responses_chat()` - Sends messages to Responses API
- `get_greeting()` - Gets greeting message
- `_load_system_prompt()` - Loads prompt from markdown file

**Current Status:** Uses fallback mode (Chat Completions) since Responses API not available yet

**When to Update:** When OpenAI releases Responses API, uncomment the API call code

---

### 2. `app/core/chat_responses_fallback.py`

**Purpose:** Fallback implementation using Chat Completions API (currently active)

**Key Functions:**
- `run_chat_completions()` - Handles chat using Chat Completions API
- `get_greeting()` - Gets greeting message
- In-memory conversation storage (`_conversations` dict)

**How It Works:**
1. Stores conversation history in memory (keyed by `conversation_id`)
2. Builds message array with system prompt + conversation history
3. Calls `openai_client.chat.completions.create()`
4. Extracts response and saves to conversation history
5. Returns reply + conversation_id for threading

**Limitations:**
- In-memory storage (lost on server restart)
- Not suitable for production at scale
- Should migrate to Redis or database

---

### 3. `app/routes/public.py`

**Purpose:** FastAPI endpoints for chat

**Endpoints:**

**`POST /api/chat`**
- Receives: `{ "message": "...", "response_id": "..." }`
- Returns: `{ "reply": "...", "response_id": "..." }`
- Handles both new conversations and threaded conversations

**`GET /api/chat/greeting`**
- Returns: `{ "reply": "...", "response_id": "...", "greeting": true }`
- Used when chat widget first opens

**Error Handling:**
- Catches all exceptions
- Returns proper HTTP status codes
- Logs errors for debugging

---

### 4. `app/templates/layout/base.html`

**Purpose:** Frontend chat widget

**Key Features:**
- Chat toggle button (bottom right)
- Message display area
- Input form
- Automatic greeting on open
- Clickable links in responses (converts `/beta/apply` etc. to links)

**JavaScript Functions:**
- `toggleChat()` - Show/hide chat panel
- `sendMessage()` - Send user message to API
- `showGreeting()` - Fetch and display greeting
- `appendMessage()` - Display message in chat UI

**Conversation Threading:**
- Stores `responseId` in JavaScript variable
- Sends `response_id` with each message
- Maintains conversation context across messages

---

### 5. `docs/chat-agent-system-prompt-responses-api.md`

**Purpose:** System prompt for the chat agent

**Content:**
- Service description
- Pricing information
- Common Q&A
- Sign-up guidance
- Tone guidelines

**How It's Used:**
- Loaded automatically by `_load_system_prompt()`
- Extracted from markdown (skips headers)
- Sent as system message to OpenAI

**To Update Agent Behavior:**
- Edit this markdown file
- Changes take effect on next request (no restart needed)

---

## What We Learned

### 1. Responses API vs Assistants API

**Old Way (Assistants API):**
- Required pre-created Assistant in OpenAI dashboard
- Used `threads` and `runs`
- More complex, required polling for completion
- Had permanent Assistant ID

**New Way (Responses API):**
- No pre-created Assistant needed
- System prompt sent with each request
- Simpler API structure
- `response_id` for threading (like conversation ID)

**Current Implementation:**
- Using Chat Completions API as fallback
- Simulates Responses API behavior
- Ready to switch when Responses API available

---

### 2. Conversation Threading

**How It Works:**
1. First message: No `response_id` → creates new conversation
2. OpenAI returns `response_id` (or `conversation_id` in fallback)
3. Next message: Include `response_id` → continues conversation
4. Frontend stores `response_id` in JavaScript variable

**Fallback Implementation:**
- Uses in-memory dict: `_conversations[conversation_id] = messages`
- Stores full message history (system + user + assistant)
- Keeps last 10 messages to avoid token limits

**Production Considerations:**
- Need persistent storage (Redis or database)
- Should expire old conversations
- Consider conversation limits per user

---

### 3. System Prompt Loading

**Approach:**
- Store prompt in markdown file (version controlled)
- Load dynamically (no code changes needed)
- Extract content between `## System Prompt` headers

**Benefits:**
- Easy to update without code changes
- Version controlled
- Can have multiple prompt versions

**Alternative Approaches:**
- Hardcode in Python (less flexible)
- Store in database (overkill for simple use case)
- Environment variable (hard to maintain long prompts)

---

### 4. Error Handling

**Layers:**
1. **Service Layer** (`chat_responses_fallback.py`)
   - Handles OpenAI API errors
   - Parses response safely
   - Returns HTTPException with proper status codes

2. **Route Layer** (`public.py`)
   - Catches all exceptions
   - Logs errors for debugging
   - Returns user-friendly error messages

3. **Frontend** (`base.html`)
   - Displays error messages to user
   - Handles network errors
   - Shows fallback messages

**Common Errors:**
- `OpenAI client not configured` - Missing API key
- `Rate limit` - Too many requests
- `Response parsing error` - Unexpected API response format
- `Network error` - Frontend can't reach backend

---

### 5. Response Parsing

**Challenge:**
- OpenAI API response structure can vary
- `content` might be string or object
- Need to handle `ResponseTextConfig` objects

**Solution:**
```python
content = response.choices[0].message.content
if isinstance(content, str):
    reply = content.strip()
elif hasattr(content, 'text'):
    reply = str(content.text).strip()
else:
    reply = str(content).strip()
```

**Key Learning:**
- Always check type before calling methods
- Use `hasattr()` to check for attributes
- Convert to string as last resort

---

## Migration Path

### Current State (Chat Completions Fallback)

✅ Working with Chat Completions API
✅ Conversation threading in memory
✅ System prompt from markdown
✅ Frontend integration complete

### Next Steps (When Responses API Available)

1. **Update `chat_responses.py`**
   - Uncomment Responses API code
   - Update model name
   - Test API structure

2. **Update System Prompt**
   - Optimize for Responses API if needed
   - Test with new API

3. **Add Persistent Storage**
   - Migrate from in-memory to Redis/DB
   - Add conversation expiration
   - Add user limits

4. **Production Hardening**
   - Add rate limiting
   - Add monitoring
   - Add analytics

---

## API Comparison

### Chat Completions (Current)

```python
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    temperature=0.7,
    max_tokens=500
)
reply = response.choices[0].message.content
```

**Pros:**
- Available now
- Well documented
- Stable API

**Cons:**
- Need to manage conversation history yourself
- No built-in threading
- More tokens used (send full history each time)

---

### Responses API (Future)

```python
response = openai_client.responses.create(
    model="gpt-5",
    store=True,
    input=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    previous_response_id=response_id
)
reply = response.output
```

**Pros:**
- Built-in conversation threading
- Simpler API
- Potentially more efficient

**Cons:**
- Not available yet
- API structure may change
- Need to migrate when available

---

## Best Practices

### 1. System Prompt Design

- **Keep it concise** - Shorter prompts = faster responses
- **Be specific** - Clear instructions = better responses
- **Include examples** - Q&A format helps
- **Update regularly** - Based on user feedback

### 2. Error Handling

- **Always catch exceptions** - Don't let errors crash the app
- **Log errors** - Helps debugging
- **User-friendly messages** - Don't expose technical details
- **Graceful degradation** - Fallback messages when API fails

### 3. Conversation Management

- **Limit history** - Keep last 10 messages max
- **Expire old conversations** - Don't store forever
- **Rate limiting** - Prevent abuse
- **User identification** - Track per user if needed

### 4. Frontend Integration

- **Show typing indicators** - Better UX
- **Handle errors gracefully** - Don't break chat UI
- **Make links clickable** - Better conversion
- **Auto-scroll** - Keep latest message visible

---

## Troubleshooting

### Chat Not Responding

1. Check OpenAI API key: `echo $OPENAI_API_KEY`
2. Check logs: `journalctl -u dispatch -f`
3. Test API directly: `curl http://localhost:8990/api/chat/greeting`
4. Check OpenAI API status

### Conversation Not Threading

1. Check `response_id` is being sent from frontend
2. Check `response_id` is being returned from backend
3. Check conversation storage (in-memory dict)
4. Verify JavaScript variable is persisting

### Wrong Responses

1. Check system prompt is loading correctly
2. Check system prompt content matches expectations
3. Test with different messages
4. Check OpenAI model being used

### High Costs

1. Use cheaper model (`gpt-4o-mini` vs `gpt-4o`)
2. Limit `max_tokens` in API call
3. Limit conversation history length
4. Add rate limiting per user

---

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
CHAT_MODEL=gpt-4o-mini          # For fallback (Chat Completions)
RESPONSES_MODEL=gpt-4o          # For Responses API (when available)
```

---

## Testing

### Manual Testing

```bash
# Test greeting endpoint
curl http://localhost:8990/api/chat/greeting

# Test chat endpoint
curl -X POST http://localhost:8990/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much does this cost?"}'

# Test threading
RESPONSE_ID=$(curl -X POST http://localhost:8990/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}' | jq -r '.response_id')

curl -X POST http://localhost:8990/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Tell me more\", \"response_id\": \"$RESPONSE_ID\"}"
```

### Frontend Testing

1. Open website
2. Click chat widget
3. Verify greeting appears
4. Send test message
5. Verify response
6. Send follow-up message
7. Verify conversation threads

---

## Future Improvements

1. **Persistent Storage**
   - Migrate to Redis or PostgreSQL
   - Add conversation expiration
   - Add user tracking

2. **Analytics**
   - Track common questions
   - Measure response quality
   - Monitor costs

3. **Advanced Features**
   - File uploads
   - Voice input
   - Multi-language support
   - Custom tools/functions

4. **Production Hardening**
   - Rate limiting
   - Caching
   - Monitoring/alerting
   - Cost tracking

---

## References

- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) (when available)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- System Prompt: `docs/chat-agent-system-prompt-responses-api.md`

---

## Summary

We've successfully deployed an OpenAI chat agent to the website using:

1. **Chat Completions API** as fallback (currently active)
2. **Responses API** structure ready for migration
3. **System prompt** loaded from markdown file
4. **Conversation threading** via response_id
5. **Frontend integration** with greeting and clickable links

The implementation is production-ready for small scale, with clear migration path for Responses API and persistent storage when needed.
