import React, { useState, useEffect } from 'react';
import { Download, Loader2, Shield, ShieldOff, Crown, Sparkles, Lock } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Smart Download Button — enforces entitlement.
 * Paid users: clean download.
 * Free users: "Upgrade to Download" CTA.
 */
export default function SmartDownloadButton({
  imageUrl,
  imageBlob,
  filename = 'download.png',
  contentType = 'COMIC',
  onDownloadComplete,
  className = '',
  variant = 'default',
  size = 'default'
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { canDownload, loading: entLoading } = useMediaEntitlement();

  const handleDownload = async () => {
    if (!canDownload) {
      toast.error('Downloads are available on paid plans', {
        action: { label: 'Upgrade', onClick: () => window.location.href = '/app/billing' },
      });
      onDownloadComplete?.({ success: false, error: 'upgrade_required' });
      return;
    }

    setIsDownloading(true);
    try {
      let downloadBlob;
      if (imageBlob) {
        downloadBlob = imageBlob;
      } else if (imageUrl) {
        const response = await fetch(imageUrl);
        downloadBlob = await response.blob();
      } else {
        throw new Error('No image source provided');
      }

      if (downloadBlob) {
        const url = URL.createObjectURL(downloadBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        onDownloadComplete?.({ success: true });
        toast.success('Download complete!');
      }
    } catch (error) {
      toast.error('Download failed. Please try again.');
      onDownloadComplete?.({ success: false, error: error.message });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className={className}>
      <Button
        onClick={handleDownload}
        disabled={isDownloading || entLoading}
        className={`${canDownload ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-600 hover:bg-amber-700'} text-white transition-all ${size === 'lg' ? 'px-6 py-3 text-lg' : ''}`}
        data-testid="smart-download-btn"
      >
        {isDownloading ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</>
        ) : canDownload ? (
          <><Download className="w-4 h-4 mr-2" />Download</>
        ) : (
          <><Lock className="w-4 h-4 mr-2" />Upgrade to Download</>
        )}
      </Button>

      {!canDownload && !entLoading && (
        <div className="mt-2 flex items-center justify-center gap-2 text-xs">
          <span className="text-amber-400/70 flex items-center gap-1">
            <Lock className="w-3 h-3" />
            Downloads are available on paid plans
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Upgrade CTA shown to free users
 */
export function DownloadUpgradeCTA() {
  return (
    <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-xl">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-amber-500/20 rounded-full flex items-center justify-center flex-shrink-0">
          <Lock className="w-5 h-5 text-amber-400" />
        </div>
        <div className="flex-1">
          <h4 className="text-amber-400 font-semibold mb-1">Downloads Locked</h4>
          <p className="text-slate-300 text-sm mb-3">
            Downloads are available on paid plans. Upgrade to download your creations.
          </p>
          <Button
            onClick={() => window.location.href = '/app/billing'}
            className="bg-amber-600 hover:bg-amber-700 text-white"
            size="sm"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            View Plans
          </Button>
        </div>
      </div>
    </div>
  );
}

// Keep backwards compat export name
export { DownloadUpgradeCTA as WatermarkUpgradeCTA };

/**
 * Batch download — entitlement-gated
 */
export function BatchDownloadButton({
  items = [],
  onComplete
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { canDownload } = useMediaEntitlement();

  const handleBatchDownload = async () => {
    if (!canDownload) {
      toast.error('Downloads are available on paid plans', {
        action: { label: 'Upgrade', onClick: () => window.location.href = '/app/billing' },
      });
      return;
    }

    setIsDownloading(true);
    setProgress(0);
    const results = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      try {
        const imageResponse = await fetch(item.imageUrl);
        const imageBlob = await imageResponse.blob();
        const url = URL.createObjectURL(imageBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = item.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        results.push({ filename: item.filename, success: true });
      } catch (error) {
        results.push({ filename: item.filename, success: false, error: error.message });
      }
      setProgress(Math.round(((i + 1) / items.length) * 100));
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    setIsDownloading(false);
    onComplete?.(results);
    const successCount = results.filter(r => r.success).length;
    toast.success(`Downloaded ${successCount}/${items.length} files`);
  };

  return (
    <div>
      <Button
        onClick={handleBatchDownload}
        disabled={isDownloading || items.length === 0}
        className={canDownload ? "bg-emerald-600 hover:bg-emerald-700" : "bg-amber-600 hover:bg-amber-700"}
      >
        {isDownloading ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Downloading... {progress}%</>
        ) : canDownload ? (
          <><Download className="w-4 h-4 mr-2" />Download All ({items.length})</>
        ) : (
          <><Lock className="w-4 h-4 mr-2" />Upgrade to Download</>
        )}
      </Button>
      {isDownloading && (
        <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-emerald-500 transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
