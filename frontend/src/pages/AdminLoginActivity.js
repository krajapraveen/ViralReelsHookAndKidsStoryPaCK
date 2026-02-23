import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Download, Search, Filter, ChevronLeft, ChevronRight,
  Shield, ShieldAlert, ShieldOff, Globe, Monitor, Smartphone, Tablet,
  CheckCircle, XCircle, LogOut, AlertTriangle, Calendar, User, MapPin,
  Clock, Eye, Ban, UserX, X, ChevronDown
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';

export default function AdminLoginActivity() {
  const [activities, setActivities] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, size: 50, total: 0, pages: 0 });
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [blockedIps, setBlockedIps] = useState([]);
  
  // Filters
  const [filters, setFilters] = useState({
    from_date: '',
    to_date: '',
    user: '',
    status: '',
    country: '',
    ip: '',
    auth_method: '',
    has_risk: ''
  });
  
  // Modals
  const [showFilters, setShowFilters] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [blockData, setBlockData] = useState({ ip: '', reason: '', duration: 24 });
  const [showForceLogoutModal, setShowForceLogoutModal] = useState(false);
  const [forceLogoutData, setForceLogoutData] = useState({ userId: '', userEmail: '', reason: '' });

  const fetchActivities = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('size', pagination.size);
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      const response = await api.get(`/api/admin/login-activity?${params.toString()}`);
      setActivities(response.data.activities || []);
      setPagination(response.data.pagination || { page: 1, size: 50, total: 0, pages: 0 });
    } catch (error) {
      toast.error('Failed to fetch login activity');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.size]);

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/admin/login-activity/stats/summary?days=7');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats', error);
    }
  };

  const fetchBlockedIps = async () => {
    try {
      const response = await api.get('/api/admin/login-activity/blocked-ips/list');
      setBlockedIps(response.data.blocked_ips || []);
    } catch (error) {
      console.error('Failed to fetch blocked IPs', error);
    }
  };

  useEffect(() => {
    fetchActivities(1);
    fetchStats();
    fetchBlockedIps();
  }, []);

  const handleSearch = () => {
    fetchActivities(1);
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      const response = await api.get(`/api/admin/login-activity/export/csv?${params.toString()}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `login_activity_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Export downloaded successfully');
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  const handleBlockIp = async () => {
    if (!blockData.ip || !blockData.reason) {
      toast.error('Please fill all fields');
      return;
    }
    
    try {
      await api.post('/api/admin/login-activity/block-ip', {
        ip_address: blockData.ip,
        reason: blockData.reason,
        duration_hours: blockData.duration
      });
      toast.success(`IP ${blockData.ip} blocked for ${blockData.duration} hours`);
      setShowBlockModal(false);
      setBlockData({ ip: '', reason: '', duration: 24 });
      fetchBlockedIps();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to block IP');
    }
  };

  const handleUnblockIp = async (ip) => {
    if (!confirm(`Unblock IP ${ip}?`)) return;
    
    try {
      await api.delete(`/api/admin/login-activity/block-ip/${ip}`);
      toast.success(`IP ${ip} unblocked`);
      fetchBlockedIps();
    } catch (error) {
      toast.error('Failed to unblock IP');
    }
  };

  const handleForceLogout = async () => {
    if (!forceLogoutData.reason) {
      toast.error('Please provide a reason');
      return;
    }
    
    try {
      await api.post('/api/admin/login-activity/force-logout', {
        user_id: forceLogoutData.userId,
        reason: forceLogoutData.reason
      });
      toast.success(`User logged out from all devices`);
      setShowForceLogoutModal(false);
      setForceLogoutData({ userId: '', userEmail: '', reason: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to force logout');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'LOGOUT':
      case 'FORCE_LOGOUT':
        return <LogOut className="w-4 h-4 text-yellow-400" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-slate-400" />;
    }
  };

  const getDeviceIcon = (deviceType) => {
    switch (deviceType?.toLowerCase()) {
      case 'mobile':
        return <Smartphone className="w-4 h-4" />;
      case 'tablet':
        return <Tablet className="w-4 h-4" />;
      default:
        return <Monitor className="w-4 h-4" />;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('en-IN', { 
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }) + ' IST';
  };

  const clearFilters = () => {
    setFilters({
      from_date: '',
      to_date: '',
      user: '',
      status: '',
      country: '',
      ip: '',
      auth_method: '',
      has_risk: ''
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
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
                <Shield className="w-6 h-6 text-blue-400" />
                <h1 className="text-2xl font-bold text-white">Login Activity</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                className="border-slate-600 text-slate-300"
              >
                <Download className="w-4 h-4 mr-2" /> Export CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { fetchActivities(pagination.page); fetchStats(); }}
                disabled={loading}
                className="border-slate-600 text-slate-300"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Total Logins (7d)</p>
              <p className="text-2xl font-bold text-white">{stats.total_logins?.toLocaleString()}</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Successful</p>
              <p className="text-2xl font-bold text-green-400">{stats.successful_logins?.toLocaleString()}</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Failed</p>
              <p className="text-2xl font-bold text-red-400">{stats.failed_logins?.toLocaleString()}</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Success Rate</p>
              <p className="text-2xl font-bold text-blue-400">{stats.success_rate}%</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Unique Users</p>
              <p className="text-2xl font-bold text-purple-400">{stats.unique_users?.toLocaleString()}</p>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
              <p className="text-slate-400 text-sm">Risky Logins</p>
              <p className="text-2xl font-bold text-orange-400">{stats.risky_logins?.toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Blocked IPs Alert */}
        {blockedIps.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldOff className="w-5 h-5 text-red-400" />
                <span className="text-red-300 font-medium">{blockedIps.length} IP(s) Currently Blocked</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {blockedIps.slice(0, 3).map((ip) => (
                  <span key={ip.id} className="bg-red-500/20 text-red-300 px-2 py-1 rounded text-sm flex items-center gap-1">
                    {ip.ip_address}
                    <button onClick={() => handleUnblockIp(ip.ip_address)} className="hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                {blockedIps.length > 3 && (
                  <span className="text-red-300 text-sm">+{blockedIps.length - 3} more</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Search User */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by email or name..."
                  value={filters.user}
                  onChange={(e) => setFilters({ ...filters, user: e.target.value })}
                  className="pl-10 bg-slate-700 border-slate-600 text-white"
                  data-testid="search-user"
                />
              </div>
            </div>

            {/* Status Filter */}
            <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
              <SelectTrigger className="w-[140px] bg-slate-700 border-slate-600 text-white">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Status</SelectItem>
                <SelectItem value="SUCCESS" className="text-white">Success</SelectItem>
                <SelectItem value="FAILED" className="text-white">Failed</SelectItem>
                <SelectItem value="LOGOUT" className="text-white">Logout</SelectItem>
              </SelectContent>
            </Select>

            {/* Auth Method Filter */}
            <Select value={filters.auth_method} onValueChange={(v) => setFilters({ ...filters, auth_method: v })}>
              <SelectTrigger className="w-[140px] bg-slate-700 border-slate-600 text-white">
                <SelectValue placeholder="Auth Method" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Methods</SelectItem>
                <SelectItem value="email_password" className="text-white">Email + Password</SelectItem>
                <SelectItem value="google" className="text-white">Google</SelectItem>
              </SelectContent>
            </Select>

            {/* More Filters Toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="border-slate-600 text-slate-300"
            >
              <Filter className="w-4 h-4 mr-2" />
              {showFilters ? 'Less' : 'More'} Filters
              <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </Button>

            <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700">
              <Search className="w-4 h-4 mr-2" /> Search
            </Button>

            <Button variant="ghost" size="sm" onClick={clearFilters} className="text-slate-400">
              Clear
            </Button>
          </div>

          {/* Extended Filters */}
          {showFilters && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-700">
              <div>
                <label className="text-slate-400 text-sm mb-1 block">From Date</label>
                <Input
                  type="datetime-local"
                  value={filters.from_date}
                  onChange={(e) => setFilters({ ...filters, from_date: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">To Date</label>
                <Input
                  type="datetime-local"
                  value={filters.to_date}
                  onChange={(e) => setFilters({ ...filters, to_date: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Country</label>
                <Input
                  placeholder="e.g., India"
                  value={filters.country}
                  onChange={(e) => setFilters({ ...filters, country: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">IP Address</label>
                <Input
                  placeholder="e.g., 192.168.1.1"
                  value={filters.ip}
                  onChange={(e) => setFilters({ ...filters, ip: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                />
              </div>
            </div>
          )}
        </div>

        {/* Activity Table */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-700/50">
                  <th className="text-left p-4 text-slate-300 font-medium">User</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Login Time</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Status</th>
                  <th className="text-left p-4 text-slate-300 font-medium">IP Address</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Location</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Device</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Auth</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Risk</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-slate-400">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading...
                    </td>
                  </tr>
                ) : activities.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-slate-400">
                      No login activity found
                    </td>
                  </tr>
                ) : (
                  activities.map((activity) => (
                    <tr key={activity.id} className="border-t border-slate-700/50 hover:bg-slate-700/30">
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-slate-400" />
                          <div>
                            <p className="text-white text-sm font-medium">{activity.user_name || '-'}</p>
                            <p className="text-slate-400 text-xs">{activity.identifier}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2 text-slate-300 text-sm">
                          <Clock className="w-4 h-4 text-slate-400" />
                          {formatDate(activity.timestamp)}
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(activity.status)}
                          <span className={`text-sm ${
                            activity.status === 'SUCCESS' ? 'text-green-400' :
                            activity.status === 'FAILED' ? 'text-red-400' :
                            'text-yellow-400'
                          }`}>
                            {activity.status}
                          </span>
                        </div>
                        {activity.failure_reason && (
                          <p className="text-xs text-red-300 mt-1">{activity.failure_reason}</p>
                        )}
                      </td>
                      <td className="p-4">
                        <p className="text-slate-300 text-sm font-mono">{activity.ip_address}</p>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <MapPin className="w-4 h-4 text-slate-400" />
                          <span className="text-slate-300 text-sm">
                            {activity.location || activity.country || '-'}
                          </span>
                        </div>
                        {activity.isp && (
                          <p className="text-xs text-slate-500 mt-1">{activity.isp}</p>
                        )}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2 text-slate-300 text-sm">
                          {getDeviceIcon(activity.device_type)}
                          <div>
                            <p>{activity.device_type}</p>
                            <p className="text-xs text-slate-500">{activity.browser}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded text-xs ${
                          activity.auth_method === 'google' 
                            ? 'bg-blue-500/20 text-blue-300' 
                            : 'bg-purple-500/20 text-purple-300'
                        }`}>
                          {activity.auth_method === 'google' ? 'Google' : 'Email'}
                        </span>
                      </td>
                      <td className="p-4">
                        {activity.risk_flags?.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {activity.risk_flags.map((flag, i) => (
                              <span key={i} className="bg-orange-500/20 text-orange-300 px-2 py-0.5 rounded text-xs flex items-center gap-1">
                                <ShieldAlert className="w-3 h-3" />
                                {flag}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-500 text-sm">-</span>
                        )}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedActivity(activity)}
                            className="text-slate-400 hover:text-white p-1"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setBlockData({ ip: activity.ip_address, reason: '', duration: 24 });
                              setShowBlockModal(true);
                            }}
                            className="text-slate-400 hover:text-red-400 p-1"
                            title="Block IP"
                          >
                            <Ban className="w-4 h-4" />
                          </Button>
                          {activity.user_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setForceLogoutData({ userId: activity.user_id, userEmail: activity.identifier, reason: '' });
                                setShowForceLogoutModal(true);
                              }}
                              className="text-slate-400 hover:text-yellow-400 p-1"
                              title="Force Logout"
                            >
                              <UserX className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination.pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t border-slate-700">
              <p className="text-slate-400 text-sm">
                Showing {((pagination.page - 1) * pagination.size) + 1} - {Math.min(pagination.page * pagination.size, pagination.total)} of {pagination.total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === 1}
                  onClick={() => fetchActivities(pagination.page - 1)}
                  className="border-slate-600"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-slate-300 text-sm">
                  Page {pagination.page} of {pagination.pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === pagination.pages}
                  onClick={() => fetchActivities(pagination.page + 1)}
                  className="border-slate-600"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Privacy Notice */}
        <div className="mt-6 bg-slate-800/30 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400 text-center">
            <Globe className="w-4 h-4 inline mr-2" />
            Location data is approximate based on IP address. Data retained for 30 days per privacy policy.
          </p>
        </div>
      </main>

      {/* Detail Side Panel */}
      {selectedActivity && (
        <div className="fixed inset-0 bg-black/50 z-50 flex justify-end" onClick={() => setSelectedActivity(null)}>
          <div 
            className="bg-slate-800 w-full max-w-lg h-full overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-slate-700 flex items-center justify-between sticky top-0 bg-slate-800">
              <h3 className="text-xl font-bold text-white">Login Details</h3>
              <Button variant="ghost" size="sm" onClick={() => setSelectedActivity(null)}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-6 space-y-6">
              {/* User Info */}
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-slate-400 text-sm mb-3 font-medium">User Information</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Name</span>
                    <span className="text-white">{selectedActivity.user_name || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Email</span>
                    <span className="text-white">{selectedActivity.identifier}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">User ID</span>
                    <span className="text-white font-mono text-sm">{selectedActivity.user_id || '-'}</span>
                  </div>
                </div>
              </div>

              {/* Session Info */}
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-slate-400 text-sm mb-3 font-medium">Session Details</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Status</span>
                    <span className={`${
                      selectedActivity.status === 'SUCCESS' ? 'text-green-400' :
                      selectedActivity.status === 'FAILED' ? 'text-red-400' : 'text-yellow-400'
                    }`}>{selectedActivity.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Auth Method</span>
                    <span className="text-white capitalize">{selectedActivity.auth_method?.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Session ID</span>
                    <span className="text-white font-mono text-sm">{selectedActivity.session_id_masked}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Timestamp</span>
                    <span className="text-white text-sm">{formatDate(selectedActivity.timestamp)}</span>
                  </div>
                  {selectedActivity.failure_reason && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Failure Reason</span>
                      <span className="text-red-400">{selectedActivity.failure_reason}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Location Info */}
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-slate-400 text-sm mb-3 font-medium">Location & Network</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">IP Address</span>
                    <span className="text-white font-mono">{selectedActivity.ip_address}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Country</span>
                    <span className="text-white">{selectedActivity.country || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Region</span>
                    <span className="text-white">{selectedActivity.region || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">City</span>
                    <span className="text-white">{selectedActivity.city || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">ISP</span>
                    <span className="text-white text-sm">{selectedActivity.isp || '-'}</span>
                  </div>
                </div>
              </div>

              {/* Device Info */}
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-slate-400 text-sm mb-3 font-medium">Device Information</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Device Type</span>
                    <span className="text-white">{selectedActivity.device_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Browser</span>
                    <span className="text-white">{selectedActivity.browser}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Operating System</span>
                    <span className="text-white">{selectedActivity.os}</span>
                  </div>
                </div>
              </div>

              {/* Risk Flags */}
              {selectedActivity.risk_flags?.length > 0 && (
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                  <h4 className="text-orange-400 text-sm mb-3 font-medium flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4" /> Risk Flags
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedActivity.risk_flags.map((flag, i) => (
                      <span key={i} className="bg-orange-500/20 text-orange-300 px-3 py-1 rounded-full text-sm">
                        {flag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button
                  onClick={() => {
                    setBlockData({ ip: selectedActivity.ip_address, reason: '', duration: 24 });
                    setShowBlockModal(true);
                    setSelectedActivity(null);
                  }}
                  variant="outline"
                  className="flex-1 border-red-500 text-red-400 hover:bg-red-500/10"
                >
                  <Ban className="w-4 h-4 mr-2" /> Block IP
                </Button>
                {selectedActivity.user_id && (
                  <Button
                    onClick={() => {
                      setForceLogoutData({ userId: selectedActivity.user_id, userEmail: selectedActivity.identifier, reason: '' });
                      setShowForceLogoutModal(true);
                      setSelectedActivity(null);
                    }}
                    variant="outline"
                    className="flex-1 border-yellow-500 text-yellow-400 hover:bg-yellow-500/10"
                  >
                    <UserX className="w-4 h-4 mr-2" /> Force Logout
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Block IP Modal */}
      {showBlockModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowBlockModal(false)}>
          <div 
            className="bg-slate-800 rounded-xl max-w-md w-full p-6 border border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Ban className="w-5 h-5 text-red-400" /> Block IP Address
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm mb-1 block">IP Address</label>
                <Input
                  value={blockData.ip}
                  onChange={(e) => setBlockData({ ...blockData, ip: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="192.168.1.1"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Reason</label>
                <Input
                  value={blockData.reason}
                  onChange={(e) => setBlockData({ ...blockData, reason: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Suspicious activity detected..."
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Duration (hours)</label>
                <Select value={String(blockData.duration)} onValueChange={(v) => setBlockData({ ...blockData, duration: parseInt(v) })}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="1" className="text-white">1 hour</SelectItem>
                    <SelectItem value="6" className="text-white">6 hours</SelectItem>
                    <SelectItem value="24" className="text-white">24 hours</SelectItem>
                    <SelectItem value="72" className="text-white">3 days</SelectItem>
                    <SelectItem value="168" className="text-white">1 week</SelectItem>
                    <SelectItem value="720" className="text-white">30 days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-3 pt-4">
                <Button variant="outline" className="flex-1 border-slate-600" onClick={() => setShowBlockModal(false)}>
                  Cancel
                </Button>
                <Button className="flex-1 bg-red-600 hover:bg-red-700" onClick={handleBlockIp}>
                  Block IP
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Force Logout Modal */}
      {showForceLogoutModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowForceLogoutModal(false)}>
          <div 
            className="bg-slate-800 rounded-xl max-w-md w-full p-6 border border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <UserX className="w-5 h-5 text-yellow-400" /> Force Logout User
            </h3>
            <p className="text-slate-400 mb-4">
              This will log out <span className="text-white font-medium">{forceLogoutData.userEmail}</span> from all devices immediately.
            </p>
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Reason</label>
                <Input
                  value={forceLogoutData.reason}
                  onChange={(e) => setForceLogoutData({ ...forceLogoutData, reason: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Account security concern..."
                />
              </div>
              <div className="flex gap-3 pt-4">
                <Button variant="outline" className="flex-1 border-slate-600" onClick={() => setShowForceLogoutModal(false)}>
                  Cancel
                </Button>
                <Button className="flex-1 bg-yellow-600 hover:bg-yellow-700" onClick={handleForceLogout}>
                  Force Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
