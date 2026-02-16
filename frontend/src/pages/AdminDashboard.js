import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  Sparkles, Users, CreditCard, FileText, ArrowLeft, 
  Eye, Star, RefreshCw, Activity, DollarSign, LogOut
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

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'visitors', label: 'Visitors' },
    { id: 'features', label: 'Features' },
    { id: 'payments', label: 'Payments' },
    { id: 'satisfaction', label: 'Satisfaction' },
    { id: 'feature-requests', label: '💡 Feature Requests' },
    { id: 'feedback', label: '📝 User Feedback' },
  ];

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
            {activeTab === 'satisfaction' && <SatisfactionTab satisfaction={satisfaction} />}
            {activeTab === 'feature-requests' && (
              <FeatureRequestsTab data={featureRequests} onUpdateStatus={updateFeatureStatus} />
            )}
            {activeTab === 'feedback' && <UserFeedbackTab />}
          </div>
        </div>
      </div>
    </div>
  );
}
