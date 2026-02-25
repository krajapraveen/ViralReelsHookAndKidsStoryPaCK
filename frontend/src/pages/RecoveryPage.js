import React, { useState, useEffect } from 'react';
import { AlertTriangle, RefreshCw, Download, MessageCircle, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL || '';

/**
 * RecoveryBanner - Shows when user has recovery issues
 */
export const RecoveryBanner = ({ onDismiss }) => {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkRecoveryStatus();
  }, []);

  const checkRecoveryStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setIssues(data.issues || []);
      }
    } catch (error) {
      console.error('Recovery status check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || issues.length === 0) return null;

  return (
    <Alert className="mb-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20">
      <AlertTriangle className="h-4 w-4 text-yellow-600" />
      <AlertTitle className="text-yellow-800 dark:text-yellow-200">
        Action Required
      </AlertTitle>
      <AlertDescription className="text-yellow-700 dark:text-yellow-300">
        {issues.length === 1 ? issues[0].message : `You have ${issues.length} items that need attention.`}
        <Button 
          variant="link" 
          className="ml-2 text-yellow-800 dark:text-yellow-200 p-0 h-auto"
          onClick={() => window.location.href = '/app/recovery'}
        >
          View Details →
        </Button>
      </AlertDescription>
    </Alert>
  );
};

/**
 * JobRecoveryCard - Shows recovery options for a failed job
 */
export const JobRecoveryCard = ({ jobId, onRetry, onAcceptFallback }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    fetchJobStatus();
  }, [jobId]);

  const fetchJobStatus = async () => {
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
      console.error('Job status fetch failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const token = localStorage.getItem('token');
      const retryOption = status.recovery_options.find(o => o.type === 'retry');
      
      const response = await fetch(`${API}/api/recovery/job/retry`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          retry_token: retryOption?.token,
          job_id: jobId
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success('Job resubmitted successfully!');
        if (onRetry) onRetry(data.new_job_id);
      } else {
        toast.error('Retry failed. Please try again.');
      }
    } catch (error) {
      toast.error('Retry failed. Please try again.');
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
        toast.success('Fallback accepted!');
        if (onAcceptFallback) onAcceptFallback(data.fallback_result);
      }
    } catch (error) {
      toast.error('Failed to accept fallback');
    }
  };

  if (loading) {
    return (
      <Card className="border-gray-200">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  if (!status) return null;

  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed': return <XCircle className="h-5 w-5 text-red-500" />;
      case 'fallback': return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'processing': return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      default: return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <Card className={`border-2 ${
      status.status === 'failed' ? 'border-red-200 bg-red-50 dark:bg-red-900/10' :
      status.status === 'fallback' ? 'border-yellow-200 bg-yellow-50 dark:bg-yellow-900/10' :
      'border-gray-200'
    }`}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <CardTitle className="text-lg">
            {status.status === 'failed' ? 'Generation Failed' :
             status.status === 'fallback' ? 'Alternative Output Available' :
             'Job Status'}
          </CardTitle>
        </div>
        {status.error && (
          <CardDescription className="text-red-600 dark:text-red-400">
            {status.error}
          </CardDescription>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Recovery Options */}
        {status.recovery_options && status.recovery_options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {status.recovery_options.map((option, index) => (
              <Button
                key={index}
                variant={option.type === 'retry' ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  if (option.type === 'retry') handleRetry();
                  else if (option.type === 'use_fallback') handleAcceptFallback();
                  else if (option.type === 'support') window.open(`mailto:support@creatorstudio.ai?subject=Job Issue: ${jobId}`);
                }}
                disabled={retrying}
              >
                {option.type === 'retry' && <RefreshCw className={`h-4 w-4 mr-1 ${retrying ? 'animate-spin' : ''}`} />}
                {option.type === 'use_fallback' && <Download className="h-4 w-4 mr-1" />}
                {option.type === 'support' && <MessageCircle className="h-4 w-4 mr-1" />}
                {option.label}
              </Button>
            ))}
          </div>
        )}
        
        {/* Fallback Result */}
        {status.fallback_available && status.status === 'fallback' && (
          <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded-md">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              We've prepared an alternative output for you. You can accept it or try generating again.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

/**
 * DownloadRecoveryButton - Handles download failures with auto-recovery
 */
export const DownloadRecoveryButton = ({ url, filename, children, className }) => {
  const [recovering, setRecovering] = useState(false);

  const handleDownload = async () => {
    try {
      const response = await fetch(url);
      
      if (response.ok) {
        // Download successful
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename || 'download';
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        // Download failed - try recovery
        await recoverDownload(response.status);
      }
    } catch (error) {
      await recoverDownload(500);
    }
  };

  const recoverDownload = async (errorCode) => {
    setRecovering(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/download`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url, error_code: errorCode })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.success && data.new_url) {
          toast.success('Download link refreshed!');
          // Retry download with new URL
          window.open(data.new_url, '_blank');
        } else if (data.fallback_options && data.fallback_options.length > 0) {
          // Show fallback options
          toast.info(data.fallback_options[0].description);
        } else {
          toast.error('Download failed. Please try again later.');
        }
      }
    } catch (error) {
      toast.error('Download recovery failed');
    } finally {
      setRecovering(false);
    }
  };

  return (
    <Button 
      onClick={handleDownload} 
      disabled={recovering}
      className={className}
    >
      {recovering ? (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Recovering...
        </>
      ) : children}
    </Button>
  );
};

/**
 * PaymentRecoveryStatus - Shows payment status with recovery info
 */
export const PaymentRecoveryStatus = ({ orderId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPaymentStatus();
    
    // Poll for updates if payment is being processed
    const interval = setInterval(() => {
      if (status && ['reconciling', 'pending'].includes(status.state)) {
        fetchPaymentStatus();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [orderId]);

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
      console.error('Payment status fetch failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Checking payment status...
      </div>
    );
  }

  if (!status) return null;

  const getStatusColor = () => {
    switch (status.state) {
      case 'success': return 'text-green-600 bg-green-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'reconciling': return 'text-yellow-600 bg-yellow-50';
      case 'refunded': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className={`p-4 rounded-lg ${getStatusColor()}`}>
      <div className="flex items-center gap-2 mb-2">
        {status.state === 'reconciling' && <Loader2 className="h-4 w-4 animate-spin" />}
        {status.state === 'success' && status.delivered && <CheckCircle className="h-4 w-4" />}
        {status.state === 'failed' && <XCircle className="h-4 w-4" />}
        <span className="font-medium">{status.status_message}</span>
      </div>
      
      {status.recovery_info && status.recovery_info.expected_resolution && (
        <p className="text-sm opacity-80">
          Expected resolution: {status.recovery_info.expected_resolution}
        </p>
      )}
      
      {status.recovery_info && status.recovery_info.can_retry && (
        <Button size="sm" variant="outline" className="mt-2">
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry Payment
        </Button>
      )}
    </div>
  );
};

/**
 * RecoveryPage - Full page showing all recovery items
 */
const RecoveryPage = () => {
  const [recoveryStatus, setRecoveryStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecoveryStatus();
  }, []);

  const fetchRecoveryStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/api/recovery/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setRecoveryStatus(await response.json());
      }
    } catch (error) {
      console.error('Recovery status fetch failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Recovery Center
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          View and resolve any issues with your generations or payments.
        </p>
      </div>

      {recoveryStatus && !recoveryStatus.has_issues && (
        <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-800 dark:text-green-200">
            All Clear!
          </AlertTitle>
          <AlertDescription className="text-green-700 dark:text-green-300">
            You have no pending issues. All your generations and payments are up to date.
          </AlertDescription>
        </Alert>
      )}

      {recoveryStatus && recoveryStatus.issues && recoveryStatus.issues.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Items Requiring Attention
          </h2>
          
          {recoveryStatus.issues.map((issue, index) => (
            <Card key={index} className="border-yellow-200">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <CardTitle className="text-base">{issue.message}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {issue.type === 'payment' && issue.auto_resolving && (
                  <div className="flex items-center gap-2 text-sm text-yellow-700">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Automatically resolving...
                  </div>
                )}
                
                {issue.type === 'job_fallback' && (
                  <JobRecoveryCard jobId={issue.job_id} />
                )}
                
                {issue.type === 'job_failed' && (
                  <JobRecoveryCard jobId={issue.job_id} />
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pending Jobs Section */}
      {recoveryStatus && recoveryStatus.pending_jobs > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-500" />
              Jobs In Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 dark:text-gray-400">
              You have {recoveryStatus.pending_jobs} job(s) currently being processed.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Support Section */}
      <Card className="bg-gray-50 dark:bg-gray-900">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Need Help?
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            If you're experiencing issues that aren't automatically resolved, our support team is here to help.
          </p>
          <Button variant="outline" onClick={() => window.open('mailto:support@creatorstudio.ai')}>
            Contact Support
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default RecoveryPage;
