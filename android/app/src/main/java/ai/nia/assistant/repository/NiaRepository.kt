package ai.nia.assistant.repository

import ai.nia.assistant.api.AssistantRequest
import ai.nia.assistant.api.AssistantResponse
import ai.nia.assistant.api.DeviceContext
import ai.nia.assistant.api.NiaRetrofitClient
import ai.nia.assistant.api.WebSearchRequest
import ai.nia.assistant.api.WebSearchResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * NIA — Repository layer.
 *
 * Single source of truth for all NIA backend calls.
 * Translates network responses into sealed results.
 * No business logic here — that belongs in NiaCommandRouter.
 */
sealed class NiaResult<out T> {
    data class Success<T>(val data: T)           : NiaResult<T>()
    data class Error(val message: String,
                     val code: Int? = null)      : NiaResult<Nothing>()
    object NetworkUnavailable                    : NiaResult<Nothing>()
    object Timeout                               : NiaResult<Nothing>()
}

class NiaRepository {

    private val api = NiaRetrofitClient.service

    // ── Health check ──────────────────────────────────────────────────────

    suspend fun healthCheck(): NiaResult<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = api.health()
            if (response.isSuccessful && response.body()?.status == "ok") {
                NiaResult.Success(true)
            } else {
                NiaResult.Error("Backend returned ${response.code()}", response.code())
            }
        } catch (e: java.net.SocketTimeoutException) {
            NiaResult.Timeout
        } catch (e: java.io.IOException) {
            NiaResult.NetworkUnavailable
        } catch (e: Exception) {
            NiaResult.Error(e.message ?: "Unknown error")
        }
    }

    // ── Send voice command ────────────────────────────────────────────────

    suspend fun sendCommand(
        text: String,
        sessionId: String,
        confirmedToolIds: List<String>,
        grantedPermissions: Set<String>,
    ): NiaResult<AssistantResponse> = withContext(Dispatchers.IO) {
        try {
            val request = AssistantRequest(
                text             = text,
                sessionId        = sessionId,
                confirmedToolIds = confirmedToolIds,
                deviceContext    = DeviceContext(
                    grantedPermissions = grantedPermissions.toList(),
                ),
            )
            val response = api.sendCommand(request)
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) NiaResult.Success(body)
                else NiaResult.Error("Empty response body", response.code())
            } else {
                NiaResult.Error("Backend error: ${response.code()}", response.code())
            }
        } catch (e: java.net.SocketTimeoutException) {
            NiaResult.Timeout
        } catch (e: java.io.IOException) {
            NiaResult.NetworkUnavailable
        } catch (e: Exception) {
            NiaResult.Error(e.message ?: "Unknown error")
        }
    }

    // ── Web search ────────────────────────────────────────────────────────

    suspend fun webSearch(query: String): NiaResult<WebSearchResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.webSearch(WebSearchRequest(query))
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) NiaResult.Success(body)
                else NiaResult.Error("Empty response body", response.code())
            } else {
                NiaResult.Error("Search failed: ${response.code()}", response.code())
            }
        } catch (e: java.net.SocketTimeoutException) {
            NiaResult.Timeout
        } catch (e: java.io.IOException) {
            NiaResult.NetworkUnavailable
        } catch (e: Exception) {
            NiaResult.Error(e.message ?: "Unknown error")
        }
    }
}
