import { Routes, Route, Link, useLocation } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RunPage from './pages/RunPage'
import RunsListPage from './pages/RunsListPage'

const NAV = [
  { to: '/', label: 'Nuevo Run', icon: '⚡' },
  { to: '/runs', label: 'Historial', icon: '📋' },
]

export default function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F0FAF5' }}>
      <header className="bg-white border-b border-[#E5E7EB] px-6 py-3 flex items-center justify-between shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-[#059669] flex items-center justify-center text-white text-sm font-bold shadow-sm">
              AI
            </div>
            <span className="text-base font-semibold tracking-tight group-hover:text-[#059669] transition" style={{ color: '#111827' }}>
              Dev Team
            </span>
          </Link>
          <nav className="flex gap-1 text-sm">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className={`px-3 py-1.5 rounded-[8px] transition flex items-center gap-1.5 ${
                  location.pathname === n.to
                    ? 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
                    : 'text-[#374151] hover:text-[#111827] hover:bg-[#F0FAF5]'
                }`}
              >
                <span className="text-xs">{n.icon}</span>
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="text-xs text-[#374151]">Multi-Agent Software Delivery</div>
      </header>
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/runs" element={<RunsListPage />} />
          <Route path="/runs/:runId" element={<RunPage />} />
        </Routes>
      </main>
    </div>
  )
}
