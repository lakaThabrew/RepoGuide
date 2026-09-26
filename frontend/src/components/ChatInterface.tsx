import { useState } from 'react'
import { Send, User, Bot, FileCode2, Info, Code } from 'lucide-react'
import type { QuestionEvidenceItem, QuestionSourceFile, Repository } from '../services/api'
import { useNavigate } from 'react-router-dom'

interface Message {
  role: 'user' | 'assistant'
  content: string
  evidence?: QuestionEvidenceItem[]
  sourceFiles?: QuestionSourceFile[]
  intent?: string
  isDeterministic?: boolean
}

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

interface ChatInterfaceProps {
  repo: Repository;
  messages: Message[];
  loading: boolean;
  onSend: (question: string) => void;
}

export default function ChatInterface({ repo, messages, loading, onSend }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const navigate = useNavigate()

  return (
    <>
      <div className="chat-history">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="chat-bubble">
              <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
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
      <form className="chat-input-form card" onSubmit={(e) => { e.preventDefault(); onSend(input); setInput('') }}>
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
    </>
  )
}
