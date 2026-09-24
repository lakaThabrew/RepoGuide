import { Link, useLocation } from 'react-router-dom'
import { Zap, Sparkles } from 'lucide-react'
import './Navbar.css'

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <nav className="public-nav">
      <div className="public-nav-inner">
        {/* Logo */}
        <Link to="/" className="nav-logo">
          <div className="logo-icon"><Zap size={17} /></div>
          <span className="logo-text">RepoGuide</span>
        </Link>

        {/* Links */}
        <div className="nav-links">
          <Link
            to="/"
            className={`nav-link ${pathname === '/' ? 'active' : ''}`}
          >
            Home
          </Link>
          <Link
            to="/features"
            className={`nav-link ${pathname === '/features' ? 'active' : ''}`}
          >
            Features
          </Link>
        </div>

        {/* CTA */}
        <Link to="/" className="btn btn-primary nav-cta">
          <Sparkles size={14} />
          Analyze a Repo
        </Link>
      </div>
    </nav>
  )
}
