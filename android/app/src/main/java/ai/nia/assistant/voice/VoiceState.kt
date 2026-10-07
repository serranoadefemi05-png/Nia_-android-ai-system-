package ai.nia.assistant.voice

/** All states the NIA voice pipeline can be in at any given moment. */
sealed class VoiceState {
    object Idle           : VoiceState()
    object Listening      : VoiceState()
    object Processing     : VoiceState()
    data class Speaking(val text: String) : VoiceState()
    data class Result(val response: String, val intent: String) : VoiceState()
    data class AwaitingConfirmation(
        val prompt: String,
        val toolId: String,
        val confirmationLevel: String,
    ) : VoiceState()
    data class PermissionRequired(val permissions: List<String>) : VoiceState()
    data class Error(val message: String) : VoiceState()
}
