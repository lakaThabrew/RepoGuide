import { useState } from 'react'
import { Link } from 'react-router-dom'
import { resetPassword } from '../../services/api'
import Navbar from '../../components/Navbar'
import Footer from '../../components/Footer'
import { Mail, ArrowLeft } from 'lucide-react'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)
    
    try {
      await resetPassword({ email })
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
            <h1 className="hero-title" style={{ fontSize: '1.75rem', marginBottom: '0.5rem' }}>
              Reset Password
            </h1>
            <p className="text-secondary">We'll send you reset instructions</p>
          </div>

          {error && (
            <div className="mb-4 p-3" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--error)', borderRadius: 'var(--radius-sm)', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          {success ? (
            <div className="text-center fade-in">
              <div className="mb-4 p-4" style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--success)', borderRadius: 'var(--radius-md)' }}>
                Instructions have been sent to your email!
              </div>
              <Link to="/signin" className="btn btn-outline mt-2 w-full" style={{ justifyContent: 'center' }}>
                Return to Sign In
              </Link>
            </div>
          ) : (
            <form onSubmit={handleReset} className="flex flex-col gap-4">
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

              <button type="submit" className="btn btn-primary w-full mt-2" disabled={loading} style={{ justifyContent: 'center' }}>
                {loading ? <div className="spinner"></div> : <><Mail size={16} /> Send Instructions</>}
              </button>
            </form>
          )}

          {!success && (
            <p className="text-center mt-6 text-sm text-secondary">
              <Link to="/signin" className="text-muted" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <ArrowLeft size={12} /> Back to Sign In
              </Link>
            </p>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
