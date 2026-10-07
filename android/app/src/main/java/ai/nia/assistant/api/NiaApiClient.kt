package ai.nia.assistant.api

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import retrofit2.Response
import retrofit2.http.*

// ── Request / Response models ─────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class AssistantRequest(
    @Json(name = "text")               val text: String,
    @Json(name = "session_id")         val sessionId: String,
    @Json(name = "confirmed_tool_ids") val confirmedToolIds: List<String> = emptyList(),
    @Json(name = "device_context")     val deviceContext: DeviceContext? = null,
)

@JsonClass(generateAdapter = true)
data class DeviceContext(
    @Json(name = "platform")         val platform: String = "android",
    @Json(name = "api_level")        val apiLevel: Int    = android.os.Build.VERSION.SDK_INT,
    @Json(name = "granted_permissions") val grantedPermissions: List<String> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class AssistantResponse(
    @Json(name = "intent")              val intent: String,
    @Json(name = "status")              val status: String,
    @Json(name = "response")            val response: String,
    @Json(name = "tool_id")             val toolId: String? = null,
    @Json(name = "tool_params")         val toolParams: Map<String, Any?>? = null,
    @Json(name = "confirmation_level")  val confirmationLevel: String? = null,
    @Json(name = "confirmation_prompt") val confirmationPrompt: String? = null,
    @Json(name = "missing_permissions") val missingPermissions: List<String>? = null,
    @Json(name = "pipeline_steps")      val pipelineSteps: List<PipelineStepDto>? = null,
    @Json(name = "duration_ms")         val durationMs: Long? = null,
)

@JsonClass(generateAdapter = true)
data class PipelineStepDto(
    @Json(name = "label")       val label: String,
    @Json(name = "detail")      val detail: String,
    @Json(name = "duration_ms") val durationMs: Long,
    @Json(name = "status")      val status: String, // "ok" | "pending" | "skipped"
)

@JsonClass(generateAdapter = true)
data class WebSearchRequest(
    @Json(name = "query") val query: String,
)

@JsonClass(generateAdapter = true)
data class WebSearchResponse(
    @Json(name = "query")   val query: String,
    @Json(name = "results") val results: List<SearchResultDto>,
    @Json(name = "summary") val summary: String,
)

@JsonClass(generateAdapter = true)
data class SearchResultDto(
    @Json(name = "title")   val title: String,
    @Json(name = "url")     val url: String,
    @Json(name = "snippet") val snippet: String,
)

@JsonClass(generateAdapter = true)
data class HealthResponse(
    @Json(name = "status")  val status: String,
    @Json(name = "version") val version: String,
)

// ── Retrofit API interface ────────────────────────────────────────────────

interface NiaApiService {

    @POST("api/v1/assistant/command")
    suspend fun sendCommand(@Body request: AssistantRequest): Response<AssistantResponse>

    @POST("api/v1/web/search")
    suspend fun webSearch(@Body request: WebSearchRequest): Response<WebSearchResponse>

    @GET("api/v1/health")
    suspend fun health(): Response<HealthResponse>
}
