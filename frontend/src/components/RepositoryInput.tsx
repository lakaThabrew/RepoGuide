import React, { useState } from 'react'
import { GitFork, ArrowRight } from 'lucide-react'

interface RepositoryInputProps {
  onSubmit: (url: string) => void;
  loading: boolean;
  error?: string;
  setError: (err: string) => void;
}

export default function RepositoryInput({ onSubmit, loading, error, setError }: RepositoryInputProps) {
  const [url, setUrl] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(url)
  }

  return (
    <form
      className="hero-form fade-in-up card"
      style={{ animationDelay: '0.15s' }}
      onSubmit={handleSubmit}
    >
      <div className="form-row">
        <div className="input-wrapper">
          <GitFork size={18} className="input-icon" />
          <input
            id="github-url-input"
            className="input hero-input"
            type="url"
            placeholder="https://github.com/owner/repository"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setError('') }}
            disabled={loading}
            autoFocus
          />
        </div>
        <button
          id="analyze-btn"
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={loading}
        >
          {loading
            ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Analyzing…</>
            : <>Analyze <ArrowRight size={16} /></>
          }
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
      <p className="form-hint">Public GitHub repositories only · Analysis takes ~30–90 s</p>
    </form>
  )
}
