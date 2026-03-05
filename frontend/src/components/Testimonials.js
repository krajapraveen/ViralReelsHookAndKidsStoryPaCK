import React, { useState, useEffect } from 'react';
import { Star, MessageSquare, ArrowRight, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Testimonials() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalReviews: 0, avgRating: 0 });

  useEffect(() => {
    fetchApprovedReviews();
  }, []);

  const fetchApprovedReviews = async () => {
    try {
      const response = await fetch(`${API_URL}/api/reviews/approved?limit=3`);
      if (response.ok) {
        const data = await response.json();
        setReviews(data.reviews || []);
        setStats({
          totalReviews: data.totalCount || 0,
          avgRating: data.avgRating || 0
        });
      }
    } catch (error) {
      console.log('Could not fetch reviews');
    } finally {
      setLoading(false);
    }
  };

  // If no approved reviews yet, show CTA to leave review
  if (!loading && reviews.length === 0) {
    return (
      <section className="py-16 px-4" id="testimonials" data-testid="testimonials-section">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-slate-900/80 to-indigo-900/30 backdrop-blur-xl rounded-3xl border border-white/10 p-8 md:p-12 text-center">
            <div className="inline-flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-4 py-2 mb-6">
              <Users className="w-4 h-4 text-indigo-400" />
              <span className="text-indigo-400 font-medium text-sm">Join Our Community</span>
            </div>
            
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Be the First to Share Your Story
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-8">
              We're building a community of creators. Try our tools and share your experience to help others discover what's possible!
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/signup">
                <Button 
                  className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-full px-8 py-4 text-lg font-semibold"
                  data-testid="testimonials-try-free-btn"
                >
                  Try Free & Share Your Experience
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <Link to="/reviews">
                <Button 
                  variant="outline"
                  className="border-white/20 text-white hover:bg-white/10 rounded-full px-6 py-4"
                  data-testid="testimonials-leave-review-btn"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Leave a Review
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  // Show approved reviews
  return (
    <section className="py-16 px-4" id="testimonials" data-testid="testimonials-section">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/30 rounded-full px-4 py-2 mb-4">
            <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
            <span className="text-yellow-400 font-medium text-sm">
              {stats.totalReviews > 0 ? `${stats.avgRating.toFixed(1)} avg from ${stats.totalReviews} reviews` : 'Community Reviews'}
            </span>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            What Creators Are Saying
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Real feedback from our community of content creators
          </p>
        </div>

        {/* Reviews Grid */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {reviews.map((review) => (
              <div 
                key={review.id}
                className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-white/10 p-6 hover:border-indigo-500/30 transition-all"
                data-testid={`review-card-${review.id}`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold">
                    {review.name?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                  <div>
                    <h4 className="text-white font-semibold">{review.name}</h4>
                    {review.role && <p className="text-slate-400 text-sm">{review.role}</p>}
                  </div>
                </div>
                
                <div className="flex gap-1 mb-3">
                  {[...Array(5)].map((_, i) => (
                    <Star 
                      key={i} 
                      className={`w-4 h-4 ${i < review.rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'}`} 
                    />
                  ))}
                </div>
                
                <p className="text-slate-300 text-sm leading-relaxed line-clamp-4">
                  "{review.message}"
                </p>
                
                <p className="text-slate-500 text-xs mt-4">
                  {new Date(review.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* CTA to see all reviews or leave one */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/reviews">
            <Button 
              variant="outline"
              className="border-white/20 text-white hover:bg-white/10 rounded-full px-6 py-3"
              data-testid="see-all-reviews-btn"
            >
              See All Reviews
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Link to="/reviews">
            <Button 
              className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-full px-6 py-3"
              data-testid="share-experience-btn"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Share Your Experience
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
