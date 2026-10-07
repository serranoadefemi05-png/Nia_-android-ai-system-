package ai.nia.assistant

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp
import ai.nia.assistant.action.ActionRegistry
import ai.nia.assistant.action.tools.ReminderTool
import ai.nia.assistant.action.tools.ScreenshotTool
import ai.nia.assistant.action.tools.SearchFilesTool
import ai.nia.assistant.action.tools.WebSearchTool

/**
 * NIA Application class.
 *
 * Responsibilities:
 *  1. Initialize Hilt dependency injection.
 *  2. Register all AndroidAction tools into the global ActionRegistry.
 *  3. Create notification channels required by NIA foreground services.
 */
@HiltAndroidApp
class NiaApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        registerActions()
    }

    // ── Action Registration ───────────────────────────────────────────────

    private fun registerActions() {
        ActionRegistry.register(ScreenshotTool(this))
        ActionRegistry.register(SearchFilesTool(this))
        ActionRegistry.register(ReminderTool(this))
        ActionRegistry.register(WebSearchTool())
    }

    // ── Notification Channels ─────────────────────────────────────────────

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)

            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_SCREENSHOT,
                    "Screenshot Service",
                    NotificationManager.IMPORTANCE_LOW,
                ).apply { description = "NIA screenshot capture foreground service" },
            )

            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_REMINDERS,
                    "NIA Reminders",
                    NotificationManager.IMPORTANCE_HIGH,
                ).apply { description = "NIA reminder and alarm notifications" },
            )
        }
    }

    companion object {
        const val CHANNEL_SCREENSHOT = "nia_screenshot"
        const val CHANNEL_REMINDERS  = "nia_reminders"
    }
}
