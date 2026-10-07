/*
 * NIA Android — app/build.gradle.kts
 *
 * Package  : ai.nia.assistant
 * Min SDK  : 26 (Android 8.0 Oreo)
 * Target   : 35 (Android 15)
 */
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.ksp)
}

android {
    namespace  = "ai.nia.assistant"
    compileSdk = 35

    defaultConfig {
        applicationId   = "ai.nia.assistant"
        minSdk          = 26
        targetSdk       = 35
        versionCode     = 1
        versionName     = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Backend URL injected from local.properties or CI environment variable.
        // Never hardcode a production URL here.
        // For the Android emulator, 10.0.2.2 reaches the host machine's localhost.
        buildConfigField(
            "String",
            "NIA_BACKEND_URL",
            "\"${project.findProperty("NIA_BACKEND_URL") ?: "http://10.0.2.2:8000"}\"",
        )
    }

    buildTypes {
        debug {
            isDebuggable        = true
            isMinifyEnabled     = false
            applicationIdSuffix = ".debug"
            versionNameSuffix   = "-debug"
        }
        release {
            isDebuggable      = false
            isMinifyEnabled   = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            // signingConfig = signingConfigs.getByName("release")  // configure in local CI
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose     = true
        buildConfig = true
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    // ── Compose BOM ─────────────────────────────────────────────────────────
    val composeBom = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    debugImplementation(libs.androidx.compose.ui.tooling)

    // ── Core Android ─────────────────────────────────────────────────────────
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    // ── Navigation ────────────────────────────────────────────────────────────
    implementation(libs.androidx.navigation.compose)

    // ── Coroutines ────────────────────────────────────────────────────────────
    implementation(libs.kotlinx.coroutines.android)

    // ── Hilt (Dependency Injection) ───────────────────────────────────────────
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.androidx.hilt.navigation.compose)

    // ── Room (local persistence: memory + task history) ───────────────────────
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    // ── Network: Retrofit + OkHttp + Moshi ────────────────────────────────────
    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.moshi)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging.interceptor)
    implementation(libs.moshi.kotlin)
    ksp(libs.moshi.kotlin.codegen)

    // ── Security (Keystore-backed EncryptedSharedPreferences) ─────────────────
    implementation(libs.androidx.security.crypto)

    // ── WorkManager (background reminders + task scheduling) ──────────────────
    implementation(libs.androidx.work.runtime.ktx)

    // ── DataStore (user preferences) ──────────────────────────────────────────
    implementation(libs.androidx.datastore.preferences)

    // ── Unit Tests ────────────────────────────────────────────────────────────
    testImplementation(libs.junit)
    testImplementation(libs.mockk)
    testImplementation(libs.kotlinx.coroutines.test)

    // ── Instrumented Tests ────────────────────────────────────────────────────
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.espresso.core)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}
