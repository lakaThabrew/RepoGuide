import { useEffect, useState } from 'react'
import { useParams, Outlet, useNavigate } from 'react-router-dom'
import { getRepository } from '../services/api'
import type { Repository } from '../services/api'
import Sidebar from '../components/Sidebar'
import './RepositoryLayout.css'


export default function RepositoryLayout() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [repo, setRepo] = useState<Repository | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    getRepository(id)
      .then(setRepo)
      .catch(() => setError('Repository not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="repo-loading bg-mesh">
        <div className="spinner" style={{ width: 36, height: 36 }} />
        <p className="text-secondary mt-4">Loading repository…</p>
      </div>
    )
  }

  if (error || !repo) {
    return (
      <div className="repo-loading bg-mesh">
        <p className="text-sm" style={{ color: 'var(--error)' }}>{error || 'Repository not found'}</p>
        <button className="btn btn-outline mt-4" onClick={() => navigate('/')}>← Back to Home</button>
      </div>
    )
  }

  return (
    <div className="repo-layout">
      {/* Sidebar */}
      <Sidebar repo={repo} />

      {/* Main content */}
      <main className="repo-main">
        <Outlet context={{ repo }} />
      </main>
    </div>
  )
}
