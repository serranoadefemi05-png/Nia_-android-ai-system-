package ai.nia.assistant.api

import ai.nia.assistant.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

/**
 * NIA — Retrofit HTTP client factory.
 *
 * The backend URL is read from BuildConfig.NIA_BACKEND_URL, which is
 * injected at build time from local.properties or a CI environment variable.
 * No URLs are hardcoded here; no API keys are stored in the app.
 */
object NiaRetrofitClient {

    private val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG)
            HttpLoggingInterceptor.Level.BODY
        else
            HttpLoggingInterceptor.Level.NONE
    }

    private val okHttpClient: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .addInterceptor { chain ->
            // Attach a NIA-Client header so the backend can identify Android requests.
            val request = chain.request().newBuilder()
                .addHeader("X-NIA-Client",  "android/${BuildConfig.VERSION_NAME}")
                .addHeader("X-NIA-Version", BuildConfig.VERSION_NAME)
                .build()
            chain.proceed(request)
        }
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    val service: NiaApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.NIA_BACKEND_URL.trimEnd('/') + "/")
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(NiaApiService::class.java)
    }
}
