import React, { useState } from 'react';
import { Download, Lock, Loader2, Crown } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * EntitledDownloadButton — universal download button that enforces entitlement.
 *
 * - Paid users: requests a short-lived download token from backend, then opens it.
 * - Free users: shows "Upgrade to Download" CTA.
 * - No raw R2 URLs are ever exposed in the frontend.
 */
export default function EntitledDownloadButton({
  assetId,
  label = 'Download Video',
  upgradeLabel = 'Upgrade to Download',
  className = '',
  variant = 'default',
  size = 'default',
  icon: CustomIcon,
  disabled = false,
  'data-testid': testId = 'entitled-download-btn',
}) {
  const { canDownload, upgradeRequired, loading: entLoading } = useMediaEntitlement();
  const [downloading, setDownloading] = useState(false);
  const navigate = useNavigate();

  const handleSecureDownload = async () => {
    if (!assetId) {
      toast.error('No asset available for download');
      return;
    }
    setDownloading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/media/download-token/${assetId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (res.status === 403) {
        toast.error('Downloads are available on paid plans', {
          action: { label: 'Upgrade', onClick: () => navigate('/app/billing') },
        });
        return;
      }

      if (!res.ok) {
        throw new Error('Failed to get download link');
      }

      const data = await res.json();
      if (data.success && data.download_url) {
        // Fetch as blob for proper download behavior
        try {
          const dlRes = await fetch(data.download_url);
          if (!dlRes.ok) throw new Error('Download fetch failed');
          const blob = await dlRes.blob();
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = blobUrl;
          a.download = `visionary-suite-${assetId.slice(0, 8)}.mp4`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
          toast.success('Download started!');
        } catch {
          // Fallback: open in new tab
          window.open(data.download_url, '_blank');
          toast.success('Download started!');
        }
      }
    } catch (err) {
      toast.error('Download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const handleUpgrade = () => {
    navigate('/app/billing');
  };

  // Still loading entitlement
  if (entLoading) {
    return (
      <Button disabled className={`opacity-40 ${className}`} data-testid={testId} variant={variant} size={size}>
        <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Verifying...
      </Button>
    );
  }

  // Free user — show upgrade CTA
  if (upgradeRequired || !canDownload) {
    return (
      <Button
        onClick={handleUpgrade}
        className={`bg-amber-600 hover:bg-amber-700 text-white ${className}`}
        data-testid={`${testId}-upgrade`}
        variant={variant}
        size={size}
        title="Downloads are available on paid plans"
      >
        <Lock className="w-4 h-4 mr-2" />
        {upgradeLabel}
      </Button>
    );
  }

  // Paid user — secure download
  const IconComponent = CustomIcon || Download;
  return (
    <Button
      onClick={handleSecureDownload}
      disabled={disabled || downloading || !assetId}
      className={`bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
      data-testid={testId}
      variant={variant}
      size={size}
    >
      {downloading ? (
        <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Downloading...</>
      ) : (
        <><IconComponent className="w-4 h-4 mr-2" /> {label}</>
      )}
    </Button>
  );
}

/**
 * Compact version for asset cards and small surfaces.
 */
export function EntitledDownloadIcon({ assetId, className = '' }) {
  const { canDownload, loading } = useMediaEntitlement();
  const [downloading, setDownloading] = useState(false);
  const navigate = useNavigate();

  const handleClick = async (e) => {
    e.stopPropagation();
    if (!canDownload) {
      toast.error('Downloads are available on paid plans', {
        action: { label: 'Upgrade', onClick: () => navigate('/app/billing') },
      });
      return;
    }
    if (!assetId) return;
    setDownloading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/media/download-token/${assetId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (res.status === 403) {
        toast.error('Downloads are available on paid plans', {
          action: { label: 'Upgrade', onClick: () => navigate('/app/billing') },
        });
        return;
      }
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      if (data.success && data.download_url) {
        window.open(data.download_url, '_blank');
        toast.success('Download started!');
      }
    } catch {
      toast.error('Download failed');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return null;

  return (
    <Button
      size="sm"
      variant="outline"
      className={`h-7 px-2 border-slate-600 text-slate-400 ${className}`}
      onClick={handleClick}
      data-testid="entitled-download-icon"
      title={canDownload ? 'Download' : 'Downloads are available on paid plans'}
    >
      {downloading ? (
        <Loader2 className="w-3 h-3 animate-spin" />
      ) : canDownload ? (
        <Download className="w-3 h-3" />
      ) : (
        <Lock className="w-3 h-3" />
      )}
    </Button>
  );
}
