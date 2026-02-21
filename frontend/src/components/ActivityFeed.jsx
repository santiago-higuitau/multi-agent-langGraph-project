import { useEffect, useRef } from 'react'
import Md from './Md'

const AGENT_COLORS = {
  'BA Agent': 'text-blue-600', 'PO Agent': 'text-purple-600', 'Architect': 'text-cyan-600',
  'Evaluator': 'text-amber-600', 'Backend Builder': 'text-[#059669]', 'Frontend Builder': 'text-pink-600',
  'QA Agent': 'text-orange-600', 'Integration Validator': 'text-red-600', 'DevOps Agent': 'text-teal-600',
  'HITL Gate 1': 'text-amber-600', 'HITL Gate 2': 'text-amber-600', 'Pipeline': 'text-[#059669]',
}

export default function ActivityFeed({ activity }) {
  const bottomRef = useRef(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [activity.length])

  if (!activity.length) return (
    <div className="text-center py-10">
      <div className="text-2xl mb-2">📡</div>
      <p className="text-[#4B5563] text-sm">Esperando actividad del pipeline...</p>
    </div>
  )

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[14px] overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
      <div className="px-4 py-2.5 border-b border-[#E5E7EB] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#059669] animate-pulse" />
          <span className="text-xs text-[#374151]">Actividad en vivo</span>
        </div>
        <span className="text-[10px] text-[#4B5563]">{activity.length} eventos</span>
      </div>
      <div className="max-h-[400px] overflow-y-auto p-3 space-y-1">
        {activity.map((entry, i) => <ActivityEntry key={i} entry={entry} />)}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function ActivityEntry({ entry }) {
  const color = AGENT_COLORS[entry.agent] || 'text-[#4B5563]'
  const time = entry.timestamp?.slice(11, 19) || ''
  return (
    <div className="flex gap-2.5 py-1.5 px-2 rounded-[8px] hover:bg-[#F7F9FB] transition group">
      <span className="text-sm flex-shrink-0 mt-0.5">{entry.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-[11px] font-medium ${color}`}>{entry.agent}</span>
          <span className="text-[10px] text-[#4B5563] font-mono">{time}</span>
        </div>
        <p className="text-xs text-[#111827] leading-relaxed">{entry.message}</p>
        {entry.detail && <Md className="text-[11px] text-[#4B5563] mt-0.5">{entry.detail}</Md>}
      </div>
    </div>
  )
}
