import { useEffect, useState, useCallback } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import {
  Code2,
  Globe,
  GitBranch,
  Star,
  Zap,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  FolderOpen,
  BookOpen,
  Package,
  Shield,
  Server,
  Layers,
  FileText,
  Terminal,
  Database,
  Layout,
  TestTube2,
  Rocket,
} from 'lucide-react'
import type { Repository, AnalysisResponse, ArchitectureComponent, FileEvidence, EntryPoint, Dependency } from '../services/api'
import { startAnalysis, getAnalysis } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

// ── Helpers ──────────────────────────────────────────────────────────────────

function badge(text: string, variant: 'accent' | 'teal' | 'success' | 'warning' | 'error' = 'accent') {
  return (
    <span key={text} className={`badge badge-${variant}`} style={{ marginRight: '0.35rem', marginBottom: '0.35rem' }}>
      {text}
    </span>
  )
}

function confidenceBadge(c: 'high' | 'medium' | 'low') {
  const map = { high: 'success', medium: 'warning', low: 'error' } as const
  return <span className={`badge badge-${map[c]}`}>{c}</span>
}

const ARCH_ICON: Record<string, React.ReactNode> = {
  frontend:   <Layout size={16} />,
  'backend/api': <Server size={16} />,
  backend:    <Server size={16} />,
  api:        <Server size={16} />,
  database:   <Database size={16} />,
  'data layer': <Database size={16} />,
  authentication: <Shield size={16} />,
  auth:       <Shield size={16} />,
  services:   <Layers size={16} />,
  tests:      <TestTube2 size={16} />,
  deployment: <Rocket size={16} />,
  infrastructure: <Rocket size={16} />,
}

function archIcon(name: string) {
  const lower = name.toLowerCase()
  for (const [key, icon] of Object.entries(ARCH_ICON)) {
    if (lower.includes(key)) return icon
  }
  return <Layers size={16} />
}

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  'entry point':    <Terminal size={14} />,
  configuration:    <FileText size={14} />,
  deployment:       <Rocket size={14} />,
  documentation:    <BookOpen size={14} />,
  api:              <Server size={14} />,
  database:         <Database size={14} />,
  authentication:   <Shield size={14} />,
  'core service':   <Layers size={14} />,
  frontend:         <Layout size={14} />,
  tests:            <TestTube2 size={14} />,
}

function categoryIcon(cat?: string) {
  if (!cat) return <FileText size={14} />
  const lower = cat.toLowerCase()
  for (const [key, icon] of Object.entries(CATEGORY_ICON)) {
    if (lower.includes(key)) return icon
  }
  return <FileText size={14} />
}

// Group FileEvidence by category
function groupByCategory(files: FileEvidence[]): Record<string, FileEvidence[]> {
  const result: Record<string, FileEvidence[]> = {}
  for (const f of files) {
    const cat = f.category ?? 'other'
    if (!result[cat]) result[cat] = []
    result[cat].push(f)
  }
  return result
}

// Group Dependency by source_file
function groupBySourceFile(deps: Dependency[]): Record<string, Dependency[]> {
  const result: Record<string, Dependency[]> = {}
  for (const d of deps) {
    if (!result[d.source_file]) result[d.source_file] = []
    result[d.source_file].push(d)
  }
  return result
}

// ── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader({ icon, title, count }: { icon: React.ReactNode; title: string; count?: number }) {
  return (
    <div className="flex items-center gap-3 mb-4" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
      <span style={{ color: 'var(--accent-light)' }}>{icon}</span>
      <h3 style={{ margin: 0 }}>{title}</h3>
      {count !== undefined && (
        <span className="badge badge-accent" style={{ marginLeft: 'auto' }}>{count}</span>
      )}
    </div>
  )
}

function TechStackSection({ tech }: { tech: AnalysisResponse['technologies'] }) {
  if (!tech) return null

  const rows: Array<{ label: string; items: string[]; variant: 'accent' | 'teal' | 'success' | 'warning' }> = [
    { label: 'Languages',        items: tech.languages,        variant: 'teal' },
    { label: 'Frameworks',       items: tech.frameworks,       variant: 'accent' },
    { label: 'Runtimes',         items: tech.runtimes,         variant: 'success' },
    { label: 'Package Managers', items: tech.package_managers, variant: 'warning' },
    { label: 'Databases',        items: tech.databases,        variant: 'teal' },
  ]

  const hasAny = rows.some((r) => r.items.length > 0) || tech.auth_signals.length > 0
  if (!hasAny) return null

  return (
    <div className="card mt-6">
      <SectionHeader icon={<Code2 size={18} />} title="Technology Stack" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        {rows.filter((r) => r.items.length > 0).map((row) => (
          <div key={row.label} className="flex" style={{ gap: '0.75rem', alignItems: 'flex-start' }}>
            <span className="text-xs text-muted" style={{ minWidth: 130, paddingTop: '0.25rem', flexShrink: 0 }}>
              {row.label}
            </span>
            <div style={{ flexWrap: 'wrap', display: 'flex' }}>
              {row.items.map((item) => badge(item, row.variant))}
            </div>
          </div>
        ))}
        {tech.auth_signals.length > 0 && (
          <div className="flex" style={{ gap: '0.75rem', alignItems: 'flex-start' }}>
            <span className="text-xs text-muted" style={{ minWidth: 130, paddingTop: '0.25rem', flexShrink: 0 }}>
              Auth Signals
            </span>
            <div style={{ flexWrap: 'wrap', display: 'flex' }}>
              {tech.auth_signals.map((sig) => badge(sig.file_path, 'accent'))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ArchitectureSection({ components }: { components: ArchitectureComponent[] }) {
  if (!components || components.length === 0) return null

  return (
    <div className="card mt-6">
      <SectionHeader icon={<GitBranch size={18} />} title="Architecture" count={components.length} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.85rem' }}>
        {components.map((comp) => (
          <div
            key={comp.name}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <span style={{ color: 'var(--accent-light)' }}>{archIcon(comp.name)}</span>
              <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{comp.name}</span>
            </div>
            <p className="text-secondary text-sm" style={{ marginBottom: comp.evidence_files.length > 0 ? '0.6rem' : 0 }}>
              {comp.description}
            </p>
            {comp.evidence_files.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {comp.evidence_files.slice(0, 4).map((f) => (
                  <code key={f} style={{ fontSize: '0.72rem' }}>{f}</code>
                ))}
                {comp.evidence_files.length > 4 && (
                  <span className="text-xs text-muted" style={{ alignSelf: 'center' }}>
                    +{comp.evidence_files.length - 4} more
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function EntryPointsSection({ entryPoints, repoId }: { entryPoints: EntryPoint[]; repoId: string }) {
  const navigate = useNavigate()
  if (!entryPoints || entryPoints.length === 0) return null

  return (
    <div className="card mt-6">
      <SectionHeader icon={<Terminal size={18} />} title="Entry Points" count={entryPoints.length} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
        {entryPoints.map((ep, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: '0.85rem',
              alignItems: 'flex-start',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-md)',
              padding: '0.85rem',
              border: '1px solid var(--border)',
            }}
          >
            <span className="badge badge-teal" style={{ flexShrink: 0, marginTop: '0.1rem' }}>{ep.kind}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <code style={{ display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>{ep.file_path}</code>
              <p className="text-secondary text-xs" style={{ margin: 0 }}>{ep.evidence}</p>
            </div>
            <button
              className="btn btn-outline"
              style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem', height: 'auto', flexShrink: 0 }}
              onClick={() => navigate(`/repository/${repoId}/files?path=${encodeURIComponent(ep.file_path)}`)}
            >
              View
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function ImportantFilesSection({ files, repoId }: { files: FileEvidence[]; repoId: string }) {
  const navigate = useNavigate()
  if (!files || files.length === 0) return null

  const grouped = groupByCategory(files)
  const categories = Object.keys(grouped).sort()

  return (
    <div className="card mt-6">
      <SectionHeader icon={<FileText size={18} />} title="Important Files" count={files.length} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {categories.map((cat) => (
          <div key={cat}>
            <div className="flex items-center gap-2 mb-2">
              <span style={{ color: 'var(--text-muted)' }}>{categoryIcon(cat)}</span>
              <span className="text-xs" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                {cat}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {grouped[cat].map((f, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    gap: '0.75rem',
                    alignItems: 'flex-start',
                    padding: '0.55rem 0.75rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <code style={{ fontSize: '0.78rem', display: 'block', marginBottom: '0.2rem' }}>{f.file_path}</code>
                    <p className="text-xs text-secondary" style={{ margin: 0 }}>{f.reason}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0 }}>
                    {confidenceBadge(f.confidence)}
                    <button
                      className="btn btn-outline"
                      style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem', height: 'auto' }}
                      onClick={() => navigate(`/repository/${repoId}/files?path=${encodeURIComponent(f.file_path)}`)}
                    >
                      View
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StructureSection({ tech }: { tech: AnalysisResponse['technologies'] }) {
  if (!tech) return null

  const hasDirs =
    tech.source_directories.length > 0 ||
    tech.test_directories.length > 0 ||
    tech.doc_directories.length > 0

  if (!hasDirs) return null

  return (
    <div className="card mt-6">
      <SectionHeader icon={<FolderOpen size={18} />} title="Repository Structure" />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
        {tech.source_directories.length > 0 && (
          <div>
            <p className="text-xs" style={{ color: 'var(--teal)', fontWeight: 600, marginBottom: '0.4rem' }}>Source</p>
            {tech.source_directories.map((d) => (
              <div key={d} className="flex items-center gap-2 mb-1">
                <FolderOpen size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                <code style={{ fontSize: '0.78rem' }}>{d}</code>
              </div>
            ))}
          </div>
        )}
        {tech.test_directories.length > 0 && (
          <div>
            <p className="text-xs" style={{ color: 'var(--warning)', fontWeight: 600, marginBottom: '0.4rem' }}>Tests</p>
            {tech.test_directories.map((d) => (
              <div key={d} className="flex items-center gap-2 mb-1">
                <FolderOpen size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                <code style={{ fontSize: '0.78rem' }}>{d}</code>
              </div>
            ))}
          </div>
        )}
        {tech.doc_directories.length > 0 && (
          <div>
            <p className="text-xs" style={{ color: 'var(--accent-light)', fontWeight: 600, marginBottom: '0.4rem' }}>Docs</p>
            {tech.doc_directories.map((d) => (
              <div key={d} className="flex items-center gap-2 mb-1">
                <FolderOpen size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                <code style={{ fontSize: '0.78rem' }}>{d}</code>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DependenciesSection({ deps }: { deps: Dependency[] }) {
  if (!deps || deps.length === 0) return null

  const grouped = groupBySourceFile(deps)
  const files = Object.keys(grouped).sort()

  return (
    <div className="card mt-6">
      <SectionHeader icon={<Package size={18} />} title="Dependencies" count={deps.length} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {files.map((srcFile) => (
          <div key={srcFile}>
            <div className="flex items-center gap-2 mb-2">
              <code style={{ fontSize: '0.78rem', color: 'var(--teal)' }}>{srcFile}</code>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {grouped[srcFile].map((dep, i) => (
                <span
                  key={i}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.2rem 0.55rem',
                    fontSize: '0.78rem',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <span style={{ color: 'var(--text-primary)' }}>{dep.name}</span>
                  {dep.version && <span style={{ color: 'var(--text-muted)' }}>{dep.version}</span>}
                  <span className={`badge badge-${dep.kind === 'runtime' ? 'success' : dep.kind === 'dev' ? 'warning' : 'accent'}`}
                    style={{ padding: '0.1rem 0.4rem', fontSize: '0.65rem' }}>
                    {dep.kind}
                  </span>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

type PageState = 'loading-analysis' | 'not-analyzed' | 'analyzing' | 'analyzed' | 'error'

export default function OverviewPage() {
  const { repo } = useOutletContext<Ctx>()

  const [pageState, setPageState] = useState<PageState>('loading-analysis')
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  const loadAnalysis = useCallback(async () => {
    setPageState('loading-analysis')
    try {
      const data = await getAnalysis(repo.id)
      setAnalysis(data)
      setPageState('analyzed')
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setPageState('not-analyzed')
      } else {
        setAnalyzeError('Failed to load analysis. Please try again.')
        setPageState('error')
      }
    }
  }, [repo.id])

  useEffect(() => {
    loadAnalysis()
  }, [loadAnalysis])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalyzeError(null)
    setPageState('analyzing')
    try {
      const result = await startAnalysis(repo.id)
      if (result.status === 'error') {
        setAnalyzeError(result.error ?? 'Analysis failed. Please try again.')
        setPageState('error')
      } else {
        // Reload to get the full analysis record
        await loadAnalysis()
      }
    } catch {
      setAnalyzeError('Analysis request failed. Please check your connection and try again.')
      setPageState('error')
    } finally {
      setAnalyzing(false)
    }
  }

  // ── Stat bar (always shown) ────────────────────────────────────────────────
  const stats = [
    { label: 'Language',  value: repo.language || '—',             icon: Code2 },
    { label: 'Branch',    value: repo.default_branch || 'main',    icon: GitBranch },
    { label: 'Status',    value: repo.status,                      icon: Star },
    { label: 'Owner',     value: repo.owner || '—',                icon: Globe },
  ]

  return (
    <div className="sub-page fade-in-up">
      {/* ── Header ── */}
      <header className="sub-header">
        <h1>{repo.name || 'Repository'}</h1>
        <p className="text-secondary mt-2">{repo.description || 'No description available.'}</p>
      </header>

      {/* ── Quick stats ── */}
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

      {/* ── Analysis status banner / loading ── */}
      {pageState === 'loading-analysis' && (
        <div className="card mt-6 flex items-center gap-3">
          <div className="spinner" />
          <p className="text-secondary text-sm">Loading analysis…</p>
        </div>
      )}

      {/* ── Analyzing (in-progress) state ── */}
      {pageState === 'analyzing' && (
        <div className="card mt-6" style={{ borderColor: 'var(--border-active)' }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="spinner" />
            <h3 style={{ margin: 0 }}>Analyzing Repository…</h3>
          </div>
          <p className="text-secondary text-sm">
            RepoGuide is scanning the repository's file structure, detecting technologies,
            architecture components, entry points, and dependencies. This may take a moment.
          </p>
        </div>
      )}

      {/* ── Not analyzed — empty state ── */}
      {pageState === 'not-analyzed' && (
        <div className="card mt-6 text-center" style={{ padding: '2.5rem' }}>
          <div
            className="page-icon"
            style={{ margin: '0 auto 1rem', width: 52, height: 52 }}
          >
            <Zap size={24} />
          </div>
          <h3>Repository Not Yet Analyzed</h3>
          <p className="text-secondary text-sm mt-2" style={{ maxWidth: 480, margin: '0.5rem auto 0' }}>
            Run an analysis to discover the technology stack, architecture components, entry points,
            important files, and dependency information for this repository.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: '0.75rem',
              margin: '1.75rem auto',
              maxWidth: 560,
              textAlign: 'left',
            }}
          >
            {[
              { icon: <Code2 size={15} />,      text: 'Languages & Frameworks' },
              { icon: <GitBranch size={15} />,   text: 'Architecture Components' },
              { icon: <Terminal size={15} />,    text: 'Entry Points' },
              { icon: <FileText size={15} />,    text: 'Important Files' },
              { icon: <Package size={15} />,     text: 'Dependencies' },
              { icon: <FolderOpen size={15} />,  text: 'Directory Structure' },
            ].map(({ icon, text }) => (
              <div
                key={text}
                className="flex items-center gap-2"
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.55rem 0.75rem',
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                }}
              >
                <span style={{ color: 'var(--accent-light)' }}>{icon}</span>
                {text}
              </div>
            ))}
          </div>

          <button
            className="btn btn-primary btn-lg"
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            <Zap size={17} />
            Analyze Repository
          </button>
        </div>
      )}

      {/* ── Error state ── */}
      {pageState === 'error' && (
        <div className="card mt-6" style={{ borderColor: 'rgba(239,68,68,0.35)' }}>
          <div className="flex items-center gap-3 mb-3">
            <AlertCircle size={20} style={{ color: 'var(--error)', flexShrink: 0 }} />
            <h3 style={{ margin: 0, color: 'var(--error)' }}>Analysis Error</h3>
          </div>
          <p className="text-secondary text-sm mb-4">
            {analyzeError ?? 'An unexpected error occurred.'}
          </p>
          <button className="btn btn-outline" onClick={handleAnalyze} disabled={analyzing}>
            <RefreshCw size={15} />
            Retry Analysis
          </button>
        </div>
      )}

      {/* ── Analyzed — full results ── */}
      {pageState === 'analyzed' && analysis && (
        <>
          {/* Analysis status bar */}
          <div
            className="card mt-6 flex items-center gap-3"
            style={{ padding: '0.85rem 1.25rem', borderColor: 'rgba(34,197,94,0.25)' }}
          >
            <CheckCircle2 size={17} style={{ color: 'var(--success)', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <span className="text-sm" style={{ color: 'var(--success)', fontWeight: 600 }}>
                Analysis complete
              </span>
              {analysis.created_at && (
                <span className="text-xs text-muted" style={{ marginLeft: '0.75rem' }}>
                  <Clock size={11} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 3 }} />
                  {new Date(analysis.created_at).toLocaleString()}
                </span>
              )}
            </div>
            <button
              className="btn btn-outline text-sm"
              style={{ padding: '0.4rem 0.85rem' }}
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              <RefreshCw size={13} />
              Re-analyze
            </button>
          </div>

          {/* Project Summary */}
          {analysis.project_summary && (
            <div className="card mt-6">
              <SectionHeader icon={<BookOpen size={18} />} title="Project Summary" />
              <p className="text-secondary text-sm" style={{ lineHeight: 1.75 }}>
                {analysis.project_summary}
              </p>
            </div>
          )}

          {/* Technology Stack */}
          <TechStackSection tech={analysis.technologies} />

          {/* Architecture */}
          {analysis.technologies?.arch_components && (
            <ArchitectureSection components={analysis.technologies.arch_components} />
          )}

          {/* Entry Points */}
          {analysis.entry_points && (
            <EntryPointsSection entryPoints={analysis.entry_points} repoId={repo.id} />
          )}

          {/* Important Files */}
          {analysis.important_files && (
            <ImportantFilesSection files={analysis.important_files} repoId={repo.id} />
          )}

          {/* Repository Structure */}
          <StructureSection tech={analysis.technologies} />

          {/* Dependencies */}
          {analysis.dependencies && (
            <DependenciesSection deps={analysis.dependencies} />
          )}

          {/* No meaningful content fallback */}
          {!analysis.project_summary &&
            !analysis.technologies?.languages?.length &&
            !analysis.entry_points?.length &&
            !analysis.important_files?.length && (
              <div className="card mt-6 text-center" style={{ padding: '2rem' }}>
                <p className="text-secondary text-sm">
                  The analysis completed but did not detect enough evidence to populate sections.
                  This may happen for very small or empty repositories.
                </p>
              </div>
            )}
        </>
      )}
    </div>
  )
}
