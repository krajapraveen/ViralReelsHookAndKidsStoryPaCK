import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Star, ArrowLeft, MessageSquare, ThumbsUp, User } from 'lucide-react';
import FeedbackForm from '../components/FeedbackForm';

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/reviews/approved`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.reviews) {
          setReviews(data.reviews);
        }
      }
    } catch (error) {
      console.log('Could not fetch reviews');
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (rating) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-5 h-5 ${i < rating ? 'fill-yellow-400 text-yellow-400' : 'text-slate-300'}`}
      />
    ));
  };

  // Reviews are now fetched from API - no fake defaults
  const defaultReviews = [];

  const displayReviews = reviews.length > 0 ? reviews : defaultReviews;

  const avgRating = displayReviews.length > 0 
    ? displayReviews.reduce((acc, r) => acc + r.rating, 0) / displayReviews.length 
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      {/* Feedback Form Modal */}
      <FeedbackForm isOpen={showFeedbackForm} onClose={() => setShowFeedbackForm(false)} />

      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-xl">C</span>
            </div>
            <span className="text-xl font-bold text-white">
              Visionary Suite
            </span>
          </Link>
          <div className="flex gap-3">
            <Button 
              onClick={() => setShowFeedbackForm(true)}
              className="bg-indigo-500 hover:bg-indigo-600"
              data-testid="write-review-btn"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Write a Review
            </Button>
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-white/10">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">Customer Reviews</h1>
          <p className="text-lg text-slate-300 max-w-2xl mx-auto mb-6">
            See what our users are saying about Visionary Suite
          </p>
          
          {/* Rating Summary */}
          <div className="inline-flex items-center gap-4 bg-slate-800/50 backdrop-blur-sm rounded-2xl px-8 py-4 border border-slate-700/50">
            <div className="text-center">
              <div className="text-4xl font-bold text-white">{avgRating.toFixed(1)}</div>
              <div className="flex gap-1 justify-center mt-1">
                {renderStars(Math.round(avgRating))}
              </div>
            </div>
            <div className="w-px h-12 bg-slate-700" />
            <div className="text-left">
              <div className="text-2xl font-bold text-white">{displayReviews.length}</div>
              <div className="text-slate-400">Total Reviews</div>
            </div>
          </div>
        </div>

        {/* Reviews Grid */}
        {displayReviews.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-6">
              <MessageSquare className="w-10 h-10 text-slate-600" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-4">Be the First to Share Your Experience!</h3>
            <p className="text-slate-400 mb-8 max-w-md mx-auto">
              We're building a community of creators. Try our tools and share your honest feedback to help others discover what's possible!
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/signup">
                <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 px-8">
                  Get Started Free
                </Button>
              </Link>
              <Button 
                onClick={() => setShowFeedbackForm(true)}
                variant="outline"
                className="border-slate-600 text-slate-300 hover:bg-slate-800"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Write a Review
              </Button>
            </div>
          </div>
        ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayReviews.map((review) => (
            <div 
              key={review.id} 
              className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6 hover:border-indigo-500/50 transition-all"
              data-testid={`review-${review.id}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{review.name}</h3>
                    <p className="text-sm text-slate-400">{new Date(review.createdAt).toLocaleDateString()}</p>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-1 mb-3">
                {renderStars(review.rating)}
              </div>
              
              <p className="text-slate-300 leading-relaxed">{review.message}</p>
              
              <div className="mt-4 pt-4 border-t border-slate-700 flex items-center gap-2 text-sm text-slate-400">
                <ThumbsUp className="w-4 h-4" />
                <span>Verified User</span>
              </div>
            </div>
          ))}
        </div>
        )}

        {/* CTA Section */}
        <div className="mt-16 text-center">
          <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl p-8 text-white">
            <h2 className="text-2xl font-bold mb-4">Ready to Join Our Happy Customers?</h2>
            <p className="text-white/90 mb-6 max-w-xl mx-auto">
              Start creating viral content today with 10 free credits. No credit card required.
            </p>
            <Link to="/signup">
              <Button className="bg-white text-indigo-600 hover:bg-slate-100 px-8 py-6 text-lg">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-8 mt-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-slate-400">
            © 2026 Visionary Suite by Visionary Suite. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
