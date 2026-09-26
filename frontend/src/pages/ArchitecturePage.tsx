import { useEffect, useState, useCallback } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import {
  GitBranch,
  Layout,
  Server,
  Database,
  Shield,
  Layers,
  TestTube2,
  Rocket,
  FileText,
  Terminal,
  BookOpen,
  ArrowDown,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
} from 'lucide-react'
import type {
  Repository,
  ArchitectureData,
  ArchitectureComponent,
  ArchitectureRelationship,
  EntryPoint,
} from '../services/api'
import { getArchitecture, getAnalysis, startAnalysis } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

// ── Helpers ───────────────────────────────────────────────────────────────────

function confidenceBadge(c: 'high' | 'medium' | 'low') {
  const map = { high: 'success', medium: 'warning', low: 'error' } as const
  return <span className={`badge badge-${map[c]}`}>{c} confidence</span>
}

function evidenceQualityBadge(q: 'sufficient' | 'partial' | 'insufficient') {
  const map = { sufficient: 'success', partial: 'warning', insufficient: 'error' } as const
  const label = { sufficient: 'Evidence: sufficient', partial: 'Evidence: partial', insufficient: 'Evidence: insufficient' }
  return <span className={`badge badge-${map[q]}`}>{label[q]}</span>
}

const COMPONENT_ICON: Record<string, React.ReactNode> = {
  frontend:            <Layout size={18} />,
  'backend/api':       <Server size={18} />,
  backend:             <Server size={18} />,
  api:                 <Server size={18} />,
  'database/data layer': <Database size={18} />,
  database:            <Database size={18} />,
  authentication:      <Shield size={18} />,
  auth:                <Shield size={18} />,
  services:            <Layers size={18} />,
  tests:               <TestTube2 size={18} />,
  'deployment/infrastructure': <Rocket size={18} />,
  deployment:          <Rocket size={18} />,
}

function componentIcon(name: string) {
  const lower = name.toLowerCase()
  for (const [key, icon] of Object.entries(COMPONENT_ICON)) {
    if (lower.includes(key)) return icon
  }
  return <Layers size={18} />
}

function componentColor(name: string): string {
  const lower = name.toLowerCase()
  if (lower.includes('frontend')) return 'var(--accent-light)'
  if (lower.includes('backend') || lower.includes('api')) return 'var(--teal)'
  if (lower.includes('database') || lower.includes('data')) return '#8b5cf6'
  if (lower.includes('auth')) return '#f59e0b'
  if (lower.includes('service')) return '#10b981'
  if (lower.includes('test')) return '#06b6d4'
  if (lower.includes('deploy') || lower.includes('infra')) return '#ec4899'
  return 'var(--accent-light)'
}

// ── Architecture Diagram ──────────────────────────────────────────────────────

function ArchitectureDiagram({
  components,
  relationships,
}: {
  components: ArchitectureComponent[]
  relationships: ArchitectureRelationship[]
}) {
  if (components.length === 0) return null

  // Build a topological sort: find components that are targets (have something pointing to them)
  const targetNames = new Set(relationships.map((r) => r.target))
  const sourceNames = new Set(relationships.map((r) => r.source))

  // Assign render tiers:
  // tier 0: have no incoming edges (sources with no in-arrows)
  // tier 1+: components that are targets
  // non-relational: components with no relationship at all
  const tiers: ArchitectureComponent[][] = []
  const placed = new Set<string>()

  // Tier 0: sources that aren't targets of anything
  const tier0 = components.filter(
    (c) => sourceNames.has(c.name) && !targetNames.has(c.name)
  )
  if (tier0.length > 0) {
    tiers.push(tier0)
    tier0.forEach((c) => placed.add(c.name))
  }

  // Middle tiers: follow relationships layer by layer (simple BFS)
  let frontier = tier0.map((c) => c.name)
  while (frontier.length > 0) {
    const nextNames = relationships
      .filter((r) => frontier.includes(r.source))
      .map((r) => r.target)
      .filter((t) => !placed.has(t))
    if (nextNames.length === 0) break
    const nextTier = components.filter((c) => nextNames.includes(c.name))
    if (nextTier.length > 0) {
      tiers.push(nextTier)
      nextTier.forEach((c) => placed.add(c.name))
      frontier = nextTier.map((c) => c.name)
    } else {
      break
    }
  }

  // Remaining: components not in any relationship (show below diagram)
  const standalone = components.filter((c) => !placed.has(c.name))

  const hasDiagram = tiers.length > 0

  return (
    <div style={{ marginTop: '1.5rem' }}>
      {hasDiagram && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.25rem',
            padding: '1.5rem',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1.25rem',
          }}
        >
          {tiers.map((tier, ti) => (
            <div key={ti} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
              {/* Tier row */}
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                {tier.map((comp) => (
                  <div
                    key={comp.name}
                    style={{
                      border: `1px solid ${componentColor(comp.name)}`,
                      borderRadius: 'var(--radius-md)',
                      padding: '0.6rem 1.1rem',
                      background: 'var(--bg-card)',
                      minWidth: 130,
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ color: componentColor(comp.name), marginBottom: '0.3rem', display: 'flex', justifyContent: 'center' }}>
                      {componentIcon(comp.name)}
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                      {comp.name}
                    </div>
                    {comp.technology && (
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        {comp.technology}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {/* Arrow between tiers */}
              {ti < tiers.length - 1 && (
                <div style={{ color: 'var(--text-muted)', margin: '0.4rem 0' }}>
                  <ArrowDown size={18} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Standalone components (no relationships) */}
      {standalone.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.75rem',
            padding: '1rem',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          {standalone.map((comp) => (
            <div
              key={comp.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                border: `1px solid ${componentColor(comp.name)}`,
                borderRadius: 'var(--radius-md)',
                padding: '0.45rem 0.85rem',
                background: 'var(--bg-card)',
              }}
            >
              <span style={{ color: componentColor(comp.name) }}>{componentIcon(comp.name)}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{comp.name}</div>
                {comp.technology && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{comp.technology}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Relationships legend */}
      {relationships.length > 0 && (
        <div style={{ marginTop: '0.85rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {relationships.map((rel, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.25rem 0.6rem',
              }}
            >
              <span style={{ fontWeight: 600, color: componentColor(rel.source) }}>{rel.source}</span>
              <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontWeight: 600, color: componentColor(rel.target) }}>{rel.target}</span>
              <span style={{ color: 'var(--text-muted)' }}>({rel.relationship_type})</span>
              {confidenceBadge(rel.confidence)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Component Card ────────────────────────────────────────────────────────────

function ComponentCard({ comp }: { comp: ArchitectureComponent }) {
  const [expanded, setExpanded] = useState(false)
  const color = componentColor(comp.name)

  return (
    <div
      className="card"
      style={{ borderLeft: `3px solid ${color}`, cursor: 'pointer' }}
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <span style={{ color }}>{componentIcon(comp.name)}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{comp.name}</span>
            {comp.technology && (
              <span className="badge badge-accent" style={{ fontSize: '0.7rem' }}>{comp.technology}</span>
            )}
            {confidenceBadge(comp.confidence)}
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{expanded ? '▲' : '▼'}</span>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0 0 0.6rem' }}>
        {comp.description}
      </p>

      {expanded && (
        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Directories */}
          {comp.directories.length > 0 && (
            <div>
              <p style={{ fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Directories
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                {comp.directories.map((d) => (
                  <code key={d} style={{ fontSize: '0.75rem', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.1rem 0.4rem' }}>
                    {d}/
                  </code>
                ))}
              </div>
            </div>
          )}

          {/* Evidence files */}
          {comp.evidence_files.length > 0 && (
            <div>
              <p style={{ fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Files
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {comp.evidence_files.map((f) => (
                  <div key={f} className="file-ref">
                    <FileText size={11} />
                    <span className="file-ref-path">{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence bullets */}
          {comp.evidence.length > 0 && (
            <div>
              <p style={{ fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Evidence
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                {comp.evidence.map((e, i) => (
                  <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <CheckCircle2 size={13} style={{ color: 'var(--success, #10b981)', marginTop: '0.15rem', flexShrink: 0 }} />
                    <span>{e}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Entry Points Section ──────────────────────────────────────────────────────

function EntryPointsSection({ entryPoints }: { entryPoints: EntryPoint[] }) {
  if (!entryPoints || entryPoints.length === 0) return null
  return (
    <div className="card mt-6">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
        <span style={{ color: 'var(--accent-light)' }}><Terminal size={18} /></span>
        <h3 style={{ margin: 0 }}>Entry Points</h3>
        <span className="badge badge-accent" style={{ marginLeft: 'auto' }}>{entryPoints.length}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {entryPoints.map((ep, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: '0.85rem',
              alignItems: 'flex-start',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-md)',
              padding: '0.75rem',
              border: '1px solid var(--border)',
            }}
          >
            <span className="badge badge-teal" style={{ flexShrink: 0, marginTop: '0.1rem' }}>{ep.kind}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <code style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.8rem', color: 'var(--teal)' }}>
                {ep.file_path}
              </code>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{ep.evidence}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Reading Order Section ─────────────────────────────────────────────────────

function ReadingOrderSection({ steps }: { steps: string[] }) {
  if (!steps || steps.length === 0) return null
  return (
    <div className="card mt-6">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
        <span style={{ color: 'var(--accent-light)' }}><BookOpen size={18} /></span>
        <h3 style={{ margin: 0 }}>How to Read This Repository</h3>
      </div>
      <ol className="steps-list">
        {steps.map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
    </div>
  )
}

// ── Architecture Summary ──────────────────────────────────────────────────────

function ArchitectureSummary({ data }: { data: ArchitectureData }) {
  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '1rem 1.25rem',
        marginBottom: '1.5rem',
      }}
    >
      <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
        {data.summary}
      </p>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

type PageState = 'loading' | 'no_repository' | 'no_analysis' | 'insufficient' | 'ready' | 'error'

export default function ArchitecturePage() {
  const { repo } = useOutletContext<Ctx>()
  const navigate = useNavigate()

  const [pageState, setPageState] = useState<PageState>('loading')
  const [archData, setArchData] = useState<ArchitectureData | null>(null)
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  const loadArchitecture = useCallback(async () => {
    setPageState('loading')
    try {
      const response = await getArchitecture(repo.id)
      if (response.status === 'no_analysis') {
        setPageState('no_analysis')
        setMessage(response.message ?? null)
      } else if (response.status === 'insufficient') {
        setArchData(response.architecture_data ?? null)
        setPageState('insufficient')
        setMessage(response.message ?? null)
      } else {
        setArchData(response.architecture_data ?? null)
        setPageState('ready')
        setMessage(null)
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setPageState('no_repository')
      } else {
        setPageState('error')
        setMessage('Failed to load architecture data. Please try again.')
      }
    }
  }, [repo.id])

  useEffect(() => {
    loadArchitecture()
  }, [loadArchitecture])

  // Extract entry points from analysis via the analysis endpoint
  // (entry_points come from the analysis, not the architecture endpoint)
  const loadEntryPoints = useCallback(async () => {
    try {
      const analysis = await getAnalysis(repo.id)
      setEntryPoints(analysis.entry_points ?? [])
    } catch {
      // Not critical — entry points are optional
    }
  }, [repo.id])

  useEffect(() => {
    loadEntryPoints()
  }, [loadEntryPoints])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setMessage(null)
    try {
      const result = await startAnalysis(repo.id)
      if (result.status === 'error') {
        setMessage(result.error ?? 'Analysis failed.')
        setPageState('error')
      } else {
        await loadArchitecture()
        await loadEntryPoints()
      }
    } catch {
      setMessage('Analysis request failed. Please check your connection.')
      setPageState('error')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="sub-page fade-in-up">
      {/* ── Header ── */}
      <header className="sub-header">
        <div className="page-icon"><GitBranch size={22} /></div>
        <h1>Repository Architecture</h1>
        <p className="text-secondary mt-2">
          Understand how this repository is structured and how its major components connect.
        </p>
      </header>

      {/* ── Loading ── */}
      {pageState === 'loading' && (
        <div className="card flex items-center gap-3">
          <div className="spinner" />
          <p className="text-secondary text-sm">Loading architecture…</p>
        </div>
      )}

      {/* ── No repository ── */}
      {pageState === 'no_repository' && (
        <div className="card coming-soon">
          <AlertCircle size={32} style={{ color: 'var(--error)' }} />
          <h3 className="mt-4">Repository Not Found</h3>
          <p className="text-secondary text-sm mt-2">This repository no longer exists.</p>
          <button className="btn btn-outline mt-4" onClick={() => navigate('/')}>← Back to Home</button>
        </div>
      )}

      {/* ── No analysis ── */}
      {pageState === 'no_analysis' && (
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <Clock size={32} style={{ color: 'var(--text-muted)' }} />
          <h3 className="mt-4">Architecture Analysis Not Generated Yet</h3>
          <p className="text-secondary text-sm mt-2" style={{ maxWidth: 440, margin: '0.5rem auto 0' }}>
            {message || 'Generate repository analysis first to explore the architecture.'}
          </p>
          <button
            className="btn btn-primary mt-6"
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            {analyzing ? (
              <><RefreshCw size={15} className="spin-icon" /> Analyzing…</>
            ) : (
              'Generate Analysis'
            )}
          </button>
        </div>
      )}

      {/* ── Error ── */}
      {pageState === 'error' && (
        <div className="card" style={{ borderColor: 'var(--error)' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
            <AlertCircle size={18} style={{ color: 'var(--error)', flexShrink: 0, marginTop: '0.1rem' }} />
            <div>
              <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Error</p>
              <p className="text-secondary text-sm">{message}</p>
            </div>
          </div>
          <button className="btn btn-outline mt-4" onClick={loadArchitecture}>
            <RefreshCw size={14} /> Try Again
          </button>
        </div>
      )}

      {/* ── Insufficient evidence ── */}
      {pageState === 'insufficient' && (
        <div className="card" style={{ padding: '2rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', marginBottom: '1rem' }}>
            <AlertCircle size={18} style={{ color: 'var(--warning)', flexShrink: 0, marginTop: '0.1rem' }} />
            <div>
              <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Limited Architecture Evidence</p>
              <p className="text-secondary text-sm">
                {message || 'The repository metadata does not contain enough information to confidently determine component relationships.'}
              </p>
            </div>
          </div>
          {archData && archData.summary && (
            <p className="text-secondary text-sm" style={{ marginTop: '0.5rem' }}>{archData.summary}</p>
          )}
        </div>
      )}

      {/* ── Ready — full architecture view ── */}
      {pageState === 'ready' && archData && (
        <>
          {/* Stats bar */}
          <div className="stats-grid">
            <div className="stat-card card">
              <CheckCircle2 size={18} style={{ color: 'var(--accent-light)' }} />
              <div>
                <p className="text-xs text-muted">Architecture Confidence</p>
                <p className="stat-value" style={{ textTransform: 'capitalize' }}>{archData.confidence}</p>
              </div>
            </div>
            <div className="stat-card card">
              <Layers size={18} style={{ color: 'var(--accent-light)' }} />
              <div>
                <p className="text-xs text-muted">Components</p>
                <p className="stat-value">{archData.components.length}</p>
              </div>
            </div>
            <div className="stat-card card">
              <GitBranch size={18} style={{ color: 'var(--accent-light)' }} />
              <div>
                <p className="text-xs text-muted">Relationships</p>
                <p className="stat-value">{archData.relationships.length}</p>
              </div>
            </div>
            <div className="stat-card card">
              <FileText size={18} style={{ color: 'var(--accent-light)' }} />
              <div>
                <p className="text-xs text-muted">Evidence Quality</p>
                <p className="stat-value" style={{ textTransform: 'capitalize' }}>{archData.evidence_quality}</p>
              </div>
            </div>
          </div>

          {/* Summary */}
          <ArchitectureSummary data={archData} />

          {/* Architecture Overview */}
          <div className="card mt-6">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '0.5rem' }}>
              <span style={{ color: 'var(--accent-light)' }}><GitBranch size={18} /></span>
              <h3 style={{ margin: 0 }}>Architecture Overview</h3>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem' }}>
                {evidenceQualityBadge(archData.evidence_quality)}
                {confidenceBadge(archData.confidence)}
              </div>
            </div>
            <ArchitectureDiagram
              components={archData.components}
              relationships={archData.relationships}
            />
          </div>

          {/* Component Cards */}
          {archData.components.length > 0 && (
            <div className="mt-6">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
                <span style={{ color: 'var(--accent-light)' }}><Layers size={18} /></span>
                <h3 style={{ margin: 0 }}>Components</h3>
                <span className="badge badge-accent" style={{ marginLeft: 'auto' }}>{archData.components.length}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {archData.components.map((comp) => (
                  <ComponentCard key={comp.name} comp={comp} />
                ))}
              </div>
            </div>
          )}

          {/* Entry Points */}
          <EntryPointsSection entryPoints={entryPoints} />

          {/* How to Read */}
          <ReadingOrderSection steps={archData.reading_order} />
        </>
      )}
    </div>
  )
}
