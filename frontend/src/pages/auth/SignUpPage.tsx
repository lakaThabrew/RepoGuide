import { useState } from 'react'
import { Link } from 'react-router-dom'
import { signUp } from '../../services/api'
import Navbar from '../../components/Navbar'
import Footer from '../../components/Footer'
import { ArrowRight, UserPlus } from 'lucide-react'

export default function SignUpPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)


  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)
    
    try {
      await signUp({ email, password, full_name: fullName })
      setSuccess(true)
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
              Create Account
            </h1>
            <p className="text-secondary">Join RepoGuide today</p>
          </div>

          {error && (
            <div className="mb-4 p-3" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)', borderRadius: 'var(--radius-sm)', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          {success ? (
            <div className="text-center fade-in">
              <div className="mb-4 p-4" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)', borderRadius: 'var(--radius-md)' }}>
                Registration successful! Please check your email to verify your account.
              </div>
              <Link to="/signin" className="btn btn-outline mt-2 w-full" style={{ justifyContent: 'center' }}>
                Go to Sign In
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSignUp} className="flex flex-col gap-4">
              <div>
                <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Full Name</label>
                <input
                  type="text"
                  className="input"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>

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
                <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Password</label>
                <input
                  type="password"
                  className="input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>

              <button type="submit" className="btn btn-primary w-full mt-2" disabled={loading} style={{ justifyContent: 'center' }}>
                {loading ? <div className="spinner"></div> : <><UserPlus size={16} /> Sign Up</>}
              </button>
            </form>
          )}

          {!success && (
            <p className="text-center mt-6 text-sm text-secondary">
              Already have an account?{' '}
              <Link to="/signin" className="gradient-text font-bold">Sign in <ArrowRight size={12} style={{ display: 'inline', verticalAlign: 'middle' }} /></Link>
            </p>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
