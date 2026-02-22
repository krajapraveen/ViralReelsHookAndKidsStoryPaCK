import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { Lightbulb, ThumbsUp, ArrowLeft, Plus, Send, Check } from 'lucide-react';

export default function FeatureRequests() {
  const [requests, setRequests] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ title: '', description: '', category: 'OTHER' });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [requestsRes, categoriesRes] = await Promise.all([
        api.get('/api/feature-requests'),
        api.get('/api/feature-requests/categories')
      ]);
      setRequests(requestsRes.data.content || []);
      setCategories(categoriesRes.data.categories || []);
    } catch (error) {
      toast.error('Failed to load feature requests');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.description.trim()) {
      toast.error('Please fill in all fields');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post('/api/feature-requests', formData);
      toast.success('Feature request submitted! Your vote has been added.');
      setFormData({ title: '', description: '', category: 'OTHER' });
      setShowForm(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVote = async (requestId, hasVoted) => {
    try {
      if (hasVoted) {
        await api.delete(`/api/feature-requests/${requestId}/vote`);
        toast.success('Vote removed');
      } else {
        await api.post(`/api/feature-requests/${requestId}/vote`);
        toast.success('Vote added!');
      }
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.message || 'Failed to update vote');
    }
  };

  const statusColors = {
    PENDING: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    UNDER_REVIEW: 'bg-blue-100 text-blue-700 border-blue-200',
    PLANNED: 'bg-purple-100 text-purple-700 border-purple-200',
    IN_PROGRESS: 'bg-indigo-100 text-indigo-700 border-indigo-200',
    COMPLETED: 'bg-green-100 text-green-700 border-green-200',
    DECLINED: 'bg-red-100 text-red-700 border-red-200',
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Lightbulb className="w-6 h-6 text-yellow-500" />
              <span className="text-xl font-bold text-white">Feature Requests</span>
            </div>
          </div>
          <Button onClick={() => setShowForm(!showForm)} className="bg-purple-600 hover:bg-purple-700">
            <Plus className="w-4 h-4 mr-2" />
            Request Feature
          </Button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Submit Form */}
        {showForm && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-8 backdrop-blur-sm">
            <h2 className="text-lg font-semibold mb-4 text-white">Submit a Feature Request</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Feature Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., Add TikTok video format export"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder:text-slate-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe the feature in detail and why it would be helpful..."
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder:text-slate-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white"
                >
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <Button type="submit" disabled={submitting} className="bg-purple-600 hover:bg-purple-700">
                  <Send className="w-4 h-4 mr-2" />
                  {submitting ? 'Submitting...' : 'Submit Request'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowForm(false)} className="border-slate-600 text-slate-300 hover:bg-slate-700">
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-500/30 rounded-xl p-4 mb-6">
          <p className="text-sm text-purple-300">
            <strong>💡 Help us build better!</strong> Vote for features you want to see, or submit your own ideas. 
            The most popular requests will be prioritized for development.
          </p>
        </div>

        {/* Feature Requests List */}
        <div className="space-y-4">
          {requests.map((request) => (
            <div key={request.id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition-colors backdrop-blur-sm">
              <div className="flex gap-4">
                {/* Vote Button */}
                <div className="flex flex-col items-center">
                  <button
                    onClick={() => handleVote(request.id, request.hasVoted)}
                    className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center transition-colors ${
                      request.hasVoted 
                        ? 'bg-green-500/20 text-green-400 border-2 border-green-500/30' 
                        : 'bg-slate-700 text-slate-400 hover:bg-purple-500/20 hover:text-purple-400'
                    }`}
                  >
                    {request.hasVoted ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <ThumbsUp className="w-5 h-5" />
                    )}
                  </button>
                  <span className={`text-lg font-bold mt-1 ${request.hasVoted ? 'text-green-400' : 'text-slate-300'}`}>
                    {request.voteCount}
                  </span>
                  <span className="text-xs text-slate-500">votes</span>
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <h3 className="font-semibold text-lg text-white">{request.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${statusColors[request.status]}`}>
                      {request.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-slate-400 mt-1">{request.description}</p>
                  <div className="flex items-center gap-3 mt-3">
                    <span className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                      {request.categoryLabel}
                    </span>
                    {request.authorName && (
                      <span className="text-xs text-slate-500">
                        by {request.authorName}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">
                      {new Date(request.createdAt).toLocaleDateString()}
                    </span>
                    {request.isOwner && (
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs border border-purple-500/30">
                        Your request
                      </span>
                    )}
                  </div>
                  {request.adminResponse && (
                    <div className="mt-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                      <span className="text-xs font-medium text-purple-400">Admin Response:</span>
                      <p className="text-sm text-purple-300 mt-1">{request.adminResponse}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {requests.length === 0 && (
            <div className="text-center py-12 bg-slate-800/50 border border-slate-700 rounded-xl backdrop-blur-sm">
              <Lightbulb className="w-12 h-12 mx-auto text-slate-600 mb-4" />
              <h3 className="text-lg font-medium text-slate-300">No feature requests yet</h3>
              <p className="text-slate-500 mt-1">Be the first to suggest a feature!</p>
              <Button onClick={() => setShowForm(true)} className="mt-4 bg-purple-600 hover:bg-purple-700">
                <Plus className="w-4 h-4 mr-2" />
                Submit First Request
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
