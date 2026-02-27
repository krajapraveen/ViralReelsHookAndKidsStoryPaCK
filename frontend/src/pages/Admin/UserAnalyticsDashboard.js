import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, BarChart3, Star, Users, Activity, AlertTriangle, 
  Download, Filter, RefreshCw, ChevronDown, Eye, TrendingUp, 
  TrendingDown, Clock, MapPin, Smartphone, Globe
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Progress } from '../../components/ui/progress';
import { toast } from 'sonner';
import api from '../../utils/api';

export default function UserAnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [featureHappiness, setFeatureHappiness] = useState(null);
  const [ratingsList, setRatingsList] = useState([]);
  const [selectedDrilldown, setSelectedDrilldown] = useState(null);
  
  // Filters
  const [days, setDays] = useState('30');
  const [featureFilter, setFeatureFilter] = useState('all');
  const [ratingFilter, setRatingFilter] = useState('all');
  
  // Active tab
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchDashboardData();
    fetchFeatureHappiness();
    fetchRatingsList();
  }, [days, featureFilter, ratingFilter]);

  const fetchDashboardData = async () => {
    try {
      const response = await api.get(`/api/admin/user-analytics/dashboard-summary?days=${days}`);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  const fetchFeatureHappiness = async () => {
    try {
      const response = await api.get(`/api/admin/user-analytics/feature-happiness?days=${days}`);
      setFeatureHappiness(response.data);
    } catch (error) {
      console.error('Failed to fetch feature happiness:', error);
    }
  };

  const fetchRatingsList = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/user-analytics/ratings/list?days=${days}&size=50`;
      if (ratingFilter !== 'all') {
        url += `&rating_filter=${ratingFilter}`;
      }
      if (featureFilter !== 'all') {
        url += `&feature_key=${featureFilter}`;
      }
      const response = await api.get(url);
      setRatingsList(response.data.ratings || []);
    } catch (error) {
      console.error('Failed to fetch ratings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDrilldown = async (ratingId) => {
    try {
      const response = await api.get(`/api/admin/user-analytics/ratings/drilldown/${ratingId}`);
      setSelectedDrilldown(response.data);
    } catch (error) {
      toast.error('Failed to load drilldown');
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await api.get(
        `/api/admin/user-analytics/ratings/export/csv?days=${days}${ratingFilter !== 'all' ? `&rating_filter=${ratingFilter}` : ''}`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ratings_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('CSV exported successfully');
    } catch (error) {
      toast.error('Failed to export CSV');
    }
  };

  const handleResetRatings = async () => {
    if (!window.confirm('Are you sure you want to reset ALL ratings? This cannot be undone.')) {
      return;
    }
    
    try {
      await api.delete('/api/admin/user-analytics/ratings/reset?confirm=true');
      toast.success('All ratings have been reset');
      fetchDashboardData();
      fetchRatingsList();
    } catch (error) {
      toast.error('Failed to reset ratings');
    }
  };

  const renderStars = (rating) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star
            key={i}
            className={`w-4 h-4 ${i <= rating ? 'fill-amber-400 text-amber-400' : 'text-slate-600'}`}
          />
        ))}
      </div>
    );
  };

  const getRatingColor = (rating) => {
    if (rating >= 4) return 'text-green-400';
    if (rating === 3) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/admin" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span>Admin</span>
              </Link>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-6 h-6 text-purple-400" />
                <h1 className="text-2xl font-bold text-white">Ratings & Experience Analytics</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  fetchDashboardData();
                  fetchFeatureHappiness();
                  fetchRatingsList();
                }}
              >
                <RefreshCw className="w-4 h-4 mr-2" /> Refresh
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleExportCSV}
              >
                <Download className="w-4 h-4 mr-2" /> Export CSV
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-slate-400 text-sm">Filters:</span>
            </div>
            
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger className="w-32 bg-slate-700 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="7" className="text-white">Last 7 days</SelectItem>
                <SelectItem value="30" className="text-white">Last 30 days</SelectItem>
                <SelectItem value="90" className="text-white">Last 90 days</SelectItem>
                <SelectItem value="365" className="text-white">Last year</SelectItem>
              </SelectContent>
            </Select>

            <Select value={ratingFilter} onValueChange={setRatingFilter}>
              <SelectTrigger className="w-36 bg-slate-700 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Ratings</SelectItem>
                <SelectItem value="1" className="text-white">1 Star</SelectItem>
                <SelectItem value="2" className="text-white">2 Stars</SelectItem>
                <SelectItem value="3" className="text-white">3 Stars</SelectItem>
                <SelectItem value="4" className="text-white">4 Stars</SelectItem>
                <SelectItem value="5" className="text-white">5 Stars</SelectItem>
              </SelectContent>
            </Select>

            <Select value={featureFilter} onValueChange={setFeatureFilter}>
              <SelectTrigger className="w-40 bg-slate-700 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Features</SelectItem>
                <SelectItem value="reel_generator" className="text-white">Reel Generator</SelectItem>
                <SelectItem value="story_pack" className="text-white">Story Pack</SelectItem>
                <SelectItem value="comix_ai" className="text-white">Comix AI</SelectItem>
                <SelectItem value="gif_maker" className="text-white">GIF Maker</SelectItem>
              </SelectContent>
            </Select>

            <Button 
              variant="destructive" 
              size="sm"
              onClick={handleResetRatings}
              className="ml-auto"
            >
              Reset All Ratings
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {['overview', 'ratings', 'features', 'drilldown'].map((tab) => (
            <Button
              key={tab}
              variant={activeTab === tab ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab(tab)}
              className={activeTab === tab ? 'bg-purple-600' : ''}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && dashboardData && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <Star className="w-4 h-4" />
                  <span className="text-sm">Total Ratings</span>
                </div>
                <p className="text-2xl font-bold text-white">{dashboardData.ratings?.total_ratings || 0}</p>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-sm">Avg Rating</span>
                </div>
                <p className={`text-2xl font-bold ${getRatingColor(dashboardData.ratings?.average_rating || 0)}`}>
                  {dashboardData.ratings?.average_rating || 0}
                </p>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <Users className="w-4 h-4" />
                  <span className="text-sm">NPS Score</span>
                </div>
                <p className={`text-2xl font-bold ${dashboardData.ratings?.nps_score >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {dashboardData.ratings?.nps_score || 0}
                </p>
              </div>
              
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <div className="flex items-center gap-2 text-slate-400 mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm">Low Ratings</span>
                </div>
                <p className="text-2xl font-bold text-red-400">{dashboardData.ratings?.low_rating_count || 0}</p>
                <p className="text-xs text-slate-500">{dashboardData.ratings?.low_rating_percentage || 0}%</p>
              </div>
            </div>

            {/* Rating Distribution */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-lg font-bold text-white mb-4">Rating Distribution</h3>
              <div className="space-y-3">
                {[5, 4, 3, 2, 1].map((rating) => {
                  const count = dashboardData.ratings?.distribution?.[rating] || 0;
                  const total = dashboardData.ratings?.total_ratings || 1;
                  const percentage = Math.round((count / total) * 100);
                  
                  return (
                    <div key={rating} className="flex items-center gap-4">
                      <div className="flex items-center gap-1 w-20">
                        <span className="text-white font-medium">{rating}</span>
                        <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                      </div>
                      <div className="flex-1">
                        <Progress value={percentage} className="h-3" />
                      </div>
                      <div className="w-24 text-right">
                        <span className="text-white font-medium">{count}</span>
                        <span className="text-slate-500 text-sm ml-2">({percentage}%)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Low Ratings Requiring Attention */}
            {dashboardData.low_ratings_requiring_attention?.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
                <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Low Ratings Requiring Attention
                </h3>
                <div className="space-y-3">
                  {dashboardData.low_ratings_requiring_attention.map((rating, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        {renderStars(rating.rating)}
                        <span className="text-white">{rating.feature_key || 'General'}</span>
                        {rating.reason_type && (
                          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                            {rating.reason_type.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setActiveTab('drilldown');
                          fetchDrilldown(rating.rating_id);
                        }}
                      >
                        <Eye className="w-4 h-4 mr-1" /> View
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Ratings List Tab */}
        {activeTab === 'ratings' && (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-700/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Rating</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Feature</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Location</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">Loading...</td>
                    </tr>
                  ) : ratingsList.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">No ratings found</td>
                    </tr>
                  ) : (
                    ratingsList.map((rating, i) => (
                      <tr key={i} className="hover:bg-slate-700/30">
                        <td className="px-4 py-3">{renderStars(rating.rating)}</td>
                        <td className="px-4 py-3">
                          <p className="text-white text-sm">{rating.user_name || 'Unknown'}</p>
                          <p className="text-slate-500 text-xs">{rating.user_email}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-white text-sm">{rating.feature_key || 'General'}</span>
                        </td>
                        <td className="px-4 py-3">
                          {rating.reason_type ? (
                            <span className="text-xs bg-slate-600 text-slate-300 px-2 py-1 rounded">
                              {rating.reason_type.replace(/_/g, ' ')}
                            </span>
                          ) : (
                            <span className="text-slate-500 text-sm">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {rating.approx_location?.country ? (
                            <div className="flex items-center gap-1 text-slate-400 text-xs">
                              <MapPin className="w-3 h-3" />
                              {rating.approx_location.city}, {rating.approx_location.country}
                            </div>
                          ) : (
                            <span className="text-slate-500 text-sm">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-sm">
                          {new Date(rating.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setActiveTab('drilldown');
                              fetchDrilldown(rating.rating_id);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Features Tab - Happy vs Unhappy */}
        {activeTab === 'features' && featureHappiness && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Happy Features */}
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6">
              <h3 className="text-lg font-bold text-green-400 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Happy Features
              </h3>
              <div className="space-y-3">
                {featureHappiness.happy_features.map((feature, i) => (
                  <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white font-medium">{feature.display_name}</span>
                      <span className="text-green-400 font-bold">{feature.happiness_score}%</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-400">
                      <span>{feature.total_uses} uses</span>
                      <span>{feature.success_rate}% success</span>
                      <span>★ {feature.avg_rating}</span>
                    </div>
                  </div>
                ))}
                {featureHappiness.happy_features.length === 0 && (
                  <p className="text-slate-400 text-center py-4">No happy features yet</p>
                )}
              </div>
            </div>

            {/* Unhappy Features */}
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
              <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                <TrendingDown className="w-5 h-5" />
                Unhappy Features
              </h3>
              <div className="space-y-3">
                {featureHappiness.unhappy_features.map((feature, i) => (
                  <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white font-medium">{feature.display_name}</span>
                      <span className="text-red-400 font-bold">{feature.happiness_score}%</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-400 mb-2">
                      <span>{feature.total_uses} uses</span>
                      <span>{feature.success_rate}% success</span>
                      <span>★ {feature.avg_rating}</span>
                    </div>
                    {feature.common_issues?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {feature.common_issues.slice(0, 3).map((issue, j) => (
                          <span key={j} className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                            {issue.reason}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {featureHappiness.unhappy_features.length === 0 && (
                  <p className="text-slate-400 text-center py-4">No unhappy features - great!</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Drilldown Tab */}
        {activeTab === 'drilldown' && (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
            {selectedDrilldown ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-white">Rating Drilldown</h3>
                  <Button variant="ghost" onClick={() => setSelectedDrilldown(null)}>
                    Close
                  </Button>
                </div>

                {/* User Info */}
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <h4 className="text-sm text-slate-400 mb-3">User Details</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Name</span>
                        <span className="text-white">{selectedDrilldown.user_name || 'Unknown'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Email</span>
                        <span className="text-white">{selectedDrilldown.user_email || 'Unknown'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">User Type</span>
                        <span className="text-white">{selectedDrilldown.user_type || 'Unknown'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <h4 className="text-sm text-slate-400 mb-3">Rating Info</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Rating</span>
                        {renderStars(selectedDrilldown.rating)}
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Feature</span>
                        <span className="text-white">{selectedDrilldown.feature_key || 'General'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Reason</span>
                        <span className="text-white">{selectedDrilldown.reason_type?.replace(/_/g, ' ') || '-'}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Comment */}
                {selectedDrilldown.comment && (
                  <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <h4 className="text-sm text-amber-400 mb-2">User Comment</h4>
                    <p className="text-white">{selectedDrilldown.comment}</p>
                  </div>
                )}

                {/* Session Info */}
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                      <Clock className="w-4 h-4" />
                      <span className="text-sm">Session Duration</span>
                    </div>
                    <p className="text-white font-bold">
                      {selectedDrilldown.session_duration_minutes || '-'} min
                    </p>
                  </div>
                  
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                      <Smartphone className="w-4 h-4" />
                      <span className="text-sm">Device</span>
                    </div>
                    <p className="text-white font-bold">
                      {selectedDrilldown.device_type || '-'} / {selectedDrilldown.browser || '-'}
                    </p>
                  </div>
                  
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                      <Globe className="w-4 h-4" />
                      <span className="text-sm">Location</span>
                    </div>
                    <p className="text-white font-bold">
                      {selectedDrilldown.approx_location?.city || '-'}, {selectedDrilldown.approx_location?.country || '-'}
                    </p>
                  </div>
                </div>

                {/* Output Status & Errors */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-700/50 rounded-lg">
                    <h4 className="text-sm text-slate-400 mb-2">Output Status</h4>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      selectedDrilldown.output_status === 'success' ? 'bg-green-500/20 text-green-400' :
                      selectedDrilldown.output_status === 'failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-slate-600 text-slate-400'
                    }`}>
                      {selectedDrilldown.output_status || 'Unknown'}
                    </span>
                  </div>
                  
                  {selectedDrilldown.error_codes?.length > 0 && (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <h4 className="text-sm text-red-400 mb-2">Error Codes</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedDrilldown.error_codes.map((code, i) => (
                          <span key={i} className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Feature Events */}
                {selectedDrilldown.feature_events_before_rating?.length > 0 && (
                  <div>
                    <h4 className="text-sm text-slate-400 mb-3">Activity Before Rating</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {selectedDrilldown.feature_events_before_rating.map((event, i) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-slate-700/30 rounded text-sm">
                          <span className="text-white">{event.event_type}</span>
                          <span className="text-slate-400">{event.feature_key}</span>
                          <span className={event.status === 'success' ? 'text-green-400' : 'text-red-400'}>
                            {event.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <Eye className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                <p className="text-lg">Select a rating from the Ratings tab to view details</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
