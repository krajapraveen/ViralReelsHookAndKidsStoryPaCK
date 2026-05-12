import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Sparkles, Download, Copy, Play } from 'lucide-react';
import { Button } from './ui/button';

/**
 * BedtimePaywallModal — P0 2026-05
 *
 * Shown when a free user attempts to:
 *   - continue playback past the preview scene
 *   - download a story
 *   - copy a story
 *
 * Backend already truncates the payload server-side; this modal is the UX
 * conversion surface, not the security layer.
 */
export default function BedtimePaywallModal({ open, onClose, reason }) {
  const navigate = useNavigate();
  if (!open) return null;

  const headlines = {
    play: {
      icon: Play,
      title: 'Continue the story',
      body: 'You just heard the opening scene. Subscribe to unlock the full bedtime adventure, every night.',
    },
    download: {
      icon: Download,
      title: 'Download requires a subscription',
      body: 'Save your stories as text or PDF — available on any paid plan.',
    },
    copy: {
      icon: Copy,
      title: 'Copying requires a subscription',
      body: 'Subscribers can copy the full narration text for personal use.',
    },
    default: {
      icon: Lock,
      title: 'Subscribe to unlock the full story',
      body: 'Play to the end, download, copy, and remix — all unlocked on any paid plan.',
    },
  };

  const cfg = headlines[reason] || headlines.default;
  const Icon = cfg.icon;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      data-testid="bedtime-paywall-modal"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md bg-gradient-to-br from-slate-900 via-indigo-950/80 to-slate-900 border border-indigo-500/30 rounded-2xl p-6 sm:p-8 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-slate-500 hover:text-white text-xl leading-none"
          aria-label="Close"
          data-testid="bedtime-paywall-close"
        >
          ×
        </button>

        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 mb-4 mx-auto">
          <Icon className="w-7 h-7 text-indigo-300" />
        </div>

        <h3 className="text-xl sm:text-2xl font-bold text-white text-center mb-2" data-testid="bedtime-paywall-title">
          {cfg.title}
        </h3>
        <p className="text-sm text-slate-400 text-center mb-6 leading-relaxed">
          {cfg.body}
        </p>

        <ul className="space-y-2 mb-6 text-sm text-slate-300">
          <li className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>Full multi-scene narration with voice playback</span>
          </li>
          <li className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>Download as text & PDF, copy to anywhere</span>
          </li>
          <li className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>Daily streak rewards & unlimited remixes</span>
          </li>
        </ul>

        <div className="flex flex-col sm:flex-row gap-2">
          <Button
            className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold py-5 rounded-xl hover:opacity-90"
            onClick={() => navigate('/pricing')}
            data-testid="bedtime-paywall-cta"
          >
            See plans
          </Button>
          <Button
            variant="outline"
            className="flex-1 border-slate-700 text-slate-400 hover:text-white py-5 rounded-xl"
            onClick={onClose}
            data-testid="bedtime-paywall-dismiss"
          >
            Maybe later
          </Button>
        </div>
      </div>
    </div>
  );
}
