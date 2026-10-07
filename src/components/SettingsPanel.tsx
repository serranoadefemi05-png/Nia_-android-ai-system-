import { useState } from 'react'
import {
  Mic, Globe, ShieldCheck, Brain, Plug, Lock, History,
  ChevronRight, CheckCircle2, Circle, Server
} from 'lucide-react'
import type { Settings } from '../types/nia'

interface Props {
  settings: Settings
  onSettingsChange: (s: Settings) => void
  backendOnline: boolean | null
}

type Section = 'voice' | 'language' | 'permissions' | 'memory' | 'services' | 'security' | 'activity' | null

const ANDROID_PERMISSIONS = [
  { id: 'MEDIA_PROJECTION', label: 'Screen Capture', desc: 'Required for screenshot tool', required: true },
  { id: 'READ_EXTERNAL_STORAGE', label: 'Storage Read', desc: 'Required for file search', required: true },
  { id: 'SET_ALARM', label: 'Set Alarms', desc: 'Required for reminders', required: true },
  { id: 'SCHEDULE_EXACT_ALARM', label: 'Exact Alarms', desc: 'Precise reminder scheduling', required: true },
  { id: 'BIND_NOTIFICATION_LISTENER_SERVICE', label: 'Notifications', desc: 'Read selected notifications', required: false },
  { id: 'SEND_SMS', label: 'Send SMS', desc: 'Send messages (HIGH risk)', required: false },
  { id: 'INTERNET', label: 'Internet', desc: 'Web search and backend', required: true },
]

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'pcm', label: 'Nigerian Pidgin (planned v0.3)' },
  { code: 'yo', label: 'Yoruba (planned v0.4)' },
  { code: 'ig', label: 'Igbo (planned v0.4)' },
  { code: 'ha', label: 'Hausa (planned v0.4)' },
]

function SectionRow({
  icon,
  label,
  value,
  active,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  value?: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={['settings-row', active ? 'settings-row-active' : ''].join(' ')}
    >
      <div className="settings-row-icon">{icon}</div>
      <div className="flex-1 text-left">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        {value && <p className="text-xs text-slate-500 mt-0.5">{value}</p>}
      </div>
      <ChevronRight className={['w-4 h-4 text-slate-600 transition-transform duration-200', active ? 'rotate-90 text-cyan-400' : ''].join(' ')} />
    </button>
  )
}

export default function SettingsPanel({ settings, onSettingsChange, backendOnline }: Props) {
  const [activeSection, setActiveSection] = useState<Section>(null)

  const toggle = (section: Section) => setActiveSection((prev) => prev === section ? null : section)

  const togglePermission = (id: string) => {
    const current = settings.permissions
    const next = current.includes(id)
      ? current.filter((p) => p !== id)
      : [...current, id]
    onSettingsChange({ ...settings, permissions: next })
  }

  return (
    <div className="nia-settings-screen">
      <div className="nia-header">
        <span className="nia-wordmark">NIA</span>
        <span className="text-sm text-slate-500">Settings</span>
      </div>

      {/* Backend status card */}
      <div className={[
        'settings-status-card',
        backendOnline === true ? 'border-emerald-800/40 bg-emerald-950/30'
          : backendOnline === false ? 'border-red-800/40 bg-red-950/20'
          : 'border-slate-800 bg-slate-900/40',
      ].join(' ')}>
        <Server className={[
          'w-4 h-4',
          backendOnline === true ? 'text-emerald-400'
            : backendOnline === false ? 'text-red-400'
            : 'text-slate-500',
        ].join(' ')} />
        <div>
          <p className="text-xs font-medium text-slate-300">NIA Backend</p>
          <p className="text-xs text-slate-500">
            {backendOnline === true ? 'Online — /api/v1 reachable'
              : backendOnline === false ? 'Offline — start the backend server'
              : 'Checking connection...'}
          </p>
        </div>
      </div>

      <div className="settings-list">
        <SectionRow
          icon={<Mic className="w-4 h-4" />}
          label="Voice"
          value={settings.voice === 'default' ? 'Default voice' : settings.voice}
          active={activeSection === 'voice'}
          onClick={() => toggle('voice')}
        />
        {activeSection === 'voice' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Voice engine</p>
            {['default', 'masculine', 'feminine'].map((v) => (
              <button
                key={v}
                className="settings-option-row"
                onClick={() => onSettingsChange({ ...settings, voice: v })}
              >
                {settings.voice === v
                  ? <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  : <Circle className="w-4 h-4 text-slate-600" />}
                <span className="text-sm text-slate-300 capitalize">{v}</span>
              </button>
            ))}
            <p className="text-xs text-slate-600 mt-2">
              Speech-to-text uses the device's on-device STT engine. Web Speech API is used in this preview.
            </p>
          </div>
        )}

        <SectionRow
          icon={<Globe className="w-4 h-4" />}
          label="Language"
          value={LANGUAGES.find((l) => l.code === settings.language)?.label ?? settings.language}
          active={activeSection === 'language'}
          onClick={() => toggle('language')}
        />
        {activeSection === 'language' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Input language</p>
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                className="settings-option-row"
                disabled={lang.code !== 'en'}
                onClick={() => onSettingsChange({ ...settings, language: lang.code })}
              >
                {settings.language === lang.code
                  ? <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  : <Circle className="w-4 h-4 text-slate-600" />}
                <span className={[
                  'text-sm',
                  lang.code !== 'en' ? 'text-slate-600' : 'text-slate-300',
                ].join(' ')}>{lang.label}</span>
              </button>
            ))}
            <p className="text-xs text-slate-600 mt-2">
              Only English is active in v0.1. The language layer is designed to support Pidgin, Yoruba, Igbo, and Hausa without re-architecting.
            </p>
          </div>
        )}

        <SectionRow
          icon={<ShieldCheck className="w-4 h-4" />}
          label="Permissions"
          value={`${settings.permissions.length} granted`}
          active={activeSection === 'permissions'}
          onClick={() => toggle('permissions')}
        />
        {activeSection === 'permissions' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Android permissions (simulated in web preview)</p>
            {ANDROID_PERMISSIONS.map((p) => (
              <button
                key={p.id}
                className="settings-option-row"
                onClick={() => togglePermission(p.id)}
              >
                {settings.permissions.includes(p.id)
                  ? <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  : <Circle className="w-4 h-4 text-slate-600" />}
                <div className="flex-1 text-left">
                  <p className="text-sm text-slate-300">{p.label}</p>
                  <p className="text-xs text-slate-600">{p.desc}</p>
                </div>
                {p.required && (
                  <span className="text-xs text-amber-500 font-mono">required</span>
                )}
              </button>
            ))}
            <p className="text-xs text-slate-600 mt-2">
              On the real Android app, these permissions are requested via the Android runtime permission system. NIA never bypasses Android permission boundaries.
            </p>
          </div>
        )}

        <SectionRow
          icon={<Brain className="w-4 h-4" />}
          label="Memory"
          value={settings.memoryEnabled ? 'Enabled' : 'Disabled'}
          active={activeSection === 'memory'}
          onClick={() => toggle('memory')}
        />
        {activeSection === 'memory' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Memory policy</p>
            <button
              className="settings-option-row"
              onClick={() => onSettingsChange({ ...settings, memoryEnabled: !settings.memoryEnabled })}
            >
              {settings.memoryEnabled
                ? <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                : <Circle className="w-4 h-4 text-slate-600" />}
              <span className="text-sm text-slate-300">Enable NIA memory</span>
            </button>
            <p className="text-xs text-slate-600 mt-2">
              NIA never stores passwords, API keys, private keys, or sensitive personal content.
              Memory is scoped to your device ID and can be fully cleared at any time.
            </p>
          </div>
        )}

        <SectionRow
          icon={<Plug className="w-4 h-4" />}
          label="Connected Services"
          value="None active"
          active={activeSection === 'services'}
          onClick={() => toggle('services')}
        />
        {activeSection === 'services' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">External integrations</p>
            <p className="text-xs text-slate-500">
              No external services are connected in v0.1. Planned: WhatsApp, Gmail, Calendar, Arc wallet.
            </p>
          </div>
        )}

        <SectionRow
          icon={<Lock className="w-4 h-4" />}
          label="Security"
          value={settings.securityLevel === 'strict' ? 'Strict' : 'Standard'}
          active={activeSection === 'security'}
          onClick={() => toggle('security')}
        />
        {activeSection === 'security' && (
          <div className="settings-sub-panel">
            <p className="settings-sub-label">Security level</p>
            {(['standard', 'strict'] as const).map((level) => (
              <button
                key={level}
                className="settings-option-row"
                onClick={() => onSettingsChange({ ...settings, securityLevel: level })}
              >
                {settings.securityLevel === level
                  ? <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  : <Circle className="w-4 h-4 text-slate-600" />}
                <div className="flex-1 text-left">
                  <p className="text-sm text-slate-300 capitalize">{level}</p>
                  <p className="text-xs text-slate-600">
                    {level === 'standard'
                      ? 'GREEN tools auto-execute. YELLOW tools require confirmation.'
                      : 'All tools require explicit confirmation before execution.'}
                  </p>
                </div>
              </button>
            ))}
            <p className="text-xs text-slate-600 mt-2">
              CRITICAL tools (payments) always require explicit typed confirmation regardless of this setting.
            </p>
          </div>
        )}

        <SectionRow
          icon={<History className="w-4 h-4" />}
          label="Activity History"
          value="View in Activity tab"
          active={activeSection === 'activity'}
          onClick={() => toggle('activity')}
        />
        {activeSection === 'activity' && (
          <div className="settings-sub-panel">
            <p className="text-xs text-slate-500">
              All task executions are recorded with task ID, timestamp, intent, tool used, permission state, outcome, and duration.
              Secrets and sensitive content are never logged.
              Switch to the Activity tab to review your command history.
            </p>
          </div>
        )}
      </div>

      <p className="text-xs text-center text-slate-700 mt-4 pb-4">
        NIA v0.1 — Nigeria-first intelligent assistant
      </p>
    </div>
  )
}
