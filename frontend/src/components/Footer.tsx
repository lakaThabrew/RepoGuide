import { Link } from 'react-router-dom'
import { Zap, GitFork, Heart } from 'lucide-react'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="public-footer">
      <div className="footer-inner">
        {/* Brand */}
        <div className="footer-brand">
          <Link to="/" className="nav-logo" style={{ marginBottom: '0.75rem', display: 'inline-flex' }}>
            <div className="logo-icon"><Zap size={16} /></div>
            <span className="logo-text">RepoGuide</span>
          </Link>
          <p className="footer-tagline">
            From unfamiliar codebase to first contribution.
          </p>
        </div>

        {/* Links */}
        <div className="footer-links-group">
          <p className="footer-group-title">Product</p>
          <Link to="/" className="footer-link">Home</Link>
          <Link to="/features" className="footer-link">Features</Link>
        </div>

        <div className="footer-links-group">
          <p className="footer-group-title">Hackathon</p>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="footer-link"
          >
            <GitFork size={13} /> GitHub
          </a>
          <span className="footer-link muted">IBM Bob 2.0</span>
        </div>
      </div>

      <div className="footer-bottom">
        <p>
          Built with <Heart size={12} className="heart-icon" /> for IBM Bob 2.0 Hackathon · September 2026
        </p>
      </div>
    </footer>
  )
}
