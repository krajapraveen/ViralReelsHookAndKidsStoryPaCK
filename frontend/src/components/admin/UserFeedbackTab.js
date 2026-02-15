import React, { useState, useEffect } from 'react';
import { MessageSquare, Star, Lightbulb, AlertCircle, TrendingUp, ThumbsUp, RefreshCw } from 'lucide-react';
import api from '../../utils/api';

export default function UserFeedbackTab() {
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, averageRating: 0, byCategory: {} });

  useEffect(() => {
    fetchFeedback();
  }, []);

  const fetchFeedback = async () => {
    try {
      const response = await api.get('/api/admin/feedback/all');
      if (response.data.success) {
        setFeedback(response.data.feedback || []);
        setStats(response.data.stats || { total: 0, averageRating: 0, byCategory: {} });
      }
    } catch (error) {
      console.log('Error fetching feedback:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      feature: 'bg-yellow-500/20 text-yellow-400',
      improvement: 'bg-blue-500/20 text-blue-400',
      bug: 'bg-red-500/20 text-red-400',
      praise: 'bg-green-500/20 text-green-400',
      suggestion: 'bg-purple-500/20 text-purple-400',
      FEATURE: 'bg-yellow-500/20 text-yellow-400',
      IMPROVEMENT: 'bg-blue-500/20 text-blue-400',
      BUG: 'bg-red-500/20 text-red-400',
      PRAISE: 'bg-green-500/20 text-green-400',
      SUGGESTION: 'bg-purple-500/20 text-purple-400'
    };
    return colors[category] || 'bg-slate-500/20 text-slate-400';
  };

  const getCategoryIcon = (category) => {
    const cat = category?.toLowerCase();
    switch(cat) {
      case 'feature': return <Lightbulb className="w-4 h-4" />;
      case 'improvement': return <TrendingUp className="w-4 h-4" />;
      case 'bug': return <AlertCircle className="w-4 h-4" />;
      case 'praise': return <ThumbsUp className="w-4 h-4" />;
      default: return <MessageSquare className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-500 mx-auto mb-4" />
        <p className="text-slate-400">Loading feedback...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <MessageSquare className="w-8 h-8 text-purple-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.total}</div>
          <div className="text-sm text-slate-400">Total Feedback</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <Star className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.averageRating || 0}</div>
          <div className="text-sm text-slate-400">Avg Rating</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <Lightbulb className="w-8 h-8 text-blue-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">
            {(stats.byCategory?.feature || 0) + (stats.byCategory?.improvement || 0) + (stats.byCategory?.SUGGESTION || 0) + (stats.byCategory?.FEATURE || 0)}
          </div>
          <div className="text-sm text-slate-400">Suggestions</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.byCategory?.bug || stats.byCategory?.BUG || 0}</div>
          <div className="text-sm text-slate-400">Bug Reports</div>
        </div>
      </div>

      {/* Feedback List */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-purple-400" />
          All User Feedback
        </h3>
        
        {feedback.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No feedback received yet</p>
            <p className="text-sm">User feedback will appear here</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {feedback.map((item, idx) => (
              <div key={idx} className="bg-slate-600/50 rounded-lg p-4 hover:bg-slate-600/70 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getCategoryColor(item.type)}`}>
                      {getCategoryIcon(item.type)}
                      {item.type || 'General'}
                    </span>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star 
                          key={star} 
                          className={`w-3 h-3 ${star <= (item.rating || 0) ? 'text-yellow-400 fill-current' : 'text-slate-500'}`} 
                        />
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-slate-400">
                    {item.createdAt ? new Date(item.createdAt).toLocaleString() : 'N/A'}
                  </span>
                </div>
                
                <p className="text-slate-200 text-sm mb-2">{item.message}</p>
                
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span>From: {item.name || 'Anonymous'}</span>
                  {item.email && item.email !== 'anonymous@feedback.local' && (
                    <span>Email: {item.email}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
