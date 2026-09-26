import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import { askQuestion } from '../services/api'
import type { Repository, QuestionResponse, QuestionEvidenceItem, QuestionSourceFile } from '../services/api'
import ChatInterface from '../components/ChatInterface'
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

export default function AskPage() {
  const { repo } = useOutletContext<Ctx>()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const send = async (question: string) => {
    if (!question.trim() || loading) return
    const userMsg: Message = { role: 'user', content: question.trim() }
    setMessages((m) => [...m, userMsg])
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

      <ChatInterface 
        repo={repo} 
        messages={messages} 
        loading={loading} 
        onSend={send} 
      />
    </div>
  )
}
