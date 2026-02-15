import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  Sparkles, Users, CreditCard, FileText, ArrowLeft, TrendingUp, 
  CheckCircle, XCircle, Eye, MousePointerClick, Star, ThumbsUp,
  BarChart3, PieChart, Activity, DollarSign, Calendar, AlertCircle,
  Monitor, Smartphone, Globe, RefreshCw, Lightbulb, ThumbsDown, MessageSquare
} from 'lucide-react';

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [featureRequests, setFeatureRequests] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [dateRange, setDateRange] = useState(30);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAnalytics();
  }, [dateRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [analyticsRes, featuresRes] = await Promise.all([
        api.get(`/api/admin/analytics/dashboard?days=${dateRange}`),
        api.get('/api/feature-requests/analytics').catch(() => ({ data: { success: false } }))
      ]);
      
      if (analyticsRes.data.success) {
        setAnalytics(analyticsRes.data.data);
      }
      if (featuresRes.data.success) {
        setFeatureRequests(featuresRes.data.data);
      }
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/app');
      } else {
        toast.error('Failed to load analytics data');
      }
    } finally {
      setLoading(false);
    }
  };

  const updateFeatureStatus = async (featureId, status, adminResponse) => {
    try {
      await api.put(`/api/feature-requests/${featureId}/status`, { status, adminResponse });
      toast.success('Status updated');
      fetchAnalytics();
    } catch (error) {
      toast.error('Failed to update status');
    }
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

  const { overview, visitors, featureUsage, payments, satisfaction, generations, recentActivity } = analytics || {};

  return (
    <div className="min-h-screen bg-slate-900 text-white">
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
          <div className="flex items-center gap-4">
            <select 
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
            </select>
            <Button onClick={fetchAnalytics} variant="outline" size="sm" className="border-slate-600">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Overview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <StatCard 
            icon={<Users className="w-5 h-5" />}
            label="Total Users"
            value={overview?.totalUsers || 0}
            subValue={`+${overview?.newUsers || 0} new`}
            color="blue"
          />
          <StatCard 
            icon={<Eye className="w-5 h-5" />}
            label="Visitors"
            value={visitors?.uniqueVisitors || 0}
            subValue={`${visitors?.totalPageViews || 0} page views`}
            color="green"
          />
          <StatCard 
            icon={<Activity className="w-5 h-5" />}
            label="Active Sessions"
            value={overview?.activeSessions || 0}
            color="purple"
          />
          <StatCard 
            icon={<FileText className="w-5 h-5" />}
            label="Generations"
            value={overview?.totalGenerations || 0}
            subValue={`${generations?.successRate || 100}% success`}
            color="indigo"
          />
          <StatCard 
            icon={<DollarSign className="w-5 h-5" />}
            label="Total Revenue"
            value={`₹${overview?.totalRevenue || 0}`}
            subValue={`₹${overview?.periodRevenue || 0} this period`}
            color="emerald"
          />
          <StatCard 
            icon={<Star className="w-5 h-5" />}
            label="Satisfaction"
            value={`${satisfaction?.satisfactionPercentage || 0}%`}
            subValue={`${satisfaction?.averageRating || 0}/5 rating`}
            color="yellow"
          />
        </div>

        {/* Tabs */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="border-b border-slate-700 flex overflow-x-auto">
            {['overview', 'visitors', 'features', 'payments', 'satisfaction'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab 
                    ? 'border-b-2 border-purple-500 text-purple-400 bg-slate-700/50' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
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
            {activeTab === 'satisfaction' && <SatisfactionTab satisfaction={satisfaction} />}
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ icon, label, value, subValue, color }) {
  const colors = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    purple: 'bg-purple-500/20 text-purple-400',
    indigo: 'bg-indigo-500/20 text-indigo-400',
    emerald: 'bg-emerald-500/20 text-emerald-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    red: 'bg-red-500/20 text-red-400',
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${colors[color]}`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
      {subValue && <div className="text-xs text-slate-500 mt-1">{subValue}</div>}
    </div>
  );
}

// Overview Tab
function OverviewTab({ visitors, generations, recentActivity }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Daily Visitors Chart */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" />
          Daily Visitors
        </h3>
        <div className="space-y-2">
          {visitors?.dailyTrend?.slice(-7).map((day, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-20">{day.date}</span>
              <div className="flex-1 bg-slate-600 rounded-full h-4">
                <div 
                  className="bg-purple-500 h-4 rounded-full"
                  style={{ width: `${Math.min((day.visitors / (visitors?.uniqueVisitors || 1)) * 500, 100)}%` }}
                />
              </div>
              <span className="text-sm text-slate-300 w-12 text-right">{day.visitors}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Generation Stats */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5 text-indigo-400" />
          Generation Stats
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-indigo-400">{generations?.reelGenerations || 0}</div>
            <div className="text-sm text-slate-400">Reel Scripts</div>
          </div>
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-purple-400">{generations?.storyGenerations || 0}</div>
            <div className="text-sm text-slate-400">Story Videos</div>
          </div>
          <div className="col-span-2 text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-2xl font-bold text-green-400">{generations?.creditsUsed || 0}</div>
            <div className="text-sm text-slate-400">Credits Used</div>
          </div>
        </div>
      </div>

      {/* Recent Users */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-blue-400" />
          Recent Users
        </h3>
        <div className="space-y-2">
          {recentActivity?.recentUsers?.slice(0, 5).map((user, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <div>
                <div className="text-sm font-medium">{user.name}</div>
                <div className="text-xs text-slate-400">{user.email}</div>
              </div>
              <div className="text-xs text-slate-500">{new Date(user.createdAt).toLocaleDateString()}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Payments */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-emerald-400" />
          Recent Payments
        </h3>
        <div className="space-y-2">
          {recentActivity?.recentPayments?.slice(0, 5).map((payment, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <div>
                <div className="text-sm font-medium">₹{payment.amount}</div>
                <div className="text-xs text-slate-400">{payment.product}</div>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                payment.status === 'PAID' ? 'bg-green-500/20 text-green-400' :
                payment.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>
                {payment.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Visitors Tab
function VisitorsTab({ visitors }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Visitor Summary */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Visitor Summary</h3>
        <div className="space-y-4">
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Unique Visitors</span>
            <span className="text-xl font-bold">{visitors?.uniqueVisitors || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Total Page Views</span>
            <span className="text-xl font-bold">{visitors?.totalPageViews || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Anonymous Visitors</span>
            <span className="text-xl font-bold">{visitors?.anonymousVisitors || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Logged-in Users</span>
            <span className="text-xl font-bold">{visitors?.loggedInVisitors || 0}</span>
          </div>
        </div>
      </div>

      {/* Page Views */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Top Pages</h3>
        <div className="space-y-2">
          {visitors?.pageViews?.slice(0, 8).map((page, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm text-slate-300 flex-1 truncate">{page.page || 'Home'}</span>
              <span className="text-sm font-medium text-purple-400">{page.views}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Device Distribution */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Monitor className="w-5 h-5 text-blue-400" />
          Device Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(visitors?.deviceDistribution || {}).map(([device, count], i) => (
            <div key={i} className="flex items-center gap-3">
              {device === 'Desktop' ? <Monitor className="w-4 h-4 text-slate-400" /> :
               device === 'Mobile' ? <Smartphone className="w-4 h-4 text-slate-400" /> :
               <Globe className="w-4 h-4 text-slate-400" />}
              <span className="text-sm text-slate-300 flex-1">{device}</span>
              <span className="text-sm font-medium">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Browser Distribution */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-green-400" />
          Browser Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(visitors?.browserDistribution || {}).map(([browser, count], i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm text-slate-300 flex-1">{browser}</span>
              <span className="text-sm font-medium">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Features Tab
function FeaturesTab({ featureUsage }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Top Features */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MousePointerClick className="w-5 h-5 text-purple-400" />
          Most Used Features
        </h3>
        <div className="space-y-3">
          {featureUsage?.topFeatures?.map((feature, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-6 h-6 flex items-center justify-center bg-purple-500/20 text-purple-400 rounded-full text-xs font-bold">
                {i + 1}
              </span>
              <span className="text-sm text-slate-300 flex-1">{formatFeatureName(feature.feature)}</span>
              <span className="text-sm font-medium text-purple-400">{feature.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Usage Percentage */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5 text-indigo-400" />
          Usage Distribution
        </h3>
        <div className="space-y-3">
          {featureUsage?.featurePercentages?.slice(0, 8).map((feature, i) => (
            <div key={i}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{formatFeatureName(feature.feature)}</span>
                <span className="text-slate-400">{feature.percentage}%</span>
              </div>
              <div className="h-2 bg-slate-600 rounded-full">
                <div 
                  className="h-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                  style={{ width: `${feature.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Unique Users per Feature */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-blue-400" />
          Unique Users per Feature
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {featureUsage?.uniqueUsersPerFeature?.slice(0, 8).map((feature, i) => (
            <div key={i} className="text-center p-3 bg-slate-600/50 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">{feature.uniqueUsers}</div>
              <div className="text-xs text-slate-400 mt-1">{formatFeatureName(feature.feature)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Payments Tab
function PaymentsTab({ payments }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Transaction Summary */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-emerald-400" />
          Transaction Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-white">{payments?.totalTransactions || 0}</div>
            <div className="text-sm text-slate-400">Total</div>
          </div>
          <div className="text-center p-4 bg-green-500/10 rounded-lg">
            <div className="text-3xl font-bold text-green-400">{payments?.successfulTransactions || 0}</div>
            <div className="text-sm text-slate-400">Successful</div>
          </div>
          <div className="text-center p-4 bg-red-500/10 rounded-lg">
            <div className="text-3xl font-bold text-red-400">{payments?.failedTransactions || 0}</div>
            <div className="text-sm text-slate-400">Failed</div>
          </div>
          <div className="text-center p-4 bg-yellow-500/10 rounded-lg">
            <div className="text-3xl font-bold text-yellow-400">{payments?.pendingTransactions || 0}</div>
            <div className="text-sm text-slate-400">Pending</div>
          </div>
        </div>
        <div className="mt-4 p-4 bg-slate-600/50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-slate-300">Success Rate</span>
            <span className="text-2xl font-bold text-green-400">{payments?.successRate || 0}%</span>
          </div>
        </div>
      </div>

      {/* Subscription Plans */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          Subscriptions by Plan
        </h3>
        <div className="space-y-3">
          {payments?.planBreakdown?.map((plan, i) => (
            <div key={i} className="p-3 bg-slate-600/50 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium">{plan.productName}</span>
                <span className="text-purple-400 font-bold">{plan.count} sales</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                Revenue: ₹{plan.revenue}
              </div>
            </div>
          ))}
          {(!payments?.planBreakdown || payments.planBreakdown.length === 0) && (
            <div className="text-center text-slate-400 py-4">No subscription data yet</div>
          )}
        </div>
      </div>

      {/* Failure Reasons */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          Failed Transaction Reasons
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {payments?.failureReasons?.map((reason, i) => (
            <div key={i} className="text-center p-4 bg-red-500/10 rounded-lg">
              <div className="text-2xl font-bold text-red-400">{reason.count || 0}</div>
              <div className="text-xs text-slate-400 mt-1">{reason.reason}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Daily Revenue Trend */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          Daily Revenue Trend
        </h3>
        <div className="space-y-2">
          {payments?.dailyRevenueTrend?.slice(-10).map((day, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-24">{day.date}</span>
              <div className="flex-1 bg-slate-600 rounded-full h-4">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-green-400 h-4 rounded-full"
                  style={{ width: `${Math.min((Number(day.revenue) / 10000) * 100, 100)}%` }}
                />
              </div>
              <span className="text-sm text-emerald-400 w-20 text-right">₹{day.revenue}</span>
              <span className="text-xs text-slate-500 w-16 text-right">{day.count} txn</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Satisfaction Tab
function SatisfactionTab({ satisfaction }) {
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

// Helper function to format feature names
function formatFeatureName(name) {
  if (!name) return 'Unknown';
  return name
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (l) => l.toUpperCase());
}
