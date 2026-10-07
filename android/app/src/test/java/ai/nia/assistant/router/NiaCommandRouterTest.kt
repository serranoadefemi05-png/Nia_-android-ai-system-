package ai.nia.assistant.router

import ai.nia.assistant.action.ConfirmationLevel
import ai.nia.assistant.action.RiskLevel
import ai.nia.assistant.api.AssistantResponse
import ai.nia.assistant.repository.NiaRepository
import ai.nia.assistant.repository.NiaResult
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * NIA — NiaCommandRouter Unit Tests
 *
 * The router bridges backend intent → Android ActionRegistry execution.
 * These tests verify the critical confirmation and permission enforcement
 * that sits at the TOOL EXECUTION LAYER, not merely in the UI.
 */
class NiaCommandRouterTest {

    private lateinit var repository: NiaRepository
    private lateinit var router: NiaCommandRouter

    private val SESSION_ID = "test-session-001"

    @Before
    fun setUp() {
        repository = mockk()
        router = NiaCommandRouter(repository)
    }

    // ── Conversational replies ─────────────────────────────────────────────

    @Test
    fun `conversational intent with no tool returns ConversationalReply`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent   = "conversational",
                    status   = "completed",
                    response = "I'm NIA. How can I help?",
                    toolId   = null,
                )
            )

        val result = router.route(
            text               = "Hello NIA",
            sessionId          = SESSION_ID,
            confirmedToolIds   = emptySet(),
            grantedPermissions = emptySet(),
        )

        assertTrue(result is NiaCommandRouter.RouteResult.ConversationalReply)
        val reply = result as NiaCommandRouter.RouteResult.ConversationalReply
        assertEquals("I'm NIA. How can I help?", reply.response)
    }

    @Test
    fun `completed status with no toolId is a conversational reply`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent = "take_screenshot",
                    status = "completed",
                    response = "Screenshot taken.",
                )
            )

        val result = router.route("screenshot", SESSION_ID, emptySet(), emptySet())
        assertTrue(result is NiaCommandRouter.RouteResult.ConversationalReply)
    }

    // ── Confirmation gate — YELLOW ─────────────────────────────────────────

    @Test
    fun `backend returns awaiting_confirmation for YELLOW tool`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent             = "send_message",
                    status             = "awaiting_confirmation",
                    response           = "I need your confirmation.",
                    toolId             = "send_message",
                    confirmationLevel  = "YELLOW",
                    confirmationPrompt = "Send a WhatsApp message to John?",
                )
            )

        val result = router.route("send message to John", SESSION_ID, emptySet(), emptySet())

        assertTrue("Expected ConfirmationRequired", result is NiaCommandRouter.RouteResult.ConfirmationRequired)
        val conf = result as NiaCommandRouter.RouteResult.ConfirmationRequired
        assertEquals("send_message", conf.toolId)
        assertEquals(ConfirmationLevel.YELLOW, conf.confirmationLevel)
    }

    // ── Confirmation gate — RED ────────────────────────────────────────────

    @Test
    fun `backend returns awaiting_confirmation for RED tool`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent             = "make_payment",
                    status             = "awaiting_confirmation",
                    response           = "Financial action — confirm required.",
                    toolId             = "make_payment",
                    confirmationLevel  = "RED",
                    confirmationPrompt = "This will transfer USDC. Type 'confirm' to proceed.",
                )
            )

        val result = router.route("pay 5 USDC to John", SESSION_ID, emptySet(), emptySet())

        assertTrue(result is NiaCommandRouter.RouteResult.ConfirmationRequired)
        val conf = result as NiaCommandRouter.RouteResult.ConfirmationRequired
        assertEquals(ConfirmationLevel.RED, conf.confirmationLevel)
    }

    // ── Permission gate ────────────────────────────────────────────────────

    @Test
    fun `backend returns permission_required`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent             = "take_screenshot",
                    status             = "permission_required",
                    response           = "I need MEDIA_PROJECTION permission.",
                    toolId             = "take_screenshot",
                    missingPermissions = listOf("MEDIA_PROJECTION"),
                )
            )

        val result = router.route("take screenshot", SESSION_ID, emptySet(), emptySet())

        assertTrue(result is NiaCommandRouter.RouteResult.PermissionRequired)
        val perm = result as NiaCommandRouter.RouteResult.PermissionRequired
        assertEquals("take_screenshot", perm.toolId)
        assertTrue("MEDIA_PROJECTION" in perm.permissions)
    }

    // ── Network / backend errors ───────────────────────────────────────────

    @Test
    fun `network unavailable returns NetworkUnavailable`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.NetworkUnavailable

        val result = router.route("any command", SESSION_ID, emptySet(), emptySet())
        assertTrue(result is NiaCommandRouter.RouteResult.NetworkUnavailable)
    }

    @Test
    fun `backend error returns BackendError`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Error("500 Internal Server Error")

        val result = router.route("any command", SESSION_ID, emptySet(), emptySet())
        assertTrue(result is NiaCommandRouter.RouteResult.BackendError)
        val err = result as NiaCommandRouter.RouteResult.BackendError
        assertTrue(err.message.contains("500"))
    }

    @Test
    fun `timeout returns Timeout`() = runBlocking {
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Timeout

        val result = router.route("any command", SESSION_ID, emptySet(), emptySet())
        assertTrue(result is NiaCommandRouter.RouteResult.Timeout)
    }

    // ── Confirmation already granted (re-route after user confirms) ────────

    @Test
    fun `confirmed toolId in set bypasses confirmation and dispatches to registry`() = runBlocking {
        // Backend says "completed" after client re-sends with confirmed_tool_ids
        coEvery { repository.sendCommand(any(), any(), any(), any()) } returns
            NiaResult.Success(
                AssistantResponse(
                    intent   = "send_message",
                    status   = "completed",
                    response = "Message sent.",
                )
            )

        val result = router.route(
            text               = "send message to John",
            sessionId          = SESSION_ID,
            confirmedToolIds   = setOf("send_message"), // already confirmed
            grantedPermissions = setOf("SEND_SMS"),
        )

        // Backend replied completed with no toolId — should be ConversationalReply
        assertTrue(result is NiaCommandRouter.RouteResult.ConversationalReply)
    }
}
