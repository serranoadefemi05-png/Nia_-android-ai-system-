# NIA Architecture

## Overview

NIA is an Android-first, voice-native AI agent operating as a monorepo with four primary layers:

```
┌─────────────────────────────────────────────────────┐
│                   ANDROID CLIENT                    │
│  SpeechRecognizer → NIA UI → TTS Response           │
│  Action Registry (controlled Android capabilities)  │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS / WSS (authenticated)
┌─────────────────────▼───────────────────────────────┐
│                  FASTAPI BACKEND                    │
│  Intent Parser → Planner → Tool Selector            │
│  Confirmation Manager → Tool Executor → Verifier    │
│  Memory Manager → Response Generator               │
└──────┬──────────────────────┬────────────────────────┘
       │                      │
┌──────▼──────┐    ┌──────────▼──────────┐
│  MemoryDB   │    │  WebAgentProvider   │
│  (SQLite/   │    │  (search, browse,   │
│   Postgres) │    │   extract, verify)  │
└─────────────┘    └─────────────────────┘
```

## AI Orchestration Flow

```
USER VOICE INPUT
     ↓
Speech-to-Text (Android SpeechRecognizer)
     ↓
Intent Parser       ← classifies intent, extracts entities
     ↓
Planner             ← breaks task into steps, selects tools
     ↓
Permission Checker  ← verifies app permissions for each tool
     ↓
Confirmation Manager ← GREEN: auto | YELLOW: confirm | RED: explicit
     ↓
Tool Executor       ← calls registered tools only (never raw Android APIs)
     ↓
Result Verifier     ← confirms the action actually succeeded
     ↓
Memory Manager      ← stores relevant context if policy allows
     ↓
Response Generator  ← creates natural language response
     ↓
Text-to-Speech (Android TTS)
     ↓
USER HEARS RESULT
```

## Confirmation System

| Level  | Color  | Examples                                      | Behavior               |
|--------|--------|-----------------------------------------------|------------------------|
| Safe   | GREEN  | screenshot, web search, file search, reminder | Auto-execute           |
| Review | YELLOW | send message, edit file, submit form          | Show + wait for tap OK |
| Danger | RED    | payment, delete data, security settings       | Explicit typed confirm |

## Tool Registry Schema

```json
{
  "id": "take_screenshot",
  "description": "Capture the current screen",
  "input_schema": {},
  "output_schema": { "path": "string", "timestamp": "string" },
  "required_permissions": ["MEDIA_PROJECTION"],
  "risk_level": "LOW",
  "confirmation_level": "GREEN"
}
```

## Memory Policy (v0.1)

- Stores: user preferences, recurring tasks, user-explicitly-saved facts, task history, conversation summaries
- Never auto-stores: passwords, financial data, private messages, location without consent
- User can delete all memory at any time
- Memory is scoped per user, encrypted at rest

## Security Layers

1. Android Keystore for local credential storage
2. JWT auth on all backend API calls
3. Tool-level authorization (permission + confirmation)
4. Rate limiting on all endpoints
5. Input/output validation (schema + content)
6. Prompt injection defense: external content tagged + sanitized
7. SSRF protection on all backend web requests
8. Action audit log (all tool executions recorded)
9. No API keys in Android app binary

## Arc Integration (Prepared for v0.2+)

NIA is designed to become an agent in the Arc ecosystem:
- Agent identity via ERC-8004
- Task attestations (verifiable records of completed actions)
- USDC micropayments for paid agent services
- User-controlled spending policies
- Agent-to-agent interactions

The `ArcService` abstraction is in place. No wallet or blockchain transaction is required for v0.1.

## WebAgentProvider Interface

```
WebAgentProvider
  ├── search(query) → SearchResult[]
  ├── browse(url) → PageContent
  ├── extract(url, schema) → StructuredData
  ├── interact(url, action) → InteractionResult
  └── verify(url, claim) → VerificationResult
```

Initial implementation: DuckDuckGo/SERP search + basic HTTP extraction.
Future: plug in "dejevu" or another browser-agent execution engine via the adapter boundary at `/backend/integrations/browser_agent/`.
