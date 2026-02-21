import Md from './Md'

const AGENT_COLORS = {
  'BA Agent': 'bg-blue-50 border-blue-200 text-blue-600',
  'Product Owner Agent': 'bg-purple-50 border-purple-200 text-purple-600',
  'Architect Agent': 'bg-cyan-50 border-cyan-200 text-cyan-600',
  'Planning Evaluator': 'bg-amber-50 border-amber-200 text-amber-600',
  'Backend Builder': 'bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]',
  'Frontend Builder': 'bg-pink-50 border-pink-200 text-pink-600',
  'QA Agent': 'bg-orange-50 border-orange-200 text-orange-600',
  'Integration Validator (Architect)': 'bg-red-50 border-red-200 text-red-600',
  'DevOps Agent': 'bg-teal-50 border-teal-200 text-teal-600',
}

export default function DecisionsLog({ decisions }) {
  if (!decisions.length) return (
    <div className="text-center py-16">
      <div className="text-3xl mb-3">📝</div>
      <p className="text-[#4B5563] text-sm">No hay decisiones registradas todavía.</p>
    </div>
  )

  return (
    <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
      {decisions.map((d, i) => {
        const agentStyle = AGENT_COLORS[d.agent] || 'bg-[#F7F9FB] border-[#E5E7EB] text-[#4B5563]'
        return (
          <div key={i} className="bg-white border border-[#E5E7EB] rounded-[14px] p-4 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="text-[10px] text-[#4B5563] font-mono">{d.timestamp?.slice(11, 19)}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${agentStyle}`}>{d.agent}</span>
              <span className="text-[10px] text-[#4B5563]">{d.phase}</span>
              {d.iteration > 0 && <span className="text-[10px] text-[#4B5563]">iter {d.iteration}</span>}
            </div>
            <Md className="text-sm text-[#111827]">{d.decision}</Md>
            {d.justification && <Md className="text-xs text-[#374151] mt-1.5">{d.justification}</Md>}
            {d.artifacts_affected?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {d.artifacts_affected.slice(0, 8).map((a, j) => (
                  <code key={j} className="text-[10px] bg-[#F7F9FB] px-1.5 py-0.5 rounded text-[#4B5563]">{a}</code>
                ))}
                {d.artifacts_affected.length > 8 && <span className="text-[10px] text-[#4B5563]">+{d.artifacts_affected.length - 8}</span>}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
