package ai.nia.assistant

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.core.content.ContextCompat
import ai.nia.assistant.ui.NiaApp
import ai.nia.assistant.ui.theme.NiaTheme
import ai.nia.assistant.ui.NiaViewModel
import dagger.hilt.android.AndroidEntryPoint

/**
 * NIA — Main Activity (Hilt entry point).
 *
 * Responsibilities:
 *  - Enable edge-to-edge immersive display.
 *  - Request RECORD_AUDIO at launch (core to NIA's voice input).
 *  - Expose a general-purpose permission launcher so NiaViewModel can
 *    request tool-specific permissions just-in-time without holding an
 *    Activity reference.
 *  - Delegate all rendering to NiaApp (Jetpack Compose).
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val viewModel: NiaViewModel by viewModels()

    private lateinit var permissionLauncher: ActivityResultLauncher<Array<String>>

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        permissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions(),
        ) { results ->
            viewModel.onPermissionsResult(results)
        }

        viewModel.bindPermissionLauncher(permissionLauncher)
        requestCorePermissions()

        setContent {
            NiaTheme {
                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0xFF080D18)),
                    color = Color(0xFF080D18),
                ) {
                    NiaApp(viewModel = viewModel)
                }
            }
        }
    }

    private fun requestCorePermissions() {
        val needed = CORE_PERMISSIONS.filter { perm ->
            ContextCompat.checkSelfPermission(this, perm) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) permissionLauncher.launch(needed.toTypedArray())
    }

    companion object {
        val CORE_PERMISSIONS = listOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.INTERNET,
        )
    }
}
