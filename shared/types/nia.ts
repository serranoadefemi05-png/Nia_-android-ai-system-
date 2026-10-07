/**
 * NIA — Shared TypeScript Type Definitions
 *
 * These types are the canonical contract between the web dashboard,
 * the backend API, and the Android client (via JSON serialisation).
 *
 * Rule: the Python Pydantic models in backend/app/orchestrator/orchestrator.py
 * and the Kotlin data classes in android/ MUST stay in sync with these.
 * When you add a field here, add it everywhere.
 */

// ── Risk levels ─────────────────────────────────────────────────────────────

export type RiskLevel = 'GREEN' | 'YELLOW' | 'RED'

export type ConfirmationLevel =
  | 'AUTO'         // GREEN — executes immediately
  | 'CONFIRM'      // YELLOW — user must tap Confirm
  | 'TYPED'        // RED — user must type "confirm"

// ── Agent states ─────────────────────────────────────────────────────────────

export type AgentState =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'confirming'
  | 'executing'
  | 'speaking'
  | 'error'

// ── Conversation ─────────────────────────────────────────────────────────────

export interface ConversationMessage {
  id: string
  role: 'user' | 'nia' | 'system'
  text: string
  intent?: string
  toolId?: string
  status?: 'processing' | 'completed' | 'failed' | 'cancelled'
  durationMs?: number
  missingPermissions?: string[]
  ts: number
}

// ── Tools ────────────────────────────────────────────────────────────────────

export interface ToolDefinition {
  id: string
  name: string
  description: string
  risk: RiskLevel
  confirmationLevel: ConfirmationLevel
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
  requiredPermissions: string[]
  tags: string[]
}

// ── Confirmation ─────────────────────────────────────────────────────────────

export interface ConfirmationRequest {
  toolId: string
  toolName: string
  description: string
  riskLevel: RiskLevel
  confirmationLevel: ConfirmationLevel
  prompt: string
  parameters: Record<string, unknown>
}

// ── Orchestrator pipeline ─────────────────────────────────────────────────────

export interface PipelineStep {
  step: string
  input?: unknown
  output?: unknown
  durationMs?: number
  error?: string
}

// ── API request / response ───────────────────────────────────────────────────

export interface AssistantRequest {
  text: string
  grantedPermissions: string[]
  confirmedToolIds: string[]
  sessionId?: string
}

export interface AssistantResponse {
  intent: string
  status: 'completed' | 'failed' | 'awaiting_confirmation' | 'missing_permissions'
  response: string
  steps: PipelineStep[]
  confirmationRequests: ConfirmationRequest[]
  missingPermissions: string[]
  sessionId?: string
}

// ── Memory ──────────────────────────────────────────────────────────────────

export type MemoryCategory =
  | 'preference'
  | 'fact'
  | 'task_history'
  | 'conversation_summary'
  | 'recurring_task'

export interface MemoryEntry {
  id: string
  category: MemoryCategory
  key: string
  value: string
  source: 'user_explicit' | 'inferred'
  createdAt: string
  updatedAt: string
}

// ── Task history ─────────────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface TaskRecord {
  id: string
  userId: string
  command: string
  intent: string
  toolId?: string
  status: TaskStatus
  response?: string
  steps: PipelineStep[]
  durationMs?: number
  createdAt: string
  completedAt?: string
}

// ── Arc integration (prepared, not active in v0.1) ───────────────────────────

export interface ArcAgentIdentity {
  agentId: string       // ERC-8004 token ID
  walletAddress: string
  chainId: number
  name: string
  description: string
}

export interface ArcSpendingPolicy {
  maxPerTransaction: number   // in USDC cents
  maxPerDay: number           // in USDC cents
  requireConfirmationAbove: number
  allowedServiceIds: string[]
}

export interface ArcPaymentIntent {
  serviceId: string
  amount: number   // USDC cents
  description: string
  taskId: string
}

// ── Settings ─────────────────────────────────────────────────────────────────

export interface NiaSettings {
  backendUrl: string
  language: 'en' | 'pcm' | 'yo' | 'ig' | 'ha'
  voiceEnabled: boolean
  ttsEnabled: boolean
  arcEnabled: boolean
  arcSpendingPolicy: ArcSpendingPolicy
  grantedPermissions: string[]
}

export const DEFAULT_SETTINGS: NiaSettings = {
  backendUrl: '',
  language: 'en',
  voiceEnabled: true,
  ttsEnabled: true,
  arcEnabled: false,
  arcSpendingPolicy: {
    maxPerTransaction: 0,
    maxPerDay: 0,
    requireConfirmationAbove: 0,
    allowedServiceIds: [],
  },
  grantedPermissions: [],
}
