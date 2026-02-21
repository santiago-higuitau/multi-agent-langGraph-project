import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { getRun, getArtifacts, getGeneratedFiles, getDecisionsLog, getActivityLog, submitHITL, exportProject, deployApp, teardownApp, deployStatus } from '../services/api'
import PipelineTracker from '../components/PipelineTracker'
import HITLGate from '../components/HITLGate'
import ArtifactsPanel from '../components/ArtifactsPanel'
import FilesPanel from '../components/FilesPanel'
import DecisionsLog from '../components/DecisionsLog'
import DeployPanel from '../components/DeployPanel'
import ActivityFeed from '../components/ActivityFeed'

const TABS = [
  { key: 'Pipeline', icon: '📊' },
  { key: 'Artefactos', icon: '📦' },
  { key: 'Archivos', icon: '📁' },
  { key: 'Decisiones', icon: '📝' },
  { key: 'Deploy', icon: '🚀' },
]
const POLL_INTERVAL = 3000

export default function RunPage() {
  const { runId } = useParams()
  const [run, setRun] = useState(null)
  const [artifacts, setArtifacts] = useState(null)
  const [files, setFiles] = useState([])
  const [decisions, setDecisions] = useState([])
  const [deploy, setDeploy] = useState({ status: 'idle', urls: {} })
  const [activityLog, setActivityLog] = useState([])
  const [tab, setTab] = useState('Pipeline')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [hitlLoading, setHitlLoading] = useState(false)
  const pollRef = useRef(null)
  const hitlJustApproved = useRef(false)

  const fetchAll = useCallback(async () => {
    try {
      const [runRes, artRes, filesRes, decRes, depRes, actRes] = await Promise.allSettled([
        getRun(runId), getArtifacts(runId), getGeneratedFiles(runId),
        getDecisionsLog(runId), deployStatus(), getActivityLog(runId),
      ])
      if (runRes.status === 'fulfilled') {
        const incoming = runRes.value.data
        if (hitlJustApproved.current) {
          if (incoming.status !== 'waiting_hitl') {
            hitlJustApproved.current = false
            setRun(incoming)
          } else {
            setRun((prev) => ({
              ...incoming, status: 'running',
              current_phase: prev?.current_phase === 'hitl_gate_1' ? 'building' : prev?.current_phase === 'hitl_gate_2' ? 'devops' : incoming.current_phase,
              current_agent: '',
            }))
          }
        } else { setRun(incoming) }
      } else if (runRes.reason?.response?.status === 404) {
        clearInterval(pollRef.current); setRun(null); setLoading(false); return
      }
      if (artRes.status === 'fulfilled') setArtifacts(artRes.value.data)
      if (filesRes.status === 'fulfilled') setFiles(filesRes.value.data.files || [])
      if (decRes.status === 'fulfilled') setDecisions(decRes.value.data.decisions || [])
      if (depRes.status === 'fulfilled') setDeploy(depRes.value.data)
      if (actRes.status === 'fulfilled') setActivityLog(actRes.value.data.activity || [])
    } catch (e) { /* silent */ }
    finally { setLoading(false) }
  }, [runId])

  useEffect(() => { fetchAll(); pollRef.current = setInterval(fetchAll, POLL_INTERVAL); return () => clearInterval(pollRef.current) }, [fetchAll])
  useEffect(() => { if (run?.status === 'completed') clearInterval(pollRef.current) }, [run?.status])

  const handleHITL = async (decision, feedback) => {
    setHitlLoading(true); setError(null)
    try {
      const { data } = await submitHITL(runId, decision, feedback)
      if (data.status !== 'already_processed') {
        hitlJustApproved.current = true
        setRun((prev) => prev ? { ...prev, status: 'running', current_phase: data.current_phase || prev.current_phase, current_agent: '' } : prev)
      }
    } catch (e) { setError(e.response?.data?.detail || e.message) }
    finally { setHitlLoading(false) }
  }
  const handleExport = async () => { try { const { data } = await exportProject(runId); await fetchAll(); return data } catch (e) { setError(e.response?.data?.detail || e.message) } }
  const handleDeploy = async (apiKey) => { try { const { data } = await deployApp(apiKey); setDeploy(data); return data } catch (e) { setError(e.response?.data?.detail || e.message) } }
  const handleTeardown = async () => { try { const { data } = await teardownApp(); setDeploy(data) } catch (e) { setError(e.response?.data?.detail || e.message) } }

  if (loading) return (
    <div className="flex items-center gap-3 text-[#4B5563] py-16 justify-center">
      <div className="w-5 h-5 border-2 border-[#E5E7EB] border-t-[#059669] rounded-full animate-spin" />
      <span className="text-sm">Cargando run...</span>
    </div>
  )
  if (!run) return (
    <div className="text-center py-16">
      <div className="text-3xl mb-3">🔍</div>
      <p className="text-[#4B5563] text-sm mb-1">Run no encontrado</p>
      <p className="text-[#9CA3AF] text-xs">Es posible que el servidor se haya reiniciado. Crea un nuevo run desde el inicio.</p>
    </div>
  )

  const isAtHITL = run.status === 'waiting_hitl'
  const hitlGate = run.current_phase
  const isActive = run.status === 'running' || run.status === 'waiting_hitl'

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-xl font-bold text-[#111827]">Run</h1>
            <code className="text-sm text-[#4B5563] font-mono bg-[#F7F9FB] px-2 py-0.5 rounded">{runId}</code>
            <StatusBadge status={run.status} />
          </div>
          <p className="text-sm text-[#374151] line-clamp-2 max-w-2xl">{run.brief}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {isActive && (
            <span className="text-[10px] text-[#059669] flex items-center gap-1.5 px-2 py-1 bg-[#ECFDF5] rounded-lg border border-[#A7F3D0]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#059669] animate-pulse" />
              auto-refresh
            </span>
          )}
          <button onClick={fetchAll} className="text-xs text-[#374151] hover:text-[#111827] border border-[#E5E7EB] hover:border-[#059669] px-3 py-1.5 rounded-[8px] transition flex items-center gap-1.5">
            <span className="text-[10px]">↻</span> Refrescar
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-[14px] p-4 text-sm text-red-700 mb-4 flex items-start justify-between">
          <div className="flex items-start gap-2"><span className="text-red-500 mt-0.5">✕</span><span>{error}</span></div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs ml-4">cerrar</button>
        </div>
      )}

      {isAtHITL && <HITLGate gate={hitlGate} onSubmit={handleHITL} loading={hitlLoading} />}

      <div className="flex gap-1 mb-5 border-b border-[#E5E7EB]">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm transition border-b-2 flex items-center gap-1.5 ${
              tab === t.key ? 'border-[#059669] text-[#111827]' : 'border-transparent text-[#4B5563] hover:text-[#374151]'
            }`}>
            <span className="text-xs">{t.icon}</span>{t.key}
          </button>
        ))}
      </div>

      <div className="min-h-[400px]">
        {tab === 'Pipeline' && <div className="space-y-4"><PipelineTracker run={run} activityLog={activityLog} /><ActivityFeed activity={activityLog} /></div>}
        {tab === 'Artefactos' && <ArtifactsPanel artifacts={artifacts} />}
        {tab === 'Archivos' && <FilesPanel files={files} runId={runId} />}
        {tab === 'Decisiones' && <DecisionsLog decisions={decisions} />}
        {tab === 'Deploy' && <DeployPanel deploy={deploy} runStatus={run.status} onExport={handleExport} onDeploy={handleDeploy} onTeardown={handleTeardown} downloadUrl={`/api/runs/${runId}/download`} />}
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    running: 'bg-blue-50 border-blue-200 text-blue-600',
    waiting_hitl: 'bg-amber-50 border-amber-200 text-amber-600',
    completed: 'bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]',
    error: 'bg-red-50 border-red-200 text-red-600',
  }
  const dots = { running: 'bg-blue-500', waiting_hitl: 'bg-amber-500', completed: 'bg-[#059669]', error: 'bg-red-500' }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border flex items-center gap-1.5 ${styles[status] || 'bg-[#F7F9FB] text-[#4B5563] border-[#E5E7EB]'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dots[status] || 'bg-[#E5E7EB]'} ${status === 'running' ? 'animate-pulse' : ''}`} />
      {status === 'waiting_hitl' ? 'esperando aprobación' : status}
    </span>
  )
}
