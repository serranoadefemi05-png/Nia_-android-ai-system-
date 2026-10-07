# NIA — Android App Setup Guide

> **NIA** · "Your Android, with an AI brain."
> Package: `ai.nia.assistant` · Min SDK: 26 (Android 8.0 Oreo) · Target SDK: 35 (Android 15)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository structure](#2-repository-structure)
3. [Backend setup](#3-backend-setup)
4. [Android project setup](#4-android-project-setup)
5. [Running in the emulator](#5-running-in-the-emulator)
6. [Running on a physical device](#6-running-on-a-physical-device)
7. [Permissions walkthrough](#7-permissions-walkthrough)
8. [Architecture overview](#8-architecture-overview)
9. [Adding a new tool (AndroidAction)](#9-adding-a-new-tool-androidaction)
10. [Running tests](#10-running-tests)
11. [Building a release APK](#11-building-a-release-apk)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Android Studio | Ladybug (2024.2) or newer | Includes AGP 8.7 support |
| JDK | 17 | Bundled with Android Studio |
| Kotlin | 2.1.0 | Via Gradle plugin |
| Gradle | 8.11.1 | Via wrapper — do not update manually |
| Android SDK | API 35 | Install via SDK Manager |
| Android Emulator | API 35 image | x86_64 recommended |
| Python | 3.11+ | For the NIA backend |

---

## 2. Repository structure

```
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/ai/nia/assistant/
│   │   │   │   ├── MainActivity.kt          ← Entry point
│   │   │   │   ├── NiaApplication.kt        ← Hilt app class
│   │   │   │   ├── action/                  ← ActionRegistry + tool definitions
│   │   │   │   │   ├── ActionRegistry.kt
│   │   │   │   │   └── tools/
│   │   │   │   │       ├── ScreenshotTool.kt
│   │   │   │   │       ├── SearchFilesTool.kt
│   │   │   │   │       ├── ReminderTool.kt
│   │   │   │   │       └── WebSearchTool.kt
│   │   │   │   ├── api/                     ← Retrofit client + DTOs
│   │   │   │   ├── permission/              ← PermissionManager
│   │   │   │   ├── receiver/                ← AlarmReceiver
│   │   │   │   ├── repository/              ← NiaRepository
│   │   │   │   ├── router/                  ← NiaCommandRouter
│   │   │   │   ├── security/                ← SecureStorage (Keystore)
│   │   │   │   ├── service/                 ← ScreenCaptureService
│   │   │   │   ├── ui/                      ← Compose screens + ViewModel
│   │   │   │   │   ├── NiaApp.kt
│   │   │   │   │   ├── NiaViewModel.kt
│   │   │   │   │   ├── screens/
│   │   │   │   │   └── theme/
│   │   │   │   └── voice/                   ← VoiceOrchestrator, STT, TTS
│   │   │   ├── AndroidManifest.xml
│   │   │   └── res/
│   │   └── test/                            ← JUnit 4 + MockK unit tests
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
├── gradle/
│   ├── libs.versions.toml                   ← Version catalog
│   └── wrapper/gradle-wrapper.properties
└── local.properties.example                 ← Copy → local.properties
```

---

## 3. Backend setup

The Android app communicates with the NIA FastAPI backend. Start it before running the app.

```bash
# From the repo root
cd backend

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets (copy and edit)
cp env.example .env
# Edit .env — set SECRET_KEY, OPENAI_API_KEY (optional), etc.

# Start the dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `curl http://localhost:8000/api/v1/health`

The Android emulator reaches the host machine at `10.0.2.2`.
A physical device needs the host IP — see §6.

---

## 4. Android project setup

### 4a. Clone and open

```bash
git clone <repo-url>
cd <repo>/android
```

Open the `android/` folder in Android Studio (not the repo root).

### 4b. Configure local.properties

```bash
cp local.properties.example android/local.properties
```

Edit `local.properties`:

```properties
# Android SDK path — set automatically by Android Studio.
sdk.dir=/Users/yourname/Library/Android/sdk

# NIA backend URL.
# Emulator → host machine:
NIA_BACKEND_URL=http://10.0.2.2:8000
# Physical device → your machine's LAN IP:
# NIA_BACKEND_URL=http://192.168.1.42:8000
```

`local.properties` is in `.gitignore` — never commit it.

### 4c. Sync Gradle

In Android Studio: **File → Sync Project with Gradle Files** (or click the elephant icon).

Gradle downloads all dependencies listed in `gradle/libs.versions.toml`. First sync may take 2–5 minutes.

---

## 5. Running in the emulator

1. **Create an AVD**: Device Manager → Create Device → Pixel 8 → API 35 (x86_64).
2. **Start the emulator** from Device Manager.
3. **Run** the `app` configuration in Android Studio (▶).
4. **Grant permissions** when prompted:
   - Microphone — required for voice input.
   - Storage / Media — required for file search and screenshot save.
5. **Try a voice command** or type in the text input field.

The app connects to `http://10.0.2.2:8000` by default (the host machine's `localhost`).

---

## 6. Running on a physical device

1. Enable **Developer Options** on your Android device (Settings → About → tap Build Number 7×).
2. Enable **USB Debugging**.
3. Connect via USB — accept the RSA key fingerprint prompt on the device.
4. Find your machine's LAN IP: `ip addr show` / `ipconfig`.
5. Set `NIA_BACKEND_URL=http://<your-lan-ip>:8000` in `local.properties`.
6. Ensure your backend is bound to `0.0.0.0` (the `--host 0.0.0.0` flag above).
7. Run from Android Studio — select your physical device from the target dropdown.

---

## 7. Permissions walkthrough

NIA requests permissions **just-in-time** — only when a tool needs them.

| Permission | When requested | Risk | Tool |
|-----------|---------------|------|------|
| `RECORD_AUDIO` | App launch | LOW | Voice input |
| `INTERNET` | App launch | LOW | All backend calls |
| `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_AUDIO`, `READ_EXTERNAL_STORAGE` | First file search | LOW | SearchFilesTool |
| `WRITE_EXTERNAL_STORAGE` | First screenshot | LOW | ScreenshotTool |
| `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PROJECTION` | First screenshot | LOW | ScreenCaptureService |
| `SET_ALARM`, `SCHEDULE_EXACT_ALARM` | First reminder | LOW | ReminderTool |
| `POST_NOTIFICATIONS` | First reminder | LOW | AlarmReceiver |
| `BIND_NOTIFICATION_LISTENER_SERVICE` | User explicitly enables | LOW | Future: ReadNotificationTool |

**HIGH / CRITICAL tools** (send message, delete file, make payment) require explicit user confirmation before NIA requests their permissions.

---

## 8. Architecture overview

```
Voice Input (SpeechRecognizer)
        │
        ▼
  VoiceOrchestrator  ←──────────────────── TextToSpeech
        │  (STT result channel)
        ▼
  NiaViewModel
        │
        ├─► NiaCommandRouter
        │         │
        │         ├─ 1. NiaRepository.sendCommand()  ──► NIA Backend (FastAPI)
        │         │         (AssistantResponse)
        │         ├─ 2. Permission check (PermissionManager)
        │         ├─ 3. Confirmation check (ConfirmationLevel)
        │         └─ 4. ActionRegistry.execute(toolId, params)
        │                     │
        │                     └─► AndroidAction implementations
        │                           (ScreenshotTool, SearchFilesTool,
        │                            ReminderTool, WebSearchTool, …)
        │
        └─► NiaUiState (StateFlow)
                  │
                  ▼
           Compose UI (NiaApp, VoiceScreen, ConfirmationSheet, …)
```

**Key design guarantee**: The AI orchestrator (backend) never calls Android APIs directly.
It returns a `tool_id` and parameters. `NiaCommandRouter` looks up the tool in `ActionRegistry`,
checks permissions and confirmation level, then calls `execute()` + `verify()`.

---

## 9. Adding a new tool (AndroidAction)

1. **Create** `android/app/src/main/java/ai/nia/assistant/action/tools/MyNewTool.kt`:

```kotlin
class MyNewTool(private val context: Context) : AndroidAction {
    override val id                = "my_new_tool"
    override val description       = "Does something useful."
    override val requiredPermissions = listOf(Manifest.permission.INTERNET)
    override val riskLevel         = RiskLevel.LOW
    override val confirmationLevel = ConfirmationLevel.GREEN
    override val parameters        = listOf(
        ActionParameter("query", "string", "What to do", required = true),
    )
    override val tags = listOf("utility")

    override suspend fun execute(params: Map<String, Any?>): ActionResult {
        val query = params["query"] as? String ?: return ActionResult.fail("Missing query")
        // … do the thing …
        return ActionResult.ok(mapOf("result" to "done"))
    }

    override suspend fun verify(result: ActionResult): Boolean = result.success
}
```

2. **Register** it in `NiaApplication.kt`:

```kotlin
ActionRegistry.register(MyNewTool(this))
```

3. **Add** it to the backend tool registry in `backend/app/tools/registry.py`.

4. **Add** its intent keywords to `backend/app/orchestrator/orchestrator.py`'s `INTENT_MAP`.

---

## 10. Running tests

```bash
# JVM unit tests (no device required)
./gradlew :app:test

# Instrumented tests (emulator or device required)
./gradlew :app:connectedAndroidTest
```

Test files are in `app/src/test/java/ai/nia/assistant/`.

---

## 11. Building a release APK

1. **Create a signing keystore** (once per project):

```bash
keytool -genkey -v -keystore nia-release.jks \
  -alias nia -keyalg RSA -keysize 2048 -validity 10000
```

Store it **outside the repository**. Never commit it.

2. **Configure signing** in `app/build.gradle.kts` (see commented `signingConfig` block).

3. **Build**:

```bash
./gradlew :app:assembleRelease
# APK: app/build/outputs/apk/release/app-release.apk
```

---

## 12. Troubleshooting

| Problem | Fix |
|---------|-----|
| `CLEARTEXT communication not permitted` | Backend URL must use HTTPS on non-emulator devices. For development, add a network security config exception or use the emulator. |
| `Connection refused` on device | Make sure the backend binds to `0.0.0.0` and `NIA_BACKEND_URL` uses your LAN IP, not `10.0.2.2`. |
| `Permission denied` for microphone | Grant `RECORD_AUDIO` in Settings → Apps → NIA → Permissions. |
| Build fails with `Duplicate class` | Run `./gradlew :app:dependencies` and look for version conflicts. Enforce via `resolutionStrategy` in `build.gradle.kts`. |
| Hilt `@AndroidEntryPoint` missing | Ensure `NiaApplication` is declared in `AndroidManifest.xml` as `android:name=".NiaApplication"`. |
| `MediaProjection` black screen | The emulator's GPU emulation can cause black frames. Test on a physical device. |
| Screenshot saved but not visible in Gallery | Open the Gallery app and force a media scan, or restart the emulator. MediaStore indexing can lag. |

---

*For backend issues, see [`docs/README.md`](./README.md).*
*For security policy, see [`docs/SECURITY.md`](./SECURITY.md).*
*For the full architecture, see [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md).*
