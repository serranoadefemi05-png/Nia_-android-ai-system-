package ai.nia.assistant.ui

import android.app.Application
import androidx.activity.result.ActivityResultLauncher
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import ai.nia.assistant.action.ConfirmationLevel
import ai.nia.assistant.permission.PermissionManager
import ai.nia.assistant.repository.NiaRepository
import ai.nia.assistant.router.NiaCommandRouter
import ai.nia.assistant.voice.SpeechToTextManager
import ai.nia.assistant.voice.VoiceOrchestrator
import ai.nia.assistant.voice.VoiceState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

// ── UI models ─────────────────────────────────────────────────────────────

data class ConversationMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: MessageRole,
    val text: String,
    val intent: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
)

enum class MessageRole { USER, NIA, SYSTEM }

data class ConfirmationDialogState(
    val toolId: String,
    val description: String,
    val confirmationLevel: ConfirmationLevel,
    val prompt: String,
)

data class NiaUiState(
    val voiceState: VoiceState         = VoiceState.Idle,
    val conversation: List<ConversationMessage> = emptyList(),
    val pendingConfirmation: ConfirmationDialogState? = null,
    val isOnline: Boolean              = true,
    val sessionId: String              = UUID.randomUUID().toString(),
)

// ── ViewModel ─────────────────────────────────────────────────────────────

@HiltViewModel
class NiaViewModel @Inject constructor(
    application: Application,
) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(NiaUiState())
    val uiState: StateFlow<NiaUiState> = _uiState

    val voiceOrchestrator = VoiceOrchestrator(application)
    private val permissionManager = PermissionManager(application)
    private val repository = NiaRepository()
    private val router = NiaCommandRouter(repository)

    private val confirmedToolIds = mutableSetOf<String>()
    private var lastUserText: String = ""

    init {
        // Collect voice state changes
        viewModelScope.launch {
            voiceOrchestrator.voiceState.collectLatest { vs ->
                _uiState.value = _uiState.value.copy(voiceState = vs)
            }
        }

        // Consume STT results
        viewModelScope.launch {
            for (result in voiceOrchestrator.sttResultChannel) {
                when (result) {
                    is SpeechToTextManager.SttResult.Success ->
                        onUserSpeech(result.text)
                    is SpeechToTextManager.SttResult.Failure ->
                        voiceOrchestrator.setError(result.message)
                }
            }
        }
    }

    // ── Bind the permission launcher from MainActivity ────────────────────

    fun bindPermissionLauncher(launcher: ActivityResultLauncher<Array<String>>) {
        permissionManager.bind(launcher)
    }

    fun onPermissionsResult(results: Map<String, Boolean>) {
        permissionManager.onPermissionsResult(results)
        _uiState.value = _uiState.value.copy(
            // Recheck online state etc. in case storage permission was just granted
        )
    }

    // ── Mic tap ───────────────────────────────────────────────────────────

    fun onMicTap() {
        when (_uiState.value.voiceState) {
            is VoiceState.Listening -> voiceOrchestrator.stopListening()
            is VoiceState.Idle,
            is VoiceState.Result,
            is VoiceState.Error     -> voiceOrchestrator.startListening()
            else -> { /* ignore while Processing / Speaking / Confirming */ }
        }
    }

    // ── Text fallback command ─────────────────────────────────────────────

    fun onTextCommand(text: String) {
        if (text.isBlank()) return
        lastUserText = text
        addMessage(ConversationMessage(role = MessageRole.USER, text = text))
        viewModelScope.launch { processCommand(text) }
    }

    // ── Confirmation actions ──────────────────────────────────────────────

    fun onConfirm(toolId: String) {
        confirmedToolIds.add(toolId)
        _uiState.value = _uiState.value.copy(pendingConfirmation = null)
        viewModelScope.launch { processCommand(lastUserText) }
    }

    fun onDeny() {
        _uiState.value = _uiState.value.copy(pendingConfirmation = null)
        val msg = "Got it — I've cancelled that action."
        addMessage(ConversationMessage(role = MessageRole.NIA, text = msg))
        voiceOrchestrator.speak(msg)
        voiceOrchestrator.reset()
    }

    // ── Internal ──────────────────────────────────────────────────────────

    private suspend fun onUserSpeech(text: String) {
        lastUserText = text
        addMessage(ConversationMessage(role = MessageRole.USER, text = text))
        processCommand(text)
    }

    private suspend fun processCommand(text: String) {
        voiceOrchestrator.setProcessing()
        try {
            val result = router.route(
                text               = text,
                sessionId          = _uiState.value.sessionId,
                confirmedToolIds   = confirmedToolIds,
                grantedPermissions = permissionManager.grantedPermissions,
            )

            when (result) {
                is NiaCommandRouter.RouteResult.Success -> {
                    val ttsText = result.response
                    addMessage(ConversationMessage(role = MessageRole.NIA, text = ttsText, intent = result.intent))
                    voiceOrchestrator.setResult(ttsText, result.intent)
                }
                is NiaCommandRouter.RouteResult.ConversationalReply -> {
                    addMessage(ConversationMessage(role = MessageRole.NIA, text = result.response))
                    voiceOrchestrator.setResult(result.response, "conversational")
                }
                is NiaCommandRouter.RouteResult.ConfirmationRequired -> {
                    _uiState.value = _uiState.value.copy(
                        pendingConfirmation = ConfirmationDialogState(
                            toolId            = result.toolId,
                            description       = result.description,
                            confirmationLevel = result.confirmationLevel,
                            prompt            = result.prompt,
                        ),
                    )
                    voiceOrchestrator.setAwaitingConfirmation(
                        result.prompt,
                        result.toolId,
                        result.confirmationLevel.name,
                    )
                }
                is NiaCommandRouter.RouteResult.PermissionRequired -> {
                    addMessage(ConversationMessage(role = MessageRole.NIA, text = result.response))
                    voiceOrchestrator.setPermissionRequired(result.permissions)
                    permissionManager.request(result.permissions)
                }
                is NiaCommandRouter.RouteResult.BackendError -> {
                    val msg = "Backend error: ${result.message}"
                    addMessage(ConversationMessage(role = MessageRole.SYSTEM, text = msg))
                    voiceOrchestrator.setError("I couldn't reach the NIA backend. Please check your connection.")
                    _uiState.value = _uiState.value.copy(isOnline = false)
                }
                is NiaCommandRouter.RouteResult.NetworkUnavailable -> {
                    addMessage(ConversationMessage(role = MessageRole.SYSTEM, text = "Network unavailable."))
                    voiceOrchestrator.setError("No internet connection. Please check your network.")
                    _uiState.value = _uiState.value.copy(isOnline = false)
                }
                is NiaCommandRouter.RouteResult.Timeout -> {
                    addMessage(ConversationMessage(role = MessageRole.SYSTEM, text = "Request timed out."))
                    voiceOrchestrator.setError("The request timed out. Please try again.")
                }
                is NiaCommandRouter.RouteResult.ActionError -> {
                    addMessage(ConversationMessage(role = MessageRole.SYSTEM, text = "Action error: ${result.message}"))
                    voiceOrchestrator.setError("Something went wrong: ${result.message}")
                }
            }
        } catch (e: Exception) {
            addMessage(ConversationMessage(role = MessageRole.SYSTEM, text = "Error: ${e.message}"))
            voiceOrchestrator.setError("An unexpected error occurred.")
        }
    }

    private fun addMessage(msg: ConversationMessage) {
        _uiState.value = _uiState.value.copy(
            conversation = (_uiState.value.conversation + msg).takeLast(100),
        )
    }

    override fun onCleared() {
        voiceOrchestrator.destroy()
    }
}
