import { useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { MessageSquare, Send, User, Bot, FileCode2, Info, Code } from 'lucide-react'
import { askQuestion } from '../services/api'
import type { Repository, QuestionResponse, QuestionEvidenceItem, QuestionSourceFile } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

interface Message {
  role: 'user' | 'assistant'
  content: string
  evidence?: QuestionEvidenceItem[]
  sourceFiles?: QuestionSourceFile[]
  intent?: string
  isDeterministic?: boolean
}

const SUGGESTED = [
  'Where does this application start?',
  'How is authentication handled?',
  'What should I read first?',
  'Where is the database logic?',
  'How are the frontend and backend connected?',
  'What technologies does this project use?',
  'Where are the tests?',
  'How do I run this project?',
]

// ---------------------------------------------------------------------------
// Source snippet display — renders repository code as plain text, never HTML
// ---------------------------------------------------------------------------

function SourceSnippet({ file, onView }: { file: QuestionSourceFile; onView: () => void }) {
  const [expanded, setExpanded] = useState(false)

  if (file.is_binary || file.error) return null
  if (!file.snippet) return null

  return (
    <div className="source-snippet">
      <div className="source-snippet-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flex: 1, minWidth: 0 }}>
          <Code size={11} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />
          <span className="file-ref-path">{file.file_path}</span>
          {file.language && (
            <span className="badge badge-accent" style={{ fontSize: '0.62rem' }}>{file.language}</span>
          )}
          {file.truncated && (
            <span className="badge badge-muted" style={{ fontSize: '0.62rem' }}>truncated</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.3rem', flexShrink: 0 }}>
          <button
            className="btn btn-outline"
            style={{ fontSize: '0.62rem', padding: '0.1rem 0.35rem', height: 'auto' }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'Less' : 'Expand'}
          </button>
          <button
            className="btn btn-outline"
            style={{ fontSize: '0.62rem', padding: '0.1rem 0.35rem', height: 'auto' }}
            onClick={onView}
          >
            View
          </button>
        </div>
      </div>
      {/* Source code displayed as plain text, never as HTML */}
      <pre className="source-snippet-body" aria-label={`Source snippet from ${file.file_path}`}>
        <code>
          {expanded
            ? file.snippet
            : file.snippet.length > 200
              ? file.snippet.slice(0, 200) + '\n…'
              : file.snippet}
        </code>
      </pre>
    </div>
  )
}

export default function AskPage() {
  const { repo } = useOutletContext<Ctx>()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async (question: string) => {
    if (!question.trim() || loading) return
    const userMsg: Message = { role: 'user', content: question.trim() }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res: QuestionResponse = await askQuestion(repo.id, question.trim())
      const botMsg: Message = {
        role: 'assistant',
        content: res.answer || 'No answer could be generated from the available repository metadata.',
        evidence: res.evidence && res.evidence.length > 0 ? res.evidence : (
          res.referenced_files && res.referenced_files.length > 0
            ? res.referenced_files.map((f) => ({ file_path: f }))
            : []
        ),
        sourceFiles: res.source_files && res.source_files.length > 0 ? res.source_files : [],
        intent: res.intent,
        isDeterministic: res.is_deterministic,
      }
      setMessages((m) => [...m, botMsg])
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number; data?: { detail?: string } } })?.response?.status
      const detail = (err as { response?: { status?: number; data?: { detail?: string } } })?.response?.data?.detail
      let errorMsg = '❌ Failed to get a response. Is the backend running?'
      if (status === 404) {
        errorMsg = detail?.includes('analysis')
          ? '⚠️ No analysis found for this repository. Please run the analysis first.'
          : '⚠️ Repository not found.'
      } else if (status === 400) {
        errorMsg = `⚠️ ${detail || 'Invalid question.'}`
      } else if (status === 422) {
        errorMsg = '⚠️ Question is too long or empty.'
      }
      setMessages((m) => [...m, { role: 'assistant', content: errorMsg }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sub-page ask-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><MessageSquare size={22} /></div>
        <h1>Ask RepoGuide</h1>
        <p className="text-secondary mt-2">
          Ask anything about this repository — answers are grounded in indexed metadata and source files.
        </p>
      </header>

      {/* Suggested questions — shown only when no conversation yet */}
      {messages.length === 0 && (
        <div className="suggested-wrap">
          <p className="text-xs text-muted mb-3">Suggested questions</p>
          <div className="suggested-grid">
            {SUGGESTED.map((q) => (
              <button key={q} className="btn btn-outline text-sm suggested-btn" onClick={() => send(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat history */}
      <div className="chat-history">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="chat-bubble">
              <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>

              {/* Source snippets — shown before evidence list */}
              {msg.sourceFiles && msg.sourceFiles.some(sf => sf.snippet && !sf.is_binary && !sf.error) && (
                <div className="source-snippets-wrap mt-3">
                  <p className="text-xs text-muted mb-1">
                    <Code size={10} style={{ verticalAlign: 'middle', marginRight: '0.2rem' }} />
                    Source files retrieved
                  </p>
                  {msg.sourceFiles
                    .filter(sf => sf.snippet && !sf.is_binary && !sf.error)
                    .map((sf, j) => (
                      <SourceSnippet
                        key={j}
                        file={sf}
                        onView={() => navigate(`/repository/${repo.id}/files?path=${encodeURIComponent(sf.file_path)}`)}
                      />
                    ))}
                </div>
              )}

              {/* Evidence / referenced files */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="file-refs mt-3">
                  <p className="text-xs text-muted mb-1">Evidence references</p>
                  {msg.evidence.map((e, j) => (
                    <div key={j} className="file-ref" style={{ justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem', flex: 1, minWidth: 0 }}>
                        <FileCode2 size={11} />
                        <span className="file-ref-path">{e.file_path}</span>
                        {e.reason && (
                          <span className="file-ref-reason text-xs text-muted"> — {e.reason}</span>
                        )}
                      </div>
                      <button
                        className="btn btn-outline"
                        style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem', height: 'auto', flexShrink: 0, marginLeft: '0.5rem' }}
                        onClick={() => navigate(`/repository/${repo.id}/files?path=${encodeURIComponent(e.file_path)}`)}
                      >
                        View
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Source badge */}
              {msg.role === 'assistant' && msg.isDeterministic !== undefined && (
                <div className="answer-meta mt-2">
                  <span className="badge badge-muted">
                    <Info size={10} />
                    {msg.isDeterministic ? ' Deterministic (metadata-grounded)' : ' AI-generated (code-grounded)'}
                  </span>
                  {msg.intent && msg.intent !== 'general' && msg.intent !== 'unknown' && (
                    <span className="badge badge-muted ml-1">intent: {msg.intent.replace(/_/g, ' ')}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <div className="chat-avatar"><Bot size={14} /></div>
            <div className="chat-bubble">
              <div className="typing-dots"><span /><span /><span /></div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form className="chat-input-form card" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <input
          id="chat-input"
          className="input"
          placeholder="Ask about this repository…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button id="chat-send-btn" type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          <Send size={16} />
        </button>
      </form>
    </div>
  )
}
