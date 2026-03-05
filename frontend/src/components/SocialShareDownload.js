import React, { useState } from 'react';
import { Share2, Download, Twitter, Facebook, Linkedin, Instagram, Copy, Check, Image } from 'lucide-react';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SocialShareDownload({ 
  content, 
  contentType = 'image', 
  imageUrl,
  title = 'My Creation',
  onDownload 
}) {
  const [showWatermarkOptions, setShowWatermarkOptions] = useState(false);
  const [watermarkEnabled, setWatermarkEnabled] = useState(true);
  const [watermarkPosition, setWatermarkPosition] = useState('bottom-right');
  const [watermarkOpacity, setWatermarkOpacity] = useState(50);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  const shareUrl = typeof window !== 'undefined' ? window.location.href : '';
  const shareText = `Check out what I created with CreatorStudio AI: ${title}`;

  const handleDownloadWithWatermark = async () => {
    if (!imageUrl || !watermarkEnabled) {
      // Direct download without watermark
      if (onDownload) {
        onDownload();
      }
      return;
    }

    setDownloading(true);
    try {
      const token = localStorage.getItem('token');
      
      // Fetch the original image
      const imageResponse = await fetch(imageUrl);
      const imageBlob = await imageResponse.blob();
      
      // Create form data
      const formData = new FormData();
      formData.append('file', imageBlob, 'image.png');
      
      // Send to watermark API
      const response = await fetch(
        `${API_URL}/api/watermark/image?position=${watermarkPosition}&opacity=${watermarkOpacity}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        }
      );
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}_visionary-suite.png`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        // Fallback to direct download
        if (onDownload) {
          onDownload();
        }
      }
    } catch (error) {
      console.error('Error downloading with watermark:', error);
      // Fallback to direct download
      if (onDownload) {
        onDownload();
      }
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
          onClick={() => setShowWatermarkOptions(!showWatermarkOptions)}
          variant="outline"
          className="w-full justify-between border-slate-600 text-slate-300 hover:bg-slate-700/50"
          data-testid="download-options-btn"
        >
          <span className="flex items-center gap-2">
            <Download className="w-4 h-4" />
            Download Options
          </span>
          <Image className="w-4 h-4" />
        </Button>

        {showWatermarkOptions && (
          <div className="mt-3 p-4 bg-slate-900/50 rounded-lg border border-slate-700 space-y-4">
            {/* Watermark Toggle */}
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-300">Add Watermark</label>
              <button
                onClick={() => setWatermarkEnabled(!watermarkEnabled)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  watermarkEnabled ? 'bg-indigo-500' : 'bg-slate-600'
                }`}
                data-testid="watermark-toggle"
              >
                <div className={`w-5 h-5 bg-white rounded-full transition-transform ${
                  watermarkEnabled ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
            </div>

            {watermarkEnabled && (
              <>
                {/* Position */}
                <div>
                  <label className="text-xs text-slate-400 block mb-2">Position</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['top-left', 'top-right', 'bottom-left', 'bottom-right'].map((pos) => (
                      <button
                        key={pos}
                        onClick={() => setWatermarkPosition(pos)}
                        className={`px-3 py-2 text-xs rounded-lg transition-colors ${
                          watermarkPosition === pos
                            ? 'bg-indigo-500 text-white'
                            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                        }`}
                      >
                        {pos.replace('-', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Opacity */}
                <div>
                  <label className="text-xs text-slate-400 block mb-2">
                    Opacity: {watermarkOpacity}%
                  </label>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    value={watermarkOpacity}
                    onChange={(e) => setWatermarkOpacity(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <p className="text-xs text-slate-500">
                  Watermark: "Made with visionary-suite.com"
                </p>
              </>
            )}

            <Button
              onClick={handleDownloadWithWatermark}
              disabled={downloading}
              className="w-full bg-indigo-500 hover:bg-indigo-600"
              data-testid="download-btn"
            >
              {downloading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  Download {watermarkEnabled ? 'with Watermark' : ''}
                </>
              )}
            </Button>
          </div>
        )}
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
