import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  Sparkles, Users, CreditCard, FileText, ArrowLeft, 
  Eye, Star, RefreshCw, Activity, DollarSign, LogOut, Coins, Shield, BarChart3,
  AlertTriangle, Trophy, ClipboardList, Database, Radio
} from 'lucide-react';

// Import tab components
import StatCard from '../components/admin/StatCard';
import OverviewTab from '../components/admin/OverviewTab';
import VisitorsTab from '../components/admin/VisitorsTab';
import FeaturesTab from '../components/admin/FeaturesTab';
import PaymentsTab from '../components/admin/PaymentsTab';
import SatisfactionTab from '../components/admin/SatisfactionTab';
import FeatureRequestsTab from '../components/admin/FeatureRequestsTab';
import UserFeedbackTab from '../components/admin/UserFeedbackTab';
import TrendingTopicsTab from '../components/admin/TrendingTopicsTab';
import PaymentMonitoringTab from '../components/admin/PaymentMonitoringTab';
import ExceptionMonitoringTab from '../components/admin/ExceptionMonitoringTab';
import UserAnalyticsTab from '../components/admin/UserAnalyticsTab';
import HelpGuide from '../components/HelpGuide';

// Default fallback data structure for graceful degradation
const defaultAnalytics = {
  overview: { totalUsers: 0, newUsers: 0, activeSessions: 0, totalGenerations: 0, totalRevenue: 0, periodRevenue: 0 },
  visitors: { uniqueVisitors: 0, totalPageViews: 0 },
  featureUsage: [],
  payments: { totalAmount: 0, successfulPayments: 0 },
  satisfaction: { satisfactionPercentage: 0, averageRating: 0 },
  generations: { successRate: 100 },
  recentActivity: []
};

export default function AdminDashboard() {
  // Individual state for each data source for better resilience
  const [analytics, setAnalytics] = useState(defaultAnalytics);
  const [featureRequests, setFeatureRequests] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [dateRange, setDateRange] = useState(30);
  const [apiErrors, setApiErrors] = useState({ analytics: null, features: null });
  const navigate = useNavigate();

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    const errors = { analytics: null, features: null };
    
    // Fetch analytics data with individual error handling
    try {
      const analyticsRes = await api.get(`/api/admin/analytics/dashboard?days=${dateRange}`);
      if (analyticsRes.data.success && analyticsRes.data.data) {
        setAnalytics(prev => ({ ...defaultAnalytics, ...analyticsRes.data.data }));
      } else {
        errors.analytics = 'Invalid response format';
        console.warn('Analytics API returned invalid format');
      }
    } catch (error) {
      const status = error.response?.status;
      if (status === 403) {
        toast.error('Admin access required');
        navigate('/app');
        return;
      } else if (status === 401) {
        // Let axios interceptor handle auth redirect
        return;
      }
      errors.analytics = error.message || 'Failed to load analytics';
      console.error('Analytics API error:', status, error.message);
      // Keep existing data or use defaults - don't clear
    }

    // Fetch feature requests data independently
    // Note: This is an optional feature - 404 means it's not deployed, don't show error
    try {
      const featuresRes = await api.get('/api/feature-requests/analytics');
      if (featuresRes.data.success) {
        setFeatureRequests(featuresRes.data.data);
      }
      // Silent fail for invalid format - not critical
    } catch (error) {
      const status = error.response?.status;
      // Only log 404s silently - feature not available in this deployment
      if (status !== 404) {
        errors.features = error.message || 'Failed to load feature requests';
        console.error('Feature requests API error:', error.message);
      }
      // Keep existing feature requests data
    }

    setApiErrors(errors);
    setLoading(false);
  }, [dateRange, navigate]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const updateFeatureStatus = async (featureId, status, adminResponse) => {
    try {
      await api.put(`/api/feature-requests/${featureId}/status`, { status, adminResponse });
      toast.success('Status updated');
      fetchAnalytics();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading analytics...</p>
        </div>
      </div>
    );
  }

  // Extract data with fallbacks to prevent undefined errors
  const { 
    overview = defaultAnalytics.overview, 
    visitors = defaultAnalytics.visitors, 
    featureUsage = defaultAnalytics.featureUsage, 
    payments = defaultAnalytics.payments, 
    satisfaction = defaultAnalytics.satisfaction, 
    generations = defaultAnalytics.generations, 
    recentActivity = defaultAnalytics.recentActivity 
  } = analytics;

  // Helper to format values with error state
  const formatValue = (value, hasError, prefix = '', suffix = '') => {
    if (hasError && (value === 0 || value === undefined || value === null)) {
      return 'N/A';
    }
    return `${prefix}${value ?? 0}${suffix}`;
  };

  const hasAnalyticsError = apiErrors.analytics !== null;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'visitors', label: 'Visitors' },
    { id: 'features', label: 'Features' },
    { id: 'payments', label: 'Payments' },
    { id: 'payment-monitoring', label: '💰 Payment Monitor' },
    { id: 'exceptions', label: '⚠️ Exceptions' },
    { id: 'satisfaction', label: 'Satisfaction' },
    { id: 'user-analytics', label: '📊 User Analytics' },
    { id: 'feature-requests', label: '💡 Feature Requests' },
    { id: 'feedback', label: '📝 User Feedback' },
    { id: 'trending', label: '📈 Trending Topics' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-500" />
              <span className="text-xl font-bold">Admin Analytics</span>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
            <Link to="/app/admin/users">
              <Button variant="outline" size="sm" className="border-yellow-500/50 text-yellow-300 hover:bg-yellow-500/20">
                <Coins className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">User Credits</span>
              </Button>
            </Link>
            <Link to="/app/admin/login-activity">
              <Button variant="outline" size="sm" className="border-blue-500/50 text-blue-300 hover:bg-blue-500/20">
                <Users className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Login Activity</span>
              </Button>
            </Link>
            <Link to="/app/admin/realtime-analytics">
              <Button variant="outline" size="sm" className="border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/20" data-testid="realtime-analytics-btn">
                <Activity className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Live Analytics</span>
              </Button>
            </Link>
            <Link to="/app/admin/monitoring">
              <Button variant="outline" size="sm" className="border-green-500/50 text-green-300 hover:bg-green-500/20">
                <Activity className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Monitoring</span>
              </Button>
            </Link>
            <Link to="/app/admin/self-healing">
              <Button variant="outline" size="sm" className="border-purple-500/50 text-purple-300 hover:bg-purple-500/20" data-testid="self-healing-btn">
                <Shield className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Self-Healing</span>
              </Button>
            </Link>
            <Link to="/app/admin/user-analytics">
              <Button variant="outline" size="sm" className="border-amber-500/50 text-amber-300 hover:bg-amber-500/20" data-testid="user-analytics-btn">
                <BarChart3 className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Ratings</span>
              </Button>
            </Link>
            <Link to="/app/admin/bio-templates">
              <Button variant="outline" size="sm" className="border-pink-500/50 text-pink-300 hover:bg-pink-500/20" data-testid="bio-templates-btn">
                <FileText className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Bio Templates</span>
              </Button>
            </Link>
            <Link to="/app/admin/template-analytics">
              <Button variant="outline" size="sm" className="border-cyan-500/50 text-cyan-300 hover:bg-cyan-500/20" data-testid="template-analytics-btn">
                <BarChart3 className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Template BI</span>
              </Button>
            </Link>
            <Link to="/app/admin/leaderboard">
              <Button variant="outline" size="sm" className="border-amber-500/50 text-amber-300 hover:bg-amber-500/20" data-testid="leaderboard-btn">
                <Trophy className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Leaderboard</span>
              </Button>
            </Link>
            <Link to="/app/admin/audit-logs">
              <Button variant="outline" size="sm" className="border-red-500/50 text-red-300 hover:bg-red-500/20" data-testid="audit-logs-btn">
                <ClipboardList className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Audit Logs</span>
              </Button>
            </Link>
            <Link to="/app/admin/environment-monitor">
              <Button variant="outline" size="sm" className="border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/20" data-testid="env-monitor-btn">
                <Database className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">DB Monitor</span>
              </Button>
            </Link>
            <Link to="/app/admin/user-activity">
              <Button variant="outline" size="sm" className="border-green-500/50 text-green-300 hover:bg-green-500/20 animate-pulse" data-testid="user-activity-btn">
                <Radio className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Live Activity</span>
              </Button>
            </Link>
            <select 
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm hidden sm:block"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
            </select>
            <Button onClick={fetchAnalytics} variant="outline" size="sm" className="border-slate-600">
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button onClick={handleLogout} variant="ghost" size="sm" className="text-slate-300 hover:text-white" data-testid="admin-logout-btn">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Error Banner - Show when some data failed to load */}
      {(apiErrors.analytics || apiErrors.features) && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-amber-300 text-sm">
                Some dashboard data couldn't be loaded.
                {apiErrors.analytics && <span className="text-amber-400/80"> Analytics: {apiErrors.analytics}.</span>}
                {apiErrors.features && <span className="text-amber-400/80"> Feature Requests: {apiErrors.features}.</span>}
              </p>
            </div>
            <Button 
              onClick={fetchAnalytics} 
              variant="outline" 
              size="sm" 
              className="border-amber-500/50 text-amber-300 hover:bg-amber-500/20"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <StatCard 
            icon={<Users className="w-5 h-5" />}
            label="Total Users"
            value={formatValue(overview?.totalUsers, hasAnalyticsError)}
            subValue={hasAnalyticsError ? 'Data unavailable' : `+${overview?.newUsers || 0} new`}
            color="blue"
            hasError={hasAnalyticsError}
          />
          <StatCard 
            icon={<Eye className="w-5 h-5" />}
            label="Visitors"
            value={formatValue(visitors?.uniqueVisitors, hasAnalyticsError)}
            subValue={hasAnalyticsError ? 'Data unavailable' : `${visitors?.totalPageViews || 0} page views`}
            color="green"
            hasError={hasAnalyticsError}
          />
          <StatCard 
            icon={<Activity className="w-5 h-5" />}
            label="Active Sessions"
            value={formatValue(overview?.activeSessions, hasAnalyticsError)}
            color="purple"
            hasError={hasAnalyticsError}
          />
          <StatCard 
            icon={<FileText className="w-5 h-5" />}
            label="Generations"
            value={formatValue(overview?.totalGenerations, hasAnalyticsError)}
            subValue={hasAnalyticsError ? 'Data unavailable' : `${generations?.successRate || 100}% success`}
            color="indigo"
            hasError={hasAnalyticsError}
          />
          <StatCard 
            icon={<DollarSign className="w-5 h-5" />}
            label="Total Revenue"
            value={hasAnalyticsError ? 'N/A' : `₹${overview?.totalRevenue || 0}`}
            subValue={hasAnalyticsError ? 'Data unavailable' : `₹${overview?.periodRevenue || 0} this period`}
            color="emerald"
            hasError={hasAnalyticsError}
          />
          <StatCard 
            icon={<Star className="w-5 h-5" />}
            label="Satisfaction"
            value={hasAnalyticsError ? 'N/A' : `${satisfaction?.satisfactionPercentage || 0}%`}
            subValue={hasAnalyticsError ? 'Data unavailable' : `${satisfaction?.averageRating || 0}/5 rating`}
            color="yellow"
            hasError={hasAnalyticsError}
          />
        </div>

        {/* Tabs */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="border-b border-slate-700 flex overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id 
                    ? 'border-b-2 border-purple-500 text-purple-400 bg-slate-700/50' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'overview' && (
              <OverviewTab 
                visitors={visitors} 
                generations={generations}
                recentActivity={recentActivity}
              />
            )}
            {activeTab === 'visitors' && <VisitorsTab visitors={visitors} />}
            {activeTab === 'features' && <FeaturesTab featureUsage={featureUsage} />}
            {activeTab === 'payments' && <PaymentsTab payments={payments} />}
            {activeTab === 'payment-monitoring' && <PaymentMonitoringTab />}
            {activeTab === 'exceptions' && <ExceptionMonitoringTab />}
            {activeTab === 'satisfaction' && <SatisfactionTab satisfaction={satisfaction} />}
            {activeTab === 'user-analytics' && <UserAnalyticsTab dateRange={dateRange} />}
            {activeTab === 'feature-requests' && (
              <FeatureRequestsTab data={featureRequests} onUpdateStatus={updateFeatureStatus} />
            )}
            {activeTab === 'feedback' && <UserFeedbackTab />}
            {activeTab === 'trending' && <TrendingTopicsTab />}
          </div>
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="admin" />
    </div>
  );
}
