# NIA Android Setup

## Requirements

- Android Studio Hedgehog (2023.1.1) or later
- Kotlin 1.9+
- Android SDK 34 (target) / 26 (min)
- Gradle 8.2+

## Project Setup

1. Open `android/` in Android Studio.
2. Sync Gradle.
3. Add your backend URL to `local.properties`:
   ```
   nia.backend.url=https://your-nia-backend.com
   ```
4. Build and run on a physical device (API 26+). Some features (MediaProjection, SpeechRecognizer) require a real device.

## Required Permissions

Add to `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_DOCUMENTS" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
<uses-permission android:name="android.permission.SET_ALARM" />
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM"
    android:minSdkVersion="31" />
<uses-permission android:name="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" />
```

## Key Dependencies (build.gradle)

```kotlin
dependencies {
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.4")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
}
```

## Architecture

```
io.nia.android/
├── action/
│   ├── ActionRegistry.kt       Central tool registry
│   └── Actions.kt              Built-in action implementations
├── voice/
│   └── VoiceOrchestrator.kt    STT + TTS pipeline
├── memory/
│   └── (MemoryService adapter for backend API)
├── arc/
│   └── ArcService.kt           Arc integration stub
├── security/
│   └── SecureStorage.kt        Android Keystore + EncryptedSharedPreferences
├── ui/
│   └── NiaViewModel.kt         Compose ViewModel
└── NiaApplication.kt           App entry point, registry setup
```

## Feature Flags

| Feature | API Level | Status |
|---|---|---|
| SpeechRecognizer | 9 | v0.1 |
| TextToSpeech | 4 | v0.1 |
| AlarmClock intents | 19 | v0.1 |
| Storage Access Framework | 19 | v0.1 |
| MediaProjection (screenshots) | 21 | v0.1 |
| Notification listener | 18 | v0.1 |
| Exact alarms (API 31+) | 31 | v0.1 |
| Android Keystore | 18 | v0.1 |
| Arc USDC payments | N/A | v0.2 |
