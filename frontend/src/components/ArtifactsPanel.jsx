import { useState } from 'react'
import Md from './Md'
import MermaidDiagram from './MermaidDiagram'

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

  const reqs = artifacts.requirements || []
  const stories = artifacts.user_stories || []
  const tests = artifacts.test_cases || []
  const techSpec = artifacts.tech_spec

  // Build lookup maps for traceability
  const reqById = Object.fromEntries(reqs.map(r => [r.id, r]))
  const storiesByReq = {}
  for (const us of stories) {
    for (const rid of (us.req_ids || [])) {
      if (!storiesByReq[rid]) storiesByReq[rid] = []
      storiesByReq[rid].push(us)
    }
  }
  const testsByUs = {}
  for (const tc of tests) {
    const uid = tc.us_id
    if (!testsByUs[uid]) testsByUs[uid] = []
    testsByUs[uid].push(tc)
  }

  const sections = [
    { key: 'requirements', label: 'Requerimientos', icon: '📋', count: reqs.length },
    { key: 'user_stories', label: 'Historias de Usuario', icon: '📖', count: stories.length },
    { key: 'test_cases', label: 'Casos de Prueba', icon: '🧪', count: tests.length },
    { key: 'tech_spec', label: 'Tech Spec', icon: '🏗️', count: techSpec ? 1 : 0 },
    { key: 'diagrams', label: 'Diagramas', icon: '📐', count: techSpec ? (techSpec.mermaid_sequence?.length || 0) + (techSpec.mermaid_er ? 1 : 0) : 0 },
    { key: 'inception', label: 'Inception / MVP', icon: '🎯', count: artifacts.inception ? 1 : 0 },
  ]

  return (
    <div className="space-y-3">
      {sections.map(({ key, label, icon, count }) => {
        const isOpen = expanded === key
        return (
          <div key={key} className="bg-white border border-[#E5E7EB] rounded-[14px] overflow-hidden shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
            <button onClick={() => setExpanded(isOpen ? null : key)}
              className="w-full flex items-center justify-between px-5 py-3.5 text-sm hover:bg-[#F7F9FB] transition">
              <div className="flex items-center gap-2.5">
                <span>{icon}</span>
                <span className="font-medium text-[#111827]">{label}</span>
                <span className="text-xs text-[#4B5563] bg-[#F7F9FB] px-2 py-0.5 rounded-full">{count}</span>
              </div>
              <span className={`text-[#4B5563] transition-transform ${isOpen ? 'rotate-90' : ''}`}>▸</span>
            </button>
            {isOpen && (
              <div className="px-5 pb-4 space-y-2 max-h-[600px] overflow-y-auto">
                {key === 'requirements' && <ReqList reqs={reqs} storiesByReq={storiesByReq} />}
                {key === 'user_stories' && <StoriesList stories={stories} reqById={reqById} testsByUs={testsByUs} />}
                {key === 'test_cases' && <TestList tests={tests} stories={stories} />}
                {key === 'tech_spec' && techSpec && <TechSpecView spec={techSpec} />}
                {key === 'diagrams' && techSpec && <DiagramsView spec={techSpec} />}
                {key === 'inception' && artifacts.inception && <InceptionView item={artifacts.inception} />}
                {count === 0 && <p className="text-xs text-[#4B5563] py-2">Sin datos todavía.</p>}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// --- Requerimientos con traza a US ---
function ReqList({ reqs, storiesByReq }) {
  const [open, setOpen] = useState(null)
  return (
    <div className="space-y-2">
      {reqs.map(r => (
        <div key={r.id} className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <code className="text-xs text-[#059669] font-mono">{r.id}</code>
            <span className="text-sm text-[#111827]">{r.title}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${PRIORITY_STYLES[r.priority] || ''}`}>{r.priority}</span>
            <span className={`text-[10px] ${DOMAIN_STYLES[r.domain] || 'text-[#4B5563]'}`}>{r.domain}</span>
          </div>
          {r.description && <Md className="text-xs text-[#374151]">{r.description}</Md>}
          {/* Traza: US que cubren este REQ */}
          {storiesByReq[r.id]?.length > 0 && (
            <div className="mt-2">
              <button onClick={() => setOpen(open === r.id ? null : r.id)}
                className="text-[10px] text-[#059669] hover:text-[#047857]">
                {storiesByReq[r.id].length} historia{storiesByReq[r.id].length > 1 ? 's' : ''} ▸
              </button>
              {open === r.id && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {storiesByReq[r.id].map(us => (
                    <code key={us.id} className="text-[10px] bg-[#ECFDF5] border border-[#A7F3D0] px-1.5 py-0.5 rounded text-[#059669]">{us.id}</code>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// --- User Stories con traza a REQ y TC ---
function StoriesList({ stories, reqById, testsByUs }) {
  const [open, setOpen] = useState(null)
  return (
    <div className="space-y-2">
      {stories.map(us => (
        <div key={us.id} className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <code className="text-xs text-[#059669] font-mono">{us.id}</code>
            <span className="text-sm text-[#111827]">{us.title}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${PRIORITY_STYLES[us.priority] || ''}`}>{us.priority}</span>
            {us.story_points && <span className="text-[10px] text-[#4B5563]">{us.story_points}pts</span>}
          </div>
          {us.description && <Md className="text-xs text-[#374151] mb-1">{us.description}</Md>}
          {/* Traza: REQ origen */}
          {us.req_ids?.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap mb-1">
              <span className="text-[10px] text-[#4B5563]">REQ:</span>
              {us.req_ids.map(rid => (
                <code key={rid} className="text-[10px] bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded text-blue-600">{rid}</code>
              ))}
            </div>
          )}
          {/* Traza: TC asociados */}
          {testsByUs[us.id]?.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap mb-1">
              <span className="text-[10px] text-[#4B5563]">TC:</span>
              {testsByUs[us.id].map(tc => (
                <code key={tc.id} className="text-[10px] bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded text-amber-600">{tc.id}</code>
              ))}
            </div>
          )}
          {us.acceptance_criteria?.length > 0 && (
            <button onClick={() => setOpen(open === us.id ? null : us.id)}
              className="text-[10px] text-[#059669] hover:text-[#047857]">
              {us.acceptance_criteria.length} criterios de aceptación ▸
            </button>
          )}
          {open === us.id && (
            <div className="mt-1 space-y-1">
              {us.acceptance_criteria.map((ac, j) => (
                <div key={j} className="pl-3 border-l-2 border-[#A7F3D0]">
                  <Md className="text-xs text-[#4B5563]">{ac}</Md>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// --- Test Cases con traza a US ---
function TestList({ tests, stories }) {
  const storyById = Object.fromEntries(stories.map(s => [s.id, s]))
  return (
    <div className="space-y-2">
      {tests.map(tc => (
        <div key={tc.id} className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <code className="text-xs text-amber-600 font-mono">{tc.id}</code>
            <span className="text-sm text-[#111827]">{tc.title}</span>
            <span className="text-[10px] text-[#4B5563] bg-[#F7F9FB] border border-[#E5E7EB] px-1.5 py-0.5 rounded">{tc.type}</span>
          </div>
          {/* Traza: US origen */}
          {tc.us_id && storyById[tc.us_id] && (
            <div className="flex items-center gap-1 mb-1">
              <span className="text-[10px] text-[#4B5563]">US:</span>
              <code className="text-[10px] bg-[#ECFDF5] border border-[#A7F3D0] px-1.5 py-0.5 rounded text-[#059669]">{tc.us_id}</code>
              <span className="text-[10px] text-[#4B5563] truncate">{storyById[tc.us_id].title}</span>
            </div>
          )}
          {tc.description && <Md className="text-xs text-[#374151]">{tc.description}</Md>}
        </div>
      ))}
    </div>
  )
}

// --- Tech Spec estructurada ---
function TechSpecView({ spec }) {
  const [section, setSection] = useState('stack')
  const tabs = [
    { key: 'stack', label: 'Stack' },
    { key: 'models', label: `Modelos (${spec.data_models?.length || 0})` },
    { key: 'endpoints', label: `Endpoints (${spec.api_endpoints?.length || 0})` },
    { key: 'files', label: `Archivos (${spec.project_structure?.files?.length || 0})` },
  ]
  return (
    <div>
      <div className="flex gap-1 mb-3 border-b border-[#E5E7EB]">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setSection(t.key)}
            className={`px-3 py-1.5 text-xs transition border-b-2 ${section === t.key ? 'border-[#059669] text-[#111827]' : 'border-transparent text-[#4B5563]'}`}>
            {t.label}
          </button>
        ))}
      </div>
      {section === 'stack' && spec.stack && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(spec.stack).map(([k, v]) => (
            <div key={k} className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3">
              <div className="text-[10px] text-[#4B5563] uppercase tracking-wide mb-1">{k}</div>
              <div className="text-xs text-[#111827]">{Array.isArray(v) ? v.join(', ') : String(v)}</div>
            </div>
          ))}
        </div>
      )}
      {section === 'models' && (
        <div className="space-y-2">
          {(spec.data_models || []).map((m, i) => (
            <div key={i} className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3">
              <div className="text-sm font-medium text-[#111827] mb-1">{m.name}</div>
              {m.fields && (
                <div className="flex flex-wrap gap-1">
                  {m.fields.map((f, j) => (
                    <code key={j} className="text-[10px] bg-white border border-[#E5E7EB] px-1.5 py-0.5 rounded text-[#4B5563]">
                      {typeof f === 'string' ? f : `${f.name}: ${f.type}`}
                    </code>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {section === 'endpoints' && (
        <div className="space-y-1.5">
          {(spec.api_endpoints || []).map((e, i) => (
            <div key={i} className="flex items-center gap-2 bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] px-3 py-2">
              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                e.method === 'GET' ? 'bg-blue-50 text-blue-600' :
                e.method === 'POST' ? 'bg-[#ECFDF5] text-[#059669]' :
                e.method === 'PUT' ? 'bg-amber-50 text-amber-600' :
                'bg-red-50 text-red-600'
              }`}>{e.method}</span>
              <code className="text-xs text-[#374151] font-mono">{e.path}</code>
              {e.description && <span className="text-[10px] text-[#4B5563] truncate">{e.description}</span>}
            </div>
          ))}
        </div>
      )}
      {section === 'files' && (
        <div className="space-y-1">
          {(spec.project_structure?.files || []).map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <code className="text-[#059669] font-mono">{typeof f === 'string' ? f : f.path}</code>
              {f.description && <span className="text-[#4B5563]">— {f.description}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Diagramas Mermaid ---
function DiagramsView({ spec }) {
  return (
    <div className="space-y-4">
      {spec.mermaid_er && <MermaidDiagram code={spec.mermaid_er} title="Diagrama ER" />}
      {(spec.mermaid_sequence || []).map((seq, i) => (
        <MermaidDiagram key={i} code={seq.code || seq} title={seq.title || `Secuencia ${i + 1}`} />
      ))}
      {!spec.mermaid_er && !spec.mermaid_sequence?.length && (
        <p className="text-xs text-[#4B5563]">No hay diagramas generados todavía.</p>
      )}
    </div>
  )
}

// --- Inception ---
function InceptionView({ item }) {
  return (
    <div className="bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-4 space-y-3">
      <div>
        <span className="text-xs text-[#4B5563]">MVP Scope</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {(item.mvp_scope || []).map(id => <code key={id} className="text-xs bg-[#ECFDF5] border border-[#A7F3D0] px-1.5 py-0.5 rounded text-[#059669]">{id}</code>)}
        </div>
      </div>
      {item.out_of_scope?.length > 0 && (
        <div>
          <span className="text-xs text-[#4B5563]">Fuera de alcance</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {item.out_of_scope.map(id => <code key={id} className="text-xs bg-[#F7F9FB] px-1.5 py-0.5 rounded text-[#4B5563]">{id}</code>)}
          </div>
        </div>
      )}
      {item.risks?.length > 0 && (
        <div>
          <span className="text-xs text-[#4B5563]">Riesgos ({item.risks.length})</span>
          {item.risks.map((r, j) => {
            const sev = r.severity || 'medium'
            const sevStyle = sev === 'high' ? 'bg-red-50 border-red-200 text-red-600' : sev === 'low' ? 'bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]' : 'bg-amber-50 border-amber-200 text-amber-600'
            return (
              <div key={j} className="mt-1.5 bg-white border border-[#E5E7EB] rounded-[8px] p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium ${sevStyle}`}>{sev}</span>
                  {r.id && <code className="text-[10px] text-[#4B5563] font-mono">{r.id}</code>}
                </div>
                <Md className="text-xs text-[#374151]">{r.description || JSON.stringify(r)}</Md>
                {r.mitigation && (
                  <div className="mt-1.5 pl-2 border-l-2 border-[#A7F3D0]">
                    <span className="text-[10px] text-[#059669] font-medium">Mitigación: </span>
                    <span className="text-[10px] text-[#4B5563]">{r.mitigation}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
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
