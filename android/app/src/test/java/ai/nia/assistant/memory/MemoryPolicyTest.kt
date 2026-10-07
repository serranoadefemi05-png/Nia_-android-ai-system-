package ai.nia.assistant.memory

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * NIA — MemoryPolicy Unit Tests
 *
 * Validates the privacy rules that govern what NIA can remember.
 * Core invariant: NIA never auto-stores sensitive keys.
 * Users can always delete their memory.
 */
class MemoryPolicyTest {

    private lateinit var policy: MemoryPolicy
    private lateinit var store: InMemoryStore

    @Before
    fun setUp() {
        policy = MemoryPolicy()
        store  = InMemoryStore()
    }

    // ── Allowed keys (non-sensitive) ───────────────────────────────────────

    @Test
    fun `user name is allowed to be stored`() {
        assertTrue(policy.canStore("user_name", "Demo User", source = "user_explicit"))
    }

    @Test
    fun `language preference is allowed`() {
        assertTrue(policy.canStore("language", "Yoruba", source = "user_explicit"))
    }

    @Test
    fun `location is allowed when user explicitly sets it`() {
        assertTrue(policy.canStore("location", "Lagos", source = "user_explicit"))
    }

    @Test
    fun `reminder title is allowed`() {
        assertTrue(policy.canStore("last_reminder", "Call supplier", source = "inferred"))
    }

    // ── Blocked keys (sensitive) ───────────────────────────────────────────

    @Test
    fun `password is never stored`() {
        assertFalse(policy.canStore("password", "hunter2", source = "inferred"))
    }

    @Test
    fun `private_key is never stored`() {
        assertFalse(policy.canStore("private_key", "0xdeadbeef", source = "inferred"))
    }

    @Test
    fun `secret key is never stored`() {
        assertFalse(policy.canStore("secret", "top-secret-value", source = "inferred"))
    }

    @Test
    fun `api_key is never stored`() {
        assertFalse(policy.canStore("api_key", "sk-abc123", source = "inferred"))
    }

    @Test
    fun `credit_card is never stored`() {
        assertFalse(policy.canStore("credit_card", "4111111111111111", source = "inferred"))
    }

    @Test
    fun `bank_account is never stored`() {
        assertFalse(policy.canStore("bank_account", "0123456789", source = "inferred"))
    }

    @Test
    fun `bvn is never stored`() {
        assertFalse(policy.canStore("bvn", "22222222222", source = "inferred"))
    }

    @Test
    fun `pin is never stored`() {
        assertFalse(policy.canStore("pin", "1234", source = "inferred"))
    }

    // ── Inferred vs explicit ───────────────────────────────────────────────

    @Test
    fun `location can be explicitly set by user`() {
        assertTrue(policy.canStore("location", "Abuja", source = "user_explicit"))
    }

    @Test
    fun `location is blocked when inferred from context`() {
        assertFalse(policy.canStore("gps_location_exact", "6.5244,3.3792", source = "inferred"))
    }

    // ── Store + retrieve ───────────────────────────────────────────────────

    @Test
    fun `allowed key can be stored and retrieved`() {
        store.save("user_name", "Adaeze")
        assertEquals("Adaeze", store.get("user_name"))
    }

    @Test
    fun `missing key returns null`() {
        assertNull(store.get("not_a_key"))
    }

    // ── Delete ─────────────────────────────────────────────────────────────

    @Test
    fun `user can delete a stored entry`() {
        store.save("language", "Igbo")
        assertNotNull(store.get("language"))
        store.delete("language")
        assertNull(store.get("language"))
    }

    @Test
    fun `user can delete all memory`() {
        store.save("name", "Tunde")
        store.save("language", "Yoruba")
        store.save("location", "Lagos")
        store.clearAll()
        assertNull(store.get("name"))
        assertNull(store.get("language"))
        assertNull(store.get("location"))
        assertEquals(0, store.count())
    }

    // ── Policy applied at write time ───────────────────────────────────────

    @Test
    fun `policy-guarded write rejects sensitive key`() {
        val written = policyGuardedWrite(store, policy, "password", "123456", "inferred")
        assertFalse(written)
        assertNull(store.get("password"))
    }

    @Test
    fun `policy-guarded write accepts safe key`() {
        val written = policyGuardedWrite(store, policy, "user_name", "Chidi", "user_explicit")
        assertTrue(written)
        assertEquals("Chidi", store.get("user_name"))
    }
}

// ── MemoryPolicy ──────────────────────────────────────────────────────────

/**
 * Defines what NIA is allowed to remember.
 * Sensitive keys are blocked permanently regardless of source.
 * Certain keys (e.g. exact GPS) are blocked for inferred sources.
 */
class MemoryPolicy {

    private val alwaysBlockedKeys = setOf(
        "password", "private_key", "secret", "api_key", "token",
        "credit_card", "card_number", "bank_account", "account_number",
        "bvn", "nin", "pin", "passphrase", "seed_phrase",
    )

    private val blockedWhenInferred = setOf(
        "gps_location_exact", "gps_lat", "gps_lng", "precise_location",
    )

    fun canStore(key: String, value: String, source: String): Boolean {
        val lower = key.lowercase()

        // Hard block — never store
        if (alwaysBlockedKeys.any { lower.contains(it) }) return false

        // Inferred-only block
        if (source != "user_explicit" && blockedWhenInferred.any { lower.contains(it) }) return false

        return true
    }
}

// ── InMemoryStore (test double for encrypted shared prefs) ────────────────

class InMemoryStore {
    private val data = mutableMapOf<String, String>()

    fun save(key: String, value: String)  { data[key] = value }
    fun get(key: String): String?         = data[key]
    fun delete(key: String)               { data.remove(key) }
    fun clearAll()                        { data.clear() }
    fun count(): Int                      = data.size
}

// ── Helper that applies policy at write time ──────────────────────────────

fun policyGuardedWrite(
    store: InMemoryStore,
    policy: MemoryPolicy,
    key: String,
    value: String,
    source: String,
): Boolean {
    if (!policy.canStore(key, value, source)) return false
    store.save(key, value)
    return true
}
