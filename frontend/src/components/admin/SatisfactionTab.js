import React from 'react';
import { ThumbsUp, Star, FileText } from 'lucide-react';

export default function SatisfactionTab({ satisfaction }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Overall Satisfaction */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <ThumbsUp className="w-5 h-5 text-green-400" />
          User Satisfaction
        </h3>
        <div className="text-center py-6">
          <div className="text-6xl font-bold text-green-400">{satisfaction?.satisfactionPercentage || 0}%</div>
          <div className="text-slate-400 mt-2">of users are satisfied (4+ stars)</div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="text-center p-3 bg-slate-600/50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-400">{satisfaction?.averageRating || 0}</div>
            <div className="text-xs text-slate-400">Avg Rating</div>
          </div>
          <div className="text-center p-3 bg-slate-600/50 rounded-lg">
            <div className="text-2xl font-bold">{satisfaction?.totalReviews || 0}</div>
            <div className="text-xs text-slate-400">Reviews</div>
          </div>
          <div className="text-center p-3 bg-slate-600/50 rounded-lg">
            <div className="text-2xl font-bold text-purple-400">{satisfaction?.npsScore || 0}</div>
            <div className="text-xs text-slate-400">NPS Score</div>
          </div>
        </div>
      </div>

      {/* Rating Distribution */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Star className="w-5 h-5 text-yellow-400" />
          Rating Distribution
        </h3>
        <div className="space-y-3">
          {[5, 4, 3, 2, 1].map((rating) => {
            const count = satisfaction?.ratingDistribution?.[rating] || 0;
            const total = satisfaction?.totalReviews || 1;
            const percentage = Math.round((count / total) * 100) || 0;
            return (
              <div key={rating} className="flex items-center gap-3">
                <div className="flex items-center gap-1 w-16">
                  <span className="text-sm">{rating}</span>
                  <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                </div>
                <div className="flex-1 bg-slate-600 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full ${
                      rating >= 4 ? 'bg-green-500' : rating === 3 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-sm text-slate-400 w-12 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Reviews */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-400" />
          Recent Reviews
        </h3>
        <div className="space-y-3">
          {satisfaction?.recentReviews?.map((review, i) => (
            <div key={i} className="p-4 bg-slate-600/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                {[...Array(5)].map((_, j) => (
                  <Star 
                    key={j}
                    className={`w-4 h-4 ${j < review.rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-500'}`}
                  />
                ))}
                <span className="text-xs text-slate-400 ml-2">
                  {new Date(review.createdAt).toLocaleDateString()}
                </span>
              </div>
              <p className="text-sm text-slate-300">{review.comment || 'No comment provided'}</p>
            </div>
          ))}
          {(!satisfaction?.recentReviews || satisfaction.recentReviews.length === 0) && (
            <div className="text-center text-slate-400 py-4">No reviews yet</div>
          )}
        </div>
      </div>

      {/* Feedback Stats */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Feedback Summary</h3>
        <div className="text-center">
          <div className="text-4xl font-bold text-purple-400">{satisfaction?.totalFeedback || 0}</div>
          <div className="text-slate-400 mt-2">Total feedback submissions received</div>
        </div>
      </div>
    </div>
  );
}
