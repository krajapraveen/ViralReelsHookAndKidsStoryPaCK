import React, { useState } from 'react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Textarea } from './ui/textarea';
import api from '../utils/api';
import { toast } from 'sonner';
import { MessageSquarePlus, Star, Send, Loader2, Lightbulb, ThumbsUp, Zap, X } from 'lucide-react';

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState({
    rating: 0,
    category: '',
    suggestion: '',
    email: ''
  });

  const categories = [
    { id: 'feature', label: 'New Feature', icon: Lightbulb, color: 'bg-yellow-100 text-yellow-700 border-yellow-300' },
    { id: 'improvement', label: 'Improvement', icon: Zap, color: 'bg-blue-100 text-blue-700 border-blue-300' },
    { id: 'bug', label: 'Bug Report', icon: X, color: 'bg-red-100 text-red-700 border-red-300' },
    { id: 'praise', label: 'Praise', icon: ThumbsUp, color: 'bg-green-100 text-green-700 border-green-300' }
  ];

  const handleSubmit = async () => {
    if (!feedback.suggestion.trim()) {
      toast.error('Please share your thoughts with us');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/feedback/suggestion', {
        rating: feedback.rating,
        category: feedback.category,
        suggestion: feedback.suggestion,
        email: feedback.email
      });
      
      toast.success('Thank you for your feedback! We truly appreciate it. 💜');
      setIsOpen(false);
      setStep(1);
      setFeedback({ rating: 0, category: '', suggestion: '', email: '' });
    } catch (error) {
      toast.error('Failed to submit feedback. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderStars = () => (
    <div className="flex gap-2 justify-center">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => setFeedback({ ...feedback, rating: star })}
          className={`p-2 rounded-full transition-all transform hover:scale-110 ${
            feedback.rating >= star 
              ? 'text-yellow-400 scale-110' 
              : 'text-gray-300 hover:text-yellow-300'
          }`}
        >
          <Star className={`w-8 h-8 ${feedback.rating >= star ? 'fill-current' : ''}`} />
        </button>
      ))}
    </div>
  );

  return (
    <>
      {/* Floating Feedback Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-24 right-6 w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full shadow-lg hover:shadow-xl transition-all flex items-center justify-center text-white z-40 group hover:scale-105"
        data-testid="feedback-toggle"
        title="Share your feedback"
      >
        <MessageSquarePlus className="w-5 h-5 group-hover:scale-110 transition-transform" />
      </button>

      {/* Feedback Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-xl">
              {step === 1 && "How can we improve? 💡"}
              {step === 2 && "Tell us more"}
              {step === 3 && "Almost done!"}
            </DialogTitle>
            <DialogDescription className="text-center">
              {step === 1 && "Your feedback helps us build a better product"}
              {step === 2 && "Share your ideas, suggestions, or concerns"}
              {step === 3 && "Optional: Leave your email for updates"}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {/* Step 1: Rating & Category */}
            {step === 1 && (
              <div className="space-y-6">
                <div>
                  <p className="text-sm text-slate-600 text-center mb-3">How's your experience so far?</p>
                  {renderStars()}
                  {feedback.rating > 0 && (
                    <p className="text-center text-sm text-slate-500 mt-2">
                      {feedback.rating <= 2 && "We're sorry to hear that. Let's fix this!"}
                      {feedback.rating === 3 && "Thanks! How can we make it better?"}
                      {feedback.rating >= 4 && "Awesome! We'd love to hear more!"}
                    </p>
                  )}
                </div>

                <div>
                  <p className="text-sm text-slate-600 text-center mb-3">What would you like to share?</p>
                  <div className="grid grid-cols-2 gap-3">
                    {categories.map((cat) => {
                      const Icon = cat.icon;
                      return (
                        <button
                          key={cat.id}
                          onClick={() => setFeedback({ ...feedback, category: cat.id })}
                          className={`p-3 rounded-lg border-2 transition-all ${
                            feedback.category === cat.id
                              ? cat.color + ' border-current'
                              : 'bg-white border-slate-200 hover:border-slate-300'
                          }`}
                        >
                          <Icon className="w-5 h-5 mx-auto mb-1" />
                          <span className="text-sm font-medium">{cat.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <Button 
                  onClick={() => setStep(2)} 
                  disabled={!feedback.category}
                  className="w-full bg-indigo-500 hover:bg-indigo-600"
                >
                  Continue
                </Button>
              </div>
            )}

            {/* Step 2: Suggestion Text */}
            {step === 2 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    {feedback.category === 'feature' && "What feature would you like to see?"}
                    {feedback.category === 'improvement' && "What could we improve?"}
                    {feedback.category === 'bug' && "What issue did you encounter?"}
                    {feedback.category === 'praise' && "What do you love about us?"}
                  </label>
                  <Textarea
                    value={feedback.suggestion}
                    onChange={(e) => setFeedback({ ...feedback, suggestion: e.target.value })}
                    placeholder={
                      feedback.category === 'feature' 
                        ? "I'd love to see a feature that..." 
                        : feedback.category === 'bug'
                        ? "I noticed that when I..."
                        : "I think it would be great if..."
                    }
                    className="min-h-[120px] resize-none"
                  />
                  <p className="text-xs text-slate-400 mt-1 text-right">
                    {feedback.suggestion.length}/500
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                    Back
                  </Button>
                  <Button 
                    onClick={() => setStep(3)} 
                    disabled={!feedback.suggestion.trim()}
                    className="flex-1 bg-indigo-500 hover:bg-indigo-600"
                  >
                    Continue
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Email (optional) & Submit */}
            {step === 3 && (
              <div className="space-y-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-sm text-slate-600 mb-2">Your feedback:</p>
                  <p className="text-sm font-medium text-slate-800 line-clamp-3">{feedback.suggestion}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Email (optional)
                  </label>
                  <input
                    type="email"
                    value={feedback.email}
                    onChange={(e) => setFeedback({ ...feedback, email: e.target.value })}
                    placeholder="your@email.com"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    We'll notify you when we act on your feedback
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                    Back
                  </Button>
                  <Button 
                    onClick={handleSubmit} 
                    disabled={loading}
                    className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
                  >
                    {loading ? (
                      <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting...</>
                    ) : (
                      <><Send className="w-4 h-4 mr-2" /> Submit Feedback</>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Progress indicator */}
          <div className="flex justify-center gap-2 pb-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-2 h-2 rounded-full transition-all ${
                  step >= s ? 'bg-indigo-500' : 'bg-slate-200'
                }`}
              />
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
