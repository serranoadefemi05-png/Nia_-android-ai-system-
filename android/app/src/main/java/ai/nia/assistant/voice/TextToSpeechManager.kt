package ai.nia.assistant.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale

/**
 * NIA — TextToSpeechManager
 *
 * Wraps Android TextToSpeech with a callback-based API.
 * Exposes [onDone] callback so callers can update UI state when speaking finishes.
 */
class TextToSpeechManager(context: Context) {

    private var tts: TextToSpeech? = null
    private var isReady = false

    var onDone: (() -> Unit)? = null

    init {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.ENGLISH
                isReady = true
                setupProgressListener()
            }
        }
    }

    private fun setupProgressListener() {
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?)  {}
            override fun onDone(utteranceId: String?)   { onDone?.invoke() }
            override fun onError(utteranceId: String?)  { onDone?.invoke() }
        })
    }

    fun speak(text: String) {
        if (!isReady || text.isBlank()) return
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
    }

    fun stop() {
        tts?.stop()
    }

    fun shutdown() {
        tts?.shutdown()
        tts = null
    }

    companion object {
        private const val UTTERANCE_ID = "nia_tts"
    }
}
