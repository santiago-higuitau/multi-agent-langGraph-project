import { useState } from 'react'
import { getFileContent } from '../services/api'

const EXT_ICONS = { py: '🐍', jsx: '⚛️', js: '📜', json: '📋', css: '🎨', html: '🌐', yml: '⚙️', yaml: '⚙️', sql: '🗄️', md: '📝', txt: '📄', conf: '⚙️' }
function getIcon(path) { const ext = path.split('.').pop()?.toLowerCase(); return EXT_ICONS[ext] || '📄' }

export default function FilesPanel({ files, runId }) {
  const [selected, setSelected] = useState(null)
  const [content, setContent] = useState('')
  const [loadingFile, setLoadingFile] = useState(false)

  const handleSelect = async (path) => {
    if (selected === path) { setSelected(null); return }
    setSelected(path); setLoadingFile(true)
    try { const { data } = await getFileContent(runId, path); setContent(data.content || '') }
    catch { setContent('// Error loading file content') }
    finally { setLoadingFile(false) }
  }

  if (!files.length) return (
    <div className="text-center py-16">
      <div className="text-3xl mb-3">📁</div>
      <p className="text-[#4B5563] text-sm">No hay archivos generados todavía.</p>
      <p className="text-[#9CA3AF] text-xs mt-1">Se generarán después de aprobar Gate 1.</p>
    </div>
  )

  const groups = {}
  files.forEach((f) => { const parts = f.path.split('/'); const folder = parts.length > 1 ? parts[0] : 'root'; if (!groups[folder]) groups[folder] = []; groups[folder].push(f) })

  return (
    <div className="flex gap-3 h-[600px]">
      <div className="w-72 flex-shrink-0 bg-white border border-[#E5E7EB] rounded-[14px] overflow-y-auto shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="px-4 py-3 border-b border-[#E5E7EB]">
          <span className="text-xs text-[#374151]">{files.length} archivos generados</span>
        </div>
        {Object.entries(groups).map(([folder, folderFiles]) => (
          <div key={folder}>
            <div className="px-4 py-2 text-[10px] font-semibold text-[#4B5563] uppercase tracking-wider sticky top-0 bg-white">{folder}/</div>
            {folderFiles.map((f) => (
              <button key={f.path} onClick={() => handleSelect(f.path)}
                className={`w-full text-left px-4 py-2 text-xs hover:bg-[#F7F9FB] transition flex items-center gap-2 ${
                  selected === f.path ? 'bg-[#ECFDF5] text-[#059669] border-r-2 border-[#059669]' : 'text-[#374151]'
                }`}>
                <span className="text-[10px]">{getIcon(f.path)}</span>
                <span className="truncate">{f.path.split('/').slice(1).join('/')}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
      <div className="flex-1 bg-white border border-[#E5E7EB] rounded-[14px] overflow-hidden flex flex-col shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        {selected ? (
          <>
            <div className="px-4 py-2.5 border-b border-[#E5E7EB] flex items-center justify-between bg-white">
              <div className="flex items-center gap-2">
                <span className="text-xs">{getIcon(selected)}</span>
                <code className="text-xs text-[#4B5563] font-mono">{selected}</code>
              </div>
              {files.find((f) => f.path === selected)?.created_by && (
                <span className="text-[10px] text-[#4B5563]">{files.find((f) => f.path === selected).created_by}</span>
              )}
            </div>
            <div className="flex-1 overflow-auto p-4">
              {loadingFile ? (
                <div className="flex items-center gap-2 text-[#4B5563] text-xs">
                  <div className="w-3 h-3 border border-[#E5E7EB] border-t-[#059669] rounded-full animate-spin" />Cargando...
                </div>
              ) : (
                <pre className="text-xs text-[#111827] whitespace-pre-wrap font-mono leading-relaxed">{content}</pre>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-[#4B5563]">
            <span className="text-2xl mb-2">👈</span>
            <span className="text-sm">Selecciona un archivo</span>
          </div>
        )}
      </div>
    </div>
  )
}
