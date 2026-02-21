import { useEffect, useRef, useState } from 'react'

let mermaidLoaded = false
let mermaidLoading = false
const callbacks = []

function loadMermaid(cb) {
  if (mermaidLoaded) { cb(); return }
  callbacks.push(cb)
  if (mermaidLoading) return
  mermaidLoading = true
  const script = document.createElement('script')
  script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'
  script.onload = () => {
    window.mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' })
    mermaidLoaded = true
    callbacks.forEach(fn => fn())
    callbacks.length = 0
  }
  document.head.appendChild(script)
}

let idCounter = 0

export default function MermaidDiagram({ code, title }) {
  const ref = useRef(null)
  const [error, setError] = useState(null)
  const [ready, setReady] = useState(false)
  const id = useRef(`mermaid-${++idCounter}`)

  useEffect(() => {
    loadMermaid(() => setReady(true))
  }, [])

  useEffect(() => {
    if (!ready || !code || !ref.current) return
    setError(null)
    ref.current.innerHTML = ''
    window.mermaid.render(id.current, code)
      .then(({ svg }) => { if (ref.current) ref.current.innerHTML = svg })
      .catch(e => setError(e.message || 'Error rendering diagram'))
  }, [ready, code])

  if (!code) return null

  return (

    <div className="bg-white border border-[#E5E7EB] rounded-[14px] overflow-hidden">
      {title && (
        <div className="px-4 py-2.5 border-b border-[#E5E7EB] flex items-center gap-2">
          <span className="text-xs font-medium text-[#374151]">{title}</span>
        </div>
      )}
      <div className="p-4">
        {error
          ? <ErrorView error={error} code={code} />
          : <div ref={ref} className="flex justify-center overflow-x-auto" />
        }
      </div>
    </div>
  )
}

function ErrorView({ error, code }) {
  const [showRaw, setShowRaw] = useState(false)
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-[8px] px-3 py-2">
        <span>⚠️</span>
        <span>Diagrama con sintaxis inválida</span>
        <button onClick={() => setShowRaw(v => !v)} className="ml-auto text-[#059669] hover:text-[#047857]">
          {showRaw ? 'ocultar' : 'ver código'}
        </button>
      </div>
      {showRaw && <pre className="text-[10px] text-[#4B5563] bg-[#F7F9FB] border border-[#E5E7EB] rounded-[8px] p-3 overflow-x-auto whitespace-pre-wrap">{code}</pre>}
    </div>
  )
}
