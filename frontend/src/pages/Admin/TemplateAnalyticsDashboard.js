import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, BarChart3, TrendingUp, Users, 
  Coins, Activity, PieChart, Calendar, Filter, Download,
  Shield, DollarSign, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TemplateAnalyticsDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [days, setDays] = useState(30);
  
  // Data states
  const [dashboard, setDashboard] = useState(null);
  const [realtimeStats, setRealtimeStats] = useState(null);
  const [revenueData, setRevenueData] = useState(null);
  const [userSegments, setUserSegments] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [featureDetail, setFeatureDetail] = useState(null);

  useEffect(() => {
    checkAdminAccess();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchAllData();
    }
  }, [isAdmin, days]);

  const checkAdminAccess = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const user = data.user || data;
        
        if (user.role?.toUpperCase() !== 'ADMIN') {
          toast.error('Access denied. Admin role required.');
          navigate('/app');
          return;
        }
        
        setIsAdmin(true);
      } else {
        navigate('/login');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      navigate('/login');
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [dashboardRes, realtimeRes, revenueRes, segmentsRes] = await Promise.all([
        fetch(`${API_URL}/api/template-analytics/dashboard?days=${days}`, { headers }),
        fetch(`${API_URL}/api/template-analytics/realtime`, { headers }),
        fetch(`${API_URL}/api/template-analytics/revenue-impact?days=${days}`, { headers }),
        fetch(`${API_URL}/api/template-analytics/user-segments?days=${days}`, { headers })
      ]);

      if (dashboardRes.ok) setDashboard(await dashboardRes.json());
      if (realtimeRes.ok) setRealtimeStats(await realtimeRes.json());
      if (revenueRes.ok) setRevenueData(await revenueRes.json());
      if (segmentsRes.ok) setUserSegments(await segmentsRes.json());

    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const fetchFeatureDetail = async (feature) => {
    setSelectedFeature(feature);
    const token = localStorage.getItem('token');
    
    try {
      const res = await fetch(`${API_URL}/api/template-analytics/feature/${feature}?days=${days}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        setFeatureDetail(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const formatFeatureName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getFeatureColor = (feature) => {
    const colors = {
      'instagram_bio_generator': 'from-pink-500 to-rose-500',
      'comment_reply_bank': 'from-blue-500 to-cyan-500',
      'bedtime_story_builder': 'from-purple-500 to-indigo-500',
      'youtube_thumbnail_generator': 'from-red-500 to-orange-500',
      'brand_story_builder': 'from-blue-500 to-sky-500',
      'offer_generator': 'from-green-500 to-emerald-500',
      'story_hook_generator': 'from-purple-500 to-pink-500',
      'daily_viral_ideas': 'from-orange-500 to-amber-500'
    };
    return colors[feature] || 'from-slate-500 to-gray-500';
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl text-white mb-2">Access Denied</h2>
          <p className="text-slate-400">Admin privileges required</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app/admin" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <BarChart3 className="w-6 h-6 text-purple-400" />
                Template Analytics
              </h1>
              <p className="text-slate-400 text-sm">Business Intelligence for template-based features</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={fetchAllData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>

        {/* Real-time Stats Bar */}
        {realtimeStats && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-green-400 font-medium">Live (Last Hour)</span>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-white">
                  <span className="text-2xl font-bold">{realtimeStats.total_generations}</span>
                  <span className="text-slate-400 text-sm ml-2">generations</span>
                </div>
                {realtimeStats.by_feature?.slice(0, 3).map((f, i) => (
                  <div key={i} className="text-slate-300 text-sm">
                    {formatFeatureName(f.feature)}: <span className="text-white font-medium">{f.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Main Stats Grid */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Activity className="w-4 h-4" /> Total Generations
              </div>
              <div className="text-3xl font-bold text-white">{dashboard.total_generations?.toLocaleString()}</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Coins className="w-4 h-4" /> Credits Consumed
              </div>
              <div className="text-3xl font-bold text-purple-400">{dashboard.total_credits_consumed?.toLocaleString()}</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Users className="w-4 h-4" /> Unique Users
              </div>
              <div className="text-3xl font-bold text-blue-400">{dashboard.total_unique_users?.toLocaleString()}</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <TrendingUp className="w-4 h-4" /> Conversion Rate
              </div>
              <div className="text-3xl font-bold text-green-400">{dashboard.conversion_rate}%</div>
            </div>
          </div>
        )}

        {/* Revenue Impact */}
        {revenueData && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-400" /> Revenue Impact
            </h2>
            <div className="grid md:grid-cols-3 gap-4 mb-6">
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-green-400">${revenueData.total_revenue_usd?.toLocaleString()}</div>
                <div className="text-slate-400 text-sm">Total Revenue ({days} days)</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-white">{revenueData.total_credits_consumed?.toLocaleString()}</div>
                <div className="text-slate-400 text-sm">Credits Consumed</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-purple-400">${revenueData.avg_daily_revenue}</div>
                <div className="text-slate-400 text-sm">Avg Daily Revenue</div>
              </div>
            </div>
            
            {/* Revenue by Feature */}
            <div className="space-y-3">
              {revenueData.by_feature?.map((f, i) => (
                <div key={i} className="flex items-center justify-between bg-slate-800/30 rounded-lg p-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-8 rounded bg-gradient-to-b ${getFeatureColor(f.feature)}`} />
                    <span className="text-white">{formatFeatureName(f.feature)}</span>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <span className="text-slate-400">{f.generations} gens</span>
                    <span className="text-purple-400">{f.credits_consumed} credits</span>
                    <span className="text-green-400 font-medium">${f.credit_value_usd}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Features Performance */}
        {dashboard?.features && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" /> Feature Performance
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {dashboard.features.map((feature, i) => (
                <div 
                  key={i}
                  onClick={() => fetchFeatureDetail(feature.feature)}
                  className={`bg-gradient-to-br ${getFeatureColor(feature.feature)} p-[1px] rounded-xl cursor-pointer hover:scale-[1.02] transition-transform`}
                >
                  <div className="bg-slate-900 rounded-xl p-4 h-full">
                    <div className="text-white font-medium mb-2">{formatFeatureName(feature.feature)}</div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-slate-400">Generations</div>
                        <div className="text-white font-bold">{feature.total_generations}</div>
                      </div>
                      <div>
                        <div className="text-slate-400">Users</div>
                        <div className="text-white font-bold">{feature.unique_users}</div>
                      </div>
                      <div>
                        <div className="text-slate-400">Credits</div>
                        <div className="text-purple-400 font-bold">{feature.credits_consumed}</div>
                      </div>
                      <div>
                        <div className="text-slate-400">Avg Time</div>
                        <div className="text-green-400 font-bold">{feature.avg_generation_time_ms}ms</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User Segments */}
        {userSegments && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <PieChart className="w-5 h-5 text-blue-400" /> User Segments
            </h2>
            <div className="grid md:grid-cols-5 gap-4">
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-purple-400">{userSegments.segments?.power_users || 0}</div>
                <div className="text-slate-300 text-sm">Power Users</div>
                <div className="text-xs text-slate-500">(50+ gens)</div>
              </div>
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-blue-400">{userSegments.segments?.regular_users || 0}</div>
                <div className="text-slate-300 text-sm">Regular Users</div>
                <div className="text-xs text-slate-500">(10-49 gens)</div>
              </div>
              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-green-400">{userSegments.segments?.casual_users || 0}</div>
                <div className="text-slate-300 text-sm">Casual Users</div>
                <div className="text-xs text-slate-500">(2-9 gens)</div>
              </div>
              <div className="bg-slate-500/10 border border-slate-500/30 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-slate-400">{userSegments.segments?.one_time || 0}</div>
                <div className="text-slate-300 text-sm">One-Time</div>
                <div className="text-xs text-slate-500">(1 gen)</div>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-amber-400">{userSegments.multi_feature_percent || 0}%</div>
                <div className="text-slate-300 text-sm">Multi-Feature</div>
                <div className="text-xs text-slate-500">Users</div>
              </div>
            </div>
          </div>
        )}

        {/* Trending */}
        {dashboard && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Trending Niches */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" /> Trending Niches
              </h3>
              <div className="space-y-3">
                {dashboard.trending_niches?.slice(0, 5).map((item, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-slate-300">{item.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-white font-medium">{item.count}</span>
                      <span className={`text-sm ${item.growth_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {item.growth_percent >= 0 ? '+' : ''}{item.growth_percent}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Trending Tones */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-400" /> Trending Tones
              </h3>
              <div className="space-y-3">
                {dashboard.trending_tones?.slice(0, 5).map((item, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-slate-300">{item.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-white font-medium">{item.count}</span>
                      <span className={`text-sm ${item.growth_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {item.growth_percent >= 0 ? '+' : ''}{item.growth_percent}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Feature Detail Modal */}
        {featureDetail && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setFeatureDetail(null)}>
            <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <h3 className="text-xl font-bold text-white mb-4">{formatFeatureName(featureDetail.feature)} Analytics</h3>
              
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white">{featureDetail.total_generations}</div>
                  <div className="text-slate-400 text-sm">Generations</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-400">{featureDetail.unique_users}</div>
                  <div className="text-slate-400 text-sm">Users</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-purple-400">{featureDetail.total_credits}</div>
                  <div className="text-slate-400 text-sm">Credits</div>
                </div>
              </div>

              {featureDetail.breakdowns && Object.keys(featureDetail.breakdowns).length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-white font-medium">Option Breakdown</h4>
                  {Object.entries(featureDetail.breakdowns).map(([key, values]) => (
                    <div key={key}>
                      <div className="text-slate-400 text-sm mb-2 capitalize">{key}</div>
                      <div className="flex flex-wrap gap-2">
                        {values.map((v, i) => (
                          <span key={i} className="px-2 py-1 bg-slate-800 rounded text-sm text-slate-300">
                            {v.value}: <span className="text-white">{v.count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => setFeatureDetail(null)}
                className="mt-6 w-full py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TemplateAnalyticsDashboard;
