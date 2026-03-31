import React, { useState } from 'react';
import { Share2, Download, Twitter, Facebook, Linkedin, Instagram, Copy, Check, Image, Lock } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SocialShareDownload({ 
  content, 
  contentType = 'image', 
  imageUrl,
  title = 'My Creation',
  onDownload 
}) {
  const [showWatermarkOptions, setShowWatermarkOptions] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const { canDownload } = useMediaEntitlement();

  const shareUrl = typeof window !== 'undefined' ? window.location.href : '';
  const shareText = `Check out what I created with Visionary Suite: ${title}`;

  const handleDownloadWithWatermark = async () => {
    if (!canDownload) {
      toast.error('Downloads are available on paid plans', {
        action: { label: 'Upgrade', onClick: () => window.location.href = '/app/billing' },
      });
      return;
    }
    if (onDownload) {
      onDownload();
      return;
    }
    if (!imageUrl) return;

    setDownloading(true);
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}_visionary-suite.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Download complete!');
    } catch {
      toast.error('Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const socialLinks = [
    {
      name: 'Twitter',
      icon: Twitter,
      url: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`,
      color: 'hover:bg-blue-500/20 hover:text-blue-400'
    },
    {
      name: 'Facebook',
      icon: Facebook,
      url: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`,
      color: 'hover:bg-blue-600/20 hover:text-blue-500'
    },
    {
      name: 'LinkedIn',
      icon: Linkedin,
      url: `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(shareUrl)}&title=${encodeURIComponent(title)}`,
      color: 'hover:bg-blue-700/20 hover:text-blue-600'
    }
  ];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Share2 className="w-5 h-5 text-indigo-400" />
        <h3 className="text-white font-semibold">Share & Download</h3>
      </div>

      {/* Download Options */}
      <div className="mb-4">
        <Button
          onClick={handleDownloadWithWatermark}
          disabled={downloading}
          className={`w-full ${canDownload ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-600 hover:bg-amber-700'}`}
          data-testid="download-btn"
        >
          {downloading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
              Processing...
            </>
          ) : canDownload ? (
            <><Download className="w-4 h-4 mr-2" />Download</>
          ) : (
            <><Lock className="w-4 h-4 mr-2" />Upgrade to Download</>
          )}
        </Button>
      </div>

      {/* Social Share */}
      <div className="flex items-center gap-2">
        {socialLinks.map((social) => (
          <a
            key={social.name}
            href={social.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`p-2 rounded-lg bg-slate-700/50 text-slate-400 transition-colors ${social.color}`}
            title={`Share on ${social.name}`}
            data-testid={`share-${social.name.toLowerCase()}`}
          >
            <social.icon className="w-4 h-4" />
          </a>
        ))}
        
        <button
          onClick={handleCopyLink}
          className="p-2 rounded-lg bg-slate-700/50 text-slate-400 hover:bg-green-500/20 hover:text-green-400 transition-colors ml-auto"
          title="Copy link"
          data-testid="copy-link-btn"
        >
          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>

      {copied && (
        <p className="text-green-400 text-xs mt-2 text-center">Link copied to clipboard!</p>
      )}
    </div>
  );
}
