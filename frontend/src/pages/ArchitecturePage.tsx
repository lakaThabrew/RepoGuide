import { GitBranch } from 'lucide-react'
import './SubPages.css'

export default function ArchitecturePage() {
  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><GitBranch size={22} /></div>
        <h1>Architecture</h1>
        <p className="text-secondary mt-2">
          A visual breakdown of the project's components, data flow, and entry points.
        </p>
      </header>

      <div className="coming-soon card">
        <GitBranch size={36} style={{ color: 'var(--accent)', opacity: 0.6 }} />
        <h3 className="mt-4">AI Analysis Pending</h3>
        <p className="text-secondary text-sm mt-2" style={{ maxWidth: 420, margin: '0.5rem auto 0' }}>
          Once IBM Bob 2.0 is integrated during the hackathon, this section will show
          the full architecture map including components, data flow, important modules,
          and entry points.
        </p>
        <div className="placeholder-section mt-6" style={{ maxWidth: 500, margin: '1.5rem auto 0' }}>
          <div className="placeholder-row" />
          <div className="placeholder-row short" />
          <div className="placeholder-row medium" />
        </div>
      </div>
    </div>
  )
}
