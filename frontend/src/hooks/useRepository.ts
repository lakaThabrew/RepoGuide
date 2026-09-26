import { useState, useEffect } from 'react'
import { getRepository } from '../services/api'
import type { Repository } from '../services/api'

interface UseRepositoryResult {
  repo: Repository | null
  loading: boolean
  error: string
}

/**
 * Load repository metadata by ID.
 *
 * Returns loading/error states and the repository object once resolved.
 * Re-fetches whenever `id` changes.
 *
 * @example
 * const { repo, loading, error } = useRepository(id)
 */
export function useRepository(id: string | undefined): UseRepositoryResult {
  const [repo, setRepo] = useState<Repository | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    getRepository(id)
      .then((r) => setRepo(r))
      .catch(() => setError('Repository not found'))
      .finally(() => setLoading(false))
  }, [id])

  return { repo, loading, error }
}
