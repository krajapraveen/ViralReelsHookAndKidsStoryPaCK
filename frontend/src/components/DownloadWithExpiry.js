import React, { useState } from 'react';
import { Download, CheckCircle, Crown, Shield, Loader2, FileText, Image } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

/**
 * PermanentDownload — replaces DownloadWithExpiry.
 * Downloads are permanent CDN-backed assets. No expiry. No countdown.
 */
export default function PermanentDownload({
  downloadUrl,
  filename,
  fileType = 'file',
  isPremium = false,
  contentType = 'COMIC',
}) {
  const [downloaded, setDownloaded] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!downloadUrl) {
      toast.error('Download not available');
      return;
    }
    setIsDownloading(true);
    try {
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename || 'download';
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setDownloaded(true);
      toast.success('Download started!');
    } catch {
      window.open(downloadUrl, '_blank');
      toast.success('Download started!');
    } finally {
      setIsDownloading(false);
    }
  };

  const icon = fileType?.includes('pdf') ? <FileText className="w-5 h-5 text-red-400" /> : <Image className="w-5 h-5 text-purple-400" />;

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
          disabled={isDownloading || !downloadUrl}
          className={`flex-1 ${isPremium
            ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600'
            : 'bg-purple-600 hover:bg-purple-700'
          }`}
          data-testid="download-btn"
        >
          {isDownloading ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</>
          ) : isPremium ? (
            <><Crown className="w-4 h-4 mr-2" />{downloaded ? 'Download Again' : 'Download (No Watermark)'}</>
          ) : (
            <><Download className="w-4 h-4 mr-2" />{downloaded ? 'Download Again' : 'Download'}</>
          )}
        </Button>
      </div>
    </div>
  );
}

// Backwards compatibility: any code importing DownloadWithExpiry gets PermanentDownload
export { PermanentDownload as DownloadWithExpiry };
