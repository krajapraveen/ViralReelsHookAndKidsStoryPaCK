import React, { useState, useEffect } from 'react';
import { Download, Loader2, Shield, ShieldOff, Crown, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Smart Download Button that applies watermark for free users
 * Premium/Paid users get clean downloads without watermark
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
  const [shouldWatermark, setShouldWatermark] = useState(null);
  const [userPlan, setUserPlan] = useState(null);

  // Check if watermark should be applied on mount
  useEffect(() => {
    checkWatermarkStatus();
  }, []);

  const checkWatermarkStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setShouldWatermark(true);
        return;
      }

      const response = await fetch(`${API_URL}/api/watermark/should-apply`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setShouldWatermark(data.shouldApply);
        setUserPlan(data.plan);
      } else {
        setShouldWatermark(true);
      }
    } catch (error) {
      console.error('Error checking watermark status:', error);
      setShouldWatermark(true);
    }
  };

  const handleDownload = async () => {
    setIsDownloading(true);

    try {
      const token = localStorage.getItem('token');
      let downloadBlob;
      let downloadFilename = filename;

      // If user is free, apply watermark
      if (shouldWatermark) {
        // Get the image as blob
        let imageData;
        if (imageBlob) {
          imageData = imageBlob;
        } else if (imageUrl) {
          const imageResponse = await fetch(imageUrl);
          imageData = await imageResponse.blob();
        } else {
          throw new Error('No image source provided');
        }

        // Send to watermark service
        const formData = new FormData();
        formData.append('file', imageData, filename);

        const watermarkResponse = await fetch(
          `${API_URL}/api/watermark/download-with-watermark?content_type=${contentType}`,
          {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
          }
        );

        if (watermarkResponse.ok) {
          downloadBlob = await watermarkResponse.blob();
          const watermarkApplied = watermarkResponse.headers.get('X-Watermark-Applied');
          
          if (watermarkApplied === 'true') {
            toast.info('Watermark added. Upgrade to remove watermarks!', {
              action: {
                label: 'Upgrade',
                onClick: () => window.location.href = '/app/billing'
              }
            });
          }
        } else {
          // Fallback to direct download if watermark service fails
          downloadBlob = imageData;
        }
      } else {
        // Premium user - direct download without watermark
        if (imageBlob) {
          downloadBlob = imageBlob;
        } else if (imageUrl) {
          const response = await fetch(imageUrl);
          downloadBlob = await response.blob();
        }
        toast.success('Premium download - no watermark!');
      }

      // Trigger download
      if (downloadBlob) {
        const url = URL.createObjectURL(downloadBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        onDownloadComplete?.({ success: true, watermarked: shouldWatermark });
        toast.success('Download complete!');
      }
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Download failed. Please try again.');
      onDownloadComplete?.({ success: false, error: error.message });
    } finally {
      setIsDownloading(false);
    }
  };

  // Button appearance based on user plan
  const getButtonStyle = () => {
    if (shouldWatermark === false) {
      // Premium user
      return 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600';
    }
    return 'bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600';
  };

  return (
    <div className={className}>
      <Button
        onClick={handleDownload}
        disabled={isDownloading}
        className={`${getButtonStyle()} text-white transition-all ${size === 'lg' ? 'px-6 py-3 text-lg' : ''}`}
        data-testid="smart-download-btn"
      >
        {isDownloading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : shouldWatermark === false ? (
          <>
            <Crown className="w-4 h-4 mr-2" />
            Download (No Watermark)
          </>
        ) : (
          <>
            <Download className="w-4 h-4 mr-2" />
            Download
          </>
        )}
      </Button>

      {/* Watermark indicator */}
      {shouldWatermark !== null && (
        <div className="mt-2 flex items-center justify-center gap-2 text-xs">
          {shouldWatermark ? (
            <span className="text-slate-400 flex items-center gap-1">
              <ShieldOff className="w-3 h-3" />
              Free download with watermark
            </span>
          ) : (
            <span className="text-amber-400 flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Premium: No watermark
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Upgrade CTA shown to free users
 */
export function WatermarkUpgradeCTA({ onUpgrade }) {
  return (
    <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-xl">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-amber-500/20 rounded-full flex items-center justify-center flex-shrink-0">
          <Crown className="w-5 h-5 text-amber-400" />
        </div>
        <div className="flex-1">
          <h4 className="text-amber-400 font-semibold mb-1">Remove Watermarks</h4>
          <p className="text-slate-300 text-sm mb-3">
            Upgrade to any paid plan to download content without watermarks. 
            Perfect for professional use!
          </p>
          <Button
            onClick={onUpgrade}
            className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white"
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

/**
 * Batch download with watermark handling
 */
export function BatchDownloadButton({
  items = [], // Array of { imageUrl, filename, contentType }
  onComplete
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleBatchDownload = async () => {
    setIsDownloading(true);
    setProgress(0);

    const results = [];
    const token = localStorage.getItem('token');

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      try {
        // Check watermark status
        const statusResponse = await fetch(`${API_URL}/api/watermark/should-apply`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const statusData = await statusResponse.json();

        // Get image
        const imageResponse = await fetch(item.imageUrl);
        const imageBlob = await imageResponse.blob();

        let finalBlob = imageBlob;

        if (statusData.shouldApply) {
          // Apply watermark
          const formData = new FormData();
          formData.append('file', imageBlob, item.filename);

          const watermarkResponse = await fetch(
            `${API_URL}/api/watermark/download-with-watermark?content_type=${item.contentType || 'COMIC'}`,
            {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${token}` },
              body: formData
            }
          );

          if (watermarkResponse.ok) {
            finalBlob = await watermarkResponse.blob();
          }
        }

        // Download
        const url = URL.createObjectURL(finalBlob);
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
      
      // Small delay between downloads
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
        className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
      >
        {isDownloading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Downloading... {progress}%
          </>
        ) : (
          <>
            <Download className="w-4 h-4 mr-2" />
            Download All ({items.length})
          </>
        )}
      </Button>

      {isDownloading && (
        <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
