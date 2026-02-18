import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Share2, Copy, Download, Twitter, Facebook, Linkedin, MessageCircle } from 'lucide-react';
import { toast } from 'sonner';

export default function ShareButton({ type, title, preview }) {
  const [open, setOpen] = useState(false);

  const generateShareImage = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext('2d');

    // Background gradient
    const gradient = ctx.createLinearGradient(0, 0, 1200, 630);
    gradient.addColorStop(0, '#6366f1');
    gradient.addColorStop(1, '#8b5cf6');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 1200, 630);

    // Overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, 1200, 630);

    // Content
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 48px Inter';
    ctx.fillText(type === 'REEL' ? '🎬 Viral Reel Script' : '📖 Kids Story Pack', 60, 100);

    ctx.font = '32px Inter';
    ctx.fillText(title || 'Generated with CreatorStudio AI', 60, 160);

    // Preview text
    if (preview) {
      ctx.font = '24px Inter';
      ctx.fillStyle = '#e0e0e0';
      const lines = preview.substring(0, 200).match(/.{1,50}/g) || [];
      lines.slice(0, 8).forEach((line, i) => {
        ctx.fillText(line, 60, 220 + (i * 40));
      });
    }

    // Branding
    ctx.font = 'bold 28px Inter';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('✨ CreatorStudio AI', 60, 580);

    return canvas.toDataURL('image/png');
  };

  const handleDownloadShare = () => {
    const dataUrl = generateShareImage();
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `creatorstudio-${type.toLowerCase()}-${Date.now()}.png`;
    a.click();
    toast.success('Share card downloaded!');
  };

  const handleCopyLink = () => {
    const shareText = `I just created an amazing ${type === 'REEL' ? 'reel script' : 'story pack'} with CreatorStudio AI! 🚀\n\nGenerate yours: ${window.location.origin}`;
    navigator.clipboard.writeText(shareText);
    toast.success('Share text copied to clipboard!');
  };

  const getShareText = () => {
    return `I just created an amazing ${type === 'REEL' ? 'reel script' : 'story pack'} with CreatorStudio AI! 🚀`;
  };

  const getShareUrl = () => {
    return window.location.origin;
  };

  const handleTwitterShare = () => {
    const text = encodeURIComponent(getShareText());
    const url = encodeURIComponent(getShareUrl());
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank', 'width=550,height=420');
    toast.success('Opening Twitter...');
  };

  const handleFacebookShare = () => {
    const url = encodeURIComponent(getShareUrl());
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`, '_blank', 'width=550,height=420');
    toast.success('Opening Facebook...');
  };

  const handleLinkedInShare = () => {
    const url = encodeURIComponent(getShareUrl());
    const text = encodeURIComponent(getShareText());
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, '_blank', 'width=550,height=420');
    toast.success('Opening LinkedIn...');
  };

  const handleWhatsAppShare = () => {
    const text = encodeURIComponent(`${getShareText()}\n\nGenerate yours: ${getShareUrl()}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
    toast.success('Opening WhatsApp...');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2 border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" data-testid="share-btn">
          <Share2 className="w-4 h-4" />
          Share
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white text-xl">Share Your Creation</DialogTitle>
        </DialogHeader>
        <div className="space-y-5">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="aspect-video bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <div className="text-center p-6">
                <div className="text-4xl font-bold mb-2">
                  {type === 'REEL' ? '🎬' : '📖'}
                </div>
                <div className="font-bold text-lg">
                  {type === 'REEL' ? 'Viral Reel Script' : 'Kids Story Pack'}
                </div>
                <div className="text-sm mt-2 opacity-90">Generated with CreatorStudio AI</div>
              </div>
            </div>
          </div>

          {/* Social Media Share Buttons */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-300">Share on social media</p>
            <div className="flex gap-3 justify-center">
              <Button 
                onClick={handleTwitterShare} 
                size="icon" 
                className="rounded-full w-12 h-12 bg-slate-800 border border-slate-700 hover:bg-sky-500/20 hover:border-sky-400 text-slate-300 hover:text-sky-400 transition-all duration-200"
                data-testid="share-twitter"
              >
                <Twitter className="w-5 h-5" />
              </Button>
              <Button 
                onClick={handleFacebookShare} 
                size="icon" 
                className="rounded-full w-12 h-12 bg-slate-800 border border-slate-700 hover:bg-blue-500/20 hover:border-blue-400 text-slate-300 hover:text-blue-400 transition-all duration-200"
                data-testid="share-facebook"
              >
                <Facebook className="w-5 h-5" />
              </Button>
              <Button 
                onClick={handleLinkedInShare} 
                size="icon" 
                className="rounded-full w-12 h-12 bg-slate-800 border border-slate-700 hover:bg-blue-600/20 hover:border-blue-500 text-slate-300 hover:text-blue-500 transition-all duration-200"
                data-testid="share-linkedin"
              >
                <Linkedin className="w-5 h-5" />
              </Button>
              <Button 
                onClick={handleWhatsAppShare} 
                size="icon" 
                className="rounded-full w-12 h-12 bg-slate-800 border border-slate-700 hover:bg-green-500/20 hover:border-green-400 text-slate-300 hover:text-green-400 transition-all duration-200"
                data-testid="share-whatsapp"
              >
                <MessageCircle className="w-5 h-5" />
              </Button>
            </div>
          </div>

          <div className="flex gap-3">
            <Button onClick={handleDownloadShare} className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium" data-testid="download-share-img">
              <Download className="w-4 h-4 mr-2" />
              Download Card
            </Button>
            <Button onClick={handleCopyLink} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium" data-testid="copy-share-link">
              <Copy className="w-4 h-4 mr-2" />
              Copy Link
            </Button>
          </div>

          <p className="text-xs text-slate-400 text-center">
            Showcase your AI-powered creation! ✨
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
