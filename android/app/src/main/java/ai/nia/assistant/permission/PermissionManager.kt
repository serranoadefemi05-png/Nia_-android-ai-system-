package ai.nia.assistant.permission

import android.content.Context
import android.content.pm.PackageManager
import androidx.activity.result.ActivityResultLauncher
import androidx.core.content.ContextCompat

/**
 * NIA — Permission Manager
 *
 * Tracks which Android permissions NIA currently holds and provides
 * helpers to request them just-in-time when a tool needs them.
 *
 * The ActivityResultLauncher is bound from MainActivity.onCreate() so
 * that the ViewModel can request permissions without holding an Activity ref.
 */
class PermissionManager(private val context: Context) {

    private val _grantedPermissions = mutableSetOf<String>()
    val grantedPermissions: Set<String> get() = _grantedPermissions.toSet()

    private var launcher: ActivityResultLauncher<Array<String>>? = null

    // Bind from MainActivity.onCreate()
    fun bind(launcher: ActivityResultLauncher<Array<String>>) {
        this.launcher = launcher
        refreshFromSystem()
    }

    // Called from NiaViewModel.onPermissionsResult()
    fun onPermissionsResult(results: Map<String, Boolean>) {
        results.forEach { (permission, granted) ->
            if (granted) _grantedPermissions.add(permission)
            else _grantedPermissions.remove(permission)
        }
    }

    fun isGranted(permission: String): Boolean =
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED

    fun areAllGranted(permissions: List<String>): Boolean =
        permissions.all { isGranted(it) }

    fun missing(permissions: List<String>): List<String> =
        permissions.filterNot { isGranted(it) }

    fun request(permissions: List<String>) {
        val needed = missing(permissions)
        if (needed.isNotEmpty()) {
            launcher?.launch(needed.toTypedArray())
        }
    }

    private fun refreshFromSystem() {
        // Reflect any permissions granted outside the app (e.g. via Settings).
        val pm = context.packageManager
        try {
            val packageInfo = pm.getPackageInfo(
                context.packageName,
                PackageManager.GET_PERMISSIONS,
            )
            packageInfo.requestedPermissions?.forEachIndexed { i, permission ->
                val flags = packageInfo.requestedPermissionsFlags[i]
                if (flags and PackageManager.GET_PERMISSIONS != 0) {
                    _grantedPermissions.add(permission)
                }
            }
        } catch (_: PackageManager.NameNotFoundException) { /* ignore */ }

        // Also check directly
        _grantedPermissions.removeAll { perm ->
            !isGranted(perm)
        }
    }
}
