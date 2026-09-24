import { useOutletContext } from 'react-router-dom'
import { Code2, Globe, GitBranch, Star } from 'lucide-react'
import type { Repository } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

export default function OverviewPage() {
  const { repo } = useOutletContext<Ctx>()

  const stats = [
    { label: 'Language', value: repo.language || '—', icon: Code2 },
    { label: 'Branch', value: repo.default_branch || 'main', icon: GitBranch },
    { label: 'Status', value: repo.status, icon: Star },
    { label: 'Owner', value: repo.owner || '—', icon: Globe },
  ]

  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <h1>{repo.name || 'Repository'}</h1>
        <p className="text-secondary mt-2">{repo.description || 'No description available.'}</p>
      </header>

      <div className="stats-grid">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="stat-card card">
            <Icon size={18} style={{ color: 'var(--accent-light)' }} />
            <div>
              <p className="text-xs text-muted">{label}</p>
              <p className="stat-value">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="card mt-6">
        <h3 className="mb-4">About this Repository</h3>
        <p className="text-secondary text-sm">
          AI-powered analysis will populate this section during the hackathon.
          Once connected to IBM Bob 2.0, you will see a full project summary,
          architecture breakdown, technology stack, and important files identified here.
        </p>
        <div className="placeholder-section mt-4">
          <div className="placeholder-row" />
          <div className="placeholder-row short" />
          <div className="placeholder-row" />
          <div className="placeholder-row medium" />
        </div>
      </div>
    </div>
  )
}
