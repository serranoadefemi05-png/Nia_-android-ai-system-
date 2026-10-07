# Build NIA APK from Android with GitHub Actions

The Android module is configured for:

- Package: `ai.nia.assistant`
- Min SDK: 26
- Target/Compile SDK: 35
- Java: 17
- Gradle: 8.9

The repository includes a GitHub Actions workflow at:

`.github/workflows/android-debug-apk.yml`

## Before building

Create a GitHub repository and upload the project. In the repository settings, add an Actions secret:

`NIA_BACKEND_URL`

Set it to the public HTTPS URL of the NIA FastAPI backend, for example:

`https://your-nia-api.example.com`

Never put an OpenRouter/API key in the Android project. AI credentials belong only on the backend.

## Build

GitHub → Actions → Build NIA Android APK → Run workflow.

When the job succeeds:

Actions → the successful run → Artifacts → `nia-debug-apk`

Download the artifact and install `app-debug.apk` on the Android phone.

## Important

Do not use `localhost` or `10.0.2.2` for a physical phone talking to a remote backend. Those are development/emulator addresses. For the real phone, use the deployed HTTPS backend URL.
