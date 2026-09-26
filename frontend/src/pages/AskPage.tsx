import { useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { MessageSquare, Send, User, Bot, FileCode2, Info } from 'lucide-react'
import { askQuestion } from '../services/api'
import type { Repository, QuestionResponse, QuestionEvidenceItem } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }

interface Message {
  role: 'user' | 'assistant'
  content: string
  evidence?: QuestionEvidenceItem[]
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
        <p className="text-secondary mt-2">Ask anything about this repository — answers are grounded in indexed metadata.</p>
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
                    {msg.isDeterministic ? ' Deterministic (metadata-grounded)' : ' AI-generated'}
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
