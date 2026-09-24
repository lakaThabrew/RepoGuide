import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GitFork, Sparkles, ArrowRight, BookOpen, GitBranch, MessageSquare, Zap } from 'lucide-react'
import { createRepository } from '../services/api'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import './LandingPage.css'

const QUICK_FEATURES = [
  { icon: BookOpen, label: 'Project Overview' },
  { icon: GitBranch, label: 'Architecture Map' },
  { icon: MessageSquare, label: 'Repo Q&A' },
  { icon: Sparkles, label: 'First Contribution' },
]

export default function LandingPage() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const isValidGithubUrl = (u: string) =>
    /^https?:\/\/github\.com\/[^/]+\/[^/]+\/?$/.test(u.trim())

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!url.trim()) { setError('Please enter a GitHub repository URL.'); return }
    if (!isValidGithubUrl(url)) {
      setError('Please enter a valid GitHub URL (e.g. https://github.com/owner/repo)')
      return
    }
    setLoading(true)
    try {
      const repo = await createRepository(url.trim())
      navigate(`/repository/${repo.id}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to connect to the backend. Make sure it is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="landing bg-mesh">
      <Navbar />

      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="hero container">
        <div className="hero-badge fade-in-up">
          <Sparkles size={13} />
          <span>IBM Bob 2.0 Hackathon Project</span>
        </div>

        <h1 className="hero-title fade-in-up" style={{ animationDelay: '0.05s' }}>
          From unfamiliar codebase<br />
          to <span className="gradient-text">first contribution</span>
        </h1>

        <p className="hero-subtitle fade-in-up" style={{ animationDelay: '0.1s' }}>
          Drop a GitHub URL. RepoGuide analyses the repository, explains the architecture,
          answers your questions, and recommends your first contribution — all powered by AI.
        </p>

        {/* Input form */}
        <form
          className="hero-form fade-in-up card"
          style={{ animationDelay: '0.15s' }}
          onSubmit={handleSubmit}
        >
          <div className="form-row">
            <div className="input-wrapper">
              <GitFork size={18} className="input-icon" />
              <input
                id="github-url-input"
                className="input hero-input"
                type="url"
                placeholder="https://github.com/owner/repository"
                value={url}
                onChange={(e) => { setUrl(e.target.value); setError('') }}
                disabled={loading}
                autoFocus
              />
            </div>
            <button
              id="analyze-btn"
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
            >
              {loading
                ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Analyzing…</>
                : <>Analyze <ArrowRight size={16} /></>
              }
            </button>
          </div>
          {error && <p className="form-error">{error}</p>}
          <p className="form-hint">Public GitHub repositories only · Analysis takes ~30–90 s</p>
        </form>

        {/* Quick feature pills */}
        <div className="hero-pills fade-in-up" style={{ animationDelay: '0.2s' }}>
          {QUICK_FEATURES.map(({ icon: Icon, label }) => (
            <span key={label} className="hero-pill">
              <Icon size={14} />{label}
            </span>
          ))}
        </div>

        <p className="hero-learn fade-in-up" style={{ animationDelay: '0.25s' }}>
          Want to see everything RepoGuide can do?{' '}
          <Link to="/features" className="hero-learn-link">
            Explore all features <ArrowRight size={13} style={{ display: 'inline', verticalAlign: 'middle' }} />
          </Link>
        </p>
      </section>

      
      {/* ── How it works (mini) ───────────────────────────── */}
      <section className="how-mini container">
        <div className="how-mini-steps">
          {[
            { n: '01', t: 'Paste GitHub URL' },
            { n: '02', t: 'AI Scans & Analyses' },
            { n: '03', t: 'Explore Dashboard' },
            { n: '04', t: 'Make First Contribution' },
          ].map(({ n, t }, i) => (
            <React.Fragment key={n}>
              <div className="how-mini-step">
                <span className="how-mini-num">{n}</span>
                <span className="how-mini-label">{t}</span>
              </div>
              {i < 3 && <div className="how-mini-arrow"><ArrowRight size={20} /></div>}
            </React.Fragment>
          ))}
        </div>
      </section>

      <Footer />
    </div>
  )
}
