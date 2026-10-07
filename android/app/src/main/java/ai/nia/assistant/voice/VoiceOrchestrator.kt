package ai.nia.assistant.voice

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * NIA — Voice Orchestrator
 *
 * Coordinates SpeechToTextManager and TextToSpeechManager into a unified
 * voice pipeline. Exposes [voiceState] as a StateFlow for Compose.
 *
 * The orchestrator does NOT call the backend. It hands raw STT text out via
 * [sttResultChannel] and NiaViewModel drives the rest of the pipeline.
 */
class VoiceOrchestrator(context: Context) {

    private val _voiceState = MutableStateFlow<VoiceState>(VoiceState.Idle)
    val voiceState: StateFlow<VoiceState> = _voiceState

    val sttManager = SpeechToTextManager(context)
    private val ttsManager = TextToSpeechManager(context)

    val sttResultChannel = sttManager.resultChannel

    init {
        ttsManager.onDone = {
            if (_voiceState.value is VoiceState.Speaking) {
                _voiceState.value = VoiceState.Idle
            }
        }

        sttManager.setStateListener(object : SpeechToTextManager.StateListener {
            override fun onReady()                     { _voiceState.value = VoiceState.Listening }
            override fun onBeginSpeech()               {}
            override fun onEndSpeech()                 { _voiceState.value = VoiceState.Processing }
            override fun onPartialResult(partial: String) {}
        })
    }

    // ── Voice control ─────────────────────────────────────────────────────

    fun startListening() {
        if (_voiceState.value is VoiceState.Listening) return
        sttManager.startListening()
    }

    fun stopListening() {
        sttManager.stopListening()
    }

    fun cancelListening() {
        sttManager.cancel()
        _voiceState.value = VoiceState.Idle
    }

    // ── State setters (called by NiaViewModel after processing) ───────────

    fun setProcessing() {
        _voiceState.value = VoiceState.Processing
    }

    fun setResult(response: String, intent: String) {
        _voiceState.value = VoiceState.Result(response, intent)
        speak(response)
    }

    fun setError(message: String) {
        _voiceState.value = VoiceState.Error(message)
        speak(message)
    }

    fun setAwaitingConfirmation(prompt: String, toolId: String, confirmationLevel: String) {
        _voiceState.value = VoiceState.AwaitingConfirmation(prompt, toolId, confirmationLevel)
        speak(prompt)
    }

    fun setPermissionRequired(permissions: List<String>) {
        _voiceState.value = VoiceState.PermissionRequired(permissions)
        speak("I need additional permissions to complete that action.")
    }

    fun reset() {
        _voiceState.value = VoiceState.Idle
    }

    // ── TTS ───────────────────────────────────────────────────────────────

    fun speak(text: String) {
        _voiceState.value = VoiceState.Speaking(text)
        ttsManager.speak(text)
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────

    fun destroy() {
        sttManager.destroy()
        ttsManager.shutdown()
    }
}
