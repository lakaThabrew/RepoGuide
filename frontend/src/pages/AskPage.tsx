import React, { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { MessageSquare, Send, User, Bot, FileCode2 } from 'lucide-react'
import { askQuestion } from '../services/api'
import type { Repository, QuestionResponse } from '../services/api'
import './SubPages.css'

interface Ctx { repo: Repository }
interface Message {
  role: 'user' | 'assistant'
  content: string
  referencedFiles?: string[]
}

const SUGGESTED = [
  'What is the main entry point?',
  'What technologies does this project use?',
  'How does authentication work?',
  'What are the most important files?',
]

export default function AskPage() {
  const { repo } = useOutletContext<Ctx>()
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
        content: res.answer || '⚠️ AI integration is not yet connected. This will work once IBM Bob 2.0 is integrated during the hackathon.',
        referencedFiles: res.referenced_files,
      }
      setMessages((m) => [...m, botMsg])
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: '❌ Failed to get a response. Is the backend running?' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sub-page ask-page fade-in-up">
      <header className="sub-header">
        <div className="page-icon"><MessageSquare size={22} /></div>
        <h1>Ask RepoGuide</h1>
        <p className="text-secondary mt-2">Ask anything about this repository.</p>
      </header>

      {/* Suggested questions */}
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
              {msg.referencedFiles && msg.referencedFiles.length > 0 && (
                <div className="file-refs mt-3">
                  <p className="text-xs text-muted mb-1">Referenced files</p>
                  {msg.referencedFiles.map((f) => (
                    <span key={f} className="file-ref"><FileCode2 size={11} /> {f}</span>
                  ))}
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
