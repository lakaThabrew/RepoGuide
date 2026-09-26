/**
 * Utility functions for the RepoGuide frontend.
 */

// ---------------------------------------------------------------------------
// File size formatting
// ---------------------------------------------------------------------------

/**
 * Format a byte count as a human-readable string.
 *
 * @example
 * formatSize(0)        // '0 B'
 * formatSize(512)      // '512 B'
 * formatSize(2048)     // '2.0 KB'
 * formatSize(1500000)  // '1.4 MB'
 */
export function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ---------------------------------------------------------------------------
// Repository URL helpers
// ---------------------------------------------------------------------------

/**
 * Extract the owner/repo display name from a GitHub URL.
 *
 * @example
 * repoDisplayName('https://github.com/owner/repo') // 'owner/repo'
 * repoDisplayName('https://github.com/owner/repo.git') // 'owner/repo'
 */
export function repoDisplayName(githubUrl: string): string {
  try {
    const url = new URL(githubUrl)
    return url.pathname.replace(/^\//, '').replace(/\.git$/, '')
  } catch {
    return githubUrl
  }
}

// ---------------------------------------------------------------------------
// File path helpers
// ---------------------------------------------------------------------------

/**
 * Return the filename component of a file path.
 *
 * @example
 * fileName('src/services/userService.ts') // 'userService.ts'
 */
export function fileName(filePath: string): string {
  return filePath.split('/').pop() ?? filePath
}

/**
 * Return the file extension from a file path (including the leading dot).
 *
 * @example
 * fileExtension('src/main.ts') // '.ts'
 */
export function fileExtension(filePath: string): string {
  const name = fileName(filePath)
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(dot) : ''
}
