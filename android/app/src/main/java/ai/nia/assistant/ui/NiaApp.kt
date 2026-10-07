package ai.nia.assistant.ui

import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.nia.assistant.ui.screens.ConfirmationSheet
import ai.nia.assistant.ui.screens.HistoryScreen
import ai.nia.assistant.ui.screens.MemoryScreen
import ai.nia.assistant.ui.screens.SettingsScreen
import ai.nia.assistant.ui.screens.ToolsScreen
import ai.nia.assistant.ui.screens.VoiceScreen
import ai.nia.assistant.ui.theme.*

enum class NiaTab { VOICE, HISTORY, MEMORY, TOOLS, SETTINGS }

@Composable
fun NiaApp(viewModel: NiaViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    var currentTab by remember { mutableStateOf(NiaTab.VOICE) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NiaBackground),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            NiaTopBar(tab = currentTab, isOnline = uiState.isOnline)

            Box(modifier = Modifier.weight(1f)) {
                AnimatedContent(
                    targetState = currentTab,
                    transitionSpec = { fadeIn(tween(160)) togetherWith fadeOut(tween(120)) },
                    label = "tab-content",
                ) { tab ->
                    when (tab) {
                        NiaTab.VOICE    -> VoiceScreen(viewModel = viewModel, uiState = uiState)
                        NiaTab.HISTORY  -> HistoryScreen(messages = uiState.conversation)
                        NiaTab.MEMORY   -> MemoryScreen(viewModel = viewModel)
                        NiaTab.TOOLS    -> ToolsScreen()
                        NiaTab.SETTINGS -> SettingsScreen(viewModel = viewModel, uiState = uiState)
                    }
                }
            }

            NiaBottomNav(currentTab = currentTab, onTabSelected = { currentTab = it })
        }

        // Confirmation overlay slides up from bottom
        AnimatedVisibility(
            visible = uiState.pendingConfirmation != null,
            enter   = slideInVertically(initialOffsetY = { it }) + fadeIn(),
            exit    = slideOutVertically(targetOffsetY = { it }) + fadeOut(),
        ) {
            uiState.pendingConfirmation?.let { req ->
                ConfirmationSheet(
                    request   = req,
                    onConfirm = { viewModel.onConfirm(req.toolId) },
                    onDeny    = { viewModel.onDeny() },
                )
            }
        }
    }
}

@Composable
private fun NiaTopBar(tab: NiaTab, isOnline: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("NIA", color = NiaCyan, fontSize = 22.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.5).sp)
            Surface(shape = MaterialTheme.shapes.small, color = NiaBorder) {
                Text(
                    text = "v0.1",
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                    color = NiaTextMuted, fontSize = 10.sp, fontWeight = FontWeight.Medium,
                )
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (!isOnline) {
                Surface(shape = MaterialTheme.shapes.small, color = NiaRed.copy(alpha = 0.15f)) {
                    Text(
                        text = "OFFLINE",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        color = NiaRed, fontSize = 9.sp, fontWeight = FontWeight.Bold,
                    )
                }
            }
            Text(tab.name, color = NiaTextMuted, fontSize = 10.sp, letterSpacing = 0.12.sp)
        }
    }
}

@Composable
private fun NiaBottomNav(currentTab: NiaTab, onTabSelected: (NiaTab) -> Unit) {
    NavigationBar(
        containerColor = NiaBackground.copy(alpha = 0.96f),
        tonalElevation = 0.dp,
        modifier = Modifier
            .height(72.dp)
            .navigationBarsPadding(),
    ) {
        NiaTab.entries.forEach { tab ->
            NavigationBarItem(
                selected = currentTab == tab,
                onClick  = { onTabSelected(tab) },
                icon = {
                    Icon(
                        imageVector = when (tab) {
                            NiaTab.VOICE    -> Icons.Rounded.Mic
                            NiaTab.HISTORY  -> Icons.Rounded.History
                            NiaTab.MEMORY   -> Icons.Rounded.Psychology
                            NiaTab.TOOLS    -> Icons.Rounded.FlashOn
                            NiaTab.SETTINGS -> Icons.Rounded.Settings
                        },
                        contentDescription = tab.name,
                    )
                },
                label = {
                    Text(
                        text = when (tab) {
                            NiaTab.VOICE    -> "NIA"
                            NiaTab.HISTORY  -> "History"
                            NiaTab.MEMORY   -> "Memory"
                            NiaTab.TOOLS    -> "Tools"
                            NiaTab.SETTINGS -> "Settings"
                        },
                        fontSize = 10.sp,
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor   = NiaCyan,
                    selectedTextColor   = NiaCyan,
                    unselectedIconColor = NiaTextMuted,
                    unselectedTextColor = NiaTextMuted,
                    indicatorColor      = NiaCyan.copy(alpha = 0.12f),
                ),
            )
        }
    }
}
