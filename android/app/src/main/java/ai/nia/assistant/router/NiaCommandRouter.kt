package ai.nia.assistant.router

import ai.nia.assistant.action.ActionRegistry
import ai.nia.assistant.action.ActionResult
import ai.nia.assistant.action.ConfirmationLevel
import ai.nia.assistant.api.AssistantResponse
import ai.nia.assistant.repository.NiaRepository
import ai.nia.assistant.repository.NiaResult

/**
 * NIA — Command Router
 *
 * The router is the bridge between the NIA backend response and the
 * Android ActionRegistry. It enforces the three-level confirmation system
 * at the execution layer (not just in the UI).
 *
 * Flow:
 *  1. Receive AssistantResponse from the backend.
 *  2. If the backend returned a tool_id, look it up in ActionRegistry.
 *  3. Check permissions (missing → RouteResult.PermissionRequired).
 *  4. Check confirmation level:
 *     - GREEN  → execute immediately.
 *     - YELLOW → RouteResult.ConfirmationRequired.
 *     - RED    → RouteResult.ConfirmationRequired (with RED flag).
 *  5. Execute the action and verify the result.
 *  6. Return RouteResult.
 */
class NiaCommandRouter(
    private val repository: NiaRepository,
) {

    // ── Route result ──────────────────────────────────────────────────────

    sealed class RouteResult {
        /** Action completed successfully. */
        data class Success(
            val intent: String,
            val response: String,
            val actionResult: ActionResult? = null,
        ) : RouteResult()

        /** Backend requires user confirmation before executing this tool. */
        data class ConfirmationRequired(
            val toolId: String,
            val description: String,
            val confirmationLevel: ConfirmationLevel,
            val prompt: String,
            val originalResponse: AssistantResponse,
        ) : RouteResult()

        /** One or more Android permissions need to be granted. */
        data class PermissionRequired(
            val toolId: String,
            val permissions: List<String>,
            val response: String,
        ) : RouteResult()

        /** Backend or network error. */
        data class BackendError(val message: String)       : RouteResult()
        object NetworkUnavailable                          : RouteResult()
        object Timeout                                     : RouteResult()
        data class ActionError(val message: String)        : RouteResult()
        data class ConversationalReply(val response: String) : RouteResult()
    }

    // ── Main route function ───────────────────────────────────────────────

    suspend fun route(
        text: String,
        sessionId: String,
        confirmedToolIds: Set<String>,
        grantedPermissions: Set<String>,
    ): RouteResult {

        // Step 1: Ask the backend what to do.
        val backendResult = repository.sendCommand(
            text             = text,
            sessionId        = sessionId,
            confirmedToolIds = confirmedToolIds.toList(),
            grantedPermissions = grantedPermissions,
        )

        val assistantResponse = when (backendResult) {
            is NiaResult.Success      -> backendResult.data
            is NiaResult.Error        -> return RouteResult.BackendError(backendResult.message)
            is NiaResult.NetworkUnavailable -> return RouteResult.NetworkUnavailable
            is NiaResult.Timeout      -> return RouteResult.Timeout
        }

        // Step 2: Pure conversation — no tool needed.
        val toolId = assistantResponse.toolId
        if (toolId.isNullOrBlank() || assistantResponse.status == "completed") {
            return RouteResult.ConversationalReply(assistantResponse.response)
        }

        // Step 3: Backend says confirmation is required.
        if (assistantResponse.status == "awaiting_confirmation") {
            val level = when (assistantResponse.confirmationLevel) {
                "RED"    -> ConfirmationLevel.RED
                "YELLOW" -> ConfirmationLevel.YELLOW
                else     -> ConfirmationLevel.YELLOW
            }
            val action = ActionRegistry.getOrNull(toolId)
            return RouteResult.ConfirmationRequired(
                toolId             = toolId,
                description        = action?.description ?: toolId,
                confirmationLevel  = level,
                prompt             = assistantResponse.confirmationPrompt ?: "Confirm this action?",
                originalResponse   = assistantResponse,
            )
        }

        // Step 4: Backend says permission is required.
        if (assistantResponse.status == "permission_required") {
            return RouteResult.PermissionRequired(
                toolId      = toolId,
                permissions = assistantResponse.missingPermissions ?: emptyList(),
                response    = assistantResponse.response,
            )
        }

        // Step 5: Backend approved execution — route to ActionRegistry.
        val action = ActionRegistry.getOrNull(toolId)
            ?: return RouteResult.ConversationalReply(assistantResponse.response)

        // Step 6: Check permissions on-device (defence-in-depth).
        val missing = ActionRegistry.missingPermissions(toolId, grantedPermissions)
        if (missing.isNotEmpty()) {
            return RouteResult.PermissionRequired(
                toolId      = toolId,
                permissions = missing,
                response    = "I need ${missing.joinToString(", ")} to do that.",
            )
        }

        // Step 7: Enforce confirmation level at the execution layer.
        if (toolId !in confirmedToolIds) {
            val level = action.confirmationLevel
            if (level != ConfirmationLevel.GREEN) {
                return RouteResult.ConfirmationRequired(
                    toolId            = toolId,
                    description       = action.description,
                    confirmationLevel = level,
                    prompt            = assistantResponse.confirmationPrompt ?: action.description,
                    originalResponse  = assistantResponse,
                )
            }
        }

        // Step 8: Execute.
        return try {
            val params = assistantResponse.toolParams ?: emptyMap()
            val actionResult = action.execute(params)
            if (!actionResult.success) {
                return RouteResult.ActionError(actionResult.error ?: "Action failed")
            }

            // Step 9: Verify.
            val verified = action.verify(actionResult)
            if (!verified) {
                return RouteResult.ActionError("Action executed but verification failed.")
            }

            RouteResult.Success(
                intent       = assistantResponse.intent,
                response     = assistantResponse.response,
                actionResult = actionResult,
            )
        } catch (e: Exception) {
            RouteResult.ActionError(e.message ?: "Unexpected error during tool execution")
        }
    }
}
