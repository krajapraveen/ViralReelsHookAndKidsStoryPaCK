import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  ArrowLeft, BarChart3, TrendingUp, Activity, Clock,
  Sparkles, Video, Film, Calendar, Wand2, Palette,
  CreditCard, Download, RefreshCw
} from 'lucide-react';
import api from '../utils/api';
import HelpGuide from '../components/HelpGuide';

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setRefreshing(true);
    try {
      const response = await api.get('/api/analytics/user-stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const features = [
    { key: 'storySeries', label: 'Story Series', icon: Film, color: 'purple' },
    { key: 'challenges', label: 'Challenges', icon: Calendar, color: 'blue' },
    { key: 'toneRewrites', label: 'Tone Rewrites', icon: Wand2, color: 'green' },
    { key: 'coloringBooks', label: 'Coloring Books', icon: Palette, color: 'pink' },
    { key: 'totalGenerations', label: 'Total Generations', icon: Video, color: 'indigo' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-8 h-8 text-purple-400" />
                <div>
                  <h1 className="text-xl font-bold text-white">Your Analytics</h1>
                  <p className="text-xs text-slate-400">Track your usage and creations</p>
                </div>
              </div>
            </div>
            <Button
              onClick={fetchStats}
              disabled={refreshing}
              variant="outline"
              className="border-slate-700"
              data-testid="refresh-stats-btn"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Credit Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/30 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-2">
              <CreditCard className="w-5 h-5 text-green-400" />
              <p className="text-sm text-green-300">Current Balance</p>
            </div>
            <p className="text-4xl font-bold text-white">{stats?.currentBalance || 0}</p>
            <p className="text-xs text-green-400 mt-2">Credits available</p>
          </div>
          <div className="bg-gradient-to-br from-purple-500/20 to-pink-600/20 border border-purple-500/30 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              <p className="text-sm text-purple-300">Credits Used This Month</p>
            </div>
            <p className="text-4xl font-bold text-white">{stats?.creditsUsedThisMonth || 0}</p>
            <p className="text-xs text-purple-400 mt-2">Since start of month</p>
          </div>
        </div>

        {/* Feature Usage */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Feature Usage
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {features.map(({ key, label, icon: Icon, color }) => (
              <FeatureCard
                key={key}
                label={label}
                value={stats?.[key] || 0}
                Icon={Icon}
                color={color}
              />
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            <Link to="/app/history">
              <Button variant="outline" className="border-slate-700 hover:bg-slate-800">
                <Clock className="w-4 h-4 mr-2" />
                View History
              </Button>
            </Link>
            <Link to="/app/billing">
              <Button variant="outline" className="border-slate-700 hover:bg-slate-800">
                <CreditCard className="w-4 h-4 mr-2" />
                Buy More Credits
              </Button>
            </Link>
            <Link to="/app/subscription">
              <Button variant="outline" className="border-slate-700 hover:bg-slate-800">
                <TrendingUp className="w-4 h-4 mr-2" />
                Manage Subscription
              </Button>
            </Link>
          </div>
        </div>
      </main>
      
      {/* Help Guide */}
      <HelpGuide pageId="analytics" />
    </div>
  );
}

function FeatureCard({ label, value, Icon, color }) {
  const colors = {
    purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30 text-purple-400',
    blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30 text-blue-400',
    green: 'from-green-500/20 to-green-600/20 border-green-500/30 text-green-400',
    pink: 'from-pink-500/20 to-pink-600/20 border-pink-500/30 text-pink-400',
    yellow: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30 text-yellow-400',
    indigo: 'from-indigo-500/20 to-indigo-600/20 border-indigo-500/30 text-indigo-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-4`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className={`w-5 h-5 ${colors[color].split(' ').pop()}`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  );
}
