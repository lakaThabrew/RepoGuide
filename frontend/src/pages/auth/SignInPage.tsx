import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signIn } from '../../services/api'
import Navbar from '../../components/Navbar'
import Footer from '../../components/Footer'
import { ArrowRight, LogIn } from 'lucide-react'

export default function SignInPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const data = await signIn({ email, password })
      if (data.session) {
        localStorage.setItem('supabase_token', data.session.access_token)
        navigate('/profile')
      } else {
        throw new Error('No session returned')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="landing bg-mesh" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main className="container fade-in-up" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem 1.5rem' }}>
        <div className="card" style={{ maxWidth: '400px', width: '100%', padding: '2.5rem' }}>
          <div className="text-center mb-6">
            <h1 className="hero-title" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
              Welcome back
            </h1>
            <p className="text-secondary">Sign in to your account</p>
          </div>

          {error && (
            <div className="mb-4 p-3" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)', borderRadius: 'var(--radius-sm)', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSignIn} className="flex flex-col gap-4">
            <div>
              <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Email</label>
              <input
                type="email"
                className="input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-sm text-secondary">Password</label>
                <Link to="/forgot-password" className="text-xs text-muted" style={{ textDecoration: 'underline' }}>Forgot?</Link>
              </div>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary w-full mt-2" disabled={loading} style={{ justifyContent: 'center' }}>
              {loading ? <div className="spinner"></div> : <><LogIn size={16} /> Sign In</>}
            </button>
          </form>

          <p className="text-center mt-6 text-sm text-secondary">
            Don't have an account?{' '}
            <Link to="/signup" className="gradient-text font-bold">Sign up <ArrowRight size={12} style={{ display: 'inline', verticalAlign: 'middle' }} /></Link>
          </p>
        </div>
      </main>

      <Footer />
    </div>
  )
}
