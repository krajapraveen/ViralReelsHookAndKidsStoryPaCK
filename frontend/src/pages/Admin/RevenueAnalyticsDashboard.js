import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, DollarSign, TrendingUp, Users, 
  CreditCard, Download, Filter, Search, ChevronLeft, ChevronRight,
  Calendar, PieChart, BarChart3, AlertCircle, CheckCircle, 
  XCircle, Clock, Eye, ArrowUpRight, ArrowDownRight, FileSpreadsheet,
  Globe, Smartphone, Monitor, Tablet, UserCheck, UserX
} from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Summary Card Component
const SummaryCard = ({ title, value, subValue, icon: Icon, color, trend }) => {
  const colorClasses = {
    green: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    amber: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    pink: 'bg-pink-500/20 text-pink-400 border-pink-500/30'
  };
  
  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]} backdrop-blur-sm`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-5 h-5" />
        {trend !== undefined && (
          <span className={`text-xs flex items-center ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm opacity-70">{title}</p>
      {subValue && <p className="text-xs opacity-50 mt-1">{subValue}</p>}
    </div>
  );
};

// Status Badge Component
const StatusBadge = ({ status }) => {
  const statusConfig = {
    PAID: { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50', icon: CheckCircle },
    PENDING: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/50', icon: Clock },
    FAILED: { color: 'bg-red-500/20 text-red-400 border-red-500/50', icon: XCircle },
    CANCELLED: { color: 'bg-slate-500/20 text-slate-400 border-slate-500/50', icon: XCircle },
    REFUNDED: { color: 'bg-purple-500/20 text-purple-400 border-purple-500/50', icon: AlertCircle },
    PARTIALLY_REFUNDED: { color: 'bg-orange-500/20 text-orange-400 border-orange-500/50', icon: AlertCircle }
  };
  
  const config = statusConfig[status] || statusConfig.PENDING;
  const Icon = config.icon;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${config.color}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
};

// Device Icon Component
const DeviceIcon = ({ type }) => {
  const icons = {
    mobile: Smartphone,
    desktop: Monitor,
    tablet: Tablet
  };
  const Icon = icons[type?.toLowerCase()] || Monitor;
  return <Icon className="w-4 h-4 text-slate-400" />;
};

export default function RevenueAnalyticsDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  
  // Data states
  const [summary, setSummary] = useState(null);
  const [subscriptions, setSubscriptions] = useState(null);
  const [topups, setTopups] = useState(null);
  const [trends, setTrends] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [topUsers, setTopUsers] = useState([]);
  const [locationData, setLocationData] = useState([]);
  const [popularProducts, setPopularProducts] = useState([]);
  
  // UI states
  const [activeTab, setActiveTab] = useState('overview');
  const [trendPeriod, setTrendPeriod] = useState('day');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  
  // Transaction filters
  const [filters, setFilters] = useState({
    status: '',
    productType: '',
    userEmail: '',
    country: ''
  });
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ total: 0, totalPages: 1 });
  
  // Modal states
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [transactionDetail, setTransactionDetail] = useState(null);
  const [userHistory, setUserHistory] = useState(null);

  useEffect(() => {
    checkAdminAccess();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      fetchAllData();
    }
  }, [isAdmin, dateRange]);

  useEffect(() => {
    if (isAdmin) {
      fetchTransactions();
    }
  }, [isAdmin, filters, page]);

  useEffect(() => {
    if (isAdmin) {
      fetchTrends();
    }
  }, [isAdmin, trendPeriod]);

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

  const fetchWithAuth = async (url) => {
    const token = localStorage.getItem('token');
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) throw new Error(`Failed to fetch ${url}`);
    return response.json();
  };

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);
      const queryString = params.toString() ? `?${params.toString()}` : '';

      const [summaryRes, subsRes, topupsRes, topUsersRes, locationRes, productsRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/api/revenue-analytics/summary${queryString}`),
        fetchWithAuth(`${API_URL}/api/revenue-analytics/subscriptions${queryString}`),
        fetchWithAuth(`${API_URL}/api/revenue-analytics/topups${queryString}`),
        fetchWithAuth(`${API_URL}/api/revenue-analytics/top-users?limit=10`),
        fetchWithAuth(`${API_URL}/api/revenue-analytics/by-location`),
        fetchWithAuth(`${API_URL}/api/revenue-analytics/popular-products`)
      ]);

      if (summaryRes.success) setSummary(summaryRes.summary);
      if (subsRes.success) setSubscriptions(subsRes.subscriptions);
      if (topupsRes.success) setTopups(topupsRes.topups);
      if (topUsersRes.success) setTopUsers(topUsersRes.topUsers);
      if (locationRes.success) setLocationData(locationRes.locationBreakdown);
      if (productsRes.success) setPopularProducts(productsRes.popularProducts);

    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load revenue data');
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('limit', 20);
      if (filters.status) params.append('status', filters.status);
      if (filters.productType) params.append('product_type', filters.productType);
      if (filters.userEmail) params.append('user_email', filters.userEmail);
      if (filters.country) params.append('country', filters.country);
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);

      const response = await fetchWithAuth(`${API_URL}/api/revenue-analytics/transactions?${params.toString()}`);
      if (response.success) {
        setTransactions(response.transactions);
        setPagination(response.pagination);
      }
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    }
  };

  const fetchTrends = async () => {
    try {
      const response = await fetchWithAuth(`${API_URL}/api/revenue-analytics/trends?period=${trendPeriod}&limit=30`);
      if (response.success) {
        setTrends(response.trends);
      }
    } catch (error) {
      console.error('Failed to fetch trends:', error);
    }
  };

  const fetchTransactionDetail = async (orderId) => {
    try {
      const response = await fetchWithAuth(`${API_URL}/api/revenue-analytics/transaction/${orderId}`);
      if (response.success) {
        setTransactionDetail(response);
        setSelectedTransaction(orderId);
      }
    } catch (error) {
      toast.error('Failed to load transaction details');
    }
  };

  const fetchUserHistory = async (userId) => {
    try {
      const response = await fetchWithAuth(`${API_URL}/api/revenue-analytics/user/${userId}/history`);
      if (response.success) {
        setUserHistory(response);
        setSelectedUser(userId);
      }
    } catch (error) {
      toast.error('Failed to load user history');
    }
  };

  const exportCSV = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);
      if (filters.status) params.append('status', filters.status);

      const response = await fetch(`${API_URL}/api/revenue-analytics/export/csv?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast.success('CSV exported successfully');
      }
    } catch (error) {
      toast.error('Failed to export CSV');
    }
  };

  const exportExcel = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);

      const response = await fetch(`${API_URL}/api/revenue-analytics/export/excel?${params.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transactions_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        toast.success('Excel exported successfully');
      }
    } catch (error) {
      toast.error('Failed to export Excel');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading revenue analytics...</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: PieChart },
    { id: 'transactions', label: 'Transactions', icon: CreditCard },
    { id: 'trends', label: 'Trends', icon: TrendingUp },
    { id: 'top-users', label: 'Top Users', icon: Users },
    { id: 'location', label: 'By Location', icon: Globe }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="revenue-analytics-dashboard">
      {/* Header */}
      <header className="bg-slate-800/50 border-b border-slate-700 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/admin">
              <button className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                Back to Admin
              </button>
            </Link>
            <div className="flex items-center gap-2">
              <DollarSign className="w-6 h-6 text-emerald-500" />
              <h1 className="text-xl font-bold">Revenue Analytics</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Date Range Filter */}
            <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                className="bg-transparent text-sm border-none outline-none w-32"
                data-testid="date-start"
              />
              <span className="text-slate-500">to</span>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                className="bg-transparent text-sm border-none outline-none w-32"
                data-testid="date-end"
              />
            </div>
            
            {/* Export Buttons */}
            <button
              onClick={exportCSV}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg transition-colors"
              data-testid="export-csv-btn"
            >
              <Download className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={exportExcel}
              className="flex items-center gap-2 px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors"
              data-testid="export-excel-btn"
            >
              <FileSpreadsheet className="w-4 h-4" />
              Excel
            </button>
            <button
              onClick={fetchAllData}
              className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg transition-colors"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
            <SummaryCard
              title="Total Revenue"
              value={`₹${summary.totalRevenueAllTime?.toLocaleString()}`}
              subValue={`${summary.totalOrdersAllTime} orders`}
              icon={DollarSign}
              color="green"
            />
            <SummaryCard
              title="Subscription Revenue"
              value={`₹${summary.subscriptionRevenue?.toLocaleString()}`}
              subValue={`${summary.subscriptionCount} subscriptions`}
              icon={CreditCard}
              color="blue"
            />
            <SummaryCard
              title="Top-up Revenue"
              value={`₹${summary.topupRevenue?.toLocaleString()}`}
              subValue={`${summary.topupCount} purchases`}
              icon={TrendingUp}
              color="purple"
            />
            <SummaryCard
              title="Active Subscribers"
              value={summary.activeSubscribers}
              icon={UserCheck}
              color="cyan"
            />
            <SummaryCard
              title="Pending Payments"
              value={`₹${summary.pendingPayments?.amount?.toLocaleString()}`}
              subValue={`${summary.pendingPayments?.count} pending`}
              icon={Clock}
              color="amber"
            />
            <SummaryCard
              title="Failed Payments"
              value={`₹${summary.failedPayments?.amount?.toLocaleString()}`}
              subValue={`${summary.failedPayments?.count} failed`}
              icon={XCircle}
              color="red"
            />
            <SummaryCard
              title="Refunded"
              value={`₹${summary.refundedPayments?.amount?.toLocaleString()}`}
              subValue={`${summary.refundedPayments?.count} refunds`}
              icon={AlertCircle}
              color="pink"
            />
          </div>
        )}

        {/* Tabs */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="border-b border-slate-700 flex overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id 
                    ? 'border-b-2 border-emerald-500 text-emerald-400 bg-slate-700/50' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Subscription Breakdown */}
                <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-blue-400" />
                    Subscription Breakdown
                  </h3>
                  <div className="space-y-3">
                    {subscriptions?.map((sub) => (
                      <div key={sub.type} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div>
                          <p className="font-medium capitalize">{sub.type}</p>
                          <p className="text-sm text-slate-400">{sub.count} subscriptions • {sub.uniqueUsers} users</p>
                        </div>
                        <p className="text-lg font-bold text-blue-400">₹{sub.revenue?.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top-up Breakdown */}
                <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-purple-400" />
                    Top-up Breakdown
                  </h3>
                  <div className="space-y-3">
                    {topups?.map((topup) => (
                      <div key={topup.type} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div>
                          <p className="font-medium capitalize">{topup.type} Pack</p>
                          <p className="text-sm text-slate-400">{topup.count} purchases • {topup.uniqueUsers} users</p>
                        </div>
                        <p className="text-lg font-bold text-purple-400">₹{topup.revenue?.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Popular Products */}
                <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50 lg:col-span-2">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-emerald-400" />
                    Most Purchased Products
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {popularProducts?.slice(0, 6).map((product, idx) => (
                      <div key={product.productId} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">
                          #{idx + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium capitalize">{product.productId}</p>
                          <p className="text-sm text-slate-400">{product.purchaseCount} purchases</p>
                        </div>
                        <p className="text-emerald-400 font-semibold">₹{product.revenue?.toLocaleString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Transactions Tab */}
            {activeTab === 'transactions' && (
              <div>
                {/* Filters */}
                <div className="flex flex-wrap gap-4 mb-6">
                  <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2">
                    <Filter className="w-4 h-4 text-slate-400" />
                    <select
                      value={filters.status}
                      onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                      className="bg-transparent text-sm border-none outline-none"
                      data-testid="filter-status"
                    >
                      <option value="">All Status</option>
                      <option value="PAID">Paid</option>
                      <option value="PENDING">Pending</option>
                      <option value="FAILED">Failed</option>
                      <option value="REFUNDED">Refunded</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2">
                    <CreditCard className="w-4 h-4 text-slate-400" />
                    <select
                      value={filters.productType}
                      onChange={(e) => setFilters(prev => ({ ...prev, productType: e.target.value }))}
                      className="bg-transparent text-sm border-none outline-none"
                      data-testid="filter-type"
                    >
                      <option value="">All Types</option>
                      <option value="subscription">Subscriptions</option>
                      <option value="topup">Top-ups</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg px-3 py-2 flex-1 max-w-xs">
                    <Search className="w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search by email..."
                      value={filters.userEmail}
                      onChange={(e) => setFilters(prev => ({ ...prev, userEmail: e.target.value }))}
                      className="bg-transparent text-sm border-none outline-none flex-1"
                      data-testid="filter-email"
                    />
                  </div>
                </div>

                {/* Transactions Table */}
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-slate-400 border-b border-slate-700">
                        <th className="pb-3 font-medium">Order ID</th>
                        <th className="pb-3 font-medium">User</th>
                        <th className="pb-3 font-medium">Product</th>
                        <th className="pb-3 font-medium">Amount</th>
                        <th className="pb-3 font-medium">Status</th>
                        <th className="pb-3 font-medium">Type</th>
                        <th className="pb-3 font-medium">Location</th>
                        <th className="pb-3 font-medium">Device</th>
                        <th className="pb-3 font-medium">Date</th>
                        <th className="pb-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr key={tx.orderId} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                          <td className="py-3 font-mono text-sm text-slate-300">
                            {tx.orderId?.substring(0, 15)}...
                          </td>
                          <td className="py-3">
                            <button
                              onClick={() => fetchUserHistory(tx.userId)}
                              className="text-left hover:text-emerald-400 transition-colors"
                              data-testid={`user-${tx.userId}`}
                            >
                              <p className="font-medium">{tx.userName}</p>
                              <p className="text-sm text-slate-400">{tx.userEmail}</p>
                            </button>
                          </td>
                          <td className="py-3">
                            <p className="font-medium capitalize">{tx.productName || tx.productId}</p>
                            <p className="text-sm text-slate-400">{tx.credits} credits</p>
                          </td>
                          <td className="py-3 font-semibold text-emerald-400">
                            ₹{tx.amount?.toLocaleString()}
                          </td>
                          <td className="py-3">
                            <StatusBadge status={tx.status} />
                          </td>
                          <td className="py-3">
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              tx.transactionType === 'subscription' 
                                ? 'bg-blue-500/20 text-blue-400' 
                                : 'bg-purple-500/20 text-purple-400'
                            }`}>
                              {tx.transactionType}
                              {tx.isRenewal && ' (Renewal)'}
                            </span>
                          </td>
                          <td className="py-3">
                            <div className="flex items-center gap-1">
                              <Globe className="w-3 h-3 text-slate-400" />
                              <span className="text-sm">
                                {tx.location?.city || tx.location?.country || 'Unknown'}
                              </span>
                            </div>
                          </td>
                          <td className="py-3">
                            <DeviceIcon type={tx.deviceType} />
                          </td>
                          <td className="py-3 text-sm text-slate-400">
                            {new Date(tx.createdAt).toLocaleDateString()}
                          </td>
                          <td className="py-3">
                            <button
                              onClick={() => fetchTransactionDetail(tx.orderId)}
                              className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors"
                              data-testid={`view-tx-${tx.orderId}`}
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-6">
                  <p className="text-sm text-slate-400">
                    Showing {transactions.length} of {pagination.total} transactions
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(prev => Math.max(1, prev - 1))}
                      disabled={page === 1}
                      className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      data-testid="prev-page"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="px-4 py-2 bg-slate-700/50 rounded-lg">
                      Page {page} of {pagination.totalPages}
                    </span>
                    <button
                      onClick={() => setPage(prev => Math.min(pagination.totalPages, prev + 1))}
                      disabled={page === pagination.totalPages}
                      className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      data-testid="next-page"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Trends Tab */}
            {activeTab === 'trends' && (
              <div>
                <div className="flex items-center gap-4 mb-6">
                  <span className="text-slate-400">View by:</span>
                  {['day', 'week', 'month', 'year'].map((period) => (
                    <button
                      key={period}
                      onClick={() => setTrendPeriod(period)}
                      className={`px-4 py-2 rounded-lg capitalize transition-colors ${
                        trendPeriod === period 
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' 
                          : 'bg-slate-700/50 text-slate-400 hover:text-white'
                      }`}
                      data-testid={`trend-${period}`}
                    >
                      {period}
                    </button>
                  ))}
                </div>

                {/* Trends Chart Visualization */}
                <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50">
                  <h3 className="text-lg font-semibold mb-4">Revenue Over Time</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {trends?.map((trend, idx) => {
                      const maxRevenue = Math.max(...(trends?.map(t => t.revenue) || [1]));
                      const percentage = (trend.revenue / maxRevenue) * 100;
                      
                      return (
                        <div key={idx} className="flex items-center gap-4">
                          <span className="text-sm text-slate-400 w-24">{trend.period}</span>
                          <div className="flex-1 bg-slate-800/50 rounded-full h-8 overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full flex items-center justify-end pr-2"
                              style={{ width: `${Math.max(percentage, 5)}%` }}
                            >
                              <span className="text-xs font-semibold text-white">
                                ₹{trend.revenue?.toLocaleString()}
                              </span>
                            </div>
                          </div>
                          <span className="text-sm text-slate-400 w-20 text-right">
                            {trend.orders} orders
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Subscription vs Top-up Comparison */}
                <div className="grid grid-cols-2 gap-6 mt-6">
                  <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50">
                    <h3 className="text-lg font-semibold mb-4 text-blue-400">Subscription Trend</h3>
                    <div className="space-y-2">
                      {trends?.slice(-7).map((trend, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-slate-400">{trend.period}</span>
                          <span className="text-blue-400">{trend.subscriptions} subs</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-slate-700/30 rounded-xl p-6 border border-slate-600/50">
                    <h3 className="text-lg font-semibold mb-4 text-purple-400">Top-up Trend</h3>
                    <div className="space-y-2">
                      {trends?.slice(-7).map((trend, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-slate-400">{trend.period}</span>
                          <span className="text-purple-400">{trend.topups} purchases</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Top Users Tab */}
            {activeTab === 'top-users' && (
              <div>
                <div className="grid gap-4">
                  {topUsers.map((user, idx) => (
                    <div 
                      key={user.userId} 
                      className="flex items-center gap-4 p-4 bg-slate-700/30 rounded-xl border border-slate-600/50 hover:border-emerald-500/50 transition-colors cursor-pointer"
                      onClick={() => fetchUserHistory(user.userId)}
                      data-testid={`top-user-${idx}`}
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center font-bold text-lg">
                        #{idx + 1}
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold">{user.name}</p>
                        <p className="text-sm text-slate-400">{user.email}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-emerald-400">₹{user.totalSpent?.toLocaleString()}</p>
                        <p className="text-sm text-slate-400">{user.orderCount} orders</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-slate-400 capitalize">{user.plan} plan</p>
                        <p className="text-xs text-slate-500">{user.currentCredits} credits</p>
                      </div>
                      <div className="flex items-center gap-1 text-sm text-slate-400">
                        <Globe className="w-4 h-4" />
                        {user.location?.country || 'Unknown'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Location Tab */}
            {activeTab === 'location' && (
              <div>
                <div className="grid gap-4">
                  {locationData.map((loc, idx) => {
                    const maxRevenue = Math.max(...locationData.map(l => l.revenue));
                    const percentage = (loc.revenue / maxRevenue) * 100;
                    
                    return (
                      <div key={idx} className="flex items-center gap-4 p-4 bg-slate-700/30 rounded-xl border border-slate-600/50">
                        <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                          <Globe className="w-5 h-5 text-blue-400" />
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold">{loc.country || 'Unknown'}</p>
                          <div className="mt-2 h-2 bg-slate-800/50 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-blue-400">₹{loc.revenue?.toLocaleString()}</p>
                          <p className="text-sm text-slate-400">{loc.orders} orders</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Transaction Detail Modal */}
      {selectedTransaction && transactionDetail && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTransaction(null)}>
          <div 
            className="bg-slate-800 rounded-xl border border-slate-700 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-xl font-bold">Transaction Details</h2>
              <button onClick={() => setSelectedTransaction(null)} className="text-slate-400 hover:text-white">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-400">Order ID</p>
                  <p className="font-mono text-sm">{transactionDetail.transaction?.order_id}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">CF Order ID</p>
                  <p className="font-mono text-sm">{transactionDetail.transaction?.cf_order_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Amount</p>
                  <p className="text-xl font-bold text-emerald-400">₹{transactionDetail.transaction?.amount}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Status</p>
                  <StatusBadge status={transactionDetail.transaction?.status} />
                </div>
                <div>
                  <p className="text-sm text-slate-400">Product</p>
                  <p>{transactionDetail.transaction?.productName}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Credits</p>
                  <p>{transactionDetail.transaction?.credits}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Created At</p>
                  <p>{new Date(transactionDetail.transaction?.createdAt).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Paid At</p>
                  <p>{transactionDetail.transaction?.paidAt ? new Date(transactionDetail.transaction.paidAt).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              
              {/* User Info */}
              {transactionDetail.user && (
                <div className="bg-slate-700/30 rounded-lg p-4">
                  <h3 className="font-semibold mb-2">User Information</h3>
                  <p><span className="text-slate-400">Name:</span> {transactionDetail.user.name}</p>
                  <p><span className="text-slate-400">Email:</span> {transactionDetail.user.email}</p>
                  <p><span className="text-slate-400">Plan:</span> {transactionDetail.user.plan}</p>
                </div>
              )}

              {/* Location Info */}
              {transactionDetail.location?.location && (
                <div className="bg-slate-700/30 rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Location & Device</h3>
                  <p><span className="text-slate-400">Country:</span> {transactionDetail.location.location.country || 'Unknown'}</p>
                  <p><span className="text-slate-400">City:</span> {transactionDetail.location.location.city || 'Unknown'}</p>
                  <p><span className="text-slate-400">IP:</span> {transactionDetail.location.ip_address || 'Unknown'}</p>
                  <p><span className="text-slate-400">Device:</span> {transactionDetail.location.device_type || 'Unknown'}</p>
                </div>
              )}

              {/* Failure Reason */}
              {transactionDetail.transaction?.failureReason && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <h3 className="font-semibold text-red-400 mb-2">Failure Reason</h3>
                  <p className="text-red-300">{transactionDetail.transaction.failureReason}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* User History Modal */}
      {selectedUser && userHistory && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setSelectedUser(null)}>
          <div 
            className="bg-slate-800 rounded-xl border border-slate-700 max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-xl font-bold">User Payment History</h2>
              <button onClick={() => setSelectedUser(null)} className="text-slate-400 hover:text-white">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-6">
              {/* User Info */}
              <div className="bg-slate-700/30 rounded-lg p-4">
                <h3 className="font-semibold mb-3">User Profile</h3>
                <div className="grid grid-cols-2 gap-4">
                  <p><span className="text-slate-400">Name:</span> {userHistory.user?.name}</p>
                  <p><span className="text-slate-400">Email:</span> {userHistory.user?.email}</p>
                  <p><span className="text-slate-400">Plan:</span> {userHistory.user?.plan}</p>
                  <p><span className="text-slate-400">Credits:</span> {userHistory.user?.credits}</p>
                </div>
              </div>

              {/* Summary */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-400">₹{userHistory.summary?.totalSpent}</p>
                  <p className="text-sm text-slate-400">Total Spent</p>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-purple-400">{userHistory.summary?.totalOrders}</p>
                  <p className="text-sm text-slate-400">Total Orders</p>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-blue-400">{userHistory.summary?.subscriptionOrders}</p>
                  <p className="text-sm text-slate-400">Subscriptions</p>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-amber-400">{userHistory.summary?.topupOrders}</p>
                  <p className="text-sm text-slate-400">Top-ups</p>
                </div>
              </div>

              {/* Order History */}
              <div>
                <h3 className="font-semibold mb-3">Order History</h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {userHistory.orders?.map((order, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div>
                        <p className="font-medium">{order.productName || order.productId}</p>
                        <p className="text-xs text-slate-400">{new Date(order.createdAt).toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-emerald-400">₹{(order.amount / 100).toFixed(2)}</p>
                        <StatusBadge status={order.status} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
