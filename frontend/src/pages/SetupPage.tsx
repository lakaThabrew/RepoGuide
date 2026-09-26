import { useState, useCallback } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  Terminal, Loader2, AlertCircle, CheckCircle2,
  ChevronDown, ChevronUp, Copy, Check,
  Package, Settings2, Database, Play, ShieldCheck,
  AlertTriangle, Info, Cpu,
} from 'lucide-react'
import { generateSetupGuide, getSetupGuide } from '../services/api'
import type {
  Repository, SetupGuide, SetupSection, SetupPrerequisite,
  SetupWarning, SetupConfidence,
} from '../services/api'
import './SubPages.css'
import './SetupPage.css'

interface Ctx { repo: Repository }

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function confidenceClass(c: SetupConfidence): string {
  switch (c) {
    case 'high':   return 'badge-success'
    case 'medium': return 'badge-warning'
    case 'low':    return 'badge-error'
  }
}

function confidenceLabel(c: SetupConfidence): string {
  switch (c) {
    case 'high':   return 'High confidence'
    case 'medium': return 'Medium confidence'
    case 'low':    return 'Low confidence'
  }
}

// ---------------------------------------------------------------------------
// CopyButton — copies a command to the clipboard
// ---------------------------------------------------------------------------

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }, [text])

  return (
    <button
      className="copy-btn"
      onClick={handleCopy}
      title="Copy command"
      aria-label="Copy command"
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  )
}

// ---------------------------------------------------------------------------
// CommandBlock — a single command with evidence and explanation
// ---------------------------------------------------------------------------

function CommandBlock({ cmd }: { cmd: { command: string; explanation: string; evidence: string[] } }) {
  return (
    <div className="setup-cmd-block">
      <div className="setup-cmd-header">
        <code className="setup-cmd-text">{cmd.command}</code>
        <CopyButton text={cmd.command} />
      </div>
      {cmd.explanation && (
        <p className="setup-cmd-explanation">{cmd.explanation}</p>
      )}
      {cmd.evidence.length > 0 && (
        <div className="setup-cmd-evidence">
          <span className="evidence-label">Evidence:</span>
          {cmd.evidence.map((e) => (
            <code key={e} className="evidence-file">{e}</code>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SetupSectionCard — a collapsible section of the guide
// ---------------------------------------------------------------------------

interface SectionCardProps {
  icon: React.ReactNode
  section: SetupSection
  defaultOpen?: boolean
}

function SectionCard({ icon, section, defaultOpen = true }: SectionCardProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="setup-section-card card">
      <button
        className="setup-section-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="setup-section-icon">{icon}</span>
        <span className="setup-section-title">{section.title}</span>
        <span className="setup-section-chevron">
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </span>
      </button>

      {open && (
        <div className="setup-section-body">
          {section.description && (
            <p className="setup-section-desc">{section.description}</p>
          )}

          {section.commands.length > 0 && (
            <div className="setup-cmd-list">
              {section.commands.map((cmd, i) => (
                <CommandBlock key={i} cmd={cmd} />
              ))}
            </div>
          )}

          {section.notes.length > 0 && (
            <div className="setup-notes-list">
              {section.notes.map((note, i) => (
                <div key={i} className="setup-note">
                  <Info size={13} className="setup-note-icon" />
                  <span>{note}</span>
                </div>
              ))}
            </div>
          )}

          {section.commands.length === 0 && section.notes.length === 0 && (
            <p className="text-muted text-sm">
              RepoGuide could not determine this from the indexed repository metadata.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// PrerequisitesCard
// ---------------------------------------------------------------------------

function PrerequisitesCard({ prereqs }: { prereqs: SetupPrerequisite[] }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="setup-section-card card">
      <button
        className="setup-section-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="setup-section-icon"><Cpu size={16} /></span>
        <span className="setup-section-title">Prerequisites</span>
        <span className="setup-section-chevron">
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </span>
      </button>

      {open && (
        <div className="setup-section-body">
          <p className="setup-section-desc">
            Tools and runtimes required to work with this repository,
            detected from indexed repository evidence.
          </p>
          <div className="prereq-grid">
            {prereqs.map((p) => (
              <div key={p.name} className="prereq-card">
                <div className="prereq-name">{p.name}</div>
                <div className="prereq-version">{p.version_note}</div>
                {p.evidence.length > 0 && (
                  <div className="prereq-evidence">
                    {p.evidence.map((e) => (
                      <code key={e} className="evidence-file">{e}</code>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// WarningsCard
// ---------------------------------------------------------------------------

function WarningsCard({ warnings }: { warnings: SetupWarning[] }) {
  const [open, setOpen] = useState(true)
  if (warnings.length === 0) return null

  return (
    <div className="setup-section-card setup-warnings-card card">
      <button
        className="setup-section-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="setup-section-icon" style={{ color: 'var(--warning, #f59e0b)' }}>
          <AlertTriangle size={16} />
        </span>
        <span className="setup-section-title">Warnings &amp; Notes</span>
        <span className="badge badge-warning" style={{ marginLeft: 'auto', marginRight: '0.5rem' }}>
          {warnings.length}
        </span>
        <span className="setup-section-chevron">
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </span>
      </button>

      {open && (
        <div className="setup-section-body">
          {warnings.map((w, i) => (
            <div key={i} className="setup-warning-item">
              <AlertTriangle size={13} className="setup-warning-icon" />
              <div>
                <p className="text-sm">{w.message}</p>
                {w.evidence.length > 0 && (
                  <div className="setup-cmd-evidence" style={{ marginTop: '0.35rem' }}>
                    {w.evidence.map((e) => (
                      <code key={e} className="evidence-file">{e}</code>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// GuideDisplay — renders a complete SetupGuide
// ---------------------------------------------------------------------------

function GuideDisplay({ guide }: { guide: SetupGuide }) {
  return (
    <div className="setup-guide fade-in-up">
      {/* Confidence banner */}
      <div className="setup-confidence-bar">
        <span className={`badge ${confidenceClass(guide.confidence)}`}>
          <CheckCircle2 size={11} />
          {confidenceLabel(guide.confidence)}
        </span>
        <span className="text-muted text-xs">
          Evidence-grounded · deterministic · no AI fabrication
        </span>
      </div>

      {/* Warnings — shown first so the developer sees them */}
      <WarningsCard warnings={guide.warnings} />

      {/* Prerequisites */}
      {guide.prerequisites.length > 0 && (
        <PrerequisitesCard prereqs={guide.prerequisites} />
      )}

      {/* Install dependencies */}
      {guide.install_dependencies && (
        <SectionCard
          icon={<Package size={16} />}
          section={guide.install_dependencies}
          defaultOpen
        />
      )}

      {/* Environment configuration */}
      {guide.environment_configuration && (
        <SectionCard
          icon={<Settings2 size={16} />}
          section={guide.environment_configuration}
          defaultOpen
        />
      )}

      {/* Database */}
      {guide.database_setup && (
        <SectionCard
          icon={<Database size={16} />}
          section={guide.database_setup}
          defaultOpen
        />
      )}

      {/* Run the application */}
      {guide.run_application && (
        <SectionCard
          icon={<Play size={16} />}
          section={guide.run_application}
          defaultOpen
        />
      )}

      {/* Verify setup */}
      {guide.verify_setup && (
        <SectionCard
          icon={<ShieldCheck size={16} />}
          section={guide.verify_setup}
          defaultOpen
        />
      )}

      <p className="text-muted text-xs mt-4 text-center">
        Commands are derived from repository metadata only. Always review them before running.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SetupPage — main page component
// ---------------------------------------------------------------------------

type PageState = 'idle' | 'loading' | 'loaded' | 'error'

export default function SetupPage() {
  const { repo } = useOutletContext<Ctx>()

  const [state, setState] = useState<PageState>('idle')
  const [guide, setGuide] = useState<SetupGuide | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [generating, setGenerating] = useState(false)

  // On first render, try loading an existing guide silently
  const handleLoad = useCallback(async () => {
    setState('loading')
    setErrorMsg('')
    try {
      const resp = await getSetupGuide(repo.id)
      if (resp.guide) {
        setGuide(resp.guide)
        setState('loaded')
      } else {
        setState('idle')
      }
    } catch {
      // No guide yet — stay in idle state
      setState('idle')
    }
  }, [repo.id])

  // Explicit generate (or re-generate)
  const handleGenerate = useCallback(async () => {
    setGenerating(true)
    setErrorMsg('')
    try {
      await generateSetupGuide(repo.id)
      // Fetch the freshly generated guide
      const resp = await getSetupGuide(repo.id)
      if (resp.guide) {
        setGuide(resp.guide)
        setState('loaded')
      } else {
        setErrorMsg(resp.error || 'Setup guide could not be generated from the available evidence.')
        setState('error')
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to generate setup guide. Ensure the repository has been analysed first.'
      setErrorMsg(msg)
      setState('error')
    } finally {
      setGenerating(false)
    }
  }, [repo.id])

  // Idle — initial prompt
  const renderIdle = () => (
    <div className="setup-idle">
      <div className="setup-idle-icon">
        <Terminal size={28} />
      </div>
      <h2 className="setup-idle-title">Get Started</h2>
      <p className="setup-idle-desc">
        RepoGuide can generate a repository-grounded setup guide from the files
        and configuration it has indexed. Commands and instructions are derived
        from repository evidence only — never fabricated.
      </p>
      <div className="setup-idle-actions">
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating
            ? <><Loader2 size={16} className="spin-icon" /> Generating…</>
            : 'Generate Setup Guide'}
        </button>
        <button
          className="btn btn-outline"
          onClick={handleLoad}
          disabled={state === 'loading'}
        >
          {state === 'loading'
            ? <><Loader2 size={16} className="spin-icon" /> Loading…</>
            : 'Load Existing Guide'}
        </button>
      </div>
    </div>
  )

  return (
    <div className="sub-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><Terminal size={22} /></div>
        <h1>Setup Guide</h1>
        <p className="text-secondary mt-2">
          Repository-grounded setup instructions — backed by indexed evidence, not guesswork.
        </p>
      </header>

      {/* Error banner */}
      {state === 'error' && (
        <div className="setup-error-banner">
          <AlertCircle size={15} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Loading spinner */}
      {state === 'loading' && (
        <div className="setup-loading">
          <Loader2 size={24} className="spin-icon" />
          <p className="text-secondary text-sm mt-2">Loading setup guide…</p>
        </div>
      )}

      {/* Idle / initial state */}
      {(state === 'idle' || state === 'error') && renderIdle()}

      {/* Loaded guide */}
      {state === 'loaded' && guide && (
        <>
          <div className="setup-actions-bar">
            <button
              className="btn btn-outline btn-sm"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating
                ? <><Loader2 size={14} className="spin-icon" /> Regenerating…</>
                : '↻ Regenerate'}
            </button>
          </div>
          <GuideDisplay guide={guide} />
        </>
      )}
    </div>
  )
}
