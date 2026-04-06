import React, { useState } from 'react';
import { Share2, Copy, Check, X, Sparkles, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SharePromptModal({ jobId, title, characterName, slug, onClose }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = slug ? `${window.location.origin}/v/${slug}` : '';
  const shareText = characterName
    ? `I just created "${title}" starring ${characterName} with AI in seconds! Continue the story:`
    : `I just created "${title}" with AI in seconds! See what happens next:`;

  const shareTo = (platform) => {
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
    };
    if (urls[platform]) window.open(urls[platform], '_blank', 'width=600,height=400');
    try {
      fetch(`${API}/api/growth/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: 'share_click',
          session_id: sessionStorage.getItem('growth_session_id') || 'unknown',
          meta: { platform, source: 'auto_share_prompt', job_id: jobId },
        }),
      }).catch(() => {});
    } catch {}
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('Link copied!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  if (!slug) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="share-prompt-modal">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#0d0d18] border border-white/10 rounded-2xl max-w-sm w-full p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 text-slate-500 hover:text-white" data-testid="share-prompt-close">
          <X className="w-4 h-4" />
        </button>

        <div className="text-center mb-5">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-rose-500/20 flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6 text-violet-400" />
          </div>
          <h3 className="text-lg font-bold text-white" data-testid="share-prompt-title">
            {characterName ? `${characterName}'s story is ready!` : 'Your creation is ready!'}
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Share it and let others continue the story
          </p>
        </div>

        <div className="space-y-2 mb-4">
          {[
            { id: 'whatsapp', label: 'Send via Message', color: 'bg-emerald-600 hover:bg-emerald-500' },
            { id: 'twitter', label: 'Post Online', color: 'bg-slate-700 hover:bg-slate-600' },
            { id: 'linkedin', label: 'Share Professionally', color: 'bg-blue-700 hover:bg-blue-600' },
          ].map(p => (
            <button
              key={p.id}
              onClick={() => shareTo(p.id)}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium text-white transition-colors ${p.color}`}
              data-testid={`share-prompt-${p.id}`}
            >
              <span>{p.label}</span>
              <ChevronRight className="w-4 h-4 text-white/50" />
            </button>
          ))}
        </div>

        <button
          onClick={copyLink}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium text-slate-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
          data-testid="share-prompt-copy"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy link'}
        </button>

        <p className="text-center text-[10px] text-slate-600 mt-4">
          Every share helps {characterName || 'your story'} reach more creators
        </p>
      </div>
    </div>
  );
}
