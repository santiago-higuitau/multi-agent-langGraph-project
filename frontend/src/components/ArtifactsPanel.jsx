import { useState } from 'react'
import Md from './Md'

const PRIORITY_STYLES = {
  must: 'bg-red-50 border-red-200 text-red-600',
  should: 'bg-amber-50 border-amber-200 text-amber-600',
  could: 'bg-[#F7F9FB] border-[#E5E7EB] text-[#4B5563]',
}
const DOMAIN_STYLES = {
  backend: 'text-blue-600', frontend: 'text-purple-600', ml: 'text-cyan-600',
  genai: 'text-[#059669]', data: 'text-orange-600', infra: 'text-[#4B5563]',
}

export default function ArtifactsPanel({ artifacts }) {
  const [expanded, setExpanded] = useState(null)
  if (!artifacts) return <Empty />

  const sections = [
    { key: 'requirements', label: 'Requerimientos', icon: '📋', data: artifacts.requirements },
    { key: 'inception', label: 'Inception / MVP', icon: '🎯', data: artifacts.inception ? [artifacts.inception] : [] },
    { key: 'user_stories', label: 'Historias de Usuario', icon: '📖', data: artifacts.user_stories },
    { key: 'test_cases', label: 'Casos de Prueba', icon: '🧪', data: artifacts.test_cases },
    { key: 'tech_spec', label: 'Tech Spec', icon: '🏗️', data: artifacts.tech_spec ? [artifacts.tech_spec] : [] },
  ]

  return (
    <div className="space-y-3">
      {sections.map((section) => {
        const count = Array.isArray(section.data) ? section.data.length : 0
        const isOpen = expanded === section.key
        return (
          <div key={section.key} className="bg-white border border-[#E5E7EB] rounded-[14px] overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <button onClick={() => setExpanded(isOpen ? null : section.key)} className="w-full flex items-center justify-between px-5 py-3.5 text-sm hover:bg-[#F7F9FB] transition">
              <div className="flex items-center gap-2.5">
                <span>{section.icon}</span>
                <span className="font-medium text-[#111827]">{section.label}</span>
                <span className="text-xs text-[#4B5563] bg-[#F7F9FB] px-2 py-0.5 rounded-full">{count}</span>
              </div>
              <span className={`text-[#4B5563] transition-transform ${isOpen ? 'rotate-90' : ''}`}>▸</span>
            </button>
            {isOpen && (
              <div className="px-5 pb-4 space-y-2 max-h-[500px] overflow-y-auto">
                {count === 0 ? <p className="text-xs text-[#4B5563] py-2">Sin datos</p>
                  : section.data.map((item, i) => <ArtifactCard key={item.id || i} item={item} sectionKey={section.key} />)}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function ArtifactCard({ item, sectionKey }) {
  const [showRaw, setShowRaw] = useState(false)

  if (sectionKey === 'tech_spec') return (
    <div className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-[#4B5563]">Especificación técnica completa</span>
        <button onClick={() => setShowRaw(!showRaw)} className="text-xs text-[#059669] hover:text-[#047857]">{showRaw ? 'Colapsar' : 'Ver JSON'}</button>
      </div>
      {showRaw
        ? <pre className="text-xs text-[#374151] overflow-x-auto whitespace-pre-wrap max-h-80 overflow-y-auto font-mono leading-relaxed">{JSON.stringify(item, null, 2)}</pre>
        : <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <MiniStat label="Archivos" value={item.project_structure?.files?.length || 0} />
            <MiniStat label="Modelos" value={item.data_models?.length || 0} />
            <MiniStat label="Endpoints" value={item.api_endpoints?.length || 0} />
            <MiniStat label="Diagramas" value={item.mermaid_sequence?.length || 0} />
          </div>}
    </div>
  )

  if (sectionKey === 'inception') return (
    <div className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-4 space-y-3">
      <div>
        <span className="text-xs text-[#4B5563]">MVP Scope</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {(item.mvp_scope || []).map((id) => <code key={id} className="text-xs bg-[#ECFDF5] border border-[#A7F3D0] px-1.5 py-0.5 rounded text-[#059669]">{id}</code>)}
        </div>
      </div>
      {item.out_of_scope?.length > 0 && (
        <div>
          <span className="text-xs text-[#4B5563]">Fuera de alcance</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {item.out_of_scope.map((id) => <code key={id} className="text-xs bg-[#F7F9FB] px-1.5 py-0.5 rounded text-[#4B5563]">{id}</code>)}
          </div>
        </div>
      )}
      {item.risks?.length > 0 && (
        <div>
          <span className="text-xs text-[#4B5563]">Riesgos ({item.risks.length})</span>
          {item.risks.map((r, j) => <div key={j} className="mt-1 pl-2 border-l-2 border-[#E5E7EB]"><Md className="text-xs text-[#374151]">{r.description || JSON.stringify(r)}</Md></div>)}
        </div>
      )}
    </div>
  )

  return (
    <div className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-4">
      <div className="flex items-center gap-2 flex-wrap">
        {item.id && <code className="text-xs text-[#059669] font-mono">{item.id}</code>}
        {item.title && <span className="text-sm text-[#111827]">{item.title}</span>}
        {item.priority && <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${PRIORITY_STYLES[item.priority] || ''}`}>{item.priority}</span>}
        {item.domain && <span className={`text-[10px] ${DOMAIN_STYLES[item.domain] || 'text-[#4B5563]'}`}>{item.domain}</span>}
        {item.story_points && <span className="text-[10px] text-[#4B5563]">{item.story_points}pts</span>}
      </div>
      {item.description && <div className="mt-1.5"><Md className="text-xs text-[#374151]">{item.description}</Md></div>}
      {item.acceptance_criteria?.length > 0 && (
        <div className="mt-2 space-y-1">
          {item.acceptance_criteria.map((ac, j) => <div key={j} className="pl-3 border-l-2 border-[#E5E7EB]"><Md className="text-xs text-[#4B5563]">{ac}</Md></div>)}
        </div>
      )}
      {item.req_ids?.length > 0 && (
        <div className="mt-2 flex gap-1">
          {item.req_ids.map((rid) => <code key={rid} className="text-[10px] bg-[#F7F9FB] px-1.5 py-0.5 rounded text-[#4B5563]">{rid}</code>)}
        </div>
      )}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[8px] p-2 text-center">
      <div className="text-base font-bold text-[#111827]">{value}</div>
      <div className="text-[10px] text-[#4B5563]">{label}</div>
    </div>
  )
}

function Empty() {
  return (
    <div className="text-center py-16">
      <div className="text-3xl mb-3">📦</div>
      <p className="text-[#4B5563] text-sm">No hay artefactos todavía.</p>
      <p className="text-[#9CA3AF] text-xs mt-1">Se generarán cuando el pipeline avance.</p>
    </div>
  )
}
