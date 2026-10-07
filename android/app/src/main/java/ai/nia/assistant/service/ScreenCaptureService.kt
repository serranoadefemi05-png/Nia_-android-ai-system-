package ai.nia.assistant.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.MediaStore
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CompletableDeferred
import java.io.OutputStream

/**
 * NIA — ScreenCaptureService
 *
 * A foreground service that uses MediaProjection to take a single screenshot
 * and save it to the device's Pictures/NIA directory via MediaStore.
 *
 * Lifecycle:
 *  1. Caller calls startForegroundService(intent) with a MediaProjection result.
 *  2. Service starts, acquires projection, captures one frame.
 *  3. Saves to MediaStore and broadcasts the URI as ACTION_SCREENSHOT_RESULT.
 *  4. Service stops itself.
 *
 * Risk: LOW. No continuous recording. Single-frame capture only.
 * Permission: android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION (auto-granted to foreground service).
 */
class ScreenCaptureService : Service() {

    companion object {
        const val TAG = "ScreenCaptureService"
        const val CHANNEL_ID = "nia_screen_capture"
        const val NOTIFICATION_ID = 1001
        const val ACTION_SCREENSHOT_RESULT = "ai.nia.assistant.SCREENSHOT_RESULT"
        const val EXTRA_SCREENSHOT_URI     = "screenshot_uri"
        const val EXTRA_SCREENSHOT_ERROR   = "screenshot_error"
        const val EXTRA_RESULT_CODE        = "result_code"
        const val EXTRA_RESULT_DATA        = "result_data"
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay?   = null
    private var imageReader: ImageReader?          = null

    // ── Lifecycle ─────────────────────────────────────────────────────────

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, -1) ?: -1
        val resultData = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
            intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        else
            @Suppress("DEPRECATION") intent?.getParcelableExtra(EXTRA_RESULT_DATA)

        if (resultCode == -1 || resultData == null) {
            broadcastError("Missing projection result data")
            stopSelf()
            return START_NOT_STICKY
        }

        val projectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = projectionManager.getMediaProjection(resultCode, resultData)

        if (mediaProjection == null) {
            broadcastError("Failed to acquire MediaProjection")
            stopSelf()
            return START_NOT_STICKY
        }

        captureScreen()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        teardown()
        super.onDestroy()
    }

    // ── Screen capture ────────────────────────────────────────────────────

    private fun captureScreen() {
        val metrics = resources.displayMetrics
        val width   = metrics.widthPixels
        val height  = metrics.heightPixels
        val density = metrics.densityDpi

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)

        virtualDisplay = mediaProjection!!.createVirtualDisplay(
            "NiaCapture",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader!!.surface,
            null,
            null,
        )

        // Give the system one frame to render before acquiring the image.
        Handler(Looper.getMainLooper()).postDelayed({
            acquireAndSave(width, height)
        }, 250)
    }

    private fun acquireAndSave(width: Int, height: Int) {
        val image = imageReader?.acquireLatestImage()
        if (image == null) {
            broadcastError("No image acquired from ImageReader")
            teardown(); stopSelf(); return
        }

        try {
            val planes = image.planes
            val buffer = planes[0].buffer
            val pixelStride  = planes[0].pixelStride
            val rowStride    = planes[0].rowStride
            val rowPadding   = rowStride - pixelStride * width

            val bitmap = Bitmap.createBitmap(
                width + rowPadding / pixelStride, height, Bitmap.Config.ARGB_8888,
            )
            bitmap.copyPixelsFromBuffer(buffer)

            // Crop away row-padding artefact
            val cropped = Bitmap.createBitmap(bitmap, 0, 0, width, height)
            bitmap.recycle()

            val uri = saveToMediaStore(cropped)
            cropped.recycle()

            if (uri != null) {
                val result = Intent(ACTION_SCREENSHOT_RESULT).apply {
                    putExtra(EXTRA_SCREENSHOT_URI, uri.toString())
                    setPackage(packageName)
                }
                sendBroadcast(result)
                Log.d(TAG, "Screenshot saved: $uri")
            } else {
                broadcastError("Failed to save screenshot to MediaStore")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Screenshot error", e)
            broadcastError(e.message ?: "Unknown capture error")
        } finally {
            image.close()
            teardown()
            stopSelf()
        }
    }

    private fun saveToMediaStore(bitmap: Bitmap): android.net.Uri? {
        val filename  = "NIA_${System.currentTimeMillis()}.png"
        val values    = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, filename)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/NIA")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }

        val resolver = contentResolver
        val uri      = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: return null

        var stream: OutputStream? = null
        return try {
            stream = resolver.openOutputStream(uri) ?: return null
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.clear()
                values.put(MediaStore.Images.Media.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            }
            uri
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            null
        } finally {
            stream?.close()
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private fun teardown() {
        runCatching { virtualDisplay?.release() }
        runCatching { imageReader?.close() }
        runCatching { mediaProjection?.stop() }
        virtualDisplay  = null
        imageReader     = null
        mediaProjection = null
    }

    private fun broadcastError(msg: String) {
        val result = Intent(ACTION_SCREENSHOT_RESULT).apply {
            putExtra(EXTRA_SCREENSHOT_ERROR, msg)
            setPackage(packageName)
        }
        sendBroadcast(result)
    }

    // ── Notification ──────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "NIA Screen Capture",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description   = "Used briefly while NIA takes a screenshot."
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("NIA")
            .setContentText("Taking screenshot…")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
}
