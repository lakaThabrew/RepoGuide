import { Fragment, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, BookOpen, GitBranch, MessageSquare } from 'lucide-react'
import { createRepository } from '../services/api'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import RepositoryInput from '../components/RepositoryInput'
import './LandingPage.css'

const QUICK_FEATURES = [
  { icon: BookOpen, label: 'Project Overview' },
  { icon: GitBranch, label: 'Architecture Map' },
  { icon: MessageSquare, label: 'Repo Q&A' },
  { icon: Sparkles, label: 'First Contribution' },
]

export default function LandingPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const isValidGithubUrl = (u: string) =>
    /^https?:\/\/github\.com\/[^/]+\/[^/]+\/?$/.test(u.trim())

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
        <RepositoryInput 
          onSubmit={(u) => {
            if (!u.trim()) { setError('Please enter a GitHub repository URL.'); return }
            if (!isValidGithubUrl(u)) {
              setError('Please enter a valid GitHub URL (e.g. https://github.com/owner/repo)')
              return
            }
            setLoading(true)
            createRepository(u.trim())
              .then(repo => navigate(`/repository/${repo.id}`))
              .catch((err: any) => setError(err?.response?.data?.detail || 'Failed to connect to the backend. Make sure it is running.'))
              .finally(() => setLoading(false))
          }}
          loading={loading}
          error={error}
          setError={setError}
        />

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
            <Fragment key={n}>
              <div className="how-mini-step">
                <span className="how-mini-num">{n}</span>
                <span className="how-mini-label">{t}</span>
              </div>
              {i < 3 && <div className="how-mini-arrow"><ArrowRight size={20} /></div>}
            </Fragment>
          ))}
        </div>
      </section>

      <Footer />
    </div>
  )
}
