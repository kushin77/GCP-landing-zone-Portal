/**
 * FAANG-Grade Error Boundary Component
 *
 * Catches React errors and displays user-friendly error messages.
 * Logs errors for debugging and monitoring.
 */
import React, { Component, ReactNode, ErrorInfo } from 'react';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorId: string | null;
}

/**
 * Error Boundary component that catches JavaScript errors in child components.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Generate unique error ID for tracking
    const errorId = Math.random().toString(36).substring(2, 10);
    return {
      hasError: true,
      error,
      errorId,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console in development
    console.error('ErrorBoundary caught error:', {
      error,
      componentStack: errorInfo.componentStack,
      errorId: this.state.errorId,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);

    // In production, send to error tracking service
    if (import.meta.env.PROD) {
      this.reportError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    // Reset error state if resetKeys change
    if (this.state.hasError && this.props.resetKeys) {
      const hasKeyChanged = this.props.resetKeys.some(
        (key, index) => key !== prevProps.resetKeys?.[index]
      );
      if (hasKeyChanged) {
        this.reset();
      }
    }
  }

  private reportError(error: Error, errorInfo: ErrorInfo): void {
    // Send error to monitoring service (e.g., Sentry, Cloud Error Reporting)
    try {
      const errorReport = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        errorId: this.state.errorId,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
      };

      // Send to backend error endpoint
      fetch('/api/v1/errors/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorReport),
      }).catch(() => {
        // Silently fail - error reporting shouldn't break the app
      });
    } catch {
      // Ignore reporting errors
    }
  }

  reset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Return custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="max-w-md w-full bg-white rounded-xl shadow-lg border border-red-100 p-8">
            <div className="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-full bg-red-100">
              <ExclamationTriangleIcon className="w-8 h-8 text-red-600" />
            </div>

            <h2 className="text-xl font-semibold text-gray-900 text-center mb-2">
              Something went wrong
            </h2>

            <p className="text-gray-600 text-center mb-6">
              An unexpected error occurred. Our team has been notified.
            </p>

            {!import.meta.env.PROD && this.state.error && (
              <details className="mb-6 p-4 bg-gray-50 rounded-lg text-sm">
                <summary className="cursor-pointer text-gray-700 font-medium">
                  Error Details
                </summary>
                <pre className="mt-2 text-red-600 whitespace-pre-wrap overflow-auto max-h-40">
                  {this.state.error.message}
                  {'\n\n'}
                  {this.state.error.stack}
                </pre>
              </details>
            )}

            <div className="flex gap-3">
              <button
                onClick={this.reset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <ArrowPathIcon className="w-4 h-4" />
                Try Again
              </button>

              <button
                onClick={() => window.location.href = '/'}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Go Home
              </button>
            </div>

            {this.state.errorId && (
              <p className="mt-4 text-xs text-gray-400 text-center">
                Error ID: {this.state.errorId}
              </p>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Wrapper component for page-level error boundaries
 */
export function PageErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
              <ExclamationTriangleIcon className="w-10 h-10 text-red-600" />
            </div>

            <h1 className="text-2xl font-bold text-gray-900 mb-3">
              Page Error
            </h1>

            <p className="text-gray-600 mb-8">
              This page encountered an error. Please try refreshing or navigating to another page.
            </p>

            <div className="flex gap-4 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                Refresh Page
              </button>

              <button
                onClick={() => window.location.href = '/'}
                className="px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Hook for handling async errors in components
 */
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  if (error) {
    throw error;
  }

  return React.useCallback((error: Error) => {
    setError(error);
  }, []);
}

export default ErrorBoundary;
