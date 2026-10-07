# NIA Roadmap

## v0.1 — Foundation (current)

- [x] Monorepo structure: /android, /backend, /contracts, /shared, /docs
- [x] FastAPI backend with JWT auth, all 7 API endpoints
- [x] Tool registry: 9 tools, GREEN/YELLOW/RED confirmation system
- [x] AI orchestrator: full 9-step pipeline
- [x] Memory service with MemoryPolicy
- [x] Web agent abstraction (BasicWebAgent)
- [x] Browser agent integration boundary (stub)
- [x] Arc service interface (stub)
- [x] Android Kotlin scaffold: ActionRegistry, VoiceOrchestrator, ArcService, SecureStorage
- [x] Web dashboard: voice screen, history, tools, settings
- [x] Security: JWT, bcrypt, injection defense, SSRF, rate limiting
- [x] Documentation: README, ARCHITECTURE, ANDROID_SETUP, SECURITY, ARC_INTEGRATION

## v0.2 — Android MVP

- [ ] Full Kotlin/Compose Android UI
- [ ] Real SpeechRecognizer integration (RECORD_AUDIO permission flow)
- [ ] Real TTS feedback
- [ ] MediaProjection screenshot capture
- [ ] Actual AlarmManager reminders (WorkManager for reliability)
- [ ] MediaStore file search (PDF, DOCX, images)
- [ ] Backend API client (Retrofit + OkHttp)
- [ ] LLM intent parsing (OpenAI / Anthropic via backend)
- [ ] LLM parameter extraction (structured output)
- [ ] Real web search (backend BasicWebAgent)
- [ ] Arc agent identity (ERC-8004 on Arc Testnet)
- [ ] Task attestation recording

## v0.3 — Intelligence

- [ ] Screen understanding (MediaProjection + vision model)
- [ ] Form-fill assistance
- [ ] Multi-step task planning
- [ ] Notification listener integration
- [ ] Dejevu / Playwright browser agent
- [ ] Nigerian language support (Pidgin, Yoruba, Igbo, Hausa)
- [ ] Arc USDC payments with spending policies
- [ ] Conversation memory and summarisation

## v0.4 — Agent Economy

- [ ] Agent marketplace discovery
- [ ] Agent-to-agent interactions via Arc
- [ ] Paid external agent services
- [ ] User-controlled spending policies with daily limits
- [ ] Task verification by external agents
- [ ] Multi-user NIA instances

## Long-term Vision

NIA becomes an Android-native alternative to Siri/Google Assistant for Africa.

User → NIA → Specialised agents/services → Execution → Verification → Optional USDC settlement

Every action is safe, verified, and reported back to the user exactly.
