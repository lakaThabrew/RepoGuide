import { useState, useEffect, useMemo, useCallback } from 'react'
import { useOutletContext, useNavigate, useSearchParams } from 'react-router-dom'
import { FolderOpen, Folder, FileCode2, FileText, AlertCircle, Info, ChevronRight, ChevronDown } from 'lucide-react'
import { listRepositoryFiles, getFileContent } from '../services/api'
import type { Repository, RepositoryFileItem, FileContentResponse } from '../services/api'
import './FilesPage.css'

interface Ctx { repo: Repository }

// ---------------------------------------------------------------------------
// File tree node
// ---------------------------------------------------------------------------

interface TreeNode {
  name: string
  path: string         // empty string for virtual root
  isDir: boolean
  children: TreeNode[]
  file?: RepositoryFileItem
}

function buildTree(files: RepositoryFileItem[]): TreeNode {
  const root: TreeNode = { name: '', path: '', isDir: true, children: [] }

  for (const f of files) {
    const parts = f.path.split('/')
    let node = root
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isLast = i === parts.length - 1
      let child = node.children.find((c) => c.name === part)
      if (!child) {
        child = {
          name: part,
          path: parts.slice(0, i + 1).join('/'),
          isDir: !isLast,
          children: [],
          file: isLast ? f : undefined,
        }
        node.children.push(child)
      } else if (isLast) {
        child.file = f
        child.isDir = false
      }
      node = child
    }
  }

  // Sort: directories first, then alphabetical
  const sort = (n: TreeNode) => {
    n.children.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    n.children.forEach(sort)
  }
  sort(root)
  return root
}

// ---------------------------------------------------------------------------
// Category badge
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  entry_point: 'var(--teal)',
  configuration: 'var(--warning)',
  service: 'var(--accent-light)',
  api: 'var(--accent-light)',
  test: '#22c55e',
  documentation: 'var(--text-muted)',
}

function CategoryBadge({ category }: { category?: string }) {
  if (!category) return null
  const color = CATEGORY_COLORS[category] || 'var(--text-muted)'
  return (
    <span
      className="files-category-badge"
      style={{ color, borderColor: color + '44', background: color + '12' }}
    >
      {category.replace(/_/g, ' ')}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Language / extension icon colour
// ---------------------------------------------------------------------------

const LANG_COLORS: Record<string, string> = {
  Python: '#3b7cc8',
  TypeScript: '#3178c6',
  JavaScript: '#f1e05a',
  'CSS/SCSS': '#e44b9f',
  CSS: '#e44b9f',
  HTML: '#e34c26',
  Markdown: '#9ba3b5',
  JSON: '#f1a42b',
  YAML: '#cb171e',
  Shell: '#89e051',
  Go: '#00add8',
  Rust: '#dea584',
  Java: '#b07219',
  'C#': '#178600',
  Ruby: '#701516',
  PHP: '#4F5D95',
  SQL: '#f29111',
  Terraform: '#7b42bc',
}

function fileIconColor(language?: string): string {
  return language ? (LANG_COLORS[language] || 'var(--text-muted)') : 'var(--text-muted)'
}

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
// Tree node component
// ---------------------------------------------------------------------------

interface TreeNodeProps {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (file: RepositoryFileItem) => void
  defaultOpen?: boolean
}

function TreeNodeItem({ node, depth, selectedPath, onSelect, defaultOpen = false }: TreeNodeProps) {
  const [open, setOpen] = useState(defaultOpen || depth < 2)

  if (node.isDir) {
    return (
      <div>
        <button
          className="files-tree-row files-tree-dir"
          style={{ paddingLeft: `${depth * 14 + 8}px` }}
          onClick={() => setOpen(!open)}
          aria-expanded={open}
        >
          {open
            ? <ChevronDown size={12} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />
            : <ChevronRight size={12} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />
          }
          {open
            ? <FolderOpen size={14} style={{ flexShrink: 0, color: 'var(--warning)' }} />
            : <Folder size={14} style={{ flexShrink: 0, color: 'var(--warning)' }} />
          }
          <span className="files-tree-name">{node.name || '/'}</span>
        </button>
        {open && node.children.map((child) => (
          <TreeNodeItem
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </div>
    )
  }

  const isSelected = node.path === selectedPath
  const lang = node.file?.language
  return (
    <button
      className={`files-tree-row files-tree-file ${isSelected ? 'selected' : ''}`}
      style={{ paddingLeft: `${depth * 14 + 8}px` }}
      onClick={() => node.file && onSelect(node.file)}
    >
      <FileCode2 size={13} style={{ flexShrink: 0, color: fileIconColor(lang) }} />
      <span className="files-tree-name">{node.name}</span>
      {node.file?.category && (
        <CategoryBadge category={node.file.category} />
      )}
    </button>
  )
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
