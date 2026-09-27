import { Link, useLocation } from 'react-router-dom'
import { Zap, Sparkles, User } from 'lucide-react'
import { useState, useEffect } from 'react'
import { getProfile } from '../services/api'
import './Navbar.css'

export default function Navbar() {
  const { pathname } = useLocation()
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const token = localStorage.getItem('supabase_token')
    if (token) {
      getProfile().then(data => setUser(data.user)).catch(() => {
        localStorage.removeItem('supabase_token')
        setUser(null)
      })
    }
  }, [])

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
        <div className="flex items-center gap-3">
          {user ? (
            <Link to="/profile" className="btn btn-outline" style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
              <User size={14} /> Profile
            </Link>
          ) : (
            <Link to="/signin" className="btn btn-outline" style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
              Sign In
            </Link>
          )}
          <Link to="/" className="btn btn-primary nav-cta">
            <Sparkles size={14} />
            Analyze a Repo
          </Link>
        </div>
      </div>
    </nav>
  )
}
