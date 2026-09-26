import { useEffect, useState } from 'react'
import { useParams, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Zap, LayoutDashboard, GitBranch, Terminal, MessageSquare, Sparkles, ExternalLink, FolderOpen } from 'lucide-react'
import { getRepository } from '../services/api'
import type { Repository } from '../services/api'
import './RepositoryLayout.css'

const NAV_ITEMS = [
  { to: '', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: 'architecture', label: 'Architecture', icon: GitBranch },
  { to: 'files', label: 'Files', icon: FolderOpen },
  { to: 'setup', label: 'Setup Guide', icon: Terminal },
  { to: 'ask', label: 'Ask RepoGuide', icon: MessageSquare },
  { to: 'contribution', label: 'First Contribution', icon: Sparkles },
]

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: 'warning',
    cloning: 'accent',
    scanning: 'accent',
    analyzing: 'accent',
    completed: 'success',
    failed: 'error',
  }
  const cls = map[status] || 'accent'
  return (
    <span className={`badge badge-${cls}`}>
      <span className={`status-dot ${status === 'completed' ? 'done' : status === 'failed' ? 'error' : status === 'pending' ? 'pending' : 'running'}`} />
      {status}
    </span>
  )
}

export default function RepositoryLayout() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [repo, setRepo] = useState<Repository | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    getRepository(id)
      .then(setRepo)
      .catch(() => setError('Repository not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="repo-loading bg-mesh">
        <div className="spinner" style={{ width: 36, height: 36 }} />
        <p className="text-secondary mt-4">Loading repository…</p>
      </div>
    )
  }

  if (error || !repo) {
    return (
      <div className="repo-loading bg-mesh">
        <p className="text-sm" style={{ color: 'var(--error)' }}>{error || 'Repository not found'}</p>
        <button className="btn btn-outline mt-4" onClick={() => navigate('/')}>← Back to Home</button>
      </div>
    )
  }

  return (
    <div className="repo-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo" onClick={() => navigate('/')}>
          <div className="logo-icon"><Zap size={16} /></div>
          <span className="logo-text">RepoGuide</span>
        </div>

        <div className="sidebar-repo">
          <p className="text-xs text-muted" style={{ marginBottom: 4 }}>Analyzing</p>
          <p className="repo-name truncate">{repo.owner}/{repo.name}</p>
          <div className="mt-2"><StatusBadge status={repo.status} /></div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={label}
              to={to}
              end={end}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <a
            href={repo.github_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline text-sm w-full"
            style={{ justifyContent: 'center' }}
          >
            <ExternalLink size={14} /> View on GitHub
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main className="repo-main">
        <Outlet context={{ repo }} />
      </main>
    </div>
  )
}
