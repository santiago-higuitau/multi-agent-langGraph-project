import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../services/api'

const STATUS_STYLES = {
  running: { bg: 'bg-blue-50 border-blue-200 text-blue-600', dot: 'bg-blue-500' },
  waiting_hitl: { bg: 'bg-amber-50 border-amber-200 text-amber-600', dot: 'bg-amber-500' },
  completed: { bg: 'bg-[#ECFDF5] border-[#A7F3D0] text-[#059669]', dot: 'bg-[#059669]' },
  error: { bg: 'bg-red-50 border-red-200 text-red-600', dot: 'bg-red-500' },
}

export default function RunsListPage() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listRuns()
      .then(({ data }) => setRuns(data.runs || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-3 text-[#4B5563] py-16 justify-center">
        <div className="w-4 h-4 border-2 border-[#E5E7EB] border-t-[#059669] rounded-full animate-spin" />
        <span className="text-sm">Cargando...</span>
      </div>
    )
  }

  if (!runs.length) {
    return (
      <div className="text-center py-20">
        <div className="text-4xl mb-4">📭</div>
        <p className="text-[#4B5563] mb-4">No hay runs todavía.</p>
        <Link to="/" className="text-[#059669] hover:text-[#047857] text-sm transition">
          Crear el primero →
        </Link>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-[#111827]">Historial de Runs</h1>
        <span className="text-xs text-[#4B5563]">{runs.length} run{runs.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="space-y-2">
        {runs.map((run) => {
          const style = STATUS_STYLES[run.status] || STATUS_STYLES.error
          return (
            <Link
              key={run.run_id}
              to={`/runs/${run.run_id}`}
              className="block bg-white border border-[#E5E7EB] rounded-[14px] p-5 hover:border-[#059669] hover:shadow-[0_6px_20px_rgba(5,150,105,0.15)] hover:-translate-y-0.5 transition-all group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <code className="text-xs text-[#4B5563] font-mono">{run.run_id}</code>
                  <span className={`text-xs px-2 py-0.5 rounded-full border flex items-center gap-1.5 ${style.bg}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                    {run.status}
                  </span>
                  <span className="text-xs text-[#4B5563]">{run.current_phase}</span>
                </div>
                <div className="text-xs text-[#4B5563] flex gap-4">
                  <span>REQ {run.num_requirements}</span>
                  <span>US {run.num_user_stories}</span>
                  <span>Files {run.num_generated_files}</span>
                </div>
              </div>
              <p className="text-sm text-[#374151] line-clamp-2 group-hover:text-[#111827] transition">{run.brief}</p>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
