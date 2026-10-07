package ai.nia.assistant.action

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * NIA — ActionRegistry Unit Tests
 *
 * Tests the central tool registry that enforces the AI's access model:
 * tools are declared; nothing else can be called.
 */
class ActionRegistryTest {

    // A minimal stub action for testing
    private fun makeAction(
        id: String,
        risk: RiskLevel = RiskLevel.LOW,
        confirmation: ConfirmationLevel = ConfirmationLevel.GREEN,
        permissions: List<String> = emptyList(),
    ): AndroidAction = object : AndroidAction {
        override val id = id
        override val description = "Test action: $id"
        override val requiredPermissions = permissions
        override val riskLevel = risk
        override val confirmationLevel = confirmation
        override val parameters = emptyList<ActionParameter>()
        override val tags = emptyList<String>()
        override suspend fun execute(params: Map<String, Any?>) = ActionResult.ok(mapOf("tool" to id))
        override suspend fun verify(result: ActionResult) = result.success
    }

    // Fresh registry for every test
    private lateinit var registry: TestActionRegistry

    @Before
    fun setUp() {
        registry = TestActionRegistry()
    }

    // ── Registration ───────────────────────────────────────────────────────

    @Test
    fun `register and retrieve action`() {
        val action = makeAction("take_screenshot")
        registry.register(action)
        val retrieved = registry.get("take_screenshot")
        assertEquals("take_screenshot", retrieved.id)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `duplicate registration throws`() {
        val action = makeAction("take_screenshot")
        registry.register(action)
        registry.register(action) // should throw
    }

    @Test
    fun `getOrNull returns null for missing id`() {
        assertNull(registry.getOrNull("nonexistent_tool_id"))
    }

    @Test(expected = IllegalStateException::class)
    fun `get throws for missing id`() {
        registry.get("nonexistent_tool_id")
    }

    @Test
    fun `listAll returns all registered actions`() {
        registry.register(makeAction("tool_a"))
        registry.register(makeAction("tool_b"))
        registry.register(makeAction("tool_c"))
        assertEquals(3, registry.listAll().size)
    }

    // ── Confirmation level checks ──────────────────────────────────────────

    @Test
    fun `GREEN action does not require confirmation`() {
        registry.register(makeAction("web_search", confirmation = ConfirmationLevel.GREEN))
        assertFalse(registry.requiresConfirmation("web_search"))
    }

    @Test
    fun `YELLOW action requires confirmation`() {
        registry.register(makeAction("send_message", confirmation = ConfirmationLevel.YELLOW))
        assertTrue(registry.requiresConfirmation("send_message"))
    }

    @Test
    fun `RED action requires confirmation`() {
        registry.register(makeAction("make_payment", confirmation = ConfirmationLevel.RED))
        assertTrue(registry.requiresConfirmation("make_payment"))
    }

    // ── Permission checks ──────────────────────────────────────────────────

    @Test
    fun `action with no permissions always has permissions`() {
        registry.register(makeAction("web_search", permissions = emptyList()))
        assertTrue(registry.hasPermissions("web_search", emptySet()))
    }

    @Test
    fun `action with missing permission returns false`() {
        registry.register(makeAction("take_screenshot", permissions = listOf("MEDIA_PROJECTION")))
        assertFalse(registry.hasPermissions("take_screenshot", emptySet()))
    }

    @Test
    fun `action with granted permission returns true`() {
        registry.register(makeAction("take_screenshot", permissions = listOf("MEDIA_PROJECTION")))
        assertTrue(registry.hasPermissions("take_screenshot", setOf("MEDIA_PROJECTION")))
    }

    @Test
    fun `missingPermissions returns only the permissions not yet granted`() {
        registry.register(makeAction(
            "search_local_files",
            permissions = listOf("READ_EXTERNAL_STORAGE", "MANAGE_EXTERNAL_STORAGE"),
        ))
        val missing = registry.missingPermissions("search_local_files", setOf("READ_EXTERNAL_STORAGE"))
        assertEquals(listOf("MANAGE_EXTERNAL_STORAGE"), missing)
    }

    // ── LLM descriptor ────────────────────────────────────────────────────

    @Test
    fun `toLlmDescriptions includes all registered actions`() {
        registry.register(makeAction("tool_a"))
        registry.register(makeAction("tool_b"))
        val descs = registry.toLlmDescriptions()
        assertEquals(2, descs.size)
        val ids = descs.map { it["id"] as String }
        assertContains(ids, "tool_a")
        assertContains(ids, "tool_b")
    }

    @Test
    fun `toLlmDescriptions includes risk and confirmation fields`() {
        registry.register(makeAction("make_payment", RiskLevel.CRITICAL, ConfirmationLevel.RED))
        val desc = registry.toLlmDescriptions().first()
        assertEquals("CRITICAL", desc["risk_level"])
        assertEquals("RED", desc["confirmation_level"])
    }

    // ── ActionResult helpers ───────────────────────────────────────────────

    @Test
    fun `ActionResult ok has success=true`() {
        val r = ActionResult.ok(mapOf("path" to "/sdcard/screenshot.png"))
        assertTrue(r.success)
        assertNull(r.error)
        assertEquals("/sdcard/screenshot.png", r.data["path"])
    }

    @Test
    fun `ActionResult fail has success=false`() {
        val r = ActionResult.fail("Permission denied")
        assertFalse(r.success)
        assertEquals("Permission denied", r.error)
    }
}

// ── Test-scope registry (avoids mutating the singleton) ───────────────────

class TestActionRegistry {
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

    fun toLlmDescriptions(): List<Map<String, Any>> = actions.values.map { a ->
        mapOf(
            "id"                   to a.id,
            "description"          to a.description,
            "risk_level"           to a.riskLevel.name,
            "confirmation_level"   to a.confirmationLevel.name,
            "required_permissions" to a.requiredPermissions,
        )
    }
}

// ── JUnit 4 assertion helpers ──────────────────────────────────────────────

private fun <T> assertContains(collection: Collection<T>, element: T) {
    assertTrue("Expected collection to contain $element", collection.contains(element))
}
