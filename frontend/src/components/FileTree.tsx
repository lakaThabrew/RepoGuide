import { useState } from 'react'
import { FolderOpen, Folder, FileCode2, ChevronRight, ChevronDown } from 'lucide-react'
import type { RepositoryFileItem } from '../services/api'

export interface TreeNode {
  name: string
  path: string
  isDir: boolean
  children: TreeNode[]
  file?: RepositoryFileItem
}

export function buildTree(files: RepositoryFileItem[]): TreeNode {
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

interface TreeNodeProps {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (file: RepositoryFileItem) => void
  defaultOpen?: boolean
}

export function TreeNodeItem({ node, depth, selectedPath, onSelect, defaultOpen = false }: TreeNodeProps) {
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
