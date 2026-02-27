import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Sparkles, Download, ExternalLink, Twitter, Facebook, 
  Linkedin, MessageCircle, Copy, Check, Loader2, 
  AlertCircle, ArrowRight, Star
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

export default function SharePage() {
  const { shareId } = useParams();
  const [shareData, setShareData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchShareData();
  }, [shareId]);

  const fetchShareData = async () => {
    try {
      const res = await api.get(`/api/share/${shareId}`);
      if (res.data.success) {
        setShareData(res.data);
      } else {
        setError('Share link not found or expired');
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError('This share link has expired or does not exist');
      } else {
        setError('Failed to load shared content');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSocialShare = (platform) => {
    const url = encodeURIComponent(window.location.href);
    const text = encodeURIComponent(`Check out this amazing ${shareData?.type || 'creation'} made with CreatorStudio AI!`);
    
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${url}`,
      whatsapp: `https://wa.me/?text=${text}%20${url}`
    };
    
    window.open(urls[platform], '_blank', 'width=550,height=420');
  };

  const getTypeEmoji = (type) => {
    const emojis = {
      'REEL': '🎬',
      'STORY': '📖',
      'COMIC': '💥',
      'GIF': '✨',
      'COLORING_BOOK': '🎨',
      'STORYBOOK': '📚'
    };
    return emojis[type] || '✨';
  };

  const getTypeName = (type) => {
    const names = {
      'REEL': 'Viral Reel Script',
      'STORY': 'Kids Story Pack',
      'COMIC': 'AI Comic',
      'GIF': 'Animated GIF',
      'COLORING_BOOK': 'Coloring Book',
      'STORYBOOK': 'Comic Storybook'
    };
    return names[type] || 'AI Creation';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading shared content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-10 h-10 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Link Not Found</h1>
          <p className="text-slate-400 mb-6">{error}</p>
          <Link to="/">
            <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
              Create Your Own
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">CreatorStudio AI</span>
          </Link>
          <Link to="/signup">
            <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700" data-testid="create-own-btn">
              Create Yours Free
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Title Section */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 px-4 py-2 rounded-full text-sm mb-4">
            <Star className="w-4 h-4" />
            <span>Shared Creation</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-4">
            {shareData.title || 'Untitled Creation'}
          </h1>
          <p className="text-slate-400">
            {getTypeName(shareData.type)} created with AI
          </p>
        </div>

        {/* Content Card */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl overflow-hidden mb-8">
          {/* Type Badge */}
          <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border-b border-slate-700/50 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center text-2xl shadow-lg">
                {getTypeEmoji(shareData.type)}
              </div>
              <div>
                <h2 className="font-semibold text-white">{getTypeName(shareData.type)}</h2>
                <p className="text-sm text-slate-400">Generated with AI</p>
              </div>
            </div>
          </div>

          {/* Preview Content */}
          <div className="p-6">
            {shareData.thumbnailUrl && (
              <div className="mb-6">
                <img 
                  src={shareData.thumbnailUrl} 
                  alt={shareData.title} 
                  className="w-full rounded-xl border border-slate-700"
                />
              </div>
            )}
            
            {shareData.preview && (
              <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
                <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {shareData.preview}
                </p>
              </div>
            )}
          </div>

          {/* Stats */}
          {shareData.views && (
            <div className="border-t border-slate-700/50 px-6 py-3 bg-slate-900/30">
              <p className="text-xs text-slate-500">
                Viewed {shareData.views} times • Shared on {new Date(shareData.createdAt).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        {/* Share Actions */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6 mb-8">
          <h3 className="font-semibold text-white mb-4">Share this creation</h3>
          
          {/* Copy Link */}
          <div className="flex gap-2 mb-4">
            <div className="flex-1 bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-400 truncate">
              {window.location.href}
            </div>
            <Button
              onClick={handleCopyLink}
              className={copied ? 'bg-green-600' : 'bg-purple-600 hover:bg-purple-700'}
              data-testid="copy-link-btn"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </Button>
          </div>

          {/* Social Buttons */}
          <div className="flex gap-3 justify-center">
            <Button
              onClick={() => handleSocialShare('whatsapp')}
              size="icon"
              className="rounded-full w-12 h-12 bg-slate-700 hover:bg-green-500/20 hover:text-green-400"
              data-testid="share-whatsapp"
            >
              <MessageCircle className="w-5 h-5" />
            </Button>
            <Button
              onClick={() => handleSocialShare('twitter')}
              size="icon"
              className="rounded-full w-12 h-12 bg-slate-700 hover:bg-sky-500/20 hover:text-sky-400"
              data-testid="share-twitter"
            >
              <Twitter className="w-5 h-5" />
            </Button>
            <Button
              onClick={() => handleSocialShare('facebook')}
              size="icon"
              className="rounded-full w-12 h-12 bg-slate-700 hover:bg-blue-500/20 hover:text-blue-400"
              data-testid="share-facebook"
            >
              <Facebook className="w-5 h-5" />
            </Button>
            <Button
              onClick={() => handleSocialShare('linkedin')}
              size="icon"
              className="rounded-full w-12 h-12 bg-slate-700 hover:bg-blue-600/20 hover:text-blue-500"
              data-testid="share-linkedin"
            >
              <Linkedin className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-2xl p-8 text-center">
          <h3 className="text-2xl font-bold text-white mb-3">
            Want to create your own?
          </h3>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
            Join thousands of creators using AI to generate viral content, stories, comics, and more!
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link to="/signup">
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 px-8" data-testid="signup-cta">
                Start Creating Free
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
            <Link to="/pricing">
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800">
                View Pricing
              </Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 mt-12 py-6">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-sm text-slate-500">
            Created with <span className="text-purple-400">CreatorStudio AI</span> • 
            <Link to="/privacy-policy" className="text-slate-400 hover:text-white ml-2">Privacy</Link> • 
            <Link to="/contact" className="text-slate-400 hover:text-white ml-2">Contact</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
