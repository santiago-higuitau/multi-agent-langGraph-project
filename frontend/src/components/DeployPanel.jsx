import { useState, useEffect } from 'react'
import { deployCheck } from '../services/api'

export default function DeployPanel({ deploy, runStatus, onExport, onDeploy, onTeardown, downloadUrl }) {
  const [exportResult, setExportResult] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [deploying, setDeploying] = useState(false)
  const [composeInfo, setComposeInfo] = useState(null)
  const [apiKey, setApiKey] = useState('')

  useEffect(() => { deployCheck().then(({ data }) => setComposeInfo(data)).catch(() => {}) }, [exportResult])
  const handleExport = async () => { setExporting(true); const result = await onExport(); if (result) setExportResult(result); setExporting(false) }
  const handleDeploy = async () => { setDeploying(true); await onDeploy(apiKey); setDeploying(false) }

  const isCompleted = runStatus === 'completed'
  const isRunning = deploy.status === 'running' || deploy.status === 'already_running'
  const noCompose = composeInfo && !composeInfo.compose_tool

  return (
    <div className="space-y-4 max-w-2xl">
      <StepCard number="1" title="Exportar proyecto" description="Genera todos los archivos en la carpeta app/ y crea un ZIP descargable." active={isCompleted} done={!!exportResult}>
        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={handleExport} disabled={exporting || !isCompleted}
            className="px-5 py-2 bg-[#059669] hover:bg-[#047857] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] text-white rounded-[8px] text-sm font-medium transition">
            {exporting ? <Spinner text="Exportando..." /> : '📦 Exportar'}
          </button>
          {exportResult && (
            <a href={downloadUrl} className="px-4 py-2 text-sm text-[#059669] hover:text-[#047857] border border-[#A7F3D0] hover:border-[#059669] rounded-[8px] transition" download>
              ⬇ Descargar ZIP ({exportResult.files_written} archivos)
            </a>
          )}
          {!isCompleted && <span className="text-xs text-[#4B5563]">Completa el pipeline primero.</span>}
        </div>
      </StepCard>

      <StepCard number="2" title="API Key (opcional)" description="Si tienes una Anthropic API key, la app generada usará GenAI real. Sin key, usa modo fallback." active={!!exportResult} done={!!apiKey}>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-ant-api03-..."
              className="flex-1 bg-[#F7F9FB] border border-[#E5E7EB] focus:border-[#059669] focus:ring-2 focus:ring-[rgba(5,150,105,0.08)] rounded-[8px] px-3 py-2 text-sm text-[#111827] placeholder-[#9CA3AF] outline-none transition font-mono" autoComplete="off" />
            {apiKey && <button onClick={() => setApiKey('')} className="text-xs text-[#4B5563] hover:text-[#374151] px-2 py-1">limpiar</button>}
          </div>
          <p className="text-[10px] text-[#4B5563]">
            {apiKey ? `🔑 ${apiKey.length} caracteres — se inyectará al contenedor backend` : '⚡ Sin key, GenAI devuelve texto placeholder (la app sigue funcionando)'}
          </p>
        </div>
      </StepCard>

      <StepCard number="3" title="Desplegar localmente" description={composeInfo?.compose_tool ? `Usando ${composeInfo.compose_tool}` : 'Ejecuta docker-compose / podman-compose up --build'} active={!!exportResult} done={isRunning}>
        {noCompose ? (
          <div className="bg-amber-50 border border-amber-200 rounded-[8px] p-4 space-y-2">
            <p className="text-sm text-amber-700">No se encontró docker-compose ni podman-compose</p>
            <div className="text-xs text-[#4B5563] space-y-1">{composeInfo.instructions?.map((inst, i) => <p key={i}>{inst}</p>)}</div>
            <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
              <p className="text-xs text-[#4B5563] mb-1">O despliega manualmente con el ZIP descargado:</p>
              <pre className="text-xs text-[#374151] bg-[#F7F9FB] rounded-[8px] p-3 font-mono">{`cd project-xxx\ndocker-compose up --build\n# o: podman-compose up --build`}</pre>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            {!isRunning ? (
              <button onClick={handleDeploy} disabled={deploying || !exportResult}
                className="px-5 py-2 bg-[#059669] hover:bg-[#047857] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] text-white rounded-[8px] text-sm font-medium transition">
                {deploying ? <Spinner text="Desplegando..." /> : '🚀 Desplegar'}
              </button>
            ) : (
              <button onClick={onTeardown} className="px-5 py-2 bg-red-500 hover:bg-red-600 text-white rounded-[8px] text-sm font-medium transition">⏹ Detener</button>
            )}
            {composeInfo?.compose_tool && !isRunning && <span className="text-[10px] text-[#4B5563] bg-[#F7F9FB] px-2 py-1 rounded">{composeInfo.compose_tool}</span>}
            {!exportResult && !isRunning && <span className="text-xs text-[#4B5563]">Exporta primero.</span>}
          </div>
        )}
      </StepCard>

      {isRunning && deploy.urls && Object.keys(deploy.urls).length > 0 && (
        <div className="bg-[#ECFDF5] border border-[#A7F3D0] rounded-[14px] p-5">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-8 h-8 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] flex items-center justify-center"><span className="text-sm">🎉</span></div>
            <div>
              <h3 className="text-sm font-semibold text-[#059669]">Aplicación desplegada</h3>
              <p className="text-xs text-[#4B5563]">Tu aplicación está corriendo localmente{deploy.compose_tool && ` (${deploy.compose_tool})`}.</p>
            </div>
          </div>
          <div className="space-y-2">
            {Object.entries(deploy.urls).map(([name, url]) => (
              <div key={name} className="flex items-center gap-3 bg-white rounded-[8px] p-3 border border-[#E5E7EB]">
                <span className="text-xs text-[#4B5563] w-20 flex-shrink-0">{name}</span>
                <a href={url} target="_blank" rel="noopener noreferrer" className="text-sm text-[#059669] hover:text-[#047857] underline underline-offset-2 transition">{url}</a>
                <span className="ml-auto text-xs text-[#4B5563]">↗</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {exportResult && !isRunning && (
        <div className="bg-white border border-[#E5E7EB] rounded-[14px] p-5 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
          <h4 className="text-xs text-[#4B5563] mb-3">Deploy manual (alternativa)</h4>
          <pre className="text-xs text-[#374151] bg-[#F7F9FB] rounded-[8px] p-3 font-mono leading-relaxed">{`# 1. Asegúrate de que Docker/Podman esté corriendo
# 2. Entra a la carpeta del proyecto exportado:
cd app/

# 3. Configura tu API key:
#    Edita .env.example → .env con tu ANTHROPIC_API_KEY

# 4. Levanta con Docker:
docker-compose up --build

# O con Podman:
podman-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8001
# API Docs: http://localhost:8001/docs`}</pre>
        </div>
      )}

      {deploy.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-[14px] p-4">
          <p className="text-sm text-red-700 mb-2">{deploy.message || 'Error en el deploy'}</p>
          {deploy.logs?.length > 0 && <pre className="text-xs text-[#4B5563] max-h-40 overflow-y-auto whitespace-pre-wrap font-mono bg-[#F7F9FB] rounded-[8px] p-3">{deploy.logs.join('\n').slice(-2000)}</pre>}
        </div>
      )}
    </div>
  )
}

function StepCard({ number, title, description, active, done, children }) {
  return (
    <div className={`bg-white border rounded-[14px] p-5 transition shadow-[0_1px_8px_rgba(0,0,0,0.04)] ${done ? 'border-[#A7F3D0]' : active ? 'border-[#E5E7EB]' : 'border-[#E5E7EB] opacity-60'}`}>
      <div className="flex items-start gap-3 mb-3">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${done ? 'bg-[#059669] text-white' : active ? 'bg-[#059669] text-white' : 'bg-[#E5E7EB] text-[#4B5563]'}`}>
          {done ? '✓' : number}
        </div>
        <div>
          <h3 className="text-sm font-medium text-[#111827]">{title}</h3>
          <p className="text-xs text-[#4B5563] mt-0.5">{description}</p>
        </div>
      </div>
      {children}
    </div>
  )
}

function Spinner({ text }) {
  return <span className="flex items-center gap-2"><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />{text}</span>
}
