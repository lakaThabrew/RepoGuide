import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProfile, updateProfile as updateProfileApi } from '../../services/api'
import Navbar from '../../components/Navbar'
import Footer from '../../components/Footer'
import { User, LogOut, Save } from 'lucide-react'

export default function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [profile, setProfile] = useState<{ full_name: string; username: string }>({ full_name: '', username: '' })
  const [message, setMessage] = useState({ text: '', type: '' })
  const navigate = useNavigate()

  useEffect(() => {
    fetchProfile()
  }, [])

  async function fetchProfile() {
    try {
      setLoading(true)
      
      const token = localStorage.getItem('supabase_token')
      if (!token) {
        navigate('/signin')
        return
      }

      const data = await getProfile()
      
      setUser(data.user)
      if (data.profile) {
        setProfile({
          full_name: data.profile.full_name || '',
          username: data.profile.username || '',
        })
      }
    } catch (error: any) {
      console.error('Error loading user data!', error)
      navigate('/signin')
    } finally {
      setLoading(false)
    }
  }

  async function updateProfile(e: React.FormEvent) {
    e.preventDefault()
    try {
      setSaving(true)
      setMessage({ text: '', type: '' })

      await updateProfileApi({
        full_name: profile.full_name,
        username: profile.username,
      })

      setMessage({ text: 'Profile updated successfully!', type: 'success' })
    } catch (error: any) {
      setMessage({ text: error.response?.data?.detail || error.message, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleSignOut() {
    localStorage.removeItem('supabase_token')
    navigate('/')
  }

  return (
    <div className="landing bg-mesh" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main className="container fade-in-up" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem 1.5rem' }}>
        <div className="card" style={{ maxWidth: '500px', width: '100%', padding: '2.5rem' }}>
          
          <div className="flex justify-between items-center mb-6 border-b" style={{ paddingBottom: '1.5rem', borderColor: 'var(--border)' }}>
            <div>
              <h1 className="hero-title" style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                Your Profile
              </h1>
              <p className="text-secondary">Manage your account settings</p>
            </div>
            <div className="badge badge-accent">
              <User size={14} /> Active
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-8"><div className="spinner"></div></div>
          ) : (
            <>
              {message.text && (
                <div className="mb-6 p-3 text-center" style={{ 
                  background: message.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)', 
                  color: message.type === 'error' ? 'var(--error)' : 'var(--success)', 
                  borderRadius: 'var(--radius-sm)', 
                  fontSize: '0.9rem' 
                }}>
                  {message.text}
                </div>
              )}

              <form onSubmit={updateProfile} className="flex flex-col gap-5">
                <div>
                  <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Email</label>
                  <input
                    type="email"
                    className="input"
                    value={user?.email || ''}
                    disabled
                    style={{ opacity: 0.7, cursor: 'not-allowed' }}
                  />
                  <p className="text-xs text-muted mt-1">Your email address cannot be changed here.</p>
                </div>

                <div>
                  <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Full Name</label>
                  <input
                    type="text"
                    className="input"
                    value={profile.full_name}
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  />
                </div>
                
                <div>
                  <label className="text-sm text-secondary mb-1" style={{ display: 'block' }}>Username</label>
                  <input
                    type="text"
                    className="input"
                    value={profile.username}
                    onChange={(e) => setProfile({ ...profile, username: e.target.value })}
                  />
                </div>

                <div className="flex gap-4 mt-4">
                  <button type="submit" className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }} disabled={saving}>
                    {saving ? <div className="spinner"></div> : <><Save size={16} /> Save Changes</>}
                  </button>
                  <button type="button" className="btn btn-outline" onClick={handleSignOut} style={{ flex: 1, justifyContent: 'center', borderColor: 'rgba(239,68,68,0.3)', color: 'var(--error)' }}>
                    <LogOut size={16} /> Sign Out
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
