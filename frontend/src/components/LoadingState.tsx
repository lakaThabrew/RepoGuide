import type { ReactNode } from 'react'

interface LoadingStateProps {
  /** Optional message shown below the spinner. Defaults to 'Loading…' */
  message?: string
  /** Optional size for the spinner in pixels. Defaults to 32. */
  spinnerSize?: number
  /** Optional extra className for the wrapper div. */
  className?: string
  /** Optional children rendered below the message. */
  children?: ReactNode
}

/**
 * Reusable full-area loading indicator.
 *
 * Renders a centred spinner with an optional message.
 * Designed to fill the available container space via flex layout.
 *
 * @example
 * <LoadingState message="Loading repository files…" />
 */
export default function LoadingState({
  message = 'Loading…',
  spinnerSize = 32,
  className = '',
  children,
}: LoadingStateProps) {
  return (
    <div
      className={`loading-state ${className}`.trim()}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 1rem',
        minHeight: 200,
      }}
    >
      <div
        className="spinner"
        style={{ width: spinnerSize, height: spinnerSize }}
        role="status"
        aria-label={message}
      />
      {message && (
        <p className="text-secondary mt-4" style={{ fontSize: '0.9rem' }}>
          {message}
        </p>
      )}
      {children}
    </div>
  )
}
