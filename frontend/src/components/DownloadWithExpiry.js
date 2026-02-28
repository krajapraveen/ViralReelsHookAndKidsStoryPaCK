import React, { useState, useEffect } from 'react';
import { Clock, Download, AlertTriangle, CheckCircle, Trash2, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { toast } from 'sonner';

const EXPIRY_MINUTES = 5;
const EXPIRY_SECONDS = EXPIRY_MINUTES * 60;

export default function DownloadWithExpiry({ 
  downloadUrl,
  downloadId,
  filename,
  fileType = 'file',
  onExpired,
  expiresAt,
  expiresInSeconds = EXPIRY_SECONDS,
  showWarning = true
}) {
  const [remainingSeconds, setRemainingSeconds] = useState(() => {
    // Calculate remaining time from expiresAt if provided
    if (expiresAt) {
      const expiryTime = new Date(expiresAt).getTime();
      const remaining = Math.floor((expiryTime - Date.now()) / 1000);
      return Math.max(0, remaining);
    }
    return expiresInSeconds;
  });
  const [downloaded, setDownloaded] = useState(false);
  const [expired, setExpired] = useState(false);

  // Countdown timer
  useEffect(() => {
    if (remainingSeconds <= 0) {
      setExpired(true);
      onExpired?.();
      return;
    }

    const timer = setInterval(() => {
      setRemainingSeconds(prev => {
        if (prev <= 1) {
          setExpired(true);
          onExpired?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [remainingSeconds, onExpired]);

  // Show warning toast at 1 minute remaining
  useEffect(() => {
    if (remainingSeconds === 60 && !downloaded) {
      toast.warning('Your download will expire in 1 minute! Download now.');
    }
    if (remainingSeconds === 30 && !downloaded) {
      toast.error('Only 30 seconds left! Download immediately.');
    }
  }, [remainingSeconds, downloaded]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgressColor = () => {
    const percentage = (remainingSeconds / EXPIRY_SECONDS) * 100;
    if (percentage > 50) return 'bg-green-500';
    if (percentage > 25) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const handleDownload = () => {
    setDownloaded(true);
    toast.success('Download started!');
    // Trigger actual download
    window.open(downloadUrl, '_blank');
  };

  if (expired) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="w-6 h-6" />
          <div>
            <p className="font-medium">Download Expired</p>
            <p className="text-sm text-red-300">
              This download is no longer available. Please generate again.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl">
      {/* Header with filename */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="text-white font-medium truncate max-w-[200px]">
            {filename || 'Your file is ready'}
          </span>
        </div>
        {downloaded && (
          <span className="text-green-400 text-xs bg-green-500/20 px-2 py-1 rounded">
            Downloaded
          </span>
        )}
      </div>

      {/* Warning message */}
      {showWarning && (
        <div className={`mb-4 p-3 rounded-lg flex items-start gap-2 ${
          remainingSeconds < 60 
            ? 'bg-red-500/10 border border-red-500/30' 
            : 'bg-amber-500/10 border border-amber-500/30'
        }`}>
          <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
            remainingSeconds < 60 ? 'text-red-400' : 'text-amber-400'
          }`} />
          <div className="text-sm">
            <p className={remainingSeconds < 60 ? 'text-red-300' : 'text-amber-300'}>
              {remainingSeconds < 60 
                ? 'Hurry! Your download expires very soon!' 
                : `Your download will be available for only ${EXPIRY_MINUTES} minutes.`
              }
            </p>
            <p className="text-slate-400 text-xs mt-1">
              Please download before it expires. The file will be automatically deleted.
            </p>
          </div>
        </div>
      )}

      {/* Countdown Timer */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-slate-400 flex items-center gap-1">
            <Clock className="w-4 h-4" />
            Time remaining
          </span>
          <span className={`font-mono font-bold ${
            remainingSeconds < 60 ? 'text-red-400' : 
            remainingSeconds < 120 ? 'text-amber-400' : 'text-green-400'
          }`}>
            {formatTime(remainingSeconds)}
          </span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-1000 ${getProgressColor()}`}
            style={{ width: `${(remainingSeconds / EXPIRY_SECONDS) * 100}%` }}
          />
        </div>
      </div>

      {/* Download Button */}
      <div className="flex gap-2">
        <Button 
          onClick={handleDownload}
          className={`flex-1 ${
            remainingSeconds < 60 
              ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
          disabled={expired}
        >
          <Download className="w-4 h-4 mr-2" />
          {downloaded ? 'Download Again' : 'Download Now'}
        </Button>
      </div>

      {/* Download count indicator */}
      {downloaded && (
        <p className="text-xs text-slate-500 text-center mt-3">
          You can download multiple times before expiry
        </p>
      )}
    </div>
  );
}

// Component to show list of user's active downloads
export function ActiveDownloadsList({ downloads = [], onRefresh }) {
  if (!downloads || downloads.length === 0) {
    return null;
  }

  return (
    <div className="p-4 bg-slate-900/50 border border-slate-700 rounded-xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Download className="w-5 h-5 text-indigo-400" />
          Active Downloads ({downloads.length})
        </h3>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          Refresh
        </Button>
      </div>
      
      <div className="space-y-3">
        {downloads.map((download, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <Download className="w-4 h-4 text-slate-400" />
              <div>
                <p className="text-white text-sm truncate max-w-[150px]">
                  {download.filename}
                </p>
                <p className="text-xs text-slate-500">{download.feature}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-mono ${
                download.remaining_seconds < 60 ? 'text-red-400' : 'text-green-400'
              }`}>
                {Math.floor(download.remaining_seconds / 60)}:
                {(download.remaining_seconds % 60).toString().padStart(2, '0')}
              </span>
              <Button size="sm" variant="ghost">
                <ExternalLink className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>
      
      <p className="text-xs text-slate-500 text-center mt-3">
        Downloads automatically expire after 5 minutes
      </p>
    </div>
  );
}
