import React, { useState, useCallback, useEffect } from 'react';
import { X, Copy, Check, MessageCircle, Twitter, Share2, Play, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Post-Generation Share Modal
 *
 * Shows immediately after any story/creation generation completes.
 * Props:
 *   visible:       boolean
 *   onClose:       () => void
 *   generationId:  string        — the job/generation ID
 *   type:          string        — e.g., "STORY_VIDEO", "COMIC", etc.
 *   title:         string
 *   preview:       string        — story text or summary
 *   thumbnailUrl:  string|null
 *   storyContext:  string|null   — full story context for continuations
 *   characters:    string[]|null
 *   tone:          string|null
 *   conflict:      string|null
 */
export default function ShareModal({
  visible, onClose, generationId, type, title,
  preview, thumbnailUrl, storyContext, characters, tone, conflict
}) {
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);
  const [hookText, setHookText] = useState('');
  const [shareCaption, setShareCaption] = useState('');

  // Generate hook text and create share link on open
  useEffect(() => {
    if (!visible || !generationId) return;

    // Generate hook and caption from the content
    const hook = _generateHook(title, preview, characters);
    const caption = _generateCaption(title, hook);
    setHookText(hook);
    setShareCaption(caption);

    // Create the share link
    (async () => {
      setCreating(true);
      try {
        const res = await api.post('/api/share/create', {
          generationId,
          type: type || 'STORY',
          title,
          preview: preview?.slice(0, 500),
          thumbnailUrl,
          storyContext: storyContext || preview?.slice(0, 1000),
          characters: characters || [],
          tone,
          conflict,
          hookText: hook,
          shareCaption: caption,
        });
        if (res.data.success) {
          const url = `${window.location.origin}/share/${res.data.shareId}`;
          setShareUrl(url);
        }
      } catch {
        toast.error('Failed to create share link');
      } finally {
        setCreating(false);
      }
    })();
  }, [visible, generationId, type, title, preview, thumbnailUrl, storyContext, characters, tone, conflict]);

  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;
    const text = shareCaption ? `${shareCaption}\n${shareUrl}` : shareUrl;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Share link copied!');
    setTimeout(() => setCopied(false), 2000);
  }, [shareUrl, shareCaption]);

  const handleWhatsApp = useCallback(() => {
    if (!shareUrl) return;
    const text = `${shareCaption}\n${shareUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  }, [shareUrl, shareCaption]);

  const handleTwitter = useCallback(() => {
    if (!shareUrl) return;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareCaption)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
  }, [shareUrl, shareCaption]);

  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      data-testid="share-modal-overlay"
    >
      <div className="w-full max-w-md bg-[#0e0e1a] border border-white/[0.08] rounded-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200" data-testid="share-modal">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Share2 className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Your story is ready</h2>
              <p className="text-xs text-slate-400">Want others to continue it?</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors" data-testid="share-modal-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Story title */}
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <p className="text-sm font-semibold text-white mb-1 line-clamp-1">{title || 'Your Story'}</p>
            {hookText && (
              <p className="text-xs text-violet-300 italic">"{hookText}"</p>
            )}
          </div>

          {/* Auto-generated share message */}
          <div>
            <label className="text-[10px] font-bold tracking-wider uppercase text-slate-500 mb-1.5 block">Share Message</label>
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
              <p className="text-sm text-slate-300 leading-relaxed" data-testid="share-caption">
                {shareCaption}
              </p>
            </div>
          </div>

          {/* Share buttons */}
          {creating ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
              <span className="text-sm text-slate-400 ml-2">Creating share link...</span>
            </div>
          ) : shareUrl ? (
            <div className="space-y-3">
              {/* Primary: WhatsApp */}
              <Button
                onClick={handleWhatsApp}
                className="w-full h-12 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl"
                data-testid="modal-whatsapp-btn"
              >
                <MessageCircle className="w-5 h-5 mr-2" />
                Share on WhatsApp
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={handleTwitter}
                  variant="outline"
                  className="h-10 border-white/10 text-white hover:bg-sky-500/10 hover:border-sky-500/30 rounded-xl"
                  data-testid="modal-twitter-btn"
                >
                  <Twitter className="w-4 h-4 mr-1.5" /> Twitter
                </Button>
                <Button
                  onClick={handleCopy}
                  variant="outline"
                  className="h-10 border-white/10 text-white hover:bg-white/[0.06] rounded-xl"
                  data-testid="modal-copy-btn"
                >
                  {copied ? <Check className="w-4 h-4 mr-1.5 text-emerald-400" /> : <Copy className="w-4 h-4 mr-1.5" />}
                  {copied ? 'Copied!' : 'Copy Link'}
                </Button>
              </div>

              {/* Link display */}
              <div className="flex items-center gap-2 bg-black/30 border border-white/[0.06] rounded-lg px-3 py-2">
                <span className="text-xs text-slate-500 truncate flex-1 font-mono">{shareUrl}</span>
                <button onClick={handleCopy} className="text-violet-400 hover:text-violet-300">
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-5 pb-5">
          <button
            onClick={onClose}
            className="text-xs text-slate-500 hover:text-white transition-colors w-full text-center"
            data-testid="share-modal-skip"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}


// ─── Hook & caption generators (lightweight, no API call) ───────────────────

function _generateHook(title, preview, characters) {
  if (!preview && !title) return 'What happens next?';

  const charName = characters?.length > 0 ? characters[0] : null;
  const hooks = [
    charName ? `${charName} discovered something they weren't supposed to…` : null,
    title ? `"${title}" — but the ending hasn't been written yet.` : null,
    'What happens next is up to you.',
    'This story just reached its turning point…',
    preview?.length > 100 ? 'The story was just getting interesting…' : null,
  ].filter(Boolean);

  return hooks[Math.floor(Math.random() * hooks.length)] || 'What happens next?';
}

function _generateCaption(title, hook) {
  const captions = [
    `I started this story… can you finish it?\n\n"${hook}"`,
    `This story isn't finished yet. Continue it:\n\n"${title || 'Untitled'}"`,
    `What happens next? I need someone to continue this:\n\n"${hook}"`,
  ];
  return captions[Math.floor(Math.random() * captions.length)];
}
