# Chat Implementation Files Reference

Quick reference guide to all files involved in the chat agent implementation.

---

## File Map

```
/srv/projects/client/dispatch/
│
├── app/
│   ├── core/
│   │   ├── chat_responses.py              ⭐ Main Responses API handler
│   │   └── chat_responses_fallback.py    ⭐ Active: Chat Completions fallback
│   │
│   ├── routes/
│   │   └── public.py                      ⭐ API endpoints (/api/chat)
│   │
│   └── templates/
│       └── layout/
│           └── base.html                  ⭐ Frontend chat widget
│
└── docs/
    ├── chat-agent-system-prompt.md                    ⭐ Long system prompt
    ├── chat-agent-system-prompt-responses-api.md      ⭐ Short system prompt (active)
    ├── chat-responses-api-setup.md                   Setup guide
    └── openai-agent-deployment.md                    ⭐ Main documentation
```

---

## File Details

### ⭐ Core Service Files

#### `app/core/chat_responses.py`
- **Purpose:** Responses API implementation (future-ready)
- **Status:** Uses fallback mode
- **Key Functions:**
  - `run_responses_chat()` - Main chat handler
  - `get_greeting()` - Greeting message
  - `_load_system_prompt()` - Loads prompt from file
- **When to Edit:** When Responses API becomes available

#### `app/core/chat_responses_fallback.py`
- **Purpose:** Chat Completions API implementation (currently active)
- **Status:** ✅ Active
- **Key Functions:**
  - `run_chat_completions()` - Handles chat requests
  - `get_greeting()` - Greeting message
- **Storage:** In-memory `_conversations` dict
- **When to Edit:** To change chat behavior, add features, or migrate to persistent storage

---

### ⭐ API Endpoints

#### `app/routes/public.py`
- **Endpoints:**
  - `POST /api/chat` - Send message, get reply
  - `GET /api/chat/greeting` - Get greeting message
- **Error Handling:** Catches all exceptions, returns proper HTTP codes
- **When to Edit:** To add new endpoints or change request/response format

---

### ⭐ Frontend

#### `app/templates/layout/base.html`
- **Location:** Chat widget JavaScript (lines ~37-104)
- **Features:**
  - Chat toggle button
  - Message display
  - Input form
  - Auto-greeting
  - Clickable links
- **Variables:**
  - `responseId` - Conversation threading
  - `greetingShown` - Prevent duplicate greetings
- **When to Edit:** To change UI, add features, or fix frontend bugs

---

### ⭐ System Prompts

#### `docs/chat-agent-system-prompt-responses-api.md`
- **Purpose:** System prompt for chat agent (short version)
- **Status:** ✅ Active (loaded automatically)
- **Content:** Service info, pricing, Q&A, sign-up guidance
- **When to Edit:** To change agent behavior, add FAQs, update info

#### `docs/chat-agent-system-prompt.md`
- **Purpose:** Full system prompt (long version)
- **Status:** Available but not used (fallback only)
- **When to Edit:** For comprehensive prompt updates

---

### 📚 Documentation

#### `docs/openai-agent-deployment.md`
- **Purpose:** Complete deployment guide
- **Content:** Architecture, file structure, what we learned, migration path
- **When to Edit:** As we learn more or add features

#### `docs/chat-responses-api-setup.md`
- **Purpose:** Setup and configuration guide
- **Content:** Environment variables, testing, troubleshooting
- **When to Edit:** When setup process changes

---

## Quick Actions

### Update Chat Behavior
1. Edit: `docs/chat-agent-system-prompt-responses-api.md`
2. Changes take effect immediately (no restart needed)

### Change Chat Model
1. Edit: `.env` → `CHAT_MODEL=gpt-4o-mini`
2. Restart: `sudo systemctl restart dispatch`

### Add New Endpoint
1. Edit: `app/routes/public.py`
2. Add route handler
3. Test: `curl http://localhost:8990/api/your-endpoint`

### Fix Frontend Bug
1. Edit: `app/templates/layout/base.html`
2. Find JavaScript section (~line 37)
3. Test in browser

### Add Persistent Storage
1. Edit: `app/core/chat_responses_fallback.py`
2. Replace `_conversations` dict with Redis/DB calls
3. Update `run_chat_completions()` function

### Migrate to Responses API
1. Edit: `app/core/chat_responses.py`
2. Uncomment Responses API code
3. Update model name
4. Test thoroughly
5. Remove fallback code

---

## File Dependencies

```
base.html (frontend)
    ↓ calls
public.py (/api/chat endpoint)
    ↓ calls
chat_responses.py (main handler)
    ↓ calls (fallback mode)
chat_responses_fallback.py (active implementation)
    ↓ loads
chat-agent-system-prompt-responses-api.md (system prompt)
    ↓ uses
OpenAI API (Chat Completions)
```

---

## Testing Checklist

When making changes, test:

- [ ] Greeting appears when chat opens
- [ ] Messages send and receive responses
- [ ] Conversation threads correctly (follow-up messages)
- [ ] Links in responses are clickable
- [ ] Error handling works (test with invalid API key)
- [ ] System prompt loads correctly
- [ ] No syntax errors (check Python imports)

---

## Common Edits

### Change System Prompt
```bash
# Edit the prompt file
nano docs/chat-agent-system-prompt-responses-api.md

# No restart needed - loaded dynamically
```

### Change Chat Model
```bash
# Edit .env
nano .env
# Change: CHAT_MODEL=gpt-4o-mini

# Restart service
sudo systemctl restart dispatch
```

### Debug Chat Issues
```bash
# Check logs
journalctl -u dispatch -f

# Test endpoint directly
curl http://localhost:8990/api/chat/greeting
```

---

## File Ownership

- **Core Logic:** `app/core/chat_responses*.py`
- **API Layer:** `app/routes/public.py`
- **Frontend:** `app/templates/layout/base.html`
- **Configuration:** `docs/chat-agent-system-prompt*.md`
- **Documentation:** `docs/openai-agent-deployment.md`

---

## Version History

- **v1.0** - Initial implementation with Chat Completions fallback
- **v1.1** - Added Responses API structure (commented, ready for future)
- **v1.2** - Fixed syntax errors, improved error handling
- **Current** - Production-ready with fallback, ready for Responses API migration
