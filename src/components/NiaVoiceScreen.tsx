import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, X, Wifi, WifiOff, Loader2, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react'
import type { NIAState, ConversationEntry } from '../types/nia'

interface Props {
  niaState: NIAState
  onSendCommand: (text: string) => void
  onCancel: () => void
  currentTranscript: string
  onTranscriptChange: (text: string) => void
  backendOnline: boolean | null
  lastEntry?: ConversationEntry
}

const STATE_LABELS: Record<NIAState, string> = {
  idle: 'How can I help?',
  listening: 'Listening...',
  processing: 'Processing...',
  executing: 'Executing...',
  awaiting_confirmation: 'Confirmation needed',
  completed: 'Done',
  error: 'Something went wrong',
}

const STATE_COLORS: Record<NIAState, string> = {
  idle: 'text-slate-400',
  listening: 'text-cyan-400',
  processing: 'text-indigo-400',
  executing: 'text-violet-400',
  awaiting_confirmation: 'text-amber-400',
  completed: 'text-emerald-400',
  error: 'text-red-400',
}

const STATE_RING_COLORS: Record<NIAState, string> = {
  idle: 'ring-slate-700',
  listening: 'ring-cyan-500',
  processing: 'ring-indigo-500',
  executing: 'ring-violet-500',
  awaiting_confirmation: 'ring-amber-500',
  completed: 'ring-emerald-500',
  error: 'ring-red-500',
}

function StateIcon({ state }: { state: NIAState }) {
  switch (state) {
    case 'listening':
      return <Mic className="w-8 h-8 text-cyan-400" />
    case 'processing':
    case 'executing':
      return <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
    case 'awaiting_confirmation':
      return <HelpCircle className="w-8 h-8 text-amber-400" />
    case 'completed':
      return <CheckCircle2 className="w-8 h-8 text-emerald-400" />
    case 'error':
      return <AlertCircle className="w-8 h-8 text-red-400" />
    default:
      return <Mic className="w-8 h-8 text-slate-500" />
  }
}

// Ripple animation for listening state
function RippleRings({ active }: { active: boolean }) {
  if (!active) return null
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border border-cyan-500/30"
          initial={{ width: 96, height: 96, opacity: 0.7 }}
          animate={{ width: 200, height: 200, opacity: 0 }}
          transition={{
            duration: 2.2,
            repeat: Infinity,
            delay: i * 0.7,
            ease: 'easeOut',
          }}
        />
      ))}
    </div>
  )
}

const DEMO_COMMANDS = [
  'Nia, take a screenshot',
  'Remind me tomorrow at 9am to call the supplier',
  'Find that PDF I downloaded yesterday',
  'Search the web for ESP32 DevKit',
]

export default function NiaVoiceScreen({
  niaState,
  onSendCommand,
  onCancel,
  currentTranscript,
  onTranscriptChange,
  backendOnline,
  lastEntry,
}: Props) {
  const [inputMode, setInputMode] = useState<'text' | 'voice'>('text')
  const [inputText, setInputText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const isActive = niaState !== 'idle' && niaState !== 'completed' && niaState !== 'error'

  const handleSubmit = useCallback(() => {
    const text = (inputMode === 'text' ? inputText : currentTranscript).trim()
    if (!text || isActive) return
    onSendCommand(text)
    setInputText('')
    onTranscriptChange('')
  }, [inputText, currentTranscript, inputMode, isActive, onSendCommand, onTranscriptChange])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleDemo = (cmd: string) => {
    if (isActive) return
    setInputText(cmd)
    setInputMode('text')
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  return (
    <div className="nia-voice-screen">
      {/* Header */}
      <div className="nia-header">
        <div className="flex items-center gap-2">
          <span className="nia-wordmark">NIA</span>
          <span className="nia-version-badge">v0.1</span>
        </div>
        <div className="flex items-center gap-2">
          {backendOnline === true && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <Wifi className="w-3.5 h-3.5" />
              Backend online
            </span>
          )}
          {backendOnline === false && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <WifiOff className="w-3.5 h-3.5" />
              Backend offline
            </span>
          )}
          {backendOnline === null && (
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Checking...
            </span>
          )}
        </div>
      </div>

      {/* Main orb */}
      <div className="nia-orb-zone">
        <div className="relative flex items-center justify-center">
          <RippleRings active={niaState === 'listening'} />
          <motion.button
            className={[
              'nia-orb',
              STATE_RING_COLORS[niaState],
              isActive ? 'cursor-not-allowed' : 'cursor-pointer',
            ].join(' ')}
            whileTap={!isActive ? { scale: 0.93 } : {}}
            whileHover={!isActive ? { scale: 1.04 } : {}}
            onClick={!isActive ? handleSubmit : undefined}
            aria-label={STATE_LABELS[niaState]}
          >
            <StateIcon state={niaState} />
          </motion.button>
        </div>

        {/* State label */}
        <motion.p
          key={niaState}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className={['nia-state-label', STATE_COLORS[niaState]].join(' ')}
        >
          {STATE_LABELS[niaState]}
        </motion.p>

        {/* Cancel button */}
        <AnimatePresence>
          {isActive && (
            <motion.button
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.15 }}
              onClick={onCancel}
              className="nia-cancel-btn"
              aria-label="Cancel"
            >
              <X className="w-4 h-4" />
              Cancel
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Last response */}
      <AnimatePresence>
        {lastEntry?.role === 'nia' && lastEntry.text && (
          <motion.div
            key={lastEntry.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="nia-response-card"
          >
            <p className="text-sm text-slate-300 leading-relaxed">{lastEntry.text}</p>
            {lastEntry.intent && (
              <div className="flex items-center gap-2 mt-2">
                <span className="nia-intent-chip">{lastEntry.intent}</span>
                {lastEntry.durationMs !== undefined && (
                  <span className="text-xs text-slate-600">{lastEntry.durationMs}ms</span>
                )}
              </div>
            )}
            {lastEntry.missingPermissions && lastEntry.missingPermissions.length > 0 && (
              <div className="mt-2 p-2 rounded-lg bg-amber-950/40 border border-amber-800/40">
                <p className="text-xs text-amber-300 font-medium">Permissions needed:</p>
                {lastEntry.missingPermissions.map((p) => (
                  <p key={p} className="text-xs text-amber-400 font-mono mt-0.5">{p}</p>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="nia-input-zone">
        <div className="nia-input-row">
          <input
            ref={inputRef}
            type="text"
            className="nia-text-input"
            placeholder="Type a command..."
            value={inputText}
            onChange={(e) => { setInputText(e.target.value); setInputMode('text') }}
            onKeyDown={handleKeyDown}
            disabled={isActive}
            aria-label="Type a command"
          />
          <motion.button
            whileTap={{ scale: 0.92 }}
            className={['nia-send-btn', isActive ? 'opacity-40 cursor-not-allowed' : ''].join(' ')}
            onClick={handleSubmit}
            disabled={isActive || !inputText.trim()}
            aria-label="Send command"
          >
            <Mic className="w-4 h-4" />
            Send
          </motion.button>
        </div>

        {/* Demo chips */}
        <div className="nia-demo-chips">
          <span className="text-xs text-slate-600 mr-1">Try:</span>
          {DEMO_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              className="nia-demo-chip"
              onClick={() => handleDemo(cmd)}
              disabled={isActive}
            >
              {cmd}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
