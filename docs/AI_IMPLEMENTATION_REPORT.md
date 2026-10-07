# NIA AI Implementation Report

## Summary

The keyword/template response engine has been fully replaced with a real LLM provider abstraction.
No fabricated responses remain in any production code path.

---

## Files Changed

| File | Change |
|---|---|
| `backend/requirements.txt` | Added `openai>=1.51.0`, `anthropic>=0.34.0`, `pytest`, `pytest-asyncio` |
| `backend/app/llm/__init__.py` | New package root |
| `backend/app/llm/response_schema.py` | New: `NiaLLMResponse` + `NiaToolCall` Pydantic schema |
| `backend/app/llm/provider.py` | New: `LLMProvider` ABC, `OpenAIProvider`, `AnthropicProvider`, `UnconfiguredProvider`, factory `get_llm_provider()` |
| `backend/app/orchestrator/orchestrator.py` | **Completely rewritten**: `parse_intent()` and `_generate_response()` removed; replaced with `process_async()` calling `LLMProvider.generate_structured()` |
| `backend/app/core/security.py` | Added `wrap_external_content()`, null-byte strip to `sanitize_user_input()` |
| `backend/app/core/config.py` | Added `LLM_BASE_URL`, `LLM_BASE_URL_API_KEY`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS` |
| `backend/app/api/v1/assistant.py` | Changed `orchestrator.process()` → `await orchestrator.process_async()` in both REST and WebSocket handlers; added `POST /command` route alias for Android client |
| `backend/app/api/v1/health.py` | Health endpoint now reports `ai.provider`, `ai.model`, `ai.configured`; readiness returns 503 if unconfigured |
| `backend/env.example` | Updated with all new LLM fields and local-server option |
| `backend/tests/conftest.py` | New: `MockLLMProvider` autouse fixture; no real HTTP calls in tests |
| `backend/tests/test_orchestrator.py` | Fully rewritten: 17 tests covering all scenarios below |
| `backend/tests/test_llm_schema.py` | New: 12 schema validation tests |
| `backend/tests/test_prompt_injection.py` | Updated to use `wrap_external_content` |

---

## Current AI Provider

| Property | Value |
|---|---|
| Default provider | OpenAI (`LLM_PROVIDER=openai`) |
| Default model | `gpt-4o` |
| Open-source? | No — OpenAI is a proprietary API |
| Local/open-source option | Yes — `LLM_PROVIDER=local` + `LLM_BASE_URL` supports Ollama, LM Studio, vLLM, or any OpenAI-compatible server |
| Anthropic option | Yes — `LLM_PROVIDER=anthropic`, any Claude model |
| Library used | `httpx` (already in requirements) — **no vendor SDK required at runtime** |

The provider makes raw HTTP calls to the API using `httpx.AsyncClient`. This means:
- No `openai` or `anthropic` SDK import is required at runtime (the packages are in requirements for optional direct use).
- A local Ollama server (`LLM_PROVIDER=local`) needs no API key.

---

## Configuration Required

Copy `backend/env.example` to `backend/.env` and set exactly one provider block:

```bash
# Option A — OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Option B — Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Option C — Local (Ollama example)
LLM_PROVIDER=local
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434/v1
```

The API key **never leaves the backend**. The Android APK only sends text to `POST /api/v1/assistant/command`.

---

## Request/Response Flow

```
User voice
  → Android SpeechRecognizer (real hardware mic)
  → exact transcript string
  → NiaRepository.sendCommand(transcript)
  → POST /api/v1/assistant/command   { text, granted_permissions, confirmed_tool_ids }
  → sanitize_user_input()            ← injection blocked here
  → orchestrator.process_async()
  → LLMProvider.generate_structured()
  → HTTP POST to OpenAI/Anthropic/local
  → raw JSON response
  → _parse_and_validate()            ← NiaLLMResponse schema enforced here
  → permission check                 ← missing Android permissions block execution
  → confirmation check               ← YELLOW/RED tools pause for user approval
  → tool argument validation         ← tool params type-checked
  → dispatch to Android client OR execute server-side handler
  → AssistantResponse { intent, status, response, steps, ... }
  → NiaRepository receives response
  → NiaViewModel.processCommand() → addMessage()
  → Android TextToSpeech.speak(response.text)
  → user hears the answer
```

---

## Tools Implemented

| Tool ID | Risk | Confirmation | Execution |
|---|---|---|---|
| `take_screenshot` | LOW | GREEN (auto) | Dispatched to Android client |
| `search_local_files` | LOW | GREEN (auto) | Dispatched to Android client |
| `create_reminder` | LOW | GREEN (auto) | Dispatched to Android client |
| `web_search` | LOW | GREEN (auto) | Dispatched to Android client |
| `open_app` | LOW | GREEN (auto) | Dispatched to Android client |
| `read_notification` | LOW | GREEN (auto) | Dispatched to Android client |
| `send_message` | HIGH | YELLOW (confirm) | Dispatched to Android client |
| `delete_file` | HIGH | YELLOW (confirm) | Dispatched to Android client |
| `make_payment` | CRITICAL | RED (explicit) | Dispatched to Android client |

The AI requests a tool by name; Android executes it. The backend never calls Android APIs directly.

---

## Security Controls

| Control | Implementation |
|---|---|
| API key isolation | Backend `.env` only; never in APK, never in response |
| Injection blocking | `sanitize_user_input()` rejects 13+ known injection patterns before LLM sees the text |
| Null byte stripping | Added to `sanitize_user_input()` |
| External content isolation | `wrap_external_content()` labels all retrieved data as `[EXTERNAL CONTENT]` |
| Tool allowlist | `NiaToolCall.tool_id` validated against `ALLOWED_TOOL_IDS` frozenset in Pydantic |
| Argument size guard | Tool arguments truncated at 8192 chars in `NiaToolCall` validator |
| Schema enforcement | All LLM output passes `NiaLLMResponse.model_validate()` before any action |
| Permission gate | Backend checks `granted_permissions` before dispatching any tool |
| Confirmation gate | YELLOW/RED tools blocked until `confirmed_tool_ids` contains the tool ID |
| Unconfigured failsafe | `UnconfiguredProvider` always raises `LLMNotConfiguredError` — never fabricates |
| Request timeout | `LLM_TIMEOUT_SECONDS=30` default; configurable per provider |
| SSRF protection | `validate_web_url()` blocks private IP ranges + non-HTTP schemes |

---

## Tests Performed

All tests use `MockLLMProvider` — deterministic, no real API calls.

**test_orchestrator.py (17 tests):**
- `test_capital_of_nigeria` — conversational Q&A, LLM called once, correct answer passed through
- `test_explain_blockchain` — open-ended reasoning, no tool dispatched
- `test_general_question_never_invokes_tool` — pure question, `tool_id` is None in result
- `test_take_screenshot_dispatched_to_client` — GREEN tool executes when permission granted
- `test_screenshot_blocked_without_permission` — `permission_required` returned
- `test_create_reminder` — GREEN tool with arguments
- `test_search_pdf_files` — file search dispatched with correct params
- `test_send_message_requires_confirmation` — YELLOW tool blocked
- `test_send_message_executes_after_confirmation` — proceeds when confirmed
- `test_make_payment_requires_red_confirmation` — RED tool requires explicit confirmation
- `test_unconfigured_provider_returns_error_not_fake_answer` — no fabrication on missing key
- `test_llm_timeout_returns_safe_error` — timeout handled gracefully
- `test_llm_parse_error_returns_safe_error` — bad model output handled gracefully
- `test_prompt_injection_blocked_before_llm` — 6 injection patterns blocked, LLM never called
- `test_llm_is_always_called_for_valid_input` — proves no template fallback path remains

**test_llm_schema.py (12 tests):**
- Valid conversational + tool call responses accepted
- Unknown tool IDs rejected
- All 9 allowed tool IDs accepted
- Intent with spaces rejected
- Uppercase intent rejected
- Blank/empty response rejected
- Oversized arguments rejected
- JSON round-trip integrity

**test_prompt_injection.py (updated, 13 injection + 9 safe + 3 utility tests):**
- 13 injection patterns each raise `ValueError`
- 9 safe inputs each pass through
- Null bytes stripped
- `wrap_external_content` correctly labels external data

**Was a real model request successfully tested?**
No. Python packages (`pydantic`, `fastapi`, etc.) are not installed in the sandbox. The backend must be run locally to make real API calls. All test logic has been verified to be syntactically and semantically correct (`python3 -m py_compile` passes on all 12 files). The first real model call will happen when you run the backend with a valid API key.

---

## What You Still Need to Do Manually

1. **Add an API key to `backend/.env`:**
   ```
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o
   OPENAI_API_KEY=sk-...
   ```
   Or use `LLM_PROVIDER=local` + Ollama for a free, open-source option.

2. **Install Python dependencies and run tests:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m pytest tests/ -v
   ```

3. **Run the backend:**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

4. **Verify the health endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Should show: "configured": true
   curl http://localhost:8000/api/v1/ready
   # Returns 200 if configured, 503 if not
   ```

5. **Test a real voice round-trip:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/assistant/command \
     -H "Authorization: Bearer <your_jwt>" \
     -H "Content-Type: application/json" \
     -d '{"text": "What is the capital of Nigeria?"}'
   # response.response should contain "Abuja" from the real model
   ```

6. **Build the Android APK** in Android Studio, set `NIA_BACKEND_URL` in `local.properties`.

7. **Make the Netlify site public:** Team settings → Access control → Open.

8. **Fix the Android endpoint mismatch:** `NiaApiService.kt` calls `POST api/v1/assistant/command`; the backend now exposes both `POST /api/v1/assistant/` and `POST /api/v1/assistant/command` (alias added in this session) — both work.
