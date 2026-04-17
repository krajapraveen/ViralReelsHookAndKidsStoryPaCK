import React from 'react';
import { Share2, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';

/**
 * One-tap share buttons — WhatsApp, Instagram, X, Facebook, Copy Link.
 * Used on: PublicCreation, StoryPreview, ShareModal, Dashboard cards.
 * 
 * Props:
 *  - url: string (share URL)
 *  - title: string (share text)
 *  - compact: boolean (smaller buttons for inline use)
 */
export default function ShareButtons({ url, title = '', compact = false }) {
  const [copied, setCopied] = React.useState(false);
  const shareUrl = url || window.location.href;
  const shareText = title ? `${title} — Made with Visionary Suite` : 'Check out this AI-generated story!';
  const encodedUrl = encodeURIComponent(shareUrl);
  const encodedText = encodeURIComponent(shareText);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('Link copied!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: shareText, url: shareUrl });
      } catch { /* user cancelled */ }
    }
  };

  const channels = [
    {
      name: 'WhatsApp',
      color: 'bg-[#25D366]/20 text-[#25D366] border-[#25D366]/20 hover:bg-[#25D366]/30',
      href: `https://wa.me/?text=${encodedText}%20${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className={compact ? 'w-4 h-4' : 'w-5 h-5'}>
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
        </svg>
      ),
    },
    {
      name: 'X',
      color: 'bg-white/10 text-white border-white/10 hover:bg-white/20',
      href: `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'}>
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      ),
    },
    {
      name: 'Facebook',
      color: 'bg-[#1877F2]/20 text-[#1877F2] border-[#1877F2]/20 hover:bg-[#1877F2]/30',
      href: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor" className={compact ? 'w-4 h-4' : 'w-5 h-5'}>
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>
      ),
    },
  ];

  const btnSize = compact ? 'h-9 px-3 text-xs gap-1.5' : 'h-11 px-4 text-sm gap-2';
  const iconBtnSize = compact ? 'h-9 w-9' : 'h-11 w-11';

  return (
    <div className={`flex items-center ${compact ? 'gap-1.5' : 'gap-2'} flex-wrap`} data-testid="share-buttons">
      {/* Native share (mobile) */}
      {typeof navigator !== 'undefined' && navigator.share && (
        <button
          onClick={handleNativeShare}
          className={`${iconBtnSize} rounded-xl border bg-violet-500/20 text-violet-400 border-violet-500/20 hover:bg-violet-500/30 flex items-center justify-center transition-colors`}
          data-testid="share-native"
          aria-label="Share"
        >
          <Share2 className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
        </button>
      )}

      {/* Channel buttons */}
      {channels.map((ch) => (
        <a
          key={ch.name}
          href={ch.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`${btnSize} rounded-xl border ${ch.color} font-medium flex items-center justify-center transition-colors`}
          data-testid={`share-${ch.name.toLowerCase()}`}
        >
          {ch.icon}
          <span className="hidden sm:inline">{ch.name}</span>
        </a>
      ))}

      {/* Copy link */}
      <button
        onClick={handleCopy}
        className={`${btnSize} rounded-xl border border-white/10 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] font-medium flex items-center justify-center transition-colors`}
        data-testid="share-copy"
      >
        {copied ? <Check className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'} /> : <Copy className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'} />}
        <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy Link'}</span>
      </button>
    </div>
  );
}
