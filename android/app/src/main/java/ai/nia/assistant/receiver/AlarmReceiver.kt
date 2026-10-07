package ai.nia.assistant.receiver

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import ai.nia.assistant.MainActivity

/**
 * NIA — AlarmReceiver
 *
 * Receives the broadcast fired by AlarmManager when a NIA reminder fires.
 * Displays a heads-up notification and optionally triggers TTS via NiaViewModel.
 *
 * Risk: LOW. Read-only notification; does not mutate any data.
 *
 * Registered in AndroidManifest with:
 *   <receiver android:name=".receiver.AlarmReceiver"
 *             android:exported="false" />
 *
 * Extras expected:
 *   EXTRA_TITLE   — String — reminder title (e.g. "Call the supplier")
 *   EXTRA_ID      — Int    — unique reminder ID for notification deduplication
 */
class AlarmReceiver : BroadcastReceiver() {

    companion object {
        const val TAG              = "AlarmReceiver"
        const val CHANNEL_ID       = "nia_reminders"
        const val CHANNEL_NAME     = "NIA Reminders"
        const val EXTRA_TITLE      = "reminder_title"
        const val EXTRA_ID         = "reminder_id"
        const val DEFAULT_TITLE    = "NIA Reminder"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val title      = intent.getStringExtra(EXTRA_TITLE) ?: DEFAULT_TITLE
        val reminderId = intent.getIntExtra(EXTRA_ID, System.currentTimeMillis().toInt())

        Log.d(TAG, "Alarm fired — id=$reminderId title=$title")

        val notificationManager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Create channel (idempotent on Android O+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description    = "Reminders created by NIA."
                enableVibration(true)
                enableLights(true)
            }
            notificationManager.createNotificationChannel(channel)
        }

        // Tap notification → open app
        val openAppIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            reminderId,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("NIA — Reminder")
            .setContentText(title)
            .setStyle(NotificationCompat.BigTextStyle().bigText(title))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        notificationManager.notify(reminderId, notification)
    }
}
