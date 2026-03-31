import React, { useState } from 'react';
import { Download, CheckCircle, Crown, Shield, Loader2, FileText, Image, Lock } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * PermanentDownload — entitlement-gated download component.
 * Paid users get secure download via token endpoint.
 * Free users see "Upgrade to Download" CTA.
 */
export default function PermanentDownload({
  downloadUrl,
  assetId,
  filename,
  fileType = 'file',
  contentType = 'COMIC',
}) {
  const [downloaded, setDownloaded] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const { canDownload, loading: entLoading } = useMediaEntitlement();
  const navigate = useNavigate();

  const handleDownload = async () => {
    if (!canDownload) {
      toast.error('Downloads are available on paid plans', {
        action: { label: 'Upgrade', onClick: () => navigate('/app/billing') },
      });
      return;
    }

    // Use secure token endpoint if assetId is available
    if (assetId) {
      setIsDownloading(true);
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_URL}/api/media/download-token/${assetId}`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        });
        if (res.status === 403) {
          toast.error('Downloads are available on paid plans');
          return;
        }
        if (!res.ok) throw new Error('Failed to get download link');
        const data = await res.json();
        if (data.success && data.download_url) {
          const dlRes = await fetch(data.download_url);
          if (!dlRes.ok) throw new Error('Download failed');
          const blob = await dlRes.blob();
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = blobUrl;
          a.download = filename || 'download';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
          setDownloaded(true);
          toast.success('Download started!');
        }
      } catch {
        toast.error('Download failed. Please try again.');
      } finally {
        setIsDownloading(false);
      }
      return;
    }

    // Fallback for legacy usage without assetId (still gated by canDownload)
    if (!downloadUrl) {
      toast.error('Download not available');
      return;
    }
    setIsDownloading(true);
    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename || 'download';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      setDownloaded(true);
      toast.success('Download started!');
    } catch {
      toast.error('Download failed. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl" data-testid="permanent-download">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <span className="text-white font-medium truncate max-w-[220px]">
            {filename || 'Your file is ready'}
          </span>
        </div>
        {downloaded && (
          <span className="text-green-400 text-xs bg-green-500/20 px-2 py-1 rounded">
            Downloaded
          </span>
        )}
      </div>

      <div className="mb-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
        <div className="flex items-center gap-2 text-sm text-emerald-300">
          <Shield className="w-4 h-4 flex-shrink-0" />
          <span>Stored permanently — download anytime</span>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleDownload}
          disabled={isDownloading || entLoading}
          className={`flex-1 ${canDownload
            ? 'bg-emerald-600 hover:bg-emerald-700'
            : 'bg-amber-600 hover:bg-amber-700'
          }`}
          data-testid="download-btn"
        >
          {isDownloading ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</>
          ) : canDownload ? (
            <><Download className="w-4 h-4 mr-2" />{downloaded ? 'Download Again' : 'Download'}</>
          ) : (
            <><Lock className="w-4 h-4 mr-2" />Upgrade to Download</>
          )}
        </Button>
      </div>
    </div>
  );
}

// Backwards compatibility
export { PermanentDownload as DownloadWithExpiry };
