import { Mic, History, Settings } from 'lucide-react'
import { motion } from 'framer-motion'

interface Props {
  activeView: string
  onNavigate: (view: string) => void
}

const NAV_ITEMS = [
  { id: 'voice', icon: Mic, label: 'Voice' },
  { id: 'history', icon: History, label: 'Activity' },
  { id: 'settings', icon: Settings, label: 'Settings' },
]

export default function BottomNav({ activeView, onNavigate }: Props) {
  return (
    <nav className="nia-bottom-nav" aria-label="Main navigation">
      {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
        const isActive = activeView === id
        return (
          <button
            key={id}
            className={['nav-item', isActive ? 'nav-item-active' : ''].join(' ')}
            onClick={() => onNavigate(id)}
            aria-label={label}
            aria-current={isActive ? 'page' : undefined}
          >
            <div className="relative">
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="nav-indicator"
                  transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                />
              )}
              <Icon className={['nav-icon', isActive ? 'text-cyan-400' : 'text-slate-600'].join(' ')} />
            </div>
            <span className={['nav-label', isActive ? 'text-cyan-400' : 'text-slate-600'].join(' ')}>
              {label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
