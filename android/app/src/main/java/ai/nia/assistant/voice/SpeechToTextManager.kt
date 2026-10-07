package ai.nia.assistant.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import kotlinx.coroutines.channels.Channel
import java.util.Locale

/**
 * NIA — SpeechToTextManager
 *
 * Wraps Android SpeechRecognizer with a clean callback-based API.
 * Callers receive STT results through [resultChannel].
 * All lifecycle management (destroy/recreate) is handled here.
 */
class SpeechToTextManager(private val context: Context) {

    val resultChannel = Channel<SttResult>(Channel.BUFFERED)

    sealed class SttResult {
        data class Success(val text: String) : SttResult()
        data class Failure(val message: String) : SttResult()
    }

    interface StateListener {
        fun onReady()
        fun onBeginSpeech()
        fun onEndSpeech()
        fun onPartialResult(partial: String)
    }

    private var recognizer: SpeechRecognizer? = null
    private var stateListener: StateListener? = null

    fun setStateListener(listener: StateListener) {
        stateListener = listener
    }

    val isAvailable: Boolean
        get() = SpeechRecognizer.isRecognitionAvailable(context)

    fun startListening() {
        if (!isAvailable) {
            resultChannel.trySend(SttResult.Failure("Speech recognition unavailable on this device."))
            return
        }

        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(context)
        recognizer?.setRecognitionListener(object : RecognitionListener {

            override fun onReadyForSpeech(params: Bundle?) {
                stateListener?.onReady()
            }

            override fun onBeginningOfSpeech() {
                stateListener?.onBeginSpeech()
            }

            override fun onEndOfSpeech() {
                stateListener?.onEndSpeech()
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val partial = partialResults
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                if (!partial.isNullOrBlank()) stateListener?.onPartialResult(partial)
            }

            override fun onResults(results: Bundle?) {
                val text = results
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                if (!text.isNullOrBlank()) {
                    resultChannel.trySend(SttResult.Success(text))
                } else {
                    resultChannel.trySend(SttResult.Failure("No speech detected. Please try again."))
                }
            }

            override fun onError(error: Int) {
                val message = when (error) {
                    SpeechRecognizer.ERROR_AUDIO                  -> "Audio recording error."
                    SpeechRecognizer.ERROR_CLIENT                 -> "Client error."
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission required."
                    SpeechRecognizer.ERROR_NETWORK                -> "Network error. Check your connection."
                    SpeechRecognizer.ERROR_NETWORK_TIMEOUT        -> "Network timeout during recognition."
                    SpeechRecognizer.ERROR_NO_MATCH               -> "No speech detected. Please try again."
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY        -> "Recognition service busy. Please wait."
                    SpeechRecognizer.ERROR_SERVER                 -> "Recognition server error."
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT         -> "No speech input detected."
                    else                                          -> "Recognition error ($error)."
                }
                resultChannel.trySend(SttResult.Failure(message))
            }

            override fun onRmsChanged(rmsdB: Float)  {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.ENGLISH)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
        }
        recognizer?.startListening(intent)
    }

    fun stopListening() {
        recognizer?.stopListening()
    }

    fun cancel() {
        recognizer?.cancel()
    }

    fun destroy() {
        recognizer?.destroy()
        recognizer = null
        resultChannel.close()
    }
}
