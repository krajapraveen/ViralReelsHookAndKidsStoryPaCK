import React, { useState } from 'react';
import { Star, AlertCircle, Send, X } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';

const RATING_REASONS = [
  { key: 'generation_failed', label: 'Generation failed or errored' },
  { key: 'poor_quality', label: 'Output quality was poor' },
  { key: 'too_slow', label: 'Generation was too slow' },
  { key: 'confusing_ui', label: 'Interface was confusing' },
  { key: 'credits_issue', label: 'Credits or payment issue' },
  { key: 'download_failed', label: 'Download failed' },
  { key: 'other', label: 'Other (please specify)' }
];

export default function RatingModal({ 
  isOpen, 
  onClose, 
  featureKey = null,
  relatedRequestId = null,
  onSubmitSuccess = () => {} 
}) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [reasonType, setReasonType] = useState('');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showReasonForm, setShowReasonForm] = useState(false);

  const handleStarClick = (value) => {
    setRating(value);
    if (value <= 2) {
      setShowReasonForm(true);
    } else {
      setShowReasonForm(false);
      setReasonType('');
      setComment('');
    }
  };

  const handleSubmit = async () => {
    if (rating === 0) {
      toast.error('Please select a rating');
      return;
    }

    // Validate mandatory feedback for low ratings
    if (rating <= 2) {
      if (!reasonType) {
        toast.error('Please select a reason for your feedback');
        return;
      }
      if (reasonType === 'other' && !comment.trim()) {
        toast.error('Please provide a comment explaining your feedback');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await api.post('/api/user-analytics/rating', {
        rating,
        feature_key: featureKey,
        reason_type: reasonType || null,
        comment: comment || null,
        related_request_id: relatedRequestId
      });
      
      toast.success('Thank you for your feedback!');
      onSubmitSuccess();
      onClose();
      
      // Reset state
      setRating(0);
      setReasonType('');
      setComment('');
      setShowReasonForm(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Rate Your Experience</h2>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stars */}
        <div className="flex justify-center gap-2 mb-6">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              key={value}
              onClick={() => handleStarClick(value)}
              onMouseEnter={() => setHoveredRating(value)}
              onMouseLeave={() => setHoveredRating(0)}
              className="transition-transform hover:scale-110"
              data-testid={`rating-star-${value}`}
            >
              <Star
                className={`w-10 h-10 ${
                  value <= (hoveredRating || rating)
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-slate-600'
                } transition-colors`}
              />
            </button>
          ))}
        </div>

        {/* Rating Label */}
        <p className="text-center text-slate-400 mb-6">
          {rating === 0 && 'Select a rating'}
          {rating === 1 && 'Very Poor'}
          {rating === 2 && 'Poor'}
          {rating === 3 && 'Average'}
          {rating === 4 && 'Good'}
          {rating === 5 && 'Excellent'}
        </p>

        {/* Mandatory Feedback Form for Low Ratings */}
        {showReasonForm && (
          <div className="space-y-4 mb-6 p-4 bg-slate-700/50 rounded-lg border border-slate-600">
            <div className="flex items-start gap-2 text-amber-400">
              <AlertCircle className="w-5 h-5 mt-0.5" />
              <p className="text-sm">
                We're sorry to hear that. Please help us improve by telling us what went wrong.
              </p>
            </div>

            {/* Reason Selection */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">
                What was the main issue? <span className="text-red-400">*</span>
              </label>
              <div className="space-y-2">
                {RATING_REASONS.map((reason) => (
                  <label
                    key={reason.key}
                    className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                      reasonType === reason.key
                        ? 'bg-amber-500/20 border border-amber-500/50'
                        : 'bg-slate-700 border border-slate-600 hover:border-slate-500'
                    }`}
                  >
                    <input
                      type="radio"
                      name="reason"
                      value={reason.key}
                      checked={reasonType === reason.key}
                      onChange={(e) => setReasonType(e.target.value)}
                      className="accent-amber-500"
                    />
                    <span className="text-sm text-white">{reason.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Comment Field */}
            {(reasonType === 'other' || reasonType) && (
              <div>
                <label className="block text-sm text-slate-300 mb-2">
                  Additional comments {reasonType === 'other' && <span className="text-red-400">*</span>}
                </label>
                <Textarea
                  placeholder="Please provide more details about your experience..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="bg-slate-700 border-slate-600 min-h-24"
                  data-testid="rating-comment-input"
                />
              </div>
            )}
          </div>
        )}

        {/* Optional Comment for Good Ratings */}
        {rating > 2 && rating > 0 && (
          <div className="mb-6">
            <label className="block text-sm text-slate-300 mb-2">
              Any comments? (optional)
            </label>
            <Textarea
              placeholder="Tell us what you liked..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="bg-slate-700 border-slate-600 min-h-20"
            />
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || rating === 0}
          className="w-full bg-amber-600 hover:bg-amber-700"
          data-testid="submit-rating-btn"
        >
          {isSubmitting ? (
            'Submitting...'
          ) : (
            <>
              <Send className="w-4 h-4 mr-2" /> Submit Feedback
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
