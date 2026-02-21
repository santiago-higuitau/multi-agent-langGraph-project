const PHASES = [
  { key: 'planning', label: 'Planificación', icon: '🔍', agents: ['BA → PO → Architect → Evaluator'] },
  { key: 'hitl_gate_1', label: 'Gate 1 — Revisión', icon: '🚦', agents: ['Aprobación humana de planificación'] },
  { key: 'building', label: 'Construcción', icon: '⚙️', agents: ['Backend ∥ Frontend → QA'] },
  { key: 'integration', label: 'Integración', icon: '🔗', agents: ['Validación cruzada de código'] },
  { key: 'hitl_gate_2', label: 'Gate 2 — Revisión', icon: '🚦', agents: ['Aprobación humana de código'] },
  { key: 'devops', label: 'DevOps', icon: '🚀', agents: ['Docker, Compose, nginx, README'] },
  { key: 'done', label: 'Completado', icon: '✅', agents: [] },
]
const AGENT_PHASE = {
  'BA Agent': 'planning', 'PO Agent': 'planning', 'Architect': 'planning', 'Evaluator': 'planning',
  'HITL Gate 1': 'hitl_gate_1', 'Backend Builder': 'building', 'Frontend Builder': 'building',
  'QA Agent': 'building', 'Integration Validator': 'integration', 'HITL Gate 2': 'hitl_gate_2',
  'DevOps Agent': 'devops', 'Pipeline': 'done',
}
const AGENT_COLORS = {
  'BA Agent': 'text-blue-600', 'PO Agent': 'text-purple-600', 'Architect': 'text-cyan-600',
  'Evaluator': 'text-amber-600', 'Backend Builder': 'text-[#059669]', 'Frontend Builder': 'text-pink-600',
  'QA Agent': 'text-orange-600', 'Integration Validator': 'text-red-600', 'DevOps Agent': 'text-teal-600',
}
function phaseIndex(phase) { const idx = PHASES.findIndex((p) => p.key === phase); return idx === -1 ? 0 : idx }

export default function PipelineTracker({ run, activityLog = [] }) {
  const current = phaseIndex(run.current_phase)
  const latestByAgent = {}
  for (const entry of activityLog) latestByAgent[entry.agent] = entry
  const lastActivity = activityLog.length > 0 ? activityLog[activityLog.length - 1] : null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Requerimientos" value={run.num_requirements} icon="📋" color="amber" />
        <Stat label="User Stories" value={run.num_user_stories} icon="📖" color="purple" />
        <Stat label="Test Cases" value={run.num_test_cases} icon="🧪" color="cyan" />
        <Stat label="Archivos" value={run.num_generated_files} icon="📁" color="green" />
      </div>

      <div className="relative">
        {PHASES.map((phase, i) => {
          const isDone = i < current
          const isCurrent = i === current
          const isPending = i > current
          const phaseAgents = Object.entries(latestByAgent).filter(([agent]) => AGENT_PHASE[agent] === phase.key)
          return (
            <div key={phase.key} className="flex gap-4 relative">
              {i < PHASES.length - 1 && (
                <div className={`absolute left-[15px] top-[36px] w-[2px] h-[calc(100%-12px)] ${isDone ? 'bg-[#A7F3D0]' : 'bg-[#E5E7EB]'}`} />
              )}
              <div className="flex-shrink-0 relative z-10">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 ${
                  isDone ? 'border-[#A7F3D0] bg-[#ECFDF5]' : isCurrent ? 'border-[#059669] bg-[#ECFDF5] shadow-lg shadow-[rgba(5,150,105,0.2)]' : 'border-[#E5E7EB] bg-white'
                }`}>
                  {isDone ? <span className="text-[#059669] text-xs">✓</span> : <span className="text-xs">{phase.icon}</span>}
                </div>
              </div>
              <div className={`flex-1 pb-6 ${isPending ? 'opacity-40' : ''}`}>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${isCurrent ? 'text-[#111827]' : isDone ? 'text-[#374151]' : 'text-[#9CA3AF]'}`}>{phase.label}</span>
                  {isCurrent && run.status === 'waiting_hitl' && <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-600">esperando</span>}
                  {isCurrent && run.status === 'running' && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-blue-600 flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-blue-500 animate-pulse" />en progreso
                    </span>
                  )}
                </div>
                {phase.agents.length > 0 && <p className="text-xs text-[#4B5563] mt-0.5">{phase.agents.join(' → ')}</p>}
                {isDone && phaseAgents.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {phaseAgents.map(([agent, entry]) => (
                      <span key={agent} className="text-[10px] px-1.5 py-0.5 rounded bg-[#ECFDF5] border border-[#A7F3D0] text-[#059669] flex items-center gap-1">
                        <span>{entry.icon}</span> {agent}
                      </span>
                    ))}
                  </div>
                )}
                {isCurrent && run.status === 'running' && phaseAgents.length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    {phaseAgents.map(([agent, entry]) => (
                      <div key={agent} className="flex items-center gap-2 bg-white border border-[#E5E7EB] rounded-[8px] px-3 py-2 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
                        <span className="w-3 h-3 border-2 border-[#059669] border-t-transparent rounded-full animate-spin flex-shrink-0" />
                        <span className={`text-[11px] font-medium ${AGENT_COLORS[agent] || 'text-[#374151]'}`}>{agent}</span>
                        <span className="text-[10px] text-[#4B5563] truncate">{entry.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {lastActivity && run.status === 'running' && (
        <div className="bg-white border border-[#E5E7EB] rounded-[14px] p-4 flex items-center gap-3 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
          <div className="w-5 h-5 border-2 border-[#059669] border-t-transparent rounded-full animate-spin flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${AGENT_COLORS[lastActivity.agent] || 'text-[#374151]'}`}>{lastActivity.agent}</span>
              <span className="text-[10px] text-[#4B5563] font-mono">{lastActivity.timestamp?.slice(11, 19)}</span>
            </div>
            <p className="text-xs text-[#374151] truncate">{lastActivity.message}</p>
          </div>
          {run.planning_iteration > 0 && <span className="text-xs text-[#4B5563] flex-shrink-0">iteración {run.planning_iteration}</span>}
        </div>
      )}
    </div>
  )
}

const STAT_COLORS = {
  amber: { text: 'text-amber-600', border: 'border-amber-200' },
  purple: { text: 'text-purple-600', border: 'border-purple-200' },
  cyan: { text: 'text-cyan-600', border: 'border-cyan-200' },
  green: { text: 'text-[#059669]', border: 'border-[#A7F3D0]' },
}
function Stat({ label, value, icon, color }) {
  const c = STAT_COLORS[color] || STAT_COLORS.green
  return (
    <div className={`bg-white border rounded-[14px] p-4 shadow-[0_1px_8px_rgba(0,0,0,0.04)] ${c.border}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg">{icon}</span>
        <span className={`text-2xl font-bold ${c.text}`}>{value ?? 0}</span>
      </div>
      <div className="text-xs text-[#374151]">{label}</div>
    </div>
  )
}
