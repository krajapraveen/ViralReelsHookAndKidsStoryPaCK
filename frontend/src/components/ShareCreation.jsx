import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { 
  Share2, Copy, Download, Twitter, Facebook, Linkedin, 
  MessageCircle, QrCode, Link, Mail, Check, Sparkles,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

// QR Code generator (simple implementation)
const generateQRCode = (text, size = 200) => {
  // Use a QR code API for simplicity
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(text)}&bgcolor=1e293b&color=a855f7`;
};

export default function ShareCreation({ 
  type, 
  title, 
  preview, 
  generationId,
  thumbnailUrl,
  contentType = 'creation'
}) {
  const [open, setOpen] = useState(false);
  const [shareData, setShareData] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && generationId) {
      createShareLink();
    }
  }, [open, generationId]);

  const createShareLink = async () => {
    setLoading(true);
    try {
      const res = await api.post('/api/share/create', {
        generationId,
        type,
        title,
        preview: preview?.substring(0, 200)
      });
      if (res.data.success) {
        setShareData(res.data);
      }
    } catch (error) {
      console.error('Failed to create share link:', error);
      // Fallback to local share data
      setShareData({
        shareUrl: `${window.location.origin}/share/${generationId}`,
        shareId: generationId
      });
    } finally {
      setLoading(false);
    }
  };

  const getShareUrl = () => {
    return shareData?.shareUrl || `${window.location.origin}/share/${generationId || 'demo'}`;
  };

  const getShareText = () => {
    const typeMap = {
      'REEL': 'viral reel script',
      'STORY': 'amazing story pack',
      'COMIC': 'comic masterpiece',
      'GIF': 'animated GIF',
      'COLORING_BOOK': 'coloring book',
      'STORYBOOK': 'comic storybook'
    };
    const contentName = typeMap[type] || 'AI creation';
    return `Check out this ${contentName} I made with CreatorStudio AI! "${title || 'My Creation'}"`;
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(getShareUrl());
    setCopied(true);
    toast.success('Link copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTwitterShare = () => {
    const text = encodeURIComponent(getShareText());
    const url = encodeURIComponent(getShareUrl());
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank', 'width=550,height=420');
  };

  const handleFacebookShare = () => {
    const url = encodeURIComponent(getShareUrl());
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`, '_blank', 'width=550,height=420');
  };

  const handleLinkedInShare = () => {
    const url = encodeURIComponent(getShareUrl());
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, '_blank', 'width=550,height=420');
  };

  const handleWhatsAppShare = () => {
    const text = encodeURIComponent(`${getShareText()}\n\n${getShareUrl()}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const handleEmailShare = () => {
    const subject = encodeURIComponent(`Check out my ${type || 'creation'} - ${title || 'My Creation'}`);
    const body = encodeURIComponent(`${getShareText()}\n\nView it here: ${getShareUrl()}\n\nCreate your own at ${window.location.origin}`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
  };

  const handleDownloadCard = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext('2d');

    // Gradient background
    const gradient = ctx.createLinearGradient(0, 0, 1200, 630);
    gradient.addColorStop(0, '#1e1b4b');
    gradient.addColorStop(0.5, '#312e81');
    gradient.addColorStop(1, '#1e1b4b');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 1200, 630);

    // Add pattern overlay
    ctx.fillStyle = 'rgba(168, 85, 247, 0.05)';
    for (let i = 0; i < 20; i++) {
      ctx.beginPath();
      ctx.arc(Math.random() * 1200, Math.random() * 630, Math.random() * 100 + 20, 0, Math.PI * 2);
      ctx.fill();
    }

    // Type emoji and title
    const typeEmoji = {
      'REEL': '🎬',
      'STORY': '📖',
      'COMIC': '💥',
      'GIF': '✨',
      'COLORING_BOOK': '🎨',
      'STORYBOOK': '📚'
    };
    
    ctx.font = 'bold 72px system-ui';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(typeEmoji[type] || '✨', 60, 120);
    
    ctx.font = 'bold 48px system-ui';
    ctx.fillText(title || 'My AI Creation', 60, 200);

    // Preview text
    if (preview) {
      ctx.font = '28px system-ui';
      ctx.fillStyle = '#c4b5fd';
      const lines = preview.substring(0, 150).match(/.{1,40}/g) || [];
      lines.slice(0, 4).forEach((line, i) => {
        ctx.fillText(line, 60, 280 + (i * 40));
      });
    }

    // Branding
    ctx.fillStyle = '#a855f7';
    ctx.fillRect(60, 520, 200, 4);
    ctx.font = 'bold 24px system-ui';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('CreatorStudio AI', 60, 570);
    ctx.font = '18px system-ui';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Create yours free at creatorstudio.ai', 60, 600);

    // Download
    const link = document.createElement('a');
    link.download = `share-${type?.toLowerCase() || 'creation'}-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    toast.success('Share card downloaded!');
  };

  const socialButtons = [
    { name: 'WhatsApp', icon: MessageCircle, handler: handleWhatsAppShare, color: 'hover:bg-green-500/20 hover:border-green-400 hover:text-green-400' },
    { name: 'Twitter', icon: Twitter, handler: handleTwitterShare, color: 'hover:bg-sky-500/20 hover:border-sky-400 hover:text-sky-400' },
    { name: 'Facebook', icon: Facebook, handler: handleFacebookShare, color: 'hover:bg-blue-500/20 hover:border-blue-400 hover:text-blue-400' },
    { name: 'LinkedIn', icon: Linkedin, handler: handleLinkedInShare, color: 'hover:bg-blue-600/20 hover:border-blue-500 hover:text-blue-500' },
    { name: 'Email', icon: Mail, handler: handleEmailShare, color: 'hover:bg-purple-500/20 hover:border-purple-400 hover:text-purple-400' },
  ];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button 
          variant="outline" 
          size="sm" 
          className="gap-2 border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" 
          data-testid="share-creation-btn"
        >
          <Share2 className="w-4 h-4" />
          Share
        </Button>
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-lg bg-gradient-to-br from-slate-900 via-indigo-950/80 to-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white text-xl flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            Share Your Creation
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-5">
          {/* Preview Card */}
          <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl p-4 border border-purple-500/30">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center text-3xl shadow-lg">
                {type === 'REEL' ? '🎬' : type === 'STORY' ? '📖' : type === 'COMIC' ? '💥' : type === 'GIF' ? '✨' : type === 'COLORING_BOOK' ? '🎨' : '📚'}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-white truncate">{title || 'My AI Creation'}</h3>
                <p className="text-sm text-slate-400 truncate">{preview?.substring(0, 50) || 'Created with CreatorStudio AI'}</p>
                <p className="text-xs text-purple-400 mt-1">CreatorStudio AI</p>
              </div>
            </div>
          </div>

          {/* Share Link with Copy */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Share Link</label>
            <div className="flex gap-2">
              <div className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 truncate">
                {loading ? 'Generating...' : getShareUrl()}
              </div>
              <Button
                onClick={handleCopyLink}
                className={`px-4 transition-all ${copied ? 'bg-green-600 hover:bg-green-700' : 'bg-purple-600 hover:bg-purple-700'}`}
                data-testid="copy-share-link"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
          </div>

          {/* Social Share Buttons */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Share on Social Media</label>
            <div className="flex gap-2 justify-center flex-wrap">
              {socialButtons.map((btn) => (
                <Button
                  key={btn.name}
                  onClick={btn.handler}
                  size="icon"
                  className={`rounded-full w-12 h-12 bg-slate-800 border border-slate-700 text-slate-300 transition-all duration-200 ${btn.color}`}
                  data-testid={`share-${btn.name.toLowerCase()}`}
                  title={btn.name}
                >
                  <btn.icon className="w-5 h-5" />
                </Button>
              ))}
            </div>
          </div>

          {/* QR Code */}
          <div className="flex items-center justify-between bg-slate-800/30 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-3">
              <QrCode className="w-5 h-5 text-purple-400" />
              <div>
                <p className="text-sm font-medium text-white">QR Code</p>
                <p className="text-xs text-slate-400">Scan to view on mobile</p>
              </div>
            </div>
            <img 
              src={generateQRCode(getShareUrl(), 80)} 
              alt="QR Code" 
              className="w-16 h-16 rounded-lg bg-slate-900 p-1"
            />
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <Button 
              onClick={handleDownloadCard} 
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
              data-testid="download-share-card"
            >
              <Download className="w-4 h-4 mr-2" />
              Download Card
            </Button>
            <Button 
              onClick={() => window.open(getShareUrl(), '_blank')}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-800"
              data-testid="preview-share-page"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              Preview Page
            </Button>
          </div>

          <p className="text-xs text-slate-500 text-center">
            Share links are valid for 30 days. Showcase your AI-powered creation!
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
