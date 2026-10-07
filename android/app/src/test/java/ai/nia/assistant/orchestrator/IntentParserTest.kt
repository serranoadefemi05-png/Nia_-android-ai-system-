package ai.nia.assistant.orchestrator

import org.junit.Assert.*
import org.junit.Test

/**
 * NIA — Intent Parser Unit Tests
 *
 * Mirrors the Python orchestrator's intent-parsing logic so the Android
 * client can do light offline intent-matching for command routing hints
 * (not authoritative — the backend always has the final say).
 */
class IntentParserTest {

    private val parser = IntentParser()

    // ── Screenshot ─────────────────────────────────────────────────────────

    @Test fun `take a screenshot`()    { assertEquals("take_screenshot", parser.parse("Take a screenshot")) }
    @Test fun `screen shot two words`() { assertEquals("take_screenshot", parser.parse("take a screen shot please")) }
    @Test fun `capture screen`()       { assertEquals("take_screenshot", parser.parse("Capture my screen now")) }

    // ── File search ────────────────────────────────────────────────────────

    @Test fun `find pdf`()             { assertEquals("search_local_files", parser.parse("Find the PDF I downloaded")) }
    @Test fun `search document`()      { assertEquals("search_local_files", parser.parse("Search for that document from last week")) }
    @Test fun `find downloaded file`() { assertEquals("search_local_files", parser.parse("I need that file I downloaded yesterday")) }

    // ── Reminder ───────────────────────────────────────────────────────────

    @Test fun `remind me`()            { assertEquals("create_reminder", parser.parse("Remind me tomorrow at 9 AM to call the supplier")) }
    @Test fun `set alarm`()            { assertEquals("create_reminder", parser.parse("Set an alarm for 7 AM")) }
    @Test fun `alert me`()             { assertEquals("create_reminder", parser.parse("Alert me at 3 PM")) }
    @Test fun `reminder`()             { assertEquals("create_reminder", parser.parse("Create a reminder for my meeting")) }

    // ── Web search ─────────────────────────────────────────────────────────

    @Test fun `search the web`()       { assertEquals("web_search", parser.parse("Search the web for ESP32 DevKit price")) }
    @Test fun `look up`()              { assertEquals("web_search", parser.parse("Look up how to set up FastAPI")) }
    @Test fun `find online`()          { assertEquals("web_search", parser.parse("Find online the cheapest Lagos flights")) }
    @Test fun `cheapest`()             { assertEquals("web_search", parser.parse("Cheapest iPhone 15 in Nigeria")) }

    // ── Open app ───────────────────────────────────────────────────────────

    @Test fun `open whatsapp`()        { assertEquals("open_app", parser.parse("Open WhatsApp")) }
    @Test fun `launch chrome`()        { assertEquals("open_app", parser.parse("Launch Chrome browser")) }
    @Test fun `open gmail`()           { assertEquals("open_app", parser.parse("Open Gmail please")) }

    // ── Send message ───────────────────────────────────────────────────────

    @Test fun `send message`()         { assertEquals("send_message", parser.parse("Send a message to John")) }
    @Test fun `whatsapp message`()     { assertEquals("send_message", parser.parse("Send a WhatsApp message to Mama")) }

    // ── Payment ────────────────────────────────────────────────────────────

    @Test fun `pay`()                  { assertEquals("make_payment", parser.parse("Pay John 5 USDC")) }
    @Test fun `send money`()           { assertEquals("make_payment", parser.parse("Send money to my sister")) }
    @Test fun `transfer money`()       { assertEquals("make_payment", parser.parse("Transfer ₦5000 to my account")) }

    // ── Conversational fallback ────────────────────────────────────────────

    @Test fun `hello`()                { assertEquals("conversational", parser.parse("Hello NIA")) }
    @Test fun `how are you`()          { assertEquals("conversational", parser.parse("How are you doing today?")) }
    @Test fun `empty string`()         { assertEquals("conversational", parser.parse("")) }
    @Test fun `gibberish`()            { assertEquals("conversational", parser.parse("asdfghjklqwerty")) }

    // ── Case insensitivity ─────────────────────────────────────────────────

    @Test fun `uppercase`()            { assertEquals("take_screenshot", parser.parse("TAKE A SCREENSHOT")) }
    @Test fun `mixed case`()           { assertEquals("create_reminder", parser.parse("REMIND Me At 9 am")) }
}

// ── IntentParser (Android-side offline classifier) ────────────────────────

/**
 * Lightweight, deterministic intent classifier that runs locally on the device.
 * Used only as a routing hint and for pre-flight checks — the backend
 * orchestrator is always the authoritative source of intent.
 *
 * This is intentionally keyword-based (no ML dependency) so it works offline
 * and has zero latency overhead.
 */
class IntentParser {

    data class IntentRule(
        val keywords: List<String>,
        val intentId: String,
    )

    private val rules: List<IntentRule> = listOf(
        IntentRule(listOf("screenshot", "screen shot", "capture screen"), "take_screenshot"),
        IntentRule(listOf("find file", "find pdf", "search file", "search pdf", "find document", "downloaded", "download"), "search_local_files"),
        IntentRule(listOf("remind", "reminder", "set alarm", "create alarm", "alert me"), "create_reminder"),
        IntentRule(listOf("alarm"), "create_reminder"),
        IntentRule(listOf("search the web", "search web", "look up", "find online", "cheapest", "best price", "google"), "web_search"),
        IntentRule(listOf("open app", "open whatsapp", "open chrome", "open gmail", "open spotify", "launch"), "open_app"),
        IntentRule(listOf("send message", "text ", "message to", "whatsapp message"), "send_message"),
        IntentRule(listOf("delete file", "remove file"), "delete_file"),
        IntentRule(listOf("pay ", "payment", "send usdc", "transfer money", "send money"), "make_payment"),
        IntentRule(listOf("read notification", "notification"), "read_notification"),
    )

    fun parse(text: String): String {
        val lower = text.lowercase()
        for (rule in rules) {
            if (rule.keywords.any { lower.contains(it) }) {
                return rule.intentId
            }
        }
        return "conversational"
    }
}
