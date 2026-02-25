import React, { useState, useEffect, useCallback } from 'react';
import { 
  AlertTriangle, RefreshCw, Download, CheckCircle, 
  Clock, HelpCircle, X, Loader2, FileText
} from 'lucide-react';
import { Button } from '../ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL || '';

/**
 * RecoveryManager - User-facing recovery UI component
 * Handles job failures, download recovery, and provides fallback options
 */
const RecoveryManager = ({ 
  jobId = null,
  contentType = 'generation',
  onRecovered = () => {},
  onDismiss = () => {},
  className = ''
}) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const fetchRecoveryStatus = useCallback(async () => {
    if (!jobId) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/job/${jobId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Recovery status fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchRecoveryStatus();
  }, [fetchRecoveryStatus]);

  const handleRetry = async (retryToken) => {
    setRetrying(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/job/retry`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ retry_token: retryToken })
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success('Job resubmitted successfully!');
        onRecovered(data.new_job_id);
      } else {
        toast.error('Retry failed. Please try again.');
      }
    } catch (error) {
      toast.error('Network error. Please check your connection.');
    } finally {
      setRetrying(false);
    }
  };

  const handleAcceptFallback = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/job/${jobId}/accept-fallback`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success('Alternative output accepted!');
        onRecovered(data.fallback_result);
      }
    } catch (error) {
      toast.error('Failed to accept fallback');
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!status) return null;

  // Render based on status
  if (status.status === 'completed' && status.result_url) {
    return null; // Job completed successfully, no recovery needed
  }

  return (
    <div className={`bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 ${className}`} data-testid="recovery-manager">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {status.status === 'failed' ? (
            <AlertTriangle className="h-5 w-5 text-red-500" />
          ) : status.status === 'fallback' ? (
            <FileText className="h-5 w-5 text-yellow-500" />
          ) : (
            <Clock className="h-5 w-5 text-blue-500" />
          )}
          <h3 className="font-medium text-gray-900 dark:text-white">
            {status.status === 'failed' 
              ? 'Generation Failed' 
              : status.status === 'fallback'
              ? 'Alternative Output Available'
              : 'Processing Issue'}
          </h3>
        </div>
        <button onClick={onDismiss} className="text-gray-400 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Error Message */}
      {status.error && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {status.error}
        </p>
      )}

      {/* Fallback Message */}
      {status.fallback_available && (
        <div className="mt-3 p-3 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            We've prepared an alternative output for you. You can use it now or retry the original request.
          </p>
        </div>
      )}

      {/* Recovery Options */}
      {status.recovery_options && status.recovery_options.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {status.recovery_options.map((option, index) => (
            <RecoveryButton
              key={index}
              option={option}
              onRetry={handleRetry}
              onAcceptFallback={handleAcceptFallback}
              retrying={retrying}
            />
          ))}
        </div>
      )}

      {/* Support Reference */}
      <p className="mt-4 text-xs text-gray-500">
        Reference ID: {jobId}
      </p>
    </div>
  );
};

/**
 * RecoveryButton - Individual action button for recovery options
 */
const RecoveryButton = ({ option, onRetry, onAcceptFallback, retrying }) => {
  const handleClick = () => {
    switch (option.action) {
      case 'retry':
        onRetry(option.token);
        break;
      case 'accept_fallback':
        onAcceptFallback();
        break;
      case 'open_support':
        window.open(`mailto:support@creatorstudio.ai?subject=Issue with ${option.reference_id}`, '_blank');
        break;
      case 'refresh':
        window.location.reload();
        break;
      default:
        break;
    }
  };

  const getIcon = () => {
    switch (option.type) {
      case 'retry':
        return retrying ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />;
      case 'use_fallback':
        return <CheckCircle className="h-4 w-4" />;
      case 'check_status':
        return <Clock className="h-4 w-4" />;
      case 'support':
        return <HelpCircle className="h-4 w-4" />;
      default:
        return null;
    }
  };

  return (
    <Button
      variant={option.type === 'retry' ? 'default' : 'outline'}
      size="sm"
      onClick={handleClick}
      disabled={retrying && option.type === 'retry'}
      data-testid={`recovery-btn-${option.type}`}
    >
      {getIcon()}
      <span className="ml-1">{option.label}</span>
    </Button>
  );
};

/**
 * DownloadRecovery - Component for handling download failures
 */
export const DownloadRecovery = ({ 
  originalUrl, 
  onNewUrl, 
  onDismiss 
}) => {
  const [loading, setLoading] = useState(false);

  const handleRecoverDownload = async (errorCode = 403) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: originalUrl, error_code: errorCode })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.new_url) {
          toast.success('Download link regenerated!');
          onNewUrl(data.new_url);
        } else if (data.fallback_options) {
          toast.info(data.message || 'Please try alternative options');
        }
      } else {
        toast.error('Could not recover download');
      }
    } catch (error) {
      toast.error('Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4" data-testid="download-recovery">
      <div className="flex items-start gap-3">
        <Download className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-medium text-gray-900 dark:text-white">Download Link Expired</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Your download link has expired. Click below to generate a new one.
          </p>
          <div className="mt-3 flex gap-2">
            <Button 
              size="sm" 
              onClick={() => handleRecoverDownload(403)}
              disabled={loading}
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
              Regenerate Link
            </Button>
            <Button variant="outline" size="sm" onClick={onDismiss}>
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * PaymentRecovery - Component for showing payment status and recovery
 */
export const PaymentRecovery = ({ orderId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPaymentStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API}/api/recovery/payment/${orderId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
          setStatus(await response.json());
        }
      } catch (error) {
        console.error('Payment status error:', error);
      } finally {
        setLoading(false);
      }
    };

    if (orderId) fetchPaymentStatus();
  }, [orderId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
        <span className="text-sm text-gray-600 dark:text-gray-400">Checking payment status...</span>
      </div>
    );
  }

  if (!status) return null;

  const getStatusColor = () => {
    switch (status.state) {
      case 'success': return 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800';
      case 'reconciling': return 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800';
      case 'failed': return 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800';
      case 'refunded': return 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800';
      default: return 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700';
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${getStatusColor()}`} data-testid="payment-recovery">
      <div className="flex items-start gap-3">
        {status.state === 'success' && status.delivered ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : status.state === 'reconciling' ? (
          <Clock className="h-5 w-5 text-yellow-500 animate-pulse" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-red-500" />
        )}
        
        <div className="flex-1">
          <h3 className="font-medium text-gray-900 dark:text-white">
            Payment {status.state === 'success' ? 'Successful' : status.state}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {status.status_message}
          </p>
          
          {status.recovery_info && (
            <div className="mt-2 text-xs text-gray-500">
              {status.recovery_info.expected_resolution && (
                <p>Expected resolution: {status.recovery_info.expected_resolution}</p>
              )}
            </div>
          )}
          
          <div className="mt-2 text-xs text-gray-500">
            Order ID: {orderId}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecoveryManager;
