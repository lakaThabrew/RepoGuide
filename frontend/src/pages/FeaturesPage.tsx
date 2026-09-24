import { Link } from 'react-router-dom'
import {
  BookOpen, GitBranch, MessageSquare, Sparkles,
  FileCode2, Terminal, Zap, ArrowRight, CheckCircle,
} from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import './FeaturesPage.css'

const FEATURES = [
  {
    icon: BookOpen,
    title: 'Project Overview',
    color: '#6c63ff',
    desc: 'Get an instant, AI-generated summary of the repository — its purpose, primary language, key technologies, and entry points. No more manually reading thousands of lines.',
    bullets: [
      'AI-generated project summary',
      'Technology stack detection',
      'Primary language & dependencies',
      'README & documentation analysis',
    ],
  },
  {
    icon: GitBranch,
    title: 'Architecture Map',
    color: '#00d8c4',
    desc: 'Understand how the pieces fit together. RepoGuide maps out the component relationships, data flow, and module boundaries so you can navigate with confidence.',
    bullets: [
      'Component relationship diagram',
      'Data flow explanation',
      'Entry point identification',
      'Important module breakdown',
    ],
  },
  {
    icon: FileCode2,
    title: 'Important Files',
    color: '#f59e0b',
    desc: 'Not every file is equally important. RepoGuide identifies the most critical files and explains what they do — so you focus on what matters first.',
    bullets: [
      'Key files identified and ranked',
      'Purpose explained for each file',
      'Links to relevant modules',
      'Config and setup files highlighted',
    ],
  },
  {
    icon: Terminal,
    title: 'Setup Guide',
    color: '#22c55e',
    desc: 'Get a step-by-step setup guide generated directly from the repository — prerequisites, installation, environment variables, and common problems, all tailored to the actual codebase.',
    bullets: [
      'Prerequisites & installation steps',
      'Environment variable explanations',
      'Database setup instructions',
      'Common errors & troubleshooting',
    ],
  },
  {
    icon: MessageSquare,
    title: 'Repository Q&A',
    color: '#8b5cf6',
    desc: 'Ask anything about the codebase in plain English. RepoGuide retrieves the relevant source files and gives you a grounded, repository-specific answer with file references.',
    bullets: [
      'Natural language questions',
      'Grounded, file-specific answers',
      'Exact file references included',
      'Context-aware follow-up support',
    ],
  },
  {
    icon: Sparkles,
    title: 'First Contribution',
    color: '#ec4899',
    desc: 'The most unique feature. RepoGuide analyses TODO comments, open issues, documentation gaps, and code complexity to recommend your first contribution — with full implementation steps.',
    bullets: [
      'Beginner-friendly task selection',
      'Relevant files identified',
      'Step-by-step implementation plan',
      'Tests to write included',
    ],
  },
]

const HOW_IT_WORKS = [
  { step: '01', title: 'Paste GitHub URL', desc: 'Drop any public GitHub repository URL into the input.' },
  { step: '02', title: 'AI Analyses the Repo', desc: 'RepoGuide scans the files, reads key documents, and runs AI analysis.' },
  { step: '03', title: 'Explore the Dashboard', desc: 'Navigate through overview, architecture, setup guide, and Q&A.' },
  { step: '04', title: 'Make Your First Contribution', desc: 'Get an AI-recommended task with step-by-step guidance.' },
]

export default function FeaturesPage() {
  return (
    <div className="features-page bg-mesh">
      <Navbar />

      {/* Hero */}
      <section className="fp-hero container">
        <div className="hero-badge fade-in-up">
          <Zap size={13} />
          <span>What RepoGuide can do</span>
        </div>
        <h1 className="fade-in-up" style={{ animationDelay: '0.05s' }}>
          Every feature you need to<br />
          <span className="gradient-text">onboard faster</span>
        </h1>
        <p className="fp-hero-sub fade-in-up" style={{ animationDelay: '0.1s' }}>
          RepoGuide uses IBM Bob 2.0 to transform an unfamiliar codebase into a clear, actionable onboarding experience.
        </p>
        <Link to="/" className="btn btn-primary btn-lg fade-in-up" style={{ animationDelay: '0.15s' }}>
          Try it now <ArrowRight size={16} />
        </Link>
      </section>

      {/* Features Grid */}
      <section className="fp-features container">
        <div className="fp-features-grid">
          {FEATURES.map(({ icon: Icon, title, color, desc, bullets }) => (
            <div key={title} className="fp-feature-card card">
              <div className="fp-feature-icon" style={{ background: `${color}18`, color }}>
                <Icon size={22} />
              </div>
              <h3 className="fp-feature-title">{title}</h3>
              <p className="text-secondary text-sm mt-2">{desc}</p>
              <ul className="fp-bullets">
                {bullets.map((b) => (
                  <li key={b}>
                    <CheckCircle size={13} style={{ color: 'var(--success)', flexShrink: 0 }} />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="fp-how container">
        <h2 className="text-center mb-4" style={{ color: 'var(--text-primary)' }}>
          How it works
        </h2>
        <div className="fp-steps">
          {HOW_IT_WORKS.map(({ step, title, desc }) => (
            <div key={step} className="fp-step">
              <div className="fp-step-num">{step}</div>
              <div>
                <h3 className="fp-step-title">{title}</h3>
                <p className="text-secondary mt-1" style={{ fontSize: '0.9rem' }}>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="fp-cta container">
        <div className="fp-cta-card card">
          <Sparkles size={28} style={{ color: 'var(--accent-light)', marginBottom: '1rem' }} />
          <h2 style={{ color: 'var(--text-primary)' }}>Ready to explore a repository?</h2>
          <p className="text-secondary mt-2">
            Paste any GitHub URL and RepoGuide will handle the rest.
          </p>
          <Link to="/" className="btn btn-primary btn-lg mt-6">
            Analyze a Repository <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}
