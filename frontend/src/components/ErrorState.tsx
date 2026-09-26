import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'

interface ErrorStateProps {
  /** Error message to display. */
  message: string
  /** Optional action button or other content below the message. */
  children?: ReactNode
  /** Optional extra className for the wrapper div. */
  className?: string
}

/**
 * Reusable full-area error indicator.
 *
 * Renders a centred error icon with a message and optional action slot.
 *
 * @example
 * <ErrorState message="Repository not found.">
 *   <button className="btn btn-outline mt-4" onClick={retry}>Retry</button>
 * </ErrorState>
 */
export default function ErrorState({ message, children, className = '' }: ErrorStateProps) {
  return (
    <div
      className={`error-state ${className}`.trim()}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1rem',
        minHeight: 200,
      }}
      role="alert"
    >
      <AlertCircle
        size={36}
        style={{ color: 'var(--error)', marginBottom: '0.75rem' }}
        aria-hidden="true"
      />
      <p className="text-sm" style={{ color: 'var(--error)', textAlign: 'center', maxWidth: 400 }}>
        {message}
      </p>
      {children}
    </div>
  )
}
