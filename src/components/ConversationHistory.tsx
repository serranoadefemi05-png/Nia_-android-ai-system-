import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { User, Bot, AlertCircle, CheckCircle2, Clock, HelpCircle } from 'lucide-react'
import type { ConversationEntry } from '../types/nia'

interface Props {
  entries: ConversationEntry[]
}

function EntryStateIcon({ entry }: { entry: ConversationEntry }) {
  if (entry.role === 'user') return <User className="w-3.5 h-3.5" />
  switch (entry.state) {
    case 'completed': return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
    case 'error': return <AlertCircle className="w-3.5 h-3.5 text-red-400" />
    case 'awaiting_confirmation': return <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
    default: return <Clock className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
  }
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function ConversationHistory({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries.length])

  return (
    <div className="nia-history-screen">
      <div className="nia-header">
        <span className="nia-wordmark">NIA</span>
        <span className="text-sm text-slate-500">Activity</span>
      </div>

      <div className="nia-history-list">
        {entries.length === 0 ? (
          <div className="nia-empty-state">
            <Bot className="w-10 h-10 text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm text-center">No conversation yet.</p>
            <p className="text-slate-600 text-xs text-center mt-1">Tap the mic and say something.</p>
          </div>
        ) : (
          entries.map((entry) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, x: entry.role === 'user' ? 16 : -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className={['nia-history-entry', entry.role === 'user' ? 'entry-user' : 'entry-nia'].join(' ')}
            >
              <div className="entry-header">
                <div className="flex items-center gap-1.5">
                  <EntryStateIcon entry={entry} />
                  <span className="text-xs font-medium text-slate-500">
                    {entry.role === 'user' ? 'You' : 'NIA'}
                  </span>
                  {entry.intent && (
                    <span className="nia-intent-chip">{entry.intent}</span>
                  )}
                </div>
                <span className="text-xs text-slate-600">{formatTime(entry.timestamp)}</span>
              </div>
              <p className={[
                'entry-text',
                entry.state === 'processing' ? 'animate-pulse' : '',
                entry.state === 'error' ? 'text-red-300' : '',
              ].join(' ')}>
                {entry.text || (entry.state === 'processing' ? 'Processing...' : '')}
              </p>
              {entry.durationMs !== undefined && (
                <p className="text-xs text-slate-700 mt-1 tabular-nums">{entry.durationMs}ms</p>
              )}
              {entry.taskId && (
                <p className="text-xs text-slate-700 font-mono mt-0.5">{entry.taskId}</p>
              )}
              {entry.missingPermissions && entry.missingPermissions.length > 0 && (
                <div className="mt-1.5 p-2 rounded-md bg-amber-950/40 border border-amber-800/40">
                  <p className="text-xs text-amber-300">Missing: {entry.missingPermissions.join(', ')}</p>
                </div>
              )}
            </motion.div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
