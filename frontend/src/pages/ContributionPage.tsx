import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Sparkles, FileCode2, ListChecks, TestTube2, Loader2 } from 'lucide-react'
import { generateContribution, getContributions } from '../services/api'
import type { Repository, Contribution } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

export default function ContributionPage() {
  const { repo } = useOutletContext<Ctx>()
  const [loading, setLoading] = useState(false)
  const [contribution, setContribution] = useState<Contribution | null>(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    try {
      await generateContribution(repo.id)
      const result = await getContributions(repo.id)
      setContribution(result)
    } catch {
      setError('Failed to generate contribution. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><Sparkles size={22} /></div>
        <h1>First Contribution</h1>
        <p className="text-secondary mt-2">
          Let the AI recommend a beginner-friendly contribution task for this repository.
        </p>
      </header>

      {!contribution && (
        <div className="coming-soon card">
          <Sparkles size={36} style={{ color: 'var(--accent)', opacity: 0.7 }} />
          <h3 className="mt-4">Find your first contribution</h3>
          <p className="text-secondary text-sm mt-2" style={{ maxWidth: 420, margin: '0.5rem auto 0' }}>
            The AI agent will analyse TODO comments, issues, documentation gaps, and code complexity
            to recommend a beginner-friendly task with full implementation guidance.
          </p>
          {error && <p className="text-sm mt-3" style={{ color: 'var(--error)' }}>{error}</p>}
          <button
            id="generate-contribution-btn"
            className="btn btn-primary btn-lg mt-6"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? <><Loader2 size={18} className="spin-icon" /> Analysing…</> : <><Sparkles size={18} /> Find First Contribution</>}
          </button>
        </div>
      )}

      {contribution && (
        <div className="contribution-result fade-in-up">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2>{contribution.title || 'Contribution Recommendation'}</h2>
              {contribution.difficulty && (
                <span className={`badge ${contribution.difficulty === 'Beginner' ? 'badge-success' : 'badge-warning'}`}>
                  {contribution.difficulty}
                </span>
              )}
            </div>
            <p className="text-secondary text-sm">{contribution.description || 'AI description will appear here.'}</p>

            {contribution.why_suitable && (
              <div className="info-box mt-4">
                <p className="text-xs text-muted mb-1">Why this task?</p>
                <p className="text-sm">{contribution.why_suitable}</p>
              </div>
            )}
          </div>

          {contribution.relevant_files.length > 0 && (
            <div className="card mt-4">
              <div className="flex items-center gap-2 mb-3">
                <FileCode2 size={16} style={{ color: 'var(--accent-light)' }} />
                <h3>Relevant Files</h3>
              </div>
              {contribution.relevant_files.map((f) => (
                <span key={f} className="file-ref"><FileCode2 size={11} /> {f}</span>
              ))}
            </div>
          )}

          {contribution.implementation_steps.length > 0 && (
            <div className="card mt-4">
              <div className="flex items-center gap-2 mb-3">
                <ListChecks size={16} style={{ color: 'var(--accent-light)' }} />
                <h3>Implementation Steps</h3>
              </div>
              <ol className="impl-steps">
                {contribution.implementation_steps.map((step, i) => (
                  <li key={i} className="text-sm text-secondary">{step}</li>
                ))}
              </ol>
            </div>
          )}

          {contribution.tests_to_add.length > 0 && (
            <div className="card mt-4">
              <div className="flex items-center gap-2 mb-3">
                <TestTube2 size={16} style={{ color: 'var(--teal)' }} />
                <h3>Tests to Add</h3>
              </div>
              <ul className="impl-steps">
                {contribution.tests_to_add.map((t, i) => (
                  <li key={i} className="text-sm text-secondary">{t}</li>
                ))}
              </ul>
            </div>
          )}

          <button className="btn btn-outline mt-4 text-sm" onClick={() => setContribution(null)}>
            ← Regenerate
          </button>
        </div>
      )}
    </div>
  )
}
