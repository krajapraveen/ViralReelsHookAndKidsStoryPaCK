import { useState, useCallback } from 'react';
import { X, Star, ThumbsUp, ThumbsDown, Send, SkipForward } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ensureSessionId,
  getUsedFeatures,
  markFeedbackSubmitted,
  markFeedbackPromptShown,
} from '../utils/feedbackSession';

const API = process.env.REACT_APP_BACKEND_URL;

const RATINGS = [
  { value: 'great', label: 'Great', color: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20' },
  { value: 'good', label: 'Good', color: 'text-blue-400 border-blue-500/40 bg-blue-500/10 hover:bg-blue-500/20' },
  { value: 'okay', label: 'Okay', color: 'text-amber-400 border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20' },
  { value: 'poor', label: 'Poor', color: 'text-red-400 border-red-500/40 bg-red-500/10 hover:bg-red-500/20' },
];

const REUSE_OPTIONS = [
  { value: 'yes', label: 'Yes' },
  { value: 'maybe', label: 'Maybe' },
  { value: 'no', label: 'No' },
];

export default function FeedbackModal({ isOpen, onClose, onSubmitDone, source = 'logout_prompt', idleSeconds = 0 }) {
  const [rating, setRating] = useState('');
  const [liked, setLiked] = useState('');
  const [improvements, setImprovements] = useState('');
  const [reuseIntent, setReuseIntent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!rating) { toast.error('Please select a rating'); return; }
    if (!improvements || improvements.trim().length < 3) { toast.error('Please tell us what needs improvement'); return; }
    if (!reuseIntent) { toast.error('Please tell us if you would use this again'); return; }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/feedback/experience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          rating,
          liked,
          improvements: improvements.trim(),
          reuse_intent: reuseIntent,
          feature_context: getUsedFeatures(),
          session_id: ensureSessionId(),
          source,
          meta: {
            browser: navigator.userAgent.slice(0, 200),
            device: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
            credits_remaining: 0,
            idle_seconds: idleSeconds,
          },
        }),
      });
      const data = await res.json();
      if (data.success) {
        markFeedbackSubmitted();
        toast.success('Thanks for your feedback!');
        onSubmitDone?.();
      } else {
        toast.error(data.message || 'Failed to submit');
      }
    } catch (err) {
      console.error('Feedback submit error:', err);
      toast.error('Could not submit feedback');
    } finally {
      setSubmitting(false);
      onClose();
    }
  }, [rating, liked, improvements, reuseIntent, source, idleSeconds, onClose, onSubmitDone]);

  const handleSkip = () => {
    markFeedbackPromptShown();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="feedback-modal-overlay">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden" data-testid="feedback-modal">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white" data-testid="feedback-modal-title">How was your experience?</h2>
            <p className="text-xs text-slate-400 mt-0.5">What worked well, and what should we improve?</p>
          </div>
          <button onClick={handleSkip} className="p-1.5 text-slate-500 hover:text-white rounded-lg hover:bg-slate-800 transition-colors" data-testid="feedback-close-btn">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[60vh] overflow-y-auto">
          {/* Rating */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-2 block">Overall experience *</label>
            <div className="grid grid-cols-4 gap-2">
              {RATINGS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => setRating(r.value)}
                  className={`px-3 py-2 rounded-xl text-sm font-medium border transition-all ${rating === r.value ? r.color + ' ring-1 ring-current' : 'border-slate-700 text-slate-400 hover:border-slate-600'}`}
                  data-testid={`feedback-rating-${r.value}`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Liked */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-1.5 block">What did you like?</label>
            <textarea
              value={liked}
              onChange={(e) => setLiked(e.target.value)}
              placeholder="Fast generation, easy to use..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm text-white placeholder-slate-500 resize-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              rows={2}
              data-testid="feedback-liked"
            />
          </div>

          {/* Improvements */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-1.5 block">What needs improvement? *</label>
            <textarea
              value={improvements}
              onChange={(e) => setImprovements(e.target.value)}
              placeholder="Speed, progress indicators, quality..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm text-white placeholder-slate-500 resize-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              rows={3}
              data-testid="feedback-improvements"
            />
          </div>

          {/* Reuse */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-2 block">Would you use this again? *</label>
            <div className="flex gap-2">
              {REUSE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  onClick={() => setReuseIntent(o.value)}
                  className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium border transition-all ${reuseIntent === o.value ? 'border-indigo-500 bg-indigo-500/15 text-indigo-300' : 'border-slate-700 text-slate-400 hover:border-slate-600'}`}
                  data-testid={`feedback-reuse-${o.value}`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 p-5 border-t border-slate-800">
          <Button
            onClick={handleSkip}
            variant="ghost"
            className="flex-1 text-slate-400 hover:text-white"
            data-testid="feedback-skip-btn"
          >
            <SkipForward className="w-4 h-4 mr-1.5" /> Skip
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white"
            data-testid="feedback-submit-btn"
          >
            <Send className="w-4 h-4 mr-1.5" /> {submitting ? 'Sending...' : 'Submit'}
          </Button>
        </div>
      </div>
    </div>
  );
}
