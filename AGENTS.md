# NIA — Project Memory

## Project
NIA — "Your Android, with an AI brain."
Android-first voice-native personal AI agent. Optimised initially for Nigeria.

## Monorepo Layout
- `/android` — Kotlin + Jetpack Compose Android app
- `/backend` — FastAPI Python backend (all API routes)
- `/contracts` — Arc smart contract interfaces (prepared, v0.2)
- `/docs` — All documentation (README, ARCHITECTURE, ANDROID_SETUP, SECURITY, ARC_INTEGRATION, ROADMAP)
- `/shared` — Shared type definitions
- `/src` — NIA web dashboard (this Vite React app)

## Web Dashboard
The `src/` directory is the NIA browser dashboard and interactive demo.
It runs at port 5173 via Vite.
- Voice screen: orb mic, demo commands, text input, response card
- History screen: full conversation log
- Tools screen: filterable action registry by risk level
- Settings screen: backend URL, Arc toggle, project info

## Backend (FastAPI)
- `backend/main.py` — entry point
- `backend/app/api/v1/` — auth, assistant, tasks, memory, tools, web
- `backend/app/orchestrator/orchestrator.py` — 9-step pipeline
- `backend/app/tools/registry.py` — 9 registered tools
- `backend/app/memory/memory_service.py` — MemoryPolicy + MemoryService
- `backend/app/web/web_agent.py` — WebAgentProvider + BasicWebAgent
- `backend/app/integrations/browser_agent/provider.py` — BrowserAgentProvider boundary
- `backend/app/arc/arc_service.py` — ArcService (stub v0.1)
- `backend/app/core/security.py` — JWT, bcrypt, injection defense, SSRF
- `backend/requirements.txt` — Python deps
- `backend/env.example` — env template (copy to .env)
- `backend/tests/` — pytest suite (security, tool registry, orchestrator, memory)

## Android (Kotlin)
- `android/.../action/ActionRegistry.kt` — AndroidAction interface + ActionRegistry
- `android/.../action/Actions.kt` — TakeScreenshot, SearchLocalFiles, CreateReminder, OpenApp, WebSearch
- `android/.../voice/VoiceOrchestrator.kt` — SpeechRecognizer + TTS + VoiceState
- `android/.../arc/ArcService.kt` — ArcServiceInterface stub
- `android/.../security/SecureStorage.kt` — Android Keystore + EncryptedSharedPreferences
- `android/.../ui/NiaViewModel.kt` — Compose ViewModel

## Deployed Contracts
None in v0.1. Arc integration prepared but not deployed.

## MVP Commands (v0.1)
1. "Take a screenshot" → take_screenshot (GREEN)
2. "Find the PDF I downloaded yesterday" → search_local_files (GREEN)
3. "Remind me tomorrow at 9 AM to call the supplier" → create_reminder (GREEN)
4. "Search the web for the cheapest ESP32 DevKit" → web_search (GREEN)

## Confirmation System
- GREEN: auto-execute (screenshot, web search, file search, reminder, open app)
- YELLOW: confirm dialog (send message, delete file)
- RED: typed confirmation (make payment — v0.2)

## Arc Integration
- All Arc interfaces defined and stubbed.
- Activation: v0.2+
- No wallet, no USDC, no blockchain in v0.1.
- `ArcService.is_available()` returns false.

## Key Design Rules
- The AI NEVER calls Android APIs directly. Only registered tools.
- HIGH/CRITICAL tools require `confirmed=True` at BOTH the orchestrator and API layers.
- Prompt injection blocked before reaching the orchestrator.
- SSRF validated on all server-side web fetches.
- Sensitive keys blocked from memory storage.
- NO secrets hardcoded anywhere.

## Run Backend Tests
```bash
cd backend
pip install -r requirements.txt
pip install pytest
SECRET_KEY=test-secret pytest tests/ -v
```
