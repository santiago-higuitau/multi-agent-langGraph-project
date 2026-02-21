import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startRun } from '../services/api'

const EXAMPLE_BRIEF = `Somos una empresa de seguros que necesita una plataforma inteligente para gestionar incidentes de ciberseguridad. Actualmente todo se maneja por correo y hojas de cálculo, lo que genera demoras y falta de visibilidad.

Necesitamos un sistema donde los analistas puedan registrar incidentes, que el sistema los clasifique automáticamente por tipo y severidad, y que genere planes de respuesta usando IA. También necesitamos un dashboard en tiempo real con métricas y gráficos para la gerencia.

Los usuarios principales son: analistas de seguridad (registran y gestionan incidentes), gerentes (ven dashboard y aprueban planes), y el sistema de IA (clasifica y genera planes). Debe tener autenticación por roles.`

const PIPELINE_STEPS = [
  { icon: '🔍', title: 'Business Analyst', desc: 'Analiza el brief y extrae requerimientos' },
  { icon: '📋', title: 'Product Owner', desc: 'Define MVP e historias de usuario' },
  { icon: '🏗️', title: 'Architect', desc: 'Diseña arquitectura y tech spec' },
  { icon: '⚙️', title: 'Backend + Frontend', desc: 'Generan código en paralelo' },
  { icon: '🧪', title: 'QA + Validator', desc: 'Tests e integración cruzada' },
  { icon: '🚀', title: 'DevOps', desc: 'Docker, deploy, listo para producción' },
]

export default function HomePage() {
  const [brief, setBrief] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!brief.trim()) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await startRun(brief)
      navigate(`/runs/${data.run_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto pt-4">

      {/* Hero */}
      <div className="text-center mb-10">
        <div
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs mb-4"
          style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', color: '#059669' }}
        >
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#059669' }} />
          9 agentes IA colaborando
        </div>
        <h1
          className="text-4xl mb-3"
          style={{ fontWeight: 850, letterSpacing: '-0.03em', color: '#0D1B14' }}
        >
          De brief a <span style={{ color: '#059669' }}>aplicación funcional</span>
        </h1>
        <p className="text-sm max-w-lg mx-auto font-light" style={{ color: '#374151' }}>
          Describe tu proyecto y el equipo de agentes lo transformará en una aplicación full-stack desplegable.
        </p>
      </div>

      {/* Pipeline steps */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 mb-8">
        {PIPELINE_STEPS.map((step, i) => (
          <div
            key={i}
            className="rounded-xl p-3 text-center transition-all hover:-translate-y-0.5"
            style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}
          >
            <div className="text-xl mb-1.5">{step.icon}</div>
            <div className="text-xs font-medium mb-0.5" style={{ color: '#111827' }}>{step.title}</div>
            <div className="text-[10px] leading-tight" style={{ color: '#4B5563' }}>{step.desc}</div>
          </div>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Describe tu proyecto aquí..."
            rows={10}
            disabled={loading}
            className="w-full rounded-xl p-5 text-sm resize-y transition outline-none"
            style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', color: '#111827' }}
          />
          <div className="absolute bottom-3 right-3 text-xs" style={{ color: '#9CA3AF' }}>
            {brief.length > 0 && `${brief.split(/\s+/).filter(Boolean).length} palabras`}
          </div>
        </div>

        {error && (
          <div
            className="rounded-xl p-4 text-sm flex items-start gap-2"
            style={{ background: '#FEF2F2', border: '1px solid #FECACA', color: '#B91C1C' }}
          >
            <span>✕</span>
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || !brief.trim()}
            className="px-6 py-2.5 rounded-lg text-sm font-medium transition"
            style={{
              background: loading || !brief.trim() ? '#E5E7EB' : '#059669',
              color: loading || !brief.trim() ? '#9CA3AF' : '#FFFFFF',
            }}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Ejecutando pipeline...
              </span>
            ) : '⚡ Iniciar Run'}
          </button>
          <button
            type="button"
            onClick={() => setBrief(EXAMPLE_BRIEF)}
            disabled={loading}
            className="px-4 py-2.5 text-sm rounded-lg transition"
            style={{ color: '#374151', border: '1px solid #D1D5DB', background: '#FFFFFF' }}
          >
            Cargar ejemplo
          </button>
        </div>
      </form>

      {loading && (
        <div
          className="mt-8 rounded-xl p-5"
          style={{ background: '#ECFDF5', border: '1px solid #A7F3D0' }}
        >
          <div className="flex items-center gap-3 mb-3" style={{ color: '#059669' }}>
            <div
              className="w-5 h-5 border-2 rounded-full animate-spin"
              style={{ borderColor: '#A7F3D0', borderTopColor: '#059669' }}
            />
            <span className="text-sm font-medium">Pipeline en ejecución</span>
          </div>
          <div className="space-y-2 text-xs" style={{ color: '#374151' }}>
            <p>Los agentes están analizando tu brief y generando artefactos de planificación.</p>
            <p>Esto puede tomar entre 1 y 3 minutos dependiendo del modelo LLM configurado.</p>
            <p>El pipeline se pausará en el Gate HITL 1 para tu revisión.</p>
          </div>
        </div>
      )}

    </div>
  )
}
