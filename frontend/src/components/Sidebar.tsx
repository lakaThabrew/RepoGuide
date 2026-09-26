import { NavLink, useNavigate } from 'react-router-dom'
import { Zap, LayoutDashboard, GitBranch, Terminal, MessageSquare, Sparkles, ExternalLink, FolderOpen } from 'lucide-react'
import type { Repository } from '../services/api'

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

interface SidebarProps {
  repo: Repository;
}

export default function Sidebar({ repo }: SidebarProps) {
  const navigate = useNavigate()

  return (
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
  )
}
