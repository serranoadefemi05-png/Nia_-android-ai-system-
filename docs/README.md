# NIA — Your Android, with an AI brain.

NIA is an Android-first, voice-native personal AI agent optimised initially for Nigerian users and eventually broader African markets.

---

## Quick Start

### Web Dashboard (this preview)
The browser preview is the **NIA dashboard and demo**.
- Voice screen: tap the orb or use the text input to issue commands.
- History: see your full conversation log.
- Tools: browse the action registry with risk levels.
- Settings: configure backend URL and preview Arc integration.

### Backend
```bash
cd backend
pip install -r requirements.txt
cp env.example .env
# Edit .env — set SECRET_KEY, OPENAI_API_KEY, etc.
uvicorn main:app --reload
# Docs at http://localhost:8000/docs
```

### Android App
See `docs/ANDROID_SETUP.md` for Kotlin build instructions.

---

## Project Structure

```
/android          Kotlin + Jetpack Compose Android app
/backend          FastAPI Python backend
/contracts        Arc smart contract interfaces (prepared, v0.2)
/docs             All documentation
/shared           Shared type definitions
/src              NIA web dashboard (this app)
```

---

## MVP Commands (v0.1)

| Command | Intent | Tool | Risk |
|---|---|---|---|
| "Take a screenshot" | `take_screenshot` | `take_screenshot` | GREEN |
| "Find the PDF I downloaded yesterday" | `search_local_files` | `search_local_files` | GREEN |
| "Remind me tomorrow at 9 AM to call the supplier" | `create_reminder` | `create_reminder` | GREEN |
| "Search the web for the cheapest ESP32 DevKit" | `web_search` | `web_search` | GREEN |

---

## License

Proprietary — NIA Project
