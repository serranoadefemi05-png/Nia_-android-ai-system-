export type NIAState =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'executing'
  | 'awaiting_confirmation'
  | 'completed'
  | 'error'

export interface ConversationEntry {
  id: string
  role: 'user' | 'nia'
  text: string
  timestamp: string
  state: 'processing' | 'completed' | 'error' | 'awaiting_confirmation'
  intent?: string
  taskId?: string
  durationMs?: number
  confirmationRequests?: ConfirmationRequest[]
  missingPermissions?: string[]
}

export interface ConfirmationRequest {
  tool_id: string
  description: string
  confirmation_level: 'GREEN' | 'YELLOW' | 'RED'
  prompt: string
  risk_summary: string
}

export interface Settings {
  voice: string
  language: string
  permissions: string[]
  memoryEnabled: boolean
  connectedServices: string[]
  securityLevel: 'standard' | 'strict'
}

export interface ToolInfo {
  id: string
  name: string
  description: string
  risk_level: string
  confirmation_level: string
  required_permissions: string[]
  tags: string[]
}
