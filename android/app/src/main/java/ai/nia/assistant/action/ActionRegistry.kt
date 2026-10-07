package ai.nia.assistant.action

/**
 * NIA Android — Action Registry
 *
 * Central registry of every capability NIA can exercise on the Android device.
 * The AI orchestrator NEVER calls Android APIs directly — it requests a
 * registered AndroidAction by ID. The registry validates, permission-checks,
 * and delegates execution to the action's own execute() + verify() handlers.
 *
 * Architecture guarantee: no AI secret is ever stored here. All AI/LLM keys
 * live exclusively on the NIA backend.
 */

// ── Risk classification ───────────────────────────────────────────────────

enum class RiskLevel { LOW, MEDIUM, HIGH, CRITICAL }

enum class ConfirmationLevel {
    /** GREEN: safe, auto-execute without asking the user. */
    GREEN,
    /** YELLOW: show a confirmation dialog and wait for the user to tap OK. */
    YELLOW,
    /** RED: require typed "confirm" before execution. */
    RED,
}

// ── Tool schema ───────────────────────────────────────────────────────────

data class ActionParameter(
    val name: String,
    val type: String,           // "string" | "integer" | "boolean"
    val description: String,
    val required: Boolean = true,
    val defaultValue: Any? = null,
)

data class ActionResult(
    val success: Boolean,
    val data: Map<String, Any?> = emptyMap(),
    val error: String? = null,
) {
    companion object {
        fun ok(data: Map<String, Any?> = emptyMap()) = ActionResult(true, data)
        fun fail(error: String)                      = ActionResult(false, error = error)
    }
}

// ── AndroidAction interface ───────────────────────────────────────────────

interface AndroidAction {
    /** Unique stable identifier — e.g. "take_screenshot". */
    val id: String

    /** Human-readable description shown in confirmation dialogs. */
    val description: String

    /** Android Manifest.permission strings this action requires. */
    val requiredPermissions: List<String>

    val riskLevel: RiskLevel
    val confirmationLevel: ConfirmationLevel
    val parameters: List<ActionParameter>
    val tags: List<String>

    /**
     * Execute the action. Called ONLY after permission + confirmation checks pass.
     * Must not access Android APIs that require permissions outside [requiredPermissions].
     */
    suspend fun execute(params: Map<String, Any?>): ActionResult

    /**
     * Verify the action's side-effect actually happened.
     * Returns true if the result is valid and the effect is confirmed.
     */
    suspend fun verify(result: ActionResult): Boolean
}

// ── Registry (singleton object) ───────────────────────────────────────────

object ActionRegistry {

    private val actions = mutableMapOf<String, AndroidAction>()

    fun register(action: AndroidAction) {
        require(!actions.containsKey(action.id)) {
            "Action already registered: '${action.id}'"
        }
        actions[action.id] = action
    }

    fun get(id: String): AndroidAction =
        actions[id] ?: error("Unknown action: '$id'")

    fun getOrNull(id: String): AndroidAction? = actions[id]

    fun listAll(): List<AndroidAction> = actions.values.toList()

    fun requiresConfirmation(id: String): Boolean =
        get(id).confirmationLevel != ConfirmationLevel.GREEN

    fun hasPermissions(id: String, grantedPermissions: Set<String>): Boolean =
        get(id).requiredPermissions.all { it in grantedPermissions }

    fun missingPermissions(id: String, grantedPermissions: Set<String>): List<String> =
        get(id).requiredPermissions.filterNot { it in grantedPermissions }

    /** Returns a descriptor map that can be sent to the LLM for tool selection. */
    fun toLlmDescriptions(): List<Map<String, Any>> = actions.values.map { a ->
        mapOf(
            "id"                   to a.id,
            "description"          to a.description,
            "risk_level"           to a.riskLevel.name,
            "confirmation_level"   to a.confirmationLevel.name,
            "required_permissions" to a.requiredPermissions,
            "parameters"           to a.parameters.map { p ->
                mapOf("name" to p.name, "type" to p.type, "required" to p.required)
            },
        )
    }
}
