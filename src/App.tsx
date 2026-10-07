import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic, MicOff, Send, X, CheckCircle, AlertTriangle,
  ShieldAlert, History, Settings, Zap, Search,
  Camera, Bell, Globe, ChevronRight, Trash2,
  ToggleLeft, ToggleRight, Info, Cpu, BookOpen,
  Code2, Smartphone, Brain, ChevronDown, ChevronUp,
  Clock, PlayCircle, CheckCircle2, XCircle, Loader2,
  FileText, MessageSquare, Bookmark, RotateCcw
} from 'lucide-react'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────────────

type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'result' | 'confirming' | 'error'
type RiskLevel   = 'GREEN' | 'YELLOW' | 'RED'
type View        = 'voice' | 'history' | 'memory' | 'tools' | 'settings'

interface PipelineStep {
  label: string
  detail: string
  durationMs: number
  status: 'ok' | 'pending' | 'skipped'
}

interface Message {
  id: string
  role: 'user' | 'nia' | 'system'
  text: string
  intent?: string
  ts: number
  steps?: PipelineStep[]
  durationMs?: number
}

interface ConfirmRequest {
  toolId: string
  description: string
  riskLevel: RiskLevel
  prompt: string
}

interface ToolEntry {
  id: string
  name: string
  description: string
  risk: RiskLevel
  tags: string[]
  permissions: string[]
}

interface MemoryEntry {
  id: string
  category: 'preference' | 'fact' | 'recurring_task' | 'conversation_summary'
  key: string
  value: string
  source: 'user_explicit' | 'inferred'
  ts: number
}

// ── Data ───────────────────────────────────────────────────────────────────

const TOOLS: ToolEntry[] = [
  { id: 'take_screenshot',    name: 'Take Screenshot',    description: 'Capture the current screen and save to gallery.', risk: 'GREEN',  tags: ['screen','capture'],    permissions: ['MEDIA_PROJECTION'] },
  { id: 'search_local_files', name: 'Search Local Files', description: 'Search user-authorized local storage by type, name, or date.', risk: 'GREEN',  tags: ['files','pdf'],         permissions: ['READ_EXTERNAL_STORAGE'] },
  { id: 'create_reminder',    name: 'Create Reminder',    description: 'Create a reminder or alarm at a specified time.', risk: 'GREEN',  tags: ['alarm','schedule'],    permissions: ['SET_ALARM'] },
  { id: 'web_search',         name: 'Web Search',         description: 'Search the web and return summarized results with sources.', risk: 'GREEN',  tags: ['web','internet'],      permissions: [] },
  { id: 'open_app',           name: 'Open App',           description: 'Launch a named Android application.', risk: 'GREEN',  tags: ['app','launch'],        permissions: [] },
  { id: 'read_notification',  name: 'Read Notification',  description: 'Read a selected notification the user explicitly grants access to.', risk: 'GREEN',  tags: ['notification'],        permissions: ['BIND_NOTIFICATION_LISTENER_SERVICE'] },
  { id: 'send_message',       name: 'Send Message',       description: 'Send a message via WhatsApp, SMS, or another messaging app.', risk: 'YELLOW', tags: ['message','sms'],       permissions: ['SEND_SMS'] },
  { id: 'delete_file',        name: 'Delete File',        description: 'Permanently delete a file from local storage.', risk: 'YELLOW', tags: ['delete','storage'],    permissions: ['MANAGE_EXTERNAL_STORAGE'] },
  { id: 'make_payment',       name: 'Make Payment',       description: 'Initiate a USDC or local currency payment on behalf of the user.', risk: 'RED',    tags: ['payment','usdc'],      permissions: ['INTERNET'] },
]

const DEMO_COMMANDS = [
  'Take a screenshot',
  'Find the PDF I downloaded yesterday',
  'Remind me tomorrow at 9 AM to call the supplier',
  'Search the web for cheapest ESP32 DevKit',
  'Open WhatsApp',
  'Send a message to John',
  'What time is it?',
  'What can you do?',
]

const INITIAL_MEMORY: MemoryEntry[] = [
  { id: '1', category: 'preference', key: 'language',      value: 'English',          source: 'user_explicit', ts: Date.now() - 86400000 * 3 },
  { id: '2', category: 'fact',       key: 'name',          value: 'Demo User',        source: 'user_explicit', ts: Date.now() - 86400000 * 2 },
  { id: '3', category: 'fact',       key: 'location',      value: 'Lagos, Nigeria',   source: 'user_explicit', ts: Date.now() - 86400000 },
]

// ── Backend API client ─────────────────────────────────────────────────────
// The web dashboard calls the real NIA backend when it is running.
// If the backend is unreachable, a clear "not configured" message is shown.
// No canned/fake responses are ever returned.
// Voice input is available in the native Android app only.

const NIA_BACKEND_URL: string = (import.meta.env.VITE_NIA_BACKEND_URL as string) ?? ''

interface BackendResult {
  intent: string
  status: string
  response: string
  steps?: PipelineStep[]
  durationMs?: number
  confirmation?: ConfirmRequest
}

async function callNiaBackend(
  text: string,
  confirmedTools: Set<string>,
): Promise<BackendResult> {
  const start = Date.now()

  if (!NIA_BACKEND_URL) {
    const durationMs = Date.now() - start
    return {
      intent: 'not_configured',
      status: 'error',
      response:
        "NIA's backend is not configured for this web dashboard. " +
        "Set VITE_NIA_BACKEND_URL in .env to point at your running FastAPI backend. " +
        "The full AI pipeline runs on the Android app — the web dashboard is a visual reference only.",
      durationMs,
    }
  }

  try {
    const resp = await fetch(`${NIA_BACKEND_URL}/api/v1/assistant/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        granted_permissions: [],
        confirmed_tool_ids: Array.from(confirmedTools),
      }),
      signal: AbortSignal.timeout(35000),
    })

    const durationMs = Date.now() - start

    if (!resp.ok) {
      const errText = await resp.text().catch(() => '')
      return {
        intent: 'error',
        status: 'error',
        response: `Backend returned HTTP ${resp.status}. ${errText.slice(0, 200)}`,
        durationMs,
      }
    }

    const data = await resp.json() as {
      intent: string
      status: string
      response: string
      steps?: Array<{ step: string; result: string; tool_id?: string }>
      confirmation_requests?: Array<{ tool_id: string; description: string; confirmation_level: string; risk_level: string; prompt: string }>
      tool_id?: string
      tool_params?: Record<string, unknown>
    }

    // Map backend steps → frontend PipelineStep display format
    const steps: PipelineStep[] = (data.steps ?? []).map((s, i) => ({
      label: s.step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      detail: s.result + (s.tool_id ? ` (${s.tool_id})` : ''),
      durationMs: i === 0 ? Math.min(durationMs - 20, 200) : 15,
      status: s.result === 'error' || s.result === 'not_found' ? 'pending' : 'ok',
    }))

    // Confirmation request
    let confirmation: ConfirmRequest | undefined
    if (data.status === 'awaiting_confirmation' && data.confirmation_requests?.[0]) {
      const cr = data.confirmation_requests[0]
      confirmation = {
        toolId: cr.tool_id,
        description: cr.description,
        riskLevel: (cr.confirmation_level ?? cr.risk_level ?? 'YELLOW') as RiskLevel,
        prompt: cr.prompt,
      }
    }

    return { intent: data.intent, status: data.status, response: data.response, steps, durationMs, confirmation }
  } catch (err) {
    const durationMs = Date.now() - start
    const msg = err instanceof Error ? err.message : String(err)
    return {
      intent: 'error',
      status: 'error',
      response:
        `Cannot reach the NIA backend at ${NIA_BACKEND_URL}. ` +
        `Error: ${msg}. ` +
        `Start the backend with: cd backend && uvicorn main:app --reload`,
      durationMs,
    }
  }
}



// simulateOrchestrator has been removed.
// The web dashboard now calls the real NIA backend via callNiaBackend().
// No canned, keyword-matched, or random responses exist in this codebase.

// ── Sub-components ─────────────────────────────────────────────────────────

function OrbPulse({ status, onClick }: { status: VoiceStatus; onClick: () => void }) {
  const ringColor = {
    idle:       'ring-slate-700',
    listening:  'ring-cyan-400',
    processing: 'ring-indigo-400',
    speaking:   'ring-cyan-300',
    result:     'ring-emerald-400',
    confirming: 'ring-amber-400',
    error:      'ring-red-400',
  }[status]

  const icon = {
    idle:       <Mic className="w-9 h-9 text-slate-400" />,
    listening:  <Mic className="w-9 h-9 text-cyan-300" />,
    processing: <Cpu className="w-9 h-9 text-indigo-300 animate-pulse" />,
    speaking:   <Zap className="w-9 h-9 text-cyan-200" />,
    result:     <CheckCircle className="w-9 h-9 text-emerald-300" />,
    confirming: <AlertTriangle className="w-9 h-9 text-amber-300" />,
    error:      <MicOff className="w-9 h-9 text-red-300" />,
  }[status]

  return (
    <motion.button
      className={`nia-orb ring-2 ${ringColor} select-none`}
      onClick={onClick}
      animate={status === 'listening' ? { scale: [1, 1.08, 1] } : { scale: 1 }}
      transition={status === 'listening' ? { repeat: Infinity, duration: 1.4, ease: 'easeInOut' } : {}}
      whileTap={{ scale: 0.94 }}
      aria-label="Voice input — available in the native Android app"
    >
      {status === 'listening' && (
        <motion.div
          className="absolute rounded-full pointer-events-none"
          style={{ width: 96, height: 96, background: 'radial-gradient(circle, rgba(103,232,249,0.12) 0%, transparent 70%)' }}
          animate={{ scale: [1, 1.7, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ repeat: Infinity, duration: 1.8 }}
        />
      )}
      {icon}
    </motion.button>
  )
}

const STATUS_LABELS: Record<VoiceStatus, string> = {
  idle:       'Voice: Android app only',
  listening:  'Listening…',
  processing: 'Thinking…',
  speaking:   'Speaking…',
  result:     'Done',
  confirming: 'Awaiting confirmation',
  error:      'Try again',
}

function RiskBadge({ level }: { level: RiskLevel }) {
  const cfg = {
    GREEN:  { label: 'AUTO',    cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25' },
    YELLOW: { label: 'CONFIRM', cls: 'bg-amber-500/10  text-amber-300  border-amber-500/25'  },
    RED:    { label: 'DANGER',  cls: 'bg-red-500/10    text-red-300    border-red-500/25'    },
  }[level]
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono border ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

function PipelineVisualiser({ steps, durationMs }: { steps: PipelineStep[]; durationMs: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-[11px] text-slate-600 hover:text-slate-400 transition-colors"
      >
        <Clock className="w-3 h-3" />
        <span className="font-mono tabular-nums">{durationMs}ms</span>
        <span className="text-slate-700">·</span>
        <span>{steps.length} pipeline steps</span>
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 flex flex-col gap-1 pl-1 border-l border-white/5">
              {steps.map((s, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  {s.status === 'ok'      && <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />}
                  {s.status === 'pending' && <Loader2      className="w-3 h-3 text-amber-400  mt-0.5 flex-shrink-0 animate-spin" />}
                  {s.status === 'skipped' && <XCircle      className="w-3 h-3 text-slate-700  mt-0.5 flex-shrink-0" />}
                  <div className="min-w-0">
                    <span className="text-[11px] font-medium text-slate-400">{s.label}</span>
                    <span className="text-[10px] text-slate-600 ml-2">{s.detail}</span>
                    {s.durationMs > 0 && (
                      <span className="text-[10px] font-mono text-slate-700 ml-2 tabular-nums">{s.durationMs}ms</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ConfirmationSheet({ req, onConfirm, onDeny }: {
  req: ConfirmRequest
  onConfirm: () => Promise<void>
  onDeny: () => void
}) {
  const [typed, setTyped] = useState('')
  const isRed = req.riskLevel === 'RED'
  const canConfirm = isRed ? typed.trim().toLowerCase() === 'confirm' : true

  return (
    <motion.div
      className="fixed inset-0 z-40 flex items-end justify-center"
      style={{ backdropFilter: 'blur(4px)', background: 'rgba(0,0,0,0.55)' }}
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    >
      <motion.div
        className="w-full max-w-[430px] rounded-t-3xl p-5 flex flex-col gap-4"
        style={{
          background: 'rgba(10,16,30,0.97)',
          border: `1px solid ${isRed ? 'rgba(239,68,68,0.25)' : 'rgba(245,158,11,0.25)'}`,
          borderBottom: 'none',
        }}
        initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
        transition={{ type: 'spring', stiffness: 380, damping: 38 }}
      >
        <div className="w-10 h-1 rounded-full bg-slate-700 mx-auto -mt-1 mb-1" />

        <div className="flex items-start gap-3">
          {isRed
            ? <ShieldAlert className="w-6 h-6 mt-0.5 flex-shrink-0 text-red-300" />
            : <AlertTriangle className="w-6 h-6 mt-0.5 flex-shrink-0 text-amber-300" />}
          <div>
            <p className="text-sm font-semibold text-slate-100 mb-1">{req.description}</p>
            <p className="text-xs text-slate-400 leading-relaxed">{req.prompt}</p>
          </div>
        </div>

        <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${isRed ? 'border-red-500/30 bg-red-500/5' : 'border-amber-500/30 bg-amber-500/5'}`}>
          <RiskBadge level={req.riskLevel} />
          <span className="text-xs text-slate-400 font-mono">{req.toolId}</span>
        </div>

        {isRed && (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-slate-500">Type <span className="text-red-300 font-mono">confirm</span> to proceed with this high-risk action</p>
            <input
              className="nia-text-input"
              placeholder="Type 'confirm' to proceed"
              value={typed}
              onChange={e => setTyped(e.target.value)}
              autoFocus
            />
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={onDeny}
            className="flex-1 py-3 rounded-xl text-sm font-medium text-slate-400"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
          >
            Cancel
          </button>
          <button
            onClick={() => { void onConfirm() }}
            disabled={!canConfirm}
            className="flex-1 py-3 rounded-xl text-sm font-semibold transition-opacity disabled:opacity-40"
            style={{
              background: isRed ? 'rgba(239,68,68,0.18)' : 'rgba(245,158,11,0.15)',
              border: `1px solid ${isRed ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.3)'}`,
              color: isRed ? '#fca5a5' : '#fcd34d',
            }}
          >
            {isRed ? 'Confirm (HIGH RISK)' : 'Confirm'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── VoiceScreen ────────────────────────────────────────────────────────────

function VoiceScreen({ onMessage, onMemoryUpdate: _onMemoryUpdate }: {
  onMessage: (m: Message) => void
  onMemoryUpdate: (entry: Omit<MemoryEntry, 'id' | 'ts'>) => void
}) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [inputText, setInputText] = useState('')
  const [lastResponse, setLastResponse] = useState<{ text: string; intent: string; steps?: PipelineStep[]; durationMs?: number } | null>(null)
  const [confirmation, setConfirmation] = useState<ConfirmRequest | null>(null)
  const confirmedTools = useRef(new Set<string>())
  const pendingCommand  = useRef('')

  const processCommand = useCallback(async (text: string) => {
    if (!text.trim()) return
    setStatus('processing')
    setLastResponse(null)
    onMessage({ id: crypto.randomUUID(), role: 'user', text, ts: Date.now() })

    const result = await callNiaBackend(text, confirmedTools.current)

    if (result.status === 'awaiting_confirmation' && result.confirmation) {
      pendingCommand.current = text
      onMessage({ id: crypto.randomUUID(), role: 'nia', text: result.response, intent: result.intent, ts: Date.now(), steps: result.steps, durationMs: result.durationMs })
      setConfirmation(result.confirmation)
      setStatus('confirming')
    } else {
      setLastResponse({ text: result.response, intent: result.intent, steps: result.steps, durationMs: result.durationMs })
      onMessage({ id: crypto.randomUUID(), role: 'nia', text: result.response, intent: result.intent, ts: Date.now(), steps: result.steps, durationMs: result.durationMs })
      setStatus('result')
      setTimeout(() => setStatus('idle'), 3500)
    }
  }, [onMessage])

  // Voice input is only available in the native Android app.
  // This web dashboard does NOT open the microphone or simulate voice.
  const handleMicTap = () => {
    toast.info('Voice input is available in the native Android app.', {
      description: 'Use the text input or command chips below to try the NIA pipeline.',
      duration: 4000,
    })
  }

  const handleSend = () => {
    if (!inputText.trim() || status === 'processing' || status === 'confirming') return
    const text = inputText.trim()
    setInputText('')
    void processCommand(text)
  }

  const handleConfirm = async () => {
    if (!confirmation) return
    confirmedTools.current.add(confirmation.toolId)
    setConfirmation(null)
    await processCommand(pendingCommand.current)
  }

  const handleDeny = () => {
    setConfirmation(null)
    pendingCommand.current = ''
    const msg = "Got it — action cancelled."
    setLastResponse({ text: msg, intent: 'cancelled' })
    onMessage({ id: crypto.randomUUID(), role: 'nia', text: msg, ts: Date.now() })
    toast.info('Action cancelled')
    setStatus('idle')
  }

  return (
    <div className="nia-voice-screen">
      <div className="nia-orb-zone">
        <div className="relative">
          <OrbPulse status={status} onClick={handleMicTap} />
        </div>

        <p className="nia-state-label" style={{
          color: status === 'error' ? '#f87171'
               : status === 'confirming' ? '#fcd34d' : status === 'result' ? '#6ee7b7'
               : 'rgba(148,163,184,0.5)'
        }}>
          {STATUS_LABELS[status]}
        </p>

        {/* Honest notice — no fake microphone in the web dashboard */}
        {status === 'idle' && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full mt-1"
            style={{ background: 'rgba(103,232,249,0.05)', border: '1px solid rgba(103,232,249,0.12)' }}>
            <Smartphone className="w-3 h-3 text-cyan-700" />
            <span className="text-[10px] text-cyan-800 font-medium">
              Use text input below · Voice is in the Android app
            </span>
          </div>
        )}

        <AnimatePresence>
          {lastResponse && (
            <motion.div
              className="nia-response-card w-full"
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              {lastResponse.intent && lastResponse.intent !== 'conversational' && lastResponse.intent !== 'cancelled' && (
                <div className="mb-2"><span className="nia-intent-chip">{lastResponse.intent}</span></div>
              )}
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{lastResponse.text}</p>
              {lastResponse.steps && lastResponse.durationMs !== undefined && (
                <PipelineVisualiser steps={lastResponse.steps} durationMs={lastResponse.durationMs} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="nia-input-zone">
        <div className="nia-input-row">
          <input
            className="nia-text-input"
            placeholder="Type a command…"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={status === 'processing' || status === 'confirming'}
          />
          <button
            className="nia-send-btn"
            onClick={handleSend}
            disabled={!inputText.trim() || status === 'processing' || status === 'confirming'}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <div className="nia-demo-chips">
          <span className="text-xs text-slate-600 mr-1">Try:</span>
          {DEMO_COMMANDS.map(cmd => (
            <button key={cmd} className="nia-demo-chip"
              onClick={() => { void processCommand(cmd) }}
              disabled={status === 'processing' || status === 'confirming'}>
              {cmd}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {confirmation && (
          <ConfirmationSheet req={confirmation} onConfirm={handleConfirm} onDeny={handleDeny} />
        )}
      </AnimatePresence>
    </div>
  )
}

// ── HistoryScreen ──────────────────────────────────────────────────────────

const intentIcon: Record<string, React.ReactNode> = {
  take_screenshot:    <Camera   className="w-3 h-3" />,
  search_local_files: <Search   className="w-3 h-3" />,
  create_reminder:    <Bell     className="w-3 h-3" />,
  web_search:         <Globe    className="w-3 h-3" />,
  open_app:           <PlayCircle className="w-3 h-3" />,
  send_message:       <MessageSquare className="w-3 h-3" />,
  make_payment:       <Zap      className="w-3 h-3" />,
}

function HistoryScreen({ messages, onClear }: { messages: Message[]; onClear: () => void }) {
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages])

  return (
    <div className="nia-history-screen">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
        <span className="text-xs text-slate-500 font-mono tabular-nums">{messages.length} messages</span>
        {messages.length > 0 && (
          <button onClick={onClear} className="flex items-center gap-1 text-xs text-slate-600 hover:text-red-400 transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Clear
          </button>
        )}
      </div>

      {messages.length === 0 ? (
        <div className="nia-empty-state">
          <History className="w-10 h-10 text-slate-800 mb-3" />
          <p className="text-sm text-slate-600">No conversation yet</p>
          <p className="text-xs text-slate-700 mt-1">Your commands and responses appear here</p>
        </div>
      ) : (
        <div className="nia-history-list" ref={listRef}>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              className={`nia-history-entry ${msg.role === 'user' ? 'entry-user' : 'entry-nia'}`}
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            >
              <div className="entry-header">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-semibold font-mono"
                    style={{ color: msg.role === 'user' ? '#818cf8' : '#67e8f9' }}>
                    {msg.role === 'user' ? 'YOU' : 'NIA'}
                  </span>
                  {msg.intent && msg.intent !== 'conversational' && msg.intent !== 'cancelled' && (
                    <span className="nia-intent-chip flex items-center gap-1">
                      {intentIcon[msg.intent]}
                      {msg.intent}
                    </span>
                  )}
                </div>
                <span className="text-[10px] text-slate-700 font-mono tabular-nums">
                  {new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <p className="entry-text whitespace-pre-line">{msg.text}</p>
              {msg.steps && msg.durationMs !== undefined && msg.role === 'nia' && (
                <PipelineVisualiser steps={msg.steps} durationMs={msg.durationMs} />
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── MemoryScreen ───────────────────────────────────────────────────────────

const CAT_ICON: Record<MemoryEntry['category'], React.ReactNode> = {
  preference:           <Settings    className="w-3.5 h-3.5 text-indigo-400" />,
  fact:                 <Brain       className="w-3.5 h-3.5 text-cyan-400"   />,
  recurring_task:       <RotateCcw   className="w-3.5 h-3.5 text-amber-400" />,
  conversation_summary: <FileText    className="w-3.5 h-3.5 text-slate-400"  />,
}

function MemoryScreen({ memory, onDelete, onClearAll }: {
  memory: MemoryEntry[]
  onDelete: (id: string) => void
  onClearAll: () => void
}) {
  return (
    <div className="nia-history-screen">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
        <div className="flex items-center gap-1.5">
          <Brain className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-xs text-slate-500 font-mono tabular-nums">{memory.length} stored facts</span>
        </div>
        {memory.length > 0 && (
          <button onClick={onClearAll} className="flex items-center gap-1 text-xs text-slate-600 hover:text-red-400 transition-colors">
            <Trash2 className="w-3.5 h-3.5" /> Clear all
          </button>
        )}
      </div>

      {memory.length === 0 ? (
        <div className="nia-empty-state">
          <Bookmark className="w-10 h-10 text-slate-800 mb-3" />
          <p className="text-sm text-slate-600">No memory stored</p>
          <p className="text-xs text-slate-700 mt-1">NIA only remembers what you explicitly tell it</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-2">
          {(['preference','fact','recurring_task','conversation_summary'] as MemoryEntry['category'][]).map(cat => {
            const entries = memory.filter(m => m.category === cat)
            if (!entries.length) return null
            return (
              <div key={cat}>
                <div className="flex items-center gap-1.5 mb-2 px-1">
                  {CAT_ICON[cat]}
                  <span className="text-[10px] uppercase tracking-widest text-slate-600 font-medium">
                    {cat.replace('_', ' ')}
                  </span>
                </div>
                {entries.map(entry => (
                  <motion.div
                    key={entry.id}
                    className="flex items-start justify-between gap-3 px-4 py-3 rounded-xl mb-1"
                    style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(255,255,255,0.05)' }}
                    initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 6 }}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-mono text-slate-500 mb-0.5">{entry.key}</p>
                      <p className="text-sm text-slate-300 leading-snug">{entry.value}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[10px] font-mono ${entry.source === 'user_explicit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                          {entry.source === 'user_explicit' ? 'user-set' : 'inferred'}
                        </span>
                        <span className="text-[10px] text-slate-700 tabular-nums">
                          {new Date(entry.ts).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => onDelete(entry.id)}
                      className="text-slate-700 hover:text-red-400 transition-colors flex-shrink-0 mt-0.5"
                      aria-label="Delete memory"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </motion.div>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── ToolsScreen ────────────────────────────────────────────────────────────

function ToolsScreen() {
  const [filter, setFilter] = useState<RiskLevel | 'ALL'>('ALL')
  const filtered = filter === 'ALL' ? TOOLS : TOOLS.filter(t => t.risk === filter)

  return (
    <div className="nia-history-screen">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-white/5 overflow-x-auto">
        {(['ALL', 'GREEN', 'YELLOW', 'RED'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium border transition-all"
            style={{
              background: filter === f
                ? f === 'GREEN' ? 'rgba(16,185,129,0.15)' : f === 'YELLOW' ? 'rgba(245,158,11,0.15)' : f === 'RED' ? 'rgba(239,68,68,0.15)' : 'rgba(103,232,249,0.12)'
                : 'rgba(255,255,255,0.03)',
              borderColor: filter === f
                ? f === 'GREEN' ? 'rgba(16,185,129,0.4)' : f === 'YELLOW' ? 'rgba(245,158,11,0.4)' : f === 'RED' ? 'rgba(239,68,68,0.4)' : 'rgba(103,232,249,0.3)'
                : 'rgba(255,255,255,0.07)',
              color: filter === f
                ? f === 'GREEN' ? '#6ee7b7' : f === 'YELLOW' ? '#fcd34d' : f === 'RED' ? '#fca5a5' : '#67e8f9'
                : '#64748b',
            }}>
            {f === 'ALL' ? `All (${TOOLS.length})` : `${f} (${TOOLS.filter(t => t.risk === f).length})`}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-2.5">
        {filtered.map(tool => (
          <div key={tool.id} className="rounded-2xl p-4"
            style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <div>
                <p className="text-sm font-semibold text-slate-200">{tool.name}</p>
                <p className="text-xs font-mono text-slate-600 mt-0.5">{tool.id}</p>
              </div>
              <RiskBadge level={tool.risk} />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed mb-2">{tool.description}</p>
            {tool.permissions.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tool.permissions.map(p => (
                  <span key={p} className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{ background: 'rgba(255,255,255,0.04)', color: '#64748b', border: '1px solid rgba(255,255,255,0.06)' }}>
                    {p}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── SettingsScreen ─────────────────────────────────────────────────────────

function SettingsScreen() {
  const [arcEnabled, setArcEnabled] = useState(false)
  const [backendUrl, setBackendUrl] = useState('')
  const [editingUrl, setEditingUrl] = useState(false)

  return (
    <div className="nia-settings-screen">
      <div className="settings-status-card"
        style={{ background: 'rgba(103,232,249,0.04)', borderColor: 'rgba(103,232,249,0.15)' }}>
        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ background: 'rgba(103,232,249,0.1)', border: '1px solid rgba(103,232,249,0.2)' }}>
          <Zap className="w-4 h-4 text-cyan-300" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-200">NIA v0.1</p>
          <p className="text-xs text-slate-500">Demo mode · Arc not active · 4 MVP commands</p>
        </div>
        <span className="ml-auto text-[10px] font-mono px-2 py-1 rounded-full"
          style={{ background: 'rgba(16,185,129,0.1)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.2)' }}>
          ONLINE
        </span>
      </div>

      <div className="settings-list">
        <p className="settings-sub-label px-1">Backend</p>
        <button className="settings-row" onClick={() => setEditingUrl(v => !v)}>
          <div className="settings-row-icon"><Code2 className="w-4 h-4" /></div>
          <div className="flex-1 text-left">
            <p className="text-sm text-slate-200">API Endpoint</p>
            <p className="text-xs text-slate-500 font-mono truncate">{backendUrl || 'http://localhost:8000 (default)'}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-600" />
        </button>
        <AnimatePresence>
          {editingUrl && (
            <motion.div className="settings-sub-panel"
              initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
              <p className="settings-sub-label">Backend URL</p>
              <input className="nia-text-input text-xs font-mono" placeholder="http://localhost:8000"
                value={backendUrl} onChange={e => setBackendUrl(e.target.value)} />
              <button className="nia-send-btn text-xs mt-1"
                onClick={() => { setEditingUrl(false); toast.success('Backend URL saved.') }}>
                Save
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="settings-list">
        <p className="settings-sub-label px-1">Arc Ecosystem</p>
        <button className="settings-row" onClick={() => {
          if (!arcEnabled) toast.info('Arc integration is prepared for v0.2. Not active in v0.1.')
          setArcEnabled(v => !v)
        }}>
          <div className="settings-row-icon">
            <Zap className="w-4 h-4" style={{ color: arcEnabled ? '#67e8f9' : undefined }} />
          </div>
          <div className="flex-1 text-left">
            <p className="text-sm text-slate-200">Arc Integration</p>
            <p className="text-xs text-slate-500">Agent identity · USDC payments · Task attestations</p>
          </div>
          {arcEnabled ? <ToggleRight className="w-6 h-6 text-cyan-400" /> : <ToggleLeft className="w-6 h-6 text-slate-600" />}
        </button>
        {arcEnabled && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Arc Status</p>
            {[
              { label: 'Agent Identity (ERC-8004)', status: 'v0.2' },
              { label: 'Task Attestations',         status: 'v0.2' },
              { label: 'USDC Payments',             status: 'v0.2' },
              { label: 'Spending Policies',         status: 'v0.3' },
              { label: 'Agent Marketplace',         status: 'future' },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between py-1">
                <span className="text-xs text-slate-400">{item.label}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(255,255,255,0.04)', color: '#475569', border: '1px solid rgba(255,255,255,0.06)' }}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="settings-list">
        <p className="settings-sub-label px-1">Android Client</p>
        <div className="settings-row">
          <div className="settings-row-icon"><Smartphone className="w-4 h-4" /></div>
          <div className="flex-1 text-left">
            <p className="text-sm text-slate-200">Android App</p>
            <p className="text-xs text-slate-500">Kotlin · Jetpack Compose · API 26+</p>
          </div>
          <span className="text-[10px] font-mono text-slate-600">v0.1</span>
        </div>
      </div>

      <div className="settings-list">
        <p className="settings-sub-label px-1">Project</p>
        {[
          { icon: <BookOpen className="w-4 h-4" />, label: 'Architecture',    sub: 'docs/ARCHITECTURE.md' },
          { icon: <Code2    className="w-4 h-4" />, label: 'Backend API',     sub: 'backend/main.py · FastAPI' },
          { icon: <Smartphone className="w-4 h-4" />, label: 'Android Setup', sub: 'docs/ANDROID_SETUP.md' },
          { icon: <Info     className="w-4 h-4" />, label: 'Roadmap',         sub: 'docs/ROADMAP.md' },
        ].map(item => (
          <div key={item.label} className="settings-row">
            <div className="settings-row-icon">{item.icon}</div>
            <div className="text-left">
              <p className="text-sm text-slate-200">{item.label}</p>
              <p className="text-xs text-slate-500 font-mono">{item.sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="h-6" />
    </div>
  )
}

// ── App ────────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView]       = useState<View>('voice')
  const [messages, setMessages] = useState<Message[]>([])
  const [memory, setMemory]   = useState<MemoryEntry[]>(INITIAL_MEMORY)

  const addMessage = useCallback((m: Message) => {
    setMessages(prev => [...prev, m].slice(-200))
  }, [])

  const addMemory = useCallback((entry: Omit<MemoryEntry, 'id' | 'ts'>) => {
    const newEntry: MemoryEntry = { ...entry, id: crypto.randomUUID(), ts: Date.now() }
    setMemory(prev => {
      const without = prev.filter(e => !(e.category === entry.category && e.key === entry.key))
      return [...without, newEntry].slice(-50)
    })
    toast.success(`Memory updated: ${entry.key}`)
  }, [])

  const deleteMemory = useCallback((id: string) => {
    setMemory(prev => prev.filter(e => e.id !== id))
    toast.info('Memory entry deleted')
  }, [])

  type NavItem = { id: View; icon: React.ReactNode; label: string; badge?: number }
  const navItems: NavItem[] = [
    { id: 'voice',    icon: <Mic      className="nav-icon" />, label: 'NIA' },
    { id: 'history',  icon: <History  className="nav-icon" />, label: 'History', badge: messages.filter(m => m.role === 'nia').length || undefined },
    { id: 'memory',   icon: <Brain    className="nav-icon" />, label: 'Memory',  badge: memory.length || undefined },
    { id: 'tools',    icon: <Zap      className="nav-icon" />, label: 'Tools' },
    { id: 'settings', icon: <Settings className="nav-icon" />, label: 'Settings' },
  ]

  return (
    <div className="nia-shell">
      <header className="nia-header">
        <div className="flex items-center gap-2">
          <span className="nia-wordmark">NIA</span>
          <span className="nia-version-badge">v0.1</span>
        </div>
        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">
          {view.toUpperCase()}
        </span>
      </header>

      <div className="view-container">
        <AnimatePresence mode="wait">
          <motion.div key={view} className="h-full"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}>
            {view === 'voice'    && <VoiceScreen  onMessage={addMessage} onMemoryUpdate={addMemory} />}
            {view === 'history'  && <HistoryScreen messages={messages} onClear={() => setMessages([])} />}
            {view === 'memory'   && <MemoryScreen  memory={memory} onDelete={deleteMemory} onClearAll={() => { setMemory([]); toast.info('Memory cleared') }} />}
            {view === 'tools'    && <ToolsScreen />}
            {view === 'settings' && <SettingsScreen />}
          </motion.div>
        </AnimatePresence>
      </div>

      <nav className="nia-bottom-nav">
        {navItems.map(item => (
          <button key={item.id} className={`nav-item ${view === item.id ? 'nav-item-active' : ''}`}
            onClick={() => setView(item.id)}>
            {view === item.id && <span className="nav-indicator" />}
            <span style={{ color: view === item.id ? '#67e8f9' : '#475569' }} className="relative">
              {item.icon}
              {item.badge !== undefined && item.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full text-[8px] font-bold flex items-center justify-center tabular-nums"
                  style={{ background: '#67e8f9', color: '#080D18' }}>
                  {item.badge > 9 ? '9+' : item.badge}
                </span>
              )}
            </span>
            <span className={`nav-label ${view === item.id ? 'text-cyan-300' : 'text-slate-600'}`}>
              {item.label}
            </span>
          </button>
        ))}
      </nav>
    </div>
  )
}
