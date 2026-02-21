import { useState } from 'react'

export default function HITLGate({ gate, onSubmit, loading }) {
  const [feedback, setFeedback] = useState('')
  const isGate1 = gate === 'hitl_gate_1'
  const gateLabel = isGate1 ? 'Gate 1 — Revisión de Planificación' : 'Gate 2 — Revisión de Código'
  const gateDesc = isGate1
    ? 'Revisa los requerimientos, historias de usuario y la arquitectura técnica en la pestaña Artefactos antes de aprobar.'
    : 'Revisa los archivos generados y la validación de integración en las pestañas Archivos y Decisiones antes de aprobar.'

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-[14px] p-5 mb-6">
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-8 h-8 rounded-full bg-amber-100 border border-amber-300 flex items-center justify-center">
          <span className="text-sm">🚦</span>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-amber-800">{gateLabel}</h3>
          <p className="text-xs text-[#4B5563]">{gateDesc}</p>
        </div>
      </div>
      <textarea
        value={feedback} onChange={(e) => setFeedback(e.target.value)}
        placeholder="Feedback opcional (ej: ajustar el modelo de datos, agregar endpoint X, cambiar prioridad de US-003...)"
        rows={3}
        className="w-full bg-white border border-[#E5E7EB] rounded-[8px] p-3 text-sm text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:border-[#059669] focus:ring-2 focus:ring-[rgba(5,150,105,0.08)] resize-y mb-3 mt-3"
        disabled={loading}
      />
      <div className="flex gap-2">
        <button onClick={() => onSubmit('approved', feedback)} disabled={loading}
          className="px-5 py-2 bg-[#059669] hover:bg-[#047857] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] text-white rounded-[8px] text-sm font-medium transition flex items-center gap-1.5">
          {loading ? <span className="flex items-center gap-2"><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Procesando...</span> : <>✓ Aprobar</>}
        </button>
        <button onClick={() => onSubmit('changes_requested', feedback)} disabled={loading || !feedback.trim()}
          className="px-4 py-2 bg-amber-100 hover:bg-amber-200 disabled:bg-[#F7F9FB] disabled:text-[#9CA3AF] text-amber-800 border border-amber-300 disabled:border-[#E5E7EB] rounded-[8px] text-sm transition">
          Pedir cambios
        </button>
        <button onClick={() => onSubmit('rejected', feedback)} disabled={loading}
          className="px-4 py-2 text-red-600 hover:bg-red-50 border border-red-200 hover:border-red-300 disabled:bg-[#F7F9FB] disabled:text-[#9CA3AF] disabled:border-[#E5E7EB] rounded-[8px] text-sm transition">
          Rechazar
        </button>
      </div>
    </div>
  )
}
