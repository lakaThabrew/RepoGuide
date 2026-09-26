import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  Sparkles, FileCode2, ListChecks, ChevronDown, ChevronUp,
  Loader2, AlertCircle, BookOpen, TestTube2, Wrench, Zap, GitPullRequest,
  Star, Info
} from 'lucide-react'
import { generateContributions, getContributions } from '../services/api'
import type {
  Repository, ContributionResponse, ContributionCandidate,
  ContributionType, Difficulty, Impact, Confidence
} from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function typeIcon(type: ContributionType) {
  switch (type) {
    case 'documentation':     return <BookOpen size={13} />
    case 'testing':           return <TestTube2 size={13} />
    case 'developer_experience': return <Zap size={13} />
    case 'maintenance':       return <Wrench size={13} />
    case 'feature':           return <GitPullRequest size={13} />
  }
}

function typeLabel(type: ContributionType): string {
  switch (type) {
    case 'documentation':     return 'Documentation'
    case 'testing':           return 'Testing'
    case 'developer_experience': return 'Developer Experience'
    case 'maintenance':       return 'Maintenance'
    case 'feature':           return 'Feature'
  }
}

function difficultyClass(d: Difficulty): string {
  switch (d) {
    case 'beginner':     return 'badge-success'
    case 'intermediate': return 'badge-warning'
    case 'advanced':     return 'badge-error'
  }
}

function impactClass(i: Impact): string {
  switch (i) {
    case 'high':   return 'badge-accent'
    case 'medium': return 'badge-muted'
    case 'low':    return 'badge-muted'
  }
}

function confidenceClass(c: Confidence): string {
  switch (c) {
    case 'high':   return 'badge-success'
    case 'medium': return 'badge-warning'
    case 'low':    return 'badge-muted'
  }
}

// ---------------------------------------------------------------------------
// CandidateDetail — expanded view of a single candidate
// ---------------------------------------------------------------------------

function CandidateDetail({ candidate }: { candidate: ContributionCandidate }) {
  return (
    <div className="contribution-detail fade-in-up">
      {/* Why good first contribution */}
      <div className="why-box mt-4">
        <p className="text-xs text-muted mb-1" style={{ fontWeight: 600 }}>
          Why this is a good first contribution
        </p>
        <p className="text-sm">{candidate.why_good_first_contribution}</p>
      </div>

      {/* Files to read */}
      {candidate.files_to_read.length > 0 && (
        <div className="detail-section">
          <h3><FileCode2 size={12} style={{ display: 'inline', marginRight: 4 }} />Files to read first</h3>
          <div className="files-to-read">
            {candidate.files_to_read.map((f, i) => (
              <div key={i} className="file-read-item">
                <div style={{ minWidth: 16, color: 'var(--text-muted)', fontSize: '0.7rem', paddingTop: 1 }}>{i + 1}.</div>
                <div>
                  <div className="file-read-path">{f.file_path}</div>
                  <div className="file-read-reason">{f.reason}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Implementation steps */}
      {candidate.suggested_steps.length > 0 && (
        <div className="detail-section">
          <h3><ListChecks size={12} style={{ display: 'inline', marginRight: 4 }} />Implementation steps</h3>
          <ol className="steps-list">
            {candidate.suggested_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {/* Evidence */}
      {candidate.evidence.length > 0 && (
        <div className="detail-section">
          <h3><Info size={12} style={{ display: 'inline', marginRight: 4 }} />Supporting evidence</h3>
          <div className="evidence-list">
            {candidate.evidence.map((ev, i) => (
              <div key={i} className="evidence-item">
                <div>{ev.observation}</div>
                <div className="evidence-source">{ev.source}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related components */}
      {candidate.related_components.length > 0 && (
        <div className="detail-section">
          <h3>Related components</h3>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            {candidate.related_components.map((c) => (
              <span key={c} className="badge badge-muted">{c}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// CandidateCard — compact card for "other opportunities" list
// ---------------------------------------------------------------------------

interface CandidateCardProps {
  candidate: ContributionCandidate
  selected: boolean
  onSelect: () => void
}

function CandidateCard({ candidate, selected, onSelect }: CandidateCardProps) {
  return (
    <div
      className={`contribution-card ${selected ? 'selected' : ''}`}
      onClick={onSelect}
      role="button"
      aria-pressed={selected}
    >
      <div className="contribution-card-title">{candidate.title}</div>
      <div className="contribution-card-desc">{candidate.description}</div>
      <div className="contribution-card-badges">
        <span className={`badge ${difficultyClass(candidate.difficulty)}`}>
          {candidate.difficulty}
        </span>
        <span className="badge badge-muted">
          {typeIcon(candidate.type)} {typeLabel(candidate.type)}
        </span>
        <span className={`badge ${impactClass(candidate.impact)}`}>
          {candidate.impact} impact
        </span>
      </div>
      {selected && <ChevronUp size={13} style={{ marginTop: 6, color: 'var(--text-muted)' }} />}
      {!selected && <ChevronDown size={13} style={{ marginTop: 6, color: 'var(--text-muted)' }} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// RecommendedCard — prominent card for the recommended candidate
// ---------------------------------------------------------------------------

function RecommendedCard({ candidate }: { candidate: ContributionCandidate }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="card" style={{ borderColor: 'var(--border-active)' }}>
      <div className="flex items-center justify-between mb-3" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', marginBottom: 4 }}>{candidate.title}</h2>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            <span className={`badge ${difficultyClass(candidate.difficulty)}`}>
              {candidate.difficulty}
            </span>
            <span className="badge badge-muted">
              {typeIcon(candidate.type)} {typeLabel(candidate.type)}
            </span>
            <span className={`badge ${impactClass(candidate.impact)}`}>
              {candidate.impact} impact
            </span>
            <span className={`badge ${confidenceClass(candidate.confidence)}`}>
              {candidate.confidence} confidence
            </span>
          </div>
        </div>
        <button
          className="btn btn-outline text-sm"
          style={{ padding: '0.35rem 0.75rem' }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <><ChevronUp size={14} /> Collapse</> : <><ChevronDown size={14} /> Expand</>}
        </button>
      </div>

      <p className="text-sm text-secondary">{candidate.description}</p>

      {expanded && <CandidateDetail candidate={candidate} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ContributionPage
// ---------------------------------------------------------------------------

export default function ContributionPage() {
  const { repo } = useOutletContext<Ctx>()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ContributionResponse | null>(null)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const handleGenerate = async () => {
    if (loading) return
    setLoading(true)
    setError('')
    setSelectedId(null)
    try {
      await generateContributions(repo.id)
      const result = await getContributions(repo.id)
      setData(result)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
      const status = axiosErr?.response?.status
      const detail = axiosErr?.response?.data?.detail

      if (status === 404 && detail?.toLowerCase().includes('analysis')) {
        setError('Run repository analysis before finding contribution opportunities.')
      } else if (status === 422) {
        setError(
          detail ||
          'RepoGuide does not have enough indexed information to safely recommend a contribution.'
        )
      } else {
        setError('Failed to generate contributions. Make sure the backend is running.')
      }
    } finally {
      setLoading(false)
    }
  }

  const recommendedCandidates =
    data?.candidates.filter((c) => data.recommended_ids.includes(c.id)) ?? []

  const otherCandidates =
    data?.candidates.filter((c) => !data.recommended_ids.includes(c.id)) ?? []

  const selectedCandidate = otherCandidates.find((c) => c.id === selectedId) ?? null

  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><Sparkles size={22} /></div>
        <h1>Find My First Contribution</h1>
        <p className="text-secondary mt-2" style={{ maxWidth: 560 }}>
          RepoGuide analyzes this repository to identify contribution opportunities
          suitable for someone new to the codebase.
        </p>
      </header>

      {/* ——— Initial / empty state ——— */}
      {!data && !error && (
        <div className="coming-soon card">
          <Sparkles size={36} style={{ color: 'var(--accent)', opacity: 0.7 }} />
          <h3 className="mt-4">Find your first contribution</h3>
          <p className="text-secondary text-sm mt-2" style={{ maxWidth: 440, margin: '0.5rem auto 0' }}>
            RepoGuide will analyze the repository metadata to identify realistic
            first-contribution opportunities grounded in real evidence.
          </p>
          <button
            id="find-contributions-btn"
            className="btn btn-primary btn-lg mt-6"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading
              ? <><Loader2 size={18} className="spin-icon" /> Analysing…</>
              : <><Sparkles size={18} /> Find Contributions</>}
          </button>
        </div>
      )}

      {/* ——— Error state ——— */}
      {!data && error && (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem 2rem' }}>
          <AlertCircle size={32} style={{ color: 'var(--error)', margin: '0 auto 1rem' }} />
          <p className="text-sm" style={{ color: 'var(--error)', marginBottom: '1.25rem', maxWidth: 480, margin: '0 auto 1.25rem' }}>
            {error}
          </p>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading}>
            {loading ? <><Loader2 size={16} className="spin-icon" /> Retrying…</> : 'Try Again'}
          </button>
        </div>
      )}

      {/* ——— Loading while we already have data (regenerating) ——— */}
      {data && loading && (
        <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
          <Loader2 size={24} className="spin-icon" style={{ margin: '0 auto 0.75rem' }} />
          <p className="text-secondary text-sm">Refreshing analysis…</p>
        </div>
      )}

      {/* ——— Results ——— */}
      {data && !loading && (
        <div className="contribution-result fade-in-up">
          {/* Recommended first contribution */}
          {recommendedCandidates.length > 0 && (
            <section className="contribution-recommended">
              <div className="recommend-label">
                <Star size={13} /> Recommended First Contribution
              </div>
              {recommendedCandidates.map((c) => (
                <RecommendedCard key={c.id} candidate={c} />
              ))}
            </section>
          )}

          {/* Other opportunities */}
          {otherCandidates.length > 0 && (
            <section>
              <h2 className="text-sm text-muted mb-3" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Other Contribution Opportunities
              </h2>
              <div className="contribution-other-grid">
                {otherCandidates.map((c) => (
                  <CandidateCard
                    key={c.id}
                    candidate={c}
                    selected={selectedId === c.id}
                    onSelect={() => setSelectedId(selectedId === c.id ? null : c.id)}
                  />
                ))}
              </div>

              {selectedCandidate && (
                <div className="card mt-4 fade-in-up">
                  <div className="flex items-center justify-between mb-3">
                    <h2 style={{ fontSize: '1rem' }}>{selectedCandidate.title}</h2>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      <span className={`badge ${difficultyClass(selectedCandidate.difficulty)}`}>
                        {selectedCandidate.difficulty}
                      </span>
                      <span className={`badge ${impactClass(selectedCandidate.impact)}`}>
                        {selectedCandidate.impact} impact
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-secondary">{selectedCandidate.description}</p>
                  <CandidateDetail candidate={selectedCandidate} />
                </div>
              )}
            </section>
          )}

          {/* Footer metadata */}
          <div className="mt-6" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
            <span className="text-xs text-muted">
              {data.is_deterministic ? 'Deterministic analysis' : 'AI-enriched analysis'}
              {data.evidence_quality ? ` · Evidence quality: ${data.evidence_quality}` : ''}
            </span>
            <button className="btn btn-outline text-sm" onClick={handleGenerate} disabled={loading}>
              {loading ? <><Loader2 size={14} className="spin-icon" /> Refreshing…</> : '↺ Regenerate'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
