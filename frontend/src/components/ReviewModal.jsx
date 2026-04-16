import React, { useState, useEffect } from 'react';
import { Star, X, Send } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'sonner';

/**
 * Post-value review modal. Show after: video_completed, share_success, second_use.
 * Usage: <ReviewModal open={open} onClose={close} sourceEvent="video_completed" />
 */
export default function ReviewModal({ open, onClose, sourceEvent }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [hasExisting, setHasExisting] = useState(false);

  useEffect(() => {
    if (open) {
      api.get('/api/reviews/my-review').then(r => {
        if (r.data?.has_review) {
          setHasExisting(true);
          setRating(r.data.review?.rating || 0);
          setComment(r.data.review?.comment || '');
        }
      }).catch(() => {});
    }
  }, [open]);

  const submit = async () => {
    if (rating === 0) { toast.error('Please select a rating'); return; }
    setSubmitting(true);
    try {
      await api.post('/api/reviews/submit', { rating, comment: comment.trim() || null, message: comment.trim() || null, source_event: sourceEvent });
      setSubmitted(true);
      toast.success('Thanks for your review!');
      setTimeout(onClose, 1500);
    } catch {
      toast.error('Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm" data-testid="review-modal">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md mx-4 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-500 hover:text-white" data-testid="review-close">
          <X className="w-5 h-5" />
        </button>

        {submitted ? (
          <div className="text-center py-8" data-testid="review-success">
            <div className="text-4xl mb-3">&#10024;</div>
            <h3 className="text-lg font-bold text-white mb-1">Thank you!</h3>
            <p className="text-sm text-slate-400">Your review helps other creators discover Visionary Suite.</p>
          </div>
        ) : (
          <>
            <h3 className="text-lg font-bold text-white mb-1" data-testid="review-title">
              {hasExisting ? 'Update your review' : 'How was your experience?'}
            </h3>
            <p className="text-sm text-slate-400 mb-5">Your honest feedback helps us improve.</p>

            {/* Star rating */}
            <div className="flex items-center gap-1 mb-5" data-testid="review-stars">
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHover(star)}
                  onMouseLeave={() => setHover(0)}
                  className="transition-transform hover:scale-110"
                  data-testid={`review-star-${star}`}
                >
                  <Star
                    className={`w-8 h-8 transition-colors ${
                      star <= (hover || rating)
                        ? 'text-amber-400 fill-amber-400'
                        : 'text-slate-600'
                    }`}
                  />
                </button>
              ))}
              {rating > 0 && (
                <span className="text-sm text-amber-400 font-bold ml-2">{rating}/5</span>
              )}
            </div>

            {/* Comment */}
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="What did you create? Any feedback? (optional)"
              className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm text-white placeholder-slate-500 resize-none h-20 focus:outline-none focus:border-violet-500"
              maxLength={500}
              data-testid="review-comment"
            />
            <p className="text-[10px] text-slate-600 text-right mt-1">{comment.length}/500</p>

            <button
              onClick={submit}
              disabled={submitting || rating === 0}
              className="w-full mt-4 h-11 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-40"
              data-testid="review-submit"
            >
              <Send className="w-4 h-4" />
              {submitting ? 'Submitting...' : hasExisting ? 'Update Review' : 'Submit Review'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
