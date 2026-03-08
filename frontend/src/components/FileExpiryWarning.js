/**
 * File Expiry Warning Component
 * Shows a warning banner about the 5-minute file expiry
 */
import React from 'react';
import { AlertTriangle, Clock, Download } from 'lucide-react';

export const FileExpiryWarning = ({ 
  variant = 'default', // 'default' | 'urgent' | 'compact'
  className = '' 
}) => {
  if (variant === 'urgent') {
    return (
      <div 
        className={`bg-red-500/20 border border-red-500/50 rounded-xl p-4 animate-pulse ${className}`}
        data-testid="file-expiry-warning-urgent"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
          <div>
            <h3 className="text-red-400 font-bold text-lg">Download Now! File expires in 5 minutes</h3>
            <p className="text-red-200/80 text-sm">
              Your file will be automatically deleted to save server space. Download immediately!
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div 
        className={`bg-amber-500/20 border border-amber-500/30 rounded-lg p-3 flex items-center gap-2 ${className}`}
        data-testid="file-expiry-warning-compact"
      >
        <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
        <p className="text-amber-200 text-sm">
          <strong>5-min expiry:</strong> Download files immediately after generation.
        </p>
      </div>
    );
  }

  // Default variant
  return (
    <div 
      className={`bg-amber-500/20 border border-amber-500/50 rounded-xl p-4 ${className}`}
      data-testid="file-expiry-warning"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-amber-400 font-semibold text-lg flex items-center gap-2">
            <Clock className="w-4 h-4" />
            5-Minute Download Window
          </h3>
          <p className="text-amber-200/80 text-sm mt-1">
            All generated files (images, videos, audio, PDFs) are automatically deleted after <strong>5 minutes</strong> to save server space. 
            Please download your files immediately after generation. Expired files cannot be recovered.
          </p>
          <div className="flex items-center gap-2 mt-2 text-amber-300 text-xs">
            <Download className="w-3 h-3" />
            <span>Tip: Right-click and "Save As" to download</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export const FileExpiryBadge = ({ expiresAt, className = '' }) => {
  if (!expiresAt) return null;
  
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diff = expiry - now;
  
  if (diff <= 0) {
    return (
      <span className={`px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full ${className}`}>
        Expired
      </span>
    );
  }
  
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  
  const isUrgent = diff < 60000; // Less than 1 minute
  
  return (
    <span 
      className={`px-2 py-1 text-xs rounded-full ${
        isUrgent 
          ? 'bg-red-500/20 text-red-400 animate-pulse' 
          : 'bg-amber-500/20 text-amber-400'
      } ${className}`}
    >
      <Clock className="w-3 h-3 inline mr-1" />
      {timeStr}
    </span>
  );
};

export default FileExpiryWarning;
