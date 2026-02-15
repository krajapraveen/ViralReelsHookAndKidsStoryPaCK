import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { toast } from 'sonner';
import { MessageSquare, Star, Send, Loader2 } from 'lucide-react';

export default function FeedbackForm({ isOpen, onClose }) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    type: 'feedback',
    rating: '5',
    message: '',
    allowPublic: false
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.email || !formData.message) {
      toast.error('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/feedback`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        toast.success('Thank you for your feedback!');
        setFormData({ name: '', email: '', type: 'feedback', rating: '5', message: '', allowPublic: false });
        onClose();
      } else {
        throw new Error('Failed to submit feedback');
      }
    } catch (error) {
      toast.error('Failed to submit feedback. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <MessageSquare className="w-5 h-5 text-indigo-500" />
            Share Your Feedback
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="feedback-form">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="feedback-name">Name *</Label>
              <Input
                id="feedback-name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="Your name"
                required
                data-testid="feedback-name"
              />
            </div>
            <div>
              <Label htmlFor="feedback-email">Email *</Label>
              <Input
                id="feedback-email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                placeholder="your@email.com"
                required
                data-testid="feedback-email"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Type</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({...formData, type: v})}>
                <SelectTrigger data-testid="feedback-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="feedback">General Feedback</SelectItem>
                  <SelectItem value="review">Product Review</SelectItem>
                  <SelectItem value="bug">Bug Report</SelectItem>
                  <SelectItem value="feature">Feature Request</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Rating</Label>
              <Select value={formData.rating} onValueChange={(v) => setFormData({...formData, rating: v})}>
                <SelectTrigger data-testid="feedback-rating">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">⭐⭐⭐⭐⭐ Excellent</SelectItem>
                  <SelectItem value="4">⭐⭐⭐⭐ Good</SelectItem>
                  <SelectItem value="3">⭐⭐⭐ Average</SelectItem>
                  <SelectItem value="2">⭐⭐ Poor</SelectItem>
                  <SelectItem value="1">⭐ Very Poor</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="feedback-message">Message *</Label>
            <Textarea
              id="feedback-message"
              value={formData.message}
              onChange={(e) => setFormData({...formData, message: e.target.value})}
              placeholder="Share your thoughts, suggestions, or report issues..."
              rows={4}
              required
              data-testid="feedback-message"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="allowPublic"
              checked={formData.allowPublic}
              onChange={(e) => setFormData({...formData, allowPublic: e.target.checked})}
              className="w-4 h-4 rounded border-slate-300"
            />
            <Label htmlFor="allowPublic" className="text-sm text-slate-600 cursor-pointer">
              Allow my review to be displayed publicly
            </Label>
          </div>

          <Button 
            type="submit" 
            disabled={loading} 
            className="w-full bg-indigo-500 hover:bg-indigo-600"
            data-testid="feedback-submit"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Submitting...</>
            ) : (
              <><Send className="w-4 h-4 mr-2" />Submit Feedback</>
            )}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
