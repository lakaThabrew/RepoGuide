import { Terminal } from 'lucide-react'
import './SubPages.css'

const SECTIONS = ['Prerequisites', 'Installation', 'Environment Variables', 'Database Setup', 'Running the App', 'Common Problems']

export default function SetupPage() {
  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><Terminal size={22} /></div>
        <h1>Setup Guide</h1>
        <p className="text-secondary mt-2">
          Step-by-step instructions for setting up and running this project locally.
        </p>
      </header>

      <div className="setup-sections">
        {SECTIONS.map((title) => (
          <div key={title} className="card" style={{ marginBottom: '1rem' }}>
            <div className="flex items-center gap-3 mb-3">
              <span className="badge badge-accent">{title}</span>
            </div>
            <div className="placeholder-section">
              <div className="placeholder-row" />
              <div className="placeholder-row short" />
            </div>
            <div className="placeholder-code mt-3" />
          </div>
        ))}
      </div>

      <p className="text-muted text-xs mt-4 text-center">
        Setup instructions will be generated from the repository by IBM Bob 2.0 during the hackathon.
      </p>
    </div>
  )
}
