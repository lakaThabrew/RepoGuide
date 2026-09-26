import { useState, useEffect, useMemo, useCallback } from 'react'
import { useOutletContext, useNavigate, useSearchParams } from 'react-router-dom'
import { FolderOpen, FileCode2, FileText, AlertCircle, Info } from 'lucide-react'
import { listRepositoryFiles, getFileContent } from '../services/api'
import type { Repository, RepositoryFileItem, FileContentResponse } from '../services/api'
import { buildTree, TreeNodeItem } from '../components/FileTree'
import './FilesPage.css'

interface Ctx { repo: Repository }



// ---------------------------------------------------------------------------
// File size formatter
// ---------------------------------------------------------------------------

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ---------------------------------------------------------------------------
// Code viewer
// ---------------------------------------------------------------------------

function CodeViewer({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <div className="files-code-wrap">
      <table className="files-code-table" aria-label="File contents">
        <tbody>
          {lines.map((line, i) => (
            <tr key={i}>
              <td className="files-line-num" aria-hidden="true">{i + 1}</td>
              <td className="files-line-code">{line || ' '}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Content panel states
// ---------------------------------------------------------------------------

function ContentPanel({
  selectedFile,
  content,
  loading,
  error,
}: {
  selectedFile: RepositoryFileItem | null
  content: FileContentResponse | null
  loading: boolean
  error: string
}) {
  if (!selectedFile) {
    return (
      <div className="files-content-empty">
        <FileText size={40} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
        <p className="text-secondary text-sm">Select a file from the tree to view its contents.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="files-content-empty">
        <div className="spinner" style={{ width: 28, height: 28 }} />
        <p className="text-secondary text-sm mt-4">Loading file…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="files-content-empty">
        <AlertCircle size={32} style={{ color: 'var(--error)', marginBottom: '0.75rem' }} />
        <p className="text-sm" style={{ color: 'var(--error)' }}>{error}</p>
      </div>
    )
  }

  if (!content) return null

  // Non-previewable states
  if (content.is_binary) {
    return (
      <div className="files-content-empty">
        <Info size={32} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
        <p className="text-secondary text-sm">This file cannot be previewed (binary or unsupported type).</p>
      </div>
    )
  }

  if (content.error === 'File too large to preview.') {
    return (
      <div className="files-content-empty">
        <Info size={32} style={{ color: 'var(--warning)', marginBottom: '0.75rem' }} />
        <p className="text-sm" style={{ color: 'var(--warning)' }}>
          This file is too large to preview ({formatSize(content.file_size)}).
        </p>
      </div>
    )
  }

  if (content.error) {
    return (
      <div className="files-content-empty">
        <AlertCircle size={32} style={{ color: 'var(--error)', marginBottom: '0.75rem' }} />
        <p className="text-sm" style={{ color: 'var(--error)' }}>{content.error}</p>
      </div>
    )
  }

  if (content.content === undefined || content.content === null) {
    return (
      <div className="files-content-empty">
        <Info size={32} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
        <p className="text-secondary text-sm">No content available.</p>
      </div>
    )
  }

  return (
    <div className="files-content-body">
      {/* File header bar */}
      <div className="files-content-header">
        <div className="files-content-meta">
          <span className="files-content-path">{content.path}</span>
          <div className="files-content-badges">
            {content.language && (
              <span className="badge badge-accent" style={{ fontSize: '0.68rem' }}>{content.language}</span>
            )}
            {content.extension && !content.language && (
              <span className="badge badge-muted" style={{ fontSize: '0.68rem' }}>{content.extension}</span>
            )}
            <span className="badge badge-muted" style={{ fontSize: '0.68rem' }}>{formatSize(content.file_size)}</span>
            {content.truncated && (
              <span className="badge badge-warning" style={{ fontSize: '0.68rem' }}>Preview truncated</span>
            )}
          </div>
        </div>
      </div>
      {/* Code viewer — content escaped as text, never evaluated */}
      <CodeViewer content={content.content} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// FilesPage — main export
// ---------------------------------------------------------------------------

type LoadState = 'loading' | 'empty' | 'ready' | 'error'

export default function FilesPage() {
  const { repo } = useOutletContext<Ctx>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [files, setFiles] = useState<RepositoryFileItem[]>([])
  const [treeError, setTreeError] = useState('')

  const [selectedFile, setSelectedFile] = useState<RepositoryFileItem | null>(null)
  const [content, setContent] = useState<FileContentResponse | null>(null)
  const [contentLoading, setContentLoading] = useState(false)
  const [contentError, setContentError] = useState('')

  // Load file tree on mount
  useEffect(() => {
    setLoadState('loading')
    listRepositoryFiles(repo.id)
      .then((tree) => {
        setFiles(tree.files)
        setLoadState(tree.files.length === 0 ? 'empty' : 'ready')
      })
      .catch(() => {
        setTreeError('Could not load repository files. Is the backend running?')
        setLoadState('error')
      })
  }, [repo.id])

  // Load file specified via ?path= query param (deep-link support)
  useEffect(() => {
    const pathParam = searchParams.get('path')
    if (!pathParam || files.length === 0) return
    const match = files.find((f) => f.path === pathParam)
    if (match) {
      handleSelectFile(match)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, searchParams])

  const tree = useMemo(() => buildTree(files), [files])

  const handleSelectFile = useCallback(
    (file: RepositoryFileItem) => {
      setSelectedFile(file)
      setContent(null)
      setContentError('')
      setContentLoading(true)
      setSearchParams({ path: file.path }, { replace: true })

      getFileContent(repo.id, file.path)
        .then((resp) => {
          setContent(resp)
        })
        .catch(() => {
          setContentError('Could not load file contents. Please try again.')
        })
        .finally(() => setContentLoading(false))
    },
    [repo.id, setSearchParams]
  )

  // Loading state
  if (loadState === 'loading') {
    return (
      <div className="files-page fade-in-up">
        <div className="files-page-loading">
          <div className="spinner" style={{ width: 32, height: 32 }} />
          <p className="text-secondary mt-4">Loading repository files…</p>
        </div>
      </div>
    )
  }

  // Error state
  if (loadState === 'error') {
    return (
      <div className="files-page fade-in-up">
        <div className="files-page-loading">
          <AlertCircle size={36} style={{ color: 'var(--error)', marginBottom: '0.75rem' }} />
          <p className="text-sm" style={{ color: 'var(--error)' }}>{treeError}</p>
          <button className="btn btn-outline mt-4" onClick={() => navigate(0)}>Retry</button>
        </div>
      </div>
    )
  }

  // Empty state
  if (loadState === 'empty') {
    return (
      <div className="files-page fade-in-up">
        <div className="files-page-loading">
          <FolderOpen size={40} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
          <p className="text-secondary text-sm">No readable source files were found.</p>
          <p className="text-xs text-muted mt-2">
            Run repository ingestion first, or this repository may contain only unsupported file types.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="files-page fade-in-up">
      {/* Header */}
      <div className="files-page-header">
        <div className="page-icon"><FileCode2 size={22} /></div>
        <div>
          <h1 style={{ fontSize: '1.4rem' }}>Repository Files</h1>
          <p className="text-secondary text-sm mt-1">
            {files.length} readable source {files.length === 1 ? 'file' : 'files'} — read-only
          </p>
        </div>
      </div>

      {/* Explorer split-pane */}
      <div className="files-explorer">
        {/* Left: file tree */}
        <aside className="files-tree-panel" aria-label="Repository file tree">
          <div className="files-tree-header">
            <span className="text-xs text-muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Files
            </span>
            <span className="badge badge-muted" style={{ fontSize: '0.65rem' }}>{files.length}</span>
          </div>
          <div className="files-tree-scroll">
            {tree.children.map((child) => (
              <TreeNodeItem
                key={child.path}
                node={child}
                depth={0}
                selectedPath={selectedFile?.path ?? null}
                onSelect={handleSelectFile}
                defaultOpen={true}
              />
            ))}
          </div>
        </aside>

        {/* Right: content viewer */}
        <section className="files-content-panel" aria-label="File contents">
          <ContentPanel
            selectedFile={selectedFile}
            content={content}
            loading={contentLoading}
            error={contentError}
          />
        </section>
      </div>
    </div>
  )
}
