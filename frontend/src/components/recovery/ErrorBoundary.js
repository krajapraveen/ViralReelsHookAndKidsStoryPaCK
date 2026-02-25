import React, { Component } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * ErrorFallback - Global error boundary with recovery options
 * Catches unhandled errors and provides user-friendly recovery UI
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    
    // Log error for monitoring
    console.error('ErrorBoundary caught:', error, errorInfo);
    
    // Send to backend monitoring (optional)
    this.logErrorToServer(error, errorInfo);
  }

  logErrorToServer = async (error, errorInfo) => {
    try {
      const API = process.env.REACT_APP_BACKEND_URL || '';
      const token = localStorage.getItem('token');
      
      if (!token) return;
      
      await fetch(`${API}/api/monitoring/client-error`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          error: error.message,
          stack: error.stack,
          componentStack: errorInfo?.componentStack,
          url: window.location.href,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {}); // Silent fail
    } catch (e) {
      // Ignore logging errors
    }
  };

  handleRetry = () => {
    this.setState(prev => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prev.retryCount + 1
    }));
  };

  handleGoHome = () => {
    window.location.href = '/app';
  };

  handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const { error, retryCount } = this.state;
      
      return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4" data-testid="error-boundary">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
              <AlertTriangle className="h-8 w-8 text-red-500" />
            </div>
            
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              Something went wrong
            </h1>
            
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {retryCount < 3 
                ? "Don't worry, this is usually temporary. Try refreshing the page."
                : "This issue persists. Please try again later or contact support."
              }
            </p>
            
            {/* Error details (collapsed by default) */}
            {process.env.NODE_ENV === 'development' && error && (
              <details className="mb-4 text-left bg-gray-50 dark:bg-gray-900 p-3 rounded text-xs">
                <summary className="cursor-pointer text-gray-500">Technical details</summary>
                <pre className="mt-2 overflow-auto text-red-600 dark:text-red-400">
                  {error.toString()}
                </pre>
              </details>
            )}
            
            {/* Recovery Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {retryCount < 3 && (
                <Button onClick={this.handleRetry} variant="default">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
              )}
              
              <Button onClick={this.handleRefresh} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh Page
              </Button>
              
              <Button onClick={this.handleGoHome} variant="outline">
                <Home className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Button>
            </div>
            
            {/* Support Info */}
            <p className="mt-6 text-xs text-gray-500">
              If this keeps happening, please contact{' '}
              <a href="mailto:support@creatorstudio.ai" className="text-indigo-500 hover:underline">
                support@creatorstudio.ai
              </a>
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * ErrorFallbackPage - Standalone error page component
 */
export const ErrorFallbackPage = ({ 
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  onRetry,
  onGoBack
}) => {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-4" data-testid="error-fallback-page">
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
          <AlertTriangle className="h-8 w-8 text-red-500" />
        </div>
        
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          {title}
        </h2>
        
        <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-sm">
          {message}
        </p>
        
        <div className="flex gap-3 justify-center">
          {onRetry && (
            <Button onClick={onRetry}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          )}
          {onGoBack && (
            <Button variant="outline" onClick={onGoBack}>
              Go Back
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * NetworkErrorBanner - Banner for network issues
 */
export const NetworkErrorBanner = ({ onRetry, onDismiss }) => {
  return (
    <div className="fixed top-0 left-0 right-0 bg-red-500 text-white py-3 px-4 flex items-center justify-center gap-4 z-50" data-testid="network-error-banner">
      <AlertTriangle className="h-5 w-5" />
      <span className="text-sm">Connection issue. Please check your internet.</span>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        <RefreshCw className="h-3 w-3 mr-1" />
        Retry
      </Button>
      {onDismiss && (
        <button onClick={onDismiss} className="text-white/80 hover:text-white">
          Dismiss
        </button>
      )}
    </div>
  );
};

export default ErrorBoundary;
