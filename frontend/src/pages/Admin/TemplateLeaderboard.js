import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Shield, Trophy, TrendingUp, 
  DollarSign, BarChart3, Download, Zap, Medal
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TemplateLeaderboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [days, setDays] = useState(30);
  
  // Data
  const [rankings, setRankings] = useState([]);
  const [summary, setSummary] = useState(null);
  const [topPerformers, setTopPerformers] = useState(null);
  const [growthTrends, setGrowthTrends] = useState(null);

  useEffect(() => {
    checkAdminAccess();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchData();
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
      navigate('/login');
    }
  };

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [rankingsRes, performersRes, trendsRes] = await Promise.all([
        fetch(`${API_URL}/api/template-leaderboard/revenue-rankings?days=${days}&limit=20`, { headers }),
        fetch(`${API_URL}/api/template-leaderboard/top-performers?days=${days}`, { headers }),
        fetch(`${API_URL}/api/template-leaderboard/growth-trends?days=${days}`, { headers })
      ]);

      if (rankingsRes.ok) {
        const data = await rankingsRes.json();
        setRankings(data.rankings || []);
        setSummary(data.summary || null);
      }

      if (performersRes.ok) {
        setTopPerformers(await performersRes.json());
      }

      if (trendsRes.ok) {
        setGrowthTrends(await trendsRes.json());
      }
    } catch (error) {
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format, type) => {
    try {
      const token = localStorage.getItem('token');
      const url = format === 'csv' 
        ? `${API_URL}/api/template-leaderboard/export/csv?days=${days}&report_type=${type}`
        : `${API_URL}/api/template-leaderboard/export/json?days=${days}`;
      
      const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });

      if (res.ok) {
        const data = await res.json();
        
        const blob = format === 'csv' 
          ? new Blob([data.data], { type: 'text/csv' })
          : new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
        
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = data.filename || `analytics_${format}.${format}`;
        a.click();
        
        toast.success(`Exported ${format.toUpperCase()}`);
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const getMedalIcon = (rank) => {
    if (rank === 1) return <Medal className="w-5 h-5 text-yellow-400" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-slate-300" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-600" />;
    return <span className="w-5 h-5 text-center text-slate-500 text-sm">#{rank}</span>;
  };

  const formatFeatureName = (name) => {
    return name?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown';
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <Shield className="w-16 h-16 text-red-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-amber-950 to-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app/admin" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Trophy className="w-6 h-6 text-amber-400" />
                Template Performance Leaderboard
              </h1>
              <p className="text-slate-400 text-sm">Which templates generate the most revenue?</p>
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
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
            <button
              onClick={() => handleExport('csv', 'summary')}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg"
            >
              <Download className="w-4 h-4" /> Export
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            {summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-green-400 mb-2">
                    <DollarSign className="w-5 h-5" />
                    <span className="text-sm">Total Revenue</span>
                  </div>
                  <div className="text-3xl font-bold text-white">${summary.total_revenue_usd?.toLocaleString()}</div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-slate-400 mb-2">
                    <Zap className="w-5 h-5" />
                    <span className="text-sm">Generations</span>
                  </div>
                  <div className="text-3xl font-bold text-white">{summary.total_generations?.toLocaleString()}</div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-slate-400 mb-2">
                    <BarChart3 className="w-5 h-5" />
                    <span className="text-sm">Avg/Generation</span>
                  </div>
                  <div className="text-3xl font-bold text-purple-400">${summary.avg_revenue_per_gen}</div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-slate-400 mb-2">
                    <TrendingUp className="w-5 h-5" />
                    <span className="text-sm">Period</span>
                  </div>
                  <div className="text-3xl font-bold text-blue-400">{days} days</div>
                </div>
              </div>
            )}

            {/* Revenue Rankings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Trophy className="w-5 h-5 text-amber-400" />
                Revenue Rankings
              </h2>
              
              <div className="space-y-3">
                {rankings.map((item) => (
                  <div 
                    key={item.rank}
                    className={`flex items-center justify-between p-4 rounded-xl ${
                      item.rank <= 3 ? 'bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30' : 'bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      {getMedalIcon(item.rank)}
                      <div>
                        <div className="text-white font-medium">{formatFeatureName(item.feature)}</div>
                        <div className="flex gap-2 text-xs text-slate-400">
                          {item.niche !== 'N/A' && <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">{item.niche}</span>}
                          {item.tone !== 'N/A' && <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">{item.tone}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <div className="text-center">
                        <div className="text-slate-400 text-xs">Generations</div>
                        <div className="text-white font-medium">{item.generations}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-slate-400 text-xs">Users</div>
                        <div className="text-white font-medium">{item.unique_users}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-slate-400 text-xs">Credits</div>
                        <div className="text-purple-400 font-medium">{item.credits_generated}</div>
                      </div>
                      <div className="text-center min-w-[80px]">
                        <div className="text-slate-400 text-xs">Revenue</div>
                        <div className="text-green-400 font-bold text-lg">${item.revenue_usd}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Growth Trends */}
            {growthTrends?.trends && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  Growth Trends (vs Previous Period)
                </h2>
                
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {growthTrends.trends.map((item, i) => (
                    <div key={i} className="bg-slate-800/50 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-white font-medium">{formatFeatureName(item.feature)}</span>
                        <span className={`text-sm font-bold ${
                          item.trend === 'up' ? 'text-green-400' : item.trend === 'down' ? 'text-red-400' : 'text-slate-400'
                        }`}>
                          {item.growth_percent >= 0 ? '+' : ''}{item.growth_percent}%
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-400">
                        <span>Current: {item.current_period}</span>
                        <span>Previous: {item.previous_period}</span>
                      </div>
                      <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            item.trend === 'up' ? 'bg-green-500' : item.trend === 'down' ? 'bg-red-500' : 'bg-slate-500'
                          }`}
                          style={{ width: `${Math.min(Math.abs(item.growth_percent), 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Performers */}
            {topPerformers && (
              <div className="grid md:grid-cols-2 gap-6">
                {/* Top Niches */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4">Top Niches</h3>
                  <div className="space-y-2">
                    {topPerformers.top_niches?.map((item, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-slate-300">{item.niche}</span>
                        <span className="text-white font-medium">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Tones */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-white mb-4">Top Tones</h3>
                  <div className="space-y-2">
                    {topPerformers.top_tones?.map((item, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-slate-300">{item.tone}</span>
                        <span className="text-white font-medium">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TemplateLeaderboard;
