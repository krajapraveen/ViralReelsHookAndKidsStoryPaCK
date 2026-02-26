import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, Star, MapPin, Clock, AlertTriangle, ThumbsUp, ThumbsDown,
  Activity, Loader2, ChevronDown, ChevronUp, Mail, Globe, Smartphone,
  TrendingUp, TrendingDown, Filter, RefreshCw, User
} from 'lucide-react';
import { Button } from '../ui/button';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL || '';

export default function UserAnalyticsTab({ dateRange = 30 }) {
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('ratings');
  const [summary, setSummary] = useState(null);
  const [feedbackDetails, setFeedbackDetails] = useState(null);
  const [featureHappiness, setFeatureHappiness] = useState(null);
  const [userSessions, setUserSessions] = useState(null);
  const [featureFailures, setFeatureFailures] = useState(null);
  const [expandedUser, setExpandedUser] = useState(null);
  const [ratingFilter, setRatingFilter] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [summaryRes, feedbackRes, happinessRes, sessionsRes, failuresRes] = await Promise.all([
        fetch(`${API}/api/admin/user-analytics/dashboard-summary?days=${dateRange}`, { headers }),
        fetch(`${API}/api/admin/user-analytics/feedback-details?days=${dateRange}`, { headers }),
        fetch(`${API}/api/admin/user-analytics/feature-happiness?days=${dateRange}`, { headers }),
        fetch(`${API}/api/admin/user-analytics/user-sessions?days=${dateRange}`, { headers }),
        fetch(`${API}/api/admin/user-analytics/feature-failures?days=${dateRange}`, { headers })
      ]);

      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (feedbackRes.ok) setFeedbackDetails(await feedbackRes.json());
      if (happinessRes.ok) setFeatureHappiness(await happinessRes.json());
      if (sessionsRes.ok) setUserSessions(await sessionsRes.json());
      if (failuresRes.ok) setFeatureFailures(await failuresRes.json());
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <span className="ml-2 text-slate-400">Loading analytics...</span>
      </div>
    );
  }

  const filteredFeedbacks = feedbackDetails?.feedbacks?.filter(fb => 
    ratingFilter ? fb.rating === ratingFilter : true
  ) || [];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <Star className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
          <div className="text-3xl font-bold text-yellow-400">{summary?.ratings?.average || 0}</div>
          <div className="text-xs text-slate-400">Avg Rating</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <Users className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
          <div className="text-3xl font-bold">{summary?.ratings?.total || 0}</div>
          <div className="text-xs text-slate-400">Total Ratings</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <Activity className="w-6 h-6 text-green-400 mx-auto mb-2" />
          <div className="text-3xl font-bold text-green-400">{summary?.sessions?.unique_users || 0}</div>
          <div className="text-xs text-slate-400">Active Users</div>
        </div>
        <div className="bg-slate-700/50 rounded-xl p-4 text-center">
          <AlertTriangle className="w-6 h-6 text-red-400 mx-auto mb-2" />
          <div className="text-3xl font-bold text-red-400">{summary?.failures?.total || 0}</div>
          <div className="text-xs text-slate-400">Failures</div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 flex-wrap">
        {['ratings', 'happiness', 'sessions', 'failures'].map(tab => (
          <Button
            key={tab}
            variant={activeSection === tab ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveSection(tab)}
            className={activeSection === tab ? 'bg-indigo-600' : 'border-slate-600'}
          >
            {tab === 'ratings' && <Star className="w-4 h-4 mr-1" />}
            {tab === 'happiness' && <ThumbsUp className="w-4 h-4 mr-1" />}
            {tab === 'sessions' && <Clock className="w-4 h-4 mr-1" />}
            {tab === 'failures' && <AlertTriangle className="w-4 h-4 mr-1" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Button>
        ))}
        <Button variant="outline" size="sm" onClick={fetchData} className="ml-auto border-slate-600">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Ratings Section */}
      {activeSection === 'ratings' && (
        <div className="space-y-4">
          {/* Rating Filter */}
          <div className="flex items-center gap-2 bg-slate-700/30 p-3 rounded-lg">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">Filter by rating:</span>
            {[null, 1, 2, 3, 4, 5].map(r => (
              <Button
                key={r ?? 'all'}
                size="sm"
                variant={ratingFilter === r ? 'default' : 'ghost'}
                onClick={() => setRatingFilter(r)}
                className={`px-2 py-1 h-7 ${ratingFilter === r ? 'bg-indigo-600' : ''}`}
              >
                {r ? (
                  <span className="flex items-center gap-1">
                    {r} <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                  </span>
                ) : 'All'}
              </Button>
            ))}
          </div>

          {/* Rating Distribution */}
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-400" />
              Who Rated & Why
            </h3>
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {filteredFeedbacks.length > 0 ? filteredFeedbacks.map((fb, i) => (
                <div key={i} className="bg-slate-600/50 rounded-lg overflow-hidden">
                  {/* User Header */}
                  <div 
                    className="p-4 cursor-pointer hover:bg-slate-600/70 transition-colors"
                    onClick={() => setExpandedUser(expandedUser === i ? null : i)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-medium">{fb.name || 'Anonymous'}</div>
                          <div className="text-sm text-slate-400 flex items-center gap-1">
                            <Mail className="w-3 h-3" />
                            {fb.email || 'No email'}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex">
                          {[...Array(5)].map((_, j) => (
                            <Star 
                              key={j}
                              className={`w-4 h-4 ${j < fb.rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-500'}`}
                            />
                          ))}
                        </div>
                        {expandedUser === i ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                      </div>
                    </div>
                    {fb.comment && fb.comment !== 'No comment provided' && (
                      <p className="mt-2 text-sm text-slate-300 italic">"{fb.comment}"</p>
                    )}
                  </div>

                  {/* Expanded Details */}
                  {expandedUser === i && (
                    <div className="px-4 pb-4 border-t border-slate-500/30 pt-3 space-y-3">
                      {/* Features Used */}
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Features Used</div>
                        <div className="flex flex-wrap gap-2">
                          {fb.features_used?.length > 0 ? fb.features_used.map((f, j) => (
                            <span key={j} className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                              {f.replace(/_/g, ' ')}
                            </span>
                          )) : <span className="text-slate-500 text-xs">No features tracked</span>}
                        </div>
                      </div>

                      {/* Features Failed */}
                      {fb.features_failed?.length > 0 && (
                        <div>
                          <div className="text-xs text-slate-400 mb-1">Features That Failed</div>
                          <div className="flex flex-wrap gap-2">
                            {fb.features_failed.map((f, j) => (
                              <span key={j} className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">
                                {f.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Session & Location */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div>
                          <div className="text-xs text-slate-400">Session Duration</div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {fb.session_duration_minutes ? `${fb.session_duration_minutes} min` : 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400">Location</div>
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {fb.location?.city && fb.location?.country 
                              ? `${fb.location.city}, ${fb.location.country}` 
                              : 'Unknown'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400">Device</div>
                          <div className="flex items-center gap-1">
                            <Smartphone className="w-3 h-3" />
                            {fb.device || 'Unknown'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400">Rated On</div>
                          <div>{new Date(fb.created_at).toLocaleDateString()}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )) : (
                <div className="text-center text-slate-400 py-8">No ratings found for this filter</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Feature Happiness Section */}
      {activeSection === 'happiness' && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Happy Features */}
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ThumbsUp className="w-5 h-5 text-green-400" />
              Users Are Happy With
            </h3>
            <div className="space-y-3">
              {featureHappiness?.happy_features?.map((f, i) => (
                <div key={i} className="p-3 bg-green-500/10 rounded-lg border border-green-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-green-400">{f.display_name}</span>
                    <span className="text-sm bg-green-500/20 px-2 py-1 rounded">
                      {f.happiness_score}% Happy
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                    <div>Uses: {f.total_uses}</div>
                    <div>Success: {f.success_rate}%</div>
                    <div>Rating: {f.average_rating}/5</div>
                  </div>
                </div>
              )) || <div className="text-slate-400 text-center py-4">No data available</div>}
            </div>
          </div>

          {/* Unhappy Features */}
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ThumbsDown className="w-5 h-5 text-red-400" />
              Users Are Unhappy With
            </h3>
            <div className="space-y-3">
              {featureHappiness?.unhappy_features?.map((f, i) => (
                <div key={i} className="p-3 bg-red-500/10 rounded-lg border border-red-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-red-400">{f.display_name}</span>
                    <span className="text-sm bg-red-500/20 px-2 py-1 rounded">
                      {f.happiness_score}% Happy
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                    <div>Uses: {f.total_uses}</div>
                    <div>Failures: {f.failure_count}</div>
                    <div>Rating: {f.average_rating}/5</div>
                  </div>
                  {f.common_issues?.length > 0 && (
                    <div className="mt-2 text-xs">
                      <span className="text-red-400">Issues: </span>
                      {f.common_issues.slice(0, 2).join(', ')}
                    </div>
                  )}
                </div>
              )) || <div className="text-slate-400 text-center py-4">All features are performing well!</div>}
            </div>
          </div>
        </div>
      )}

      {/* Sessions Section */}
      {activeSection === 'sessions' && (
        <div className="space-y-4">
          {/* Session Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-700/50 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold">{userSessions?.summary?.total_sessions || 0}</div>
              <div className="text-xs text-slate-400">Total Sessions</div>
            </div>
            <div className="bg-slate-700/50 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold">{userSessions?.summary?.unique_users || 0}</div>
              <div className="text-xs text-slate-400">Unique Users</div>
            </div>
            <div className="bg-slate-700/50 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold">{userSessions?.summary?.avg_session_duration_minutes || 0}m</div>
              <div className="text-xs text-slate-400">Avg Duration</div>
            </div>
            <div className="bg-slate-700/50 rounded-xl p-4 text-center">
              <Globe className="w-6 h-6 mx-auto mb-1 text-indigo-400" />
              <div className="text-lg font-bold">{userSessions?.summary?.top_locations?.length || 0}</div>
              <div className="text-xs text-slate-400">Countries</div>
            </div>
          </div>

          {/* Top Locations */}
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-indigo-400" />
              Top Login Locations
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {userSessions?.summary?.top_locations?.map((loc, i) => (
                <div key={i} className="bg-slate-600/50 rounded-lg p-3 text-center">
                  <div className="font-medium">{loc.country}</div>
                  <div className="text-xl font-bold text-indigo-400">{loc.count}</div>
                  <div className="text-xs text-slate-400">sessions</div>
                </div>
              ))}
            </div>
          </div>

          {/* User Sessions List */}
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4">User Sessions</h3>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {userSessions?.users?.slice(0, 20).map((user, i) => (
                <div key={i} className="bg-slate-600/50 rounded-lg p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-sm">
                      {user.name?.charAt(0) || 'U'}
                    </div>
                    <div>
                      <div className="font-medium">{user.name || user.email}</div>
                      <div className="text-xs text-slate-400">{user.email}</div>
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <div>{user.session_count} sessions</div>
                    <div className="text-slate-400">{user.avg_session_minutes}m avg</div>
                  </div>
                  <div className="text-right text-xs text-slate-400">
                    <div>{user.last_location?.city}, {user.last_location?.country}</div>
                    <div>{user.last_device}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Failures Section */}
      {activeSection === 'failures' && (
        <div className="space-y-4">
          <div className="bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              Feature Failures Impact
              <span className="ml-auto text-sm text-slate-400">
                {featureFailures?.total_failures || 0} total failures affecting {featureFailures?.total_affected_users || 0} users
              </span>
            </h3>
            <div className="space-y-3">
              {featureFailures?.features?.map((f, i) => (
                <div 
                  key={i} 
                  className={`p-4 rounded-lg border ${
                    f.impact_severity === 'High' ? 'bg-red-500/10 border-red-500/30' :
                    f.impact_severity === 'Medium' ? 'bg-yellow-500/10 border-yellow-500/30' :
                    'bg-slate-600/50 border-slate-500/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{f.display_name}</span>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm px-2 py-1 rounded ${
                        f.impact_severity === 'High' ? 'bg-red-500/20 text-red-400' :
                        f.impact_severity === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-slate-500/20 text-slate-400'
                      }`}>
                        {f.impact_severity} Impact
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm mb-2">
                    <div>
                      <span className="text-slate-400">Failures:</span>
                      <span className="ml-2 font-medium text-red-400">{f.total_failures}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Affected Users:</span>
                      <span className="ml-2 font-medium">{f.affected_users_count}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Avg User Rating:</span>
                      <span className="ml-2 font-medium">{f.avg_user_rating}</span>
                    </div>
                  </div>
                  {f.common_errors?.length > 0 && (
                    <div className="text-xs text-slate-400 bg-slate-700/50 p-2 rounded">
                      <span className="font-medium">Common errors:</span> {f.common_errors.slice(0, 2).join(' | ')}
                    </div>
                  )}
                </div>
              ))}
              {(!featureFailures?.features || featureFailures.features.length === 0) && (
                <div className="text-center text-green-400 py-8">
                  <ThumbsUp className="w-12 h-12 mx-auto mb-2" />
                  No feature failures in this period!
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
