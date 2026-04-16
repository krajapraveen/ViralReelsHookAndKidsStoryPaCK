import React, { useState, useEffect, useRef } from 'react';
import { Star, ChevronLeft, ChevronRight } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Homepage review wall — shows real user reviews with avg rating.
 * Rotates automatically. Used on Landing page.
 */
export default function ReviewWall() {
  const [data, setData] = useState(null);
  const [current, setCurrent] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/api/reviews/public?limit=12`).then(r => {
      if (r.data && r.data.total_reviews > 0) setData(r.data);
    }).catch(() => {});
  }, []);

  // Auto-rotate every 5s
  useEffect(() => {
    if (!data?.reviews?.length) return;
    intervalRef.current = setInterval(() => {
      setCurrent(c => (c + 1) % data.reviews.length);
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, [data]);

  if (!data || data.total_reviews === 0) return null;

  const reviews = data.reviews;
  const avg = data.avg_rating;
  const total = data.total_reviews;
  const todayCount = data.today_count || 0;
  const fullStars = Math.floor(avg);
  const hasHalf = avg - fullStars >= 0.3;

  const prev = () => setCurrent(c => (c - 1 + reviews.length) % reviews.length);
  const next = () => setCurrent(c => (c + 1) % reviews.length);

  // Show 3 reviews at a time on desktop, 1 on mobile
  const visible = reviews.length > 0 ? [
    reviews[current % reviews.length],
    reviews[(current + 1) % reviews.length],
    reviews[(current + 2) % reviews.length],
  ].filter(Boolean) : [];

  return (
    <section className="py-12 px-4 border-t border-white/[0.04]" data-testid="review-wall">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-3">
            {total >= 20 ? 'Loved by creators worldwide' : 'Rated highly by early creators'}
          </h2>
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="flex items-center gap-0.5">
              {[1, 2, 3, 4, 5].map(s => (
                <Star
                  key={s}
                  className={`w-5 h-5 ${
                    s <= fullStars ? 'text-amber-400 fill-amber-400' :
                    s === fullStars + 1 && hasHalf ? 'text-amber-400 fill-amber-400/50' :
                    'text-slate-600'
                  }`}
                />
              ))}
            </div>
            <span className="text-lg font-bold text-white">{avg}</span>
            <span className="text-sm text-slate-500">/5 from {total} {total >= 20 ? 'creators' : 'reviews'}</span>
          </div>
          {todayCount > 0 && (
            <p className="text-[11px] text-emerald-400 font-medium">+{todayCount} new review{todayCount !== 1 ? 's' : ''} today</p>
          )}
        </div>

        {/* Review Cards */}
        {reviews.length > 0 && (
          <div className="relative">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {visible.map((review, idx) => (
                <div
                  key={review.id || idx}
                  className={`bg-white/[0.03] border border-white/[0.06] rounded-2xl p-5 transition-all duration-500 ${idx === 0 ? '' : 'hidden md:block'}`}
                  data-testid={`review-card-${idx}`}
                >
                  <div className="flex items-center gap-0.5 mb-3">
                    {[1, 2, 3, 4, 5].map(s => (
                      <Star key={s} className={`w-3.5 h-3.5 ${s <= review.rating ? 'text-amber-400 fill-amber-400' : 'text-slate-700'}`} />
                    ))}
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed mb-4 line-clamp-3">
                    &ldquo;{review.comment}&rdquo;
                  </p>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-medium text-white">{review.display_name || 'Creator'}</span>
                      {review.country && (
                        <span className="text-[10px] text-slate-500 ml-1.5">{review.country}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Navigation arrows */}
            {reviews.length > 3 && (
              <div className="flex items-center justify-center gap-3 mt-6">
                <button onClick={prev} className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/20 transition-colors" data-testid="review-prev">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="flex gap-1">
                  {reviews.slice(0, Math.min(reviews.length, 6)).map((_, i) => (
                    <div key={i} className={`w-1.5 h-1.5 rounded-full transition-colors ${i === current % Math.min(reviews.length, 6) ? 'bg-violet-400' : 'bg-slate-700'}`} />
                  ))}
                </div>
                <button onClick={next} className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/20 transition-colors" data-testid="review-next">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
