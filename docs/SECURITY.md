# NIA Security

## Threat Model

NIA acts on behalf of the user on their Android device. The primary threats are:

1. **Unauthorised actions** — AI executing device actions without user knowledge.
2. **Prompt injection** — Malicious input tricking the AI into dangerous actions.
3. **Credential theft** — API keys or tokens exposed to attackers.
4. **SSRF** — Backend fetching attacker-controlled internal resources.
5. **Over-permissioned AI** — AI having broader device access than needed.

## Controls

### Authentication
- JWT access tokens (configurable expiry, default 60 min)
- JWT refresh tokens with server-side revocation (jti tracking)
- bcrypt password hashing
- All tokens stored in Android Keystore / EncryptedSharedPreferences

### Tool Execution Safety
- The AI NEVER calls Android APIs directly.
- Every device capability is registered in the ActionRegistry.
- Each tool has a RiskLevel and ConfirmationLevel.
- Confirmation enforcement is at the tool-execution layer, NOT just the UI.
- GREEN tools: auto-execute.
- YELLOW tools: require tap confirmation.
- RED tools: require typed "confirm" — never silently executed.

### Prompt Injection Defense
- Input sanitization rejects known injection patterns before reaching the orchestrator.
- Patterns blocked: "ignore previous instructions", "act as", "new system prompt", DAN mode, etc.
- Input length limited to 4096 chars.
- All fetched web content is treated as untrusted data, never as instructions.
- LLM prompt templates use separate system/user sections; user input never bleeds into system context.

### SSRF Protection
- All server-side web fetches validate the URL scheme (http/https only).
- Private IP ranges blocked (127.x, 10.x, 172.16-31.x, 192.168.x, ::1, localhost).
- Optional allowlist (ALLOWED_WEB_HOSTS in .env) for production.

### Secrets
- NO secrets hardcoded in source.
- NO API keys in the Android app binary.
- All secrets in .env (backend) or Android Keystore (app).
- .env and recovery files in .gitignore.

### Rate Limiting
- Per-IP rate limiting (default 60 req/min).
- Redis-based limiting recommended for production.

### Memory Policy
- Sensitive keys (password, pin, secret, private_key, seed, etc.) are blocked from storage.
- Memory values capped at 10 000 chars.
- Users can delete all their memory at any time.
- Sensitive data is NEVER auto-stored by the orchestrator without explicit user request.

## Audit Log

Every tool execution is logged with:
- User ID
- Intent
- Tool ID
- Parameters (sanitized — no sensitive values)
- Success/failure
- Timestamp

## What NIA v0.1 Does NOT Do

- No payments, transfers, or financial transactions.
- No wallet creation or blockchain interactions.
- No access to SMS content, contacts, or call logs without explicit permission.
- No screen access without explicit MediaProjection consent.
- No background data collection.
