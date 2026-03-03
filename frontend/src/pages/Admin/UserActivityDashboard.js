import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Users, MapPin, Clock, Activity, RefreshCw, Eye, 
  CheckCircle, XCircle, Globe, Smartphone, Monitor, UserPlus,
  TrendingUp, Filter, Download, Search, Calendar, Star, Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const UserActivityDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('realtime');
  const [dashboardData, setDashboardData] = useState(null);
  const [activeUsers, setActiveUsers] = useState([]);
  const [loginHistory, setLoginHistory] = useState(null);
  const [newUsers, setNewUsers] = useState([]);
  const [generationReport, setGenerationReport] = useState(null);
  const [featureUsage, setFeatureUsage] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchAllData();
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchAllData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [dashboardRes, activeRes, loginRes, newUsersRes, generationRes, featureRes] = await Promise.all([
        fetch(`${API_URL}/api/live-stats/dashboard-summary`, { headers }),
        fetch(`${API_URL}/api/live-stats/active-users`, { headers }),
        fetch(`${API_URL}/api/live-stats/login-history?days=30`, { headers }),
        fetch(`${API_URL}/api/live-stats/new-users?days=30`, { headers }),
        fetch(`${API_URL}/api/live-stats/generation-report?days=7`, { headers }),
        fetch(`${API_URL}/api/live-stats/feature-usage?days=30`, { headers })
      ]);

      if (dashboardRes.ok) {
        const data = await dashboardRes.json();
        setDashboardData(data);
      }

      if (activeRes.ok) {
        const data = await activeRes.json();
        setActiveUsers(data.active_users || []);
      }

      if (loginRes.ok) {
        const data = await loginRes.json();
        setLoginHistory(data);
      }

      if (newUsersRes.ok) {
        const data = await newUsersRes.json();
        setNewUsers(data.new_users || []);
      }

      if (generationRes.ok) {
        const data = await generationRes.json();
        setGenerationReport(data);
      }

      if (featureRes.ok) {
        const data = await featureRes.json();
        setFeatureUsage(data);
      }

    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load activity data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAllData();
    toast.success('Data refreshed');
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-IN', { 
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]" data-testid="loading-spinner">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6" data-testid="user-activity-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/app/admin" className="text-gray-500 hover:text-gray-700" data-testid="back-button">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="h-6 w-6 text-indigo-500" />
              User Activity Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Real-time monitoring of all user activities
            </p>
          </div>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing} data-testid="refresh-btn">
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Real-time Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="border-2 border-green-500 bg-green-50" data-testid="active-users-card">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-500 rounded-xl">
                <Users className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Online Now</p>
                <p className="text-3xl font-bold text-green-600">
                  {dashboardData?.real_time?.active_users_now || activeUsers.length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="today-logins-card">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-500 rounded-xl">
                <Clock className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Today's Logins</p>
                <p className="text-3xl font-bold text-blue-600">
                  {dashboardData?.real_time?.today_logins || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="today-generations-card">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-500 rounded-xl">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Today's Generations</p>
                <p className="text-3xl font-bold text-purple-600">
                  {dashboardData?.real_time?.today_generations || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="new-users-card">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-orange-500 rounded-xl">
                <UserPlus className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">New This Week</p>
                <p className="text-3xl font-bold text-orange-600">
                  {dashboardData?.totals?.new_users_this_week || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {['realtime', 'logins', 'new-users', 'generations', 'experience'].map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "outline"}
            onClick={() => setActiveTab(tab)}
            className="whitespace-nowrap"
            data-testid={`tab-${tab}`}
          >
            {tab === 'realtime' && <Users className="h-4 w-4 mr-2" />}
            {tab === 'logins' && <MapPin className="h-4 w-4 mr-2" />}
            {tab === 'new-users' && <UserPlus className="h-4 w-4 mr-2" />}
            {tab === 'generations' && <Zap className="h-4 w-4 mr-2" />}
            {tab === 'experience' && <Star className="h-4 w-4 mr-2" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ')}
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'realtime' && (
        <Card data-testid="realtime-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-green-500" />
              Who's Online Right Now
            </CardTitle>
            <CardDescription>Users active in the last 15 minutes</CardDescription>
          </CardHeader>
          <CardContent>
            {activeUsers.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Users className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                <p>No users currently online</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">User</th>
                      <th className="px-4 py-3 text-left font-medium">Email</th>
                      <th className="px-4 py-3 text-left font-medium">Last Active</th>
                      <th className="px-4 py-3 text-left font-medium">Current Page</th>
                      <th className="px-4 py-3 text-left font-medium">IP Address</th>
                      <th className="px-4 py-3 text-left font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {activeUsers.map((user, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{user.name}</td>
                        <td className="px-4 py-3 text-gray-600">{user.email}</td>
                        <td className="px-4 py-3 text-gray-600">{formatTime(user.last_active)}</td>
                        <td className="px-4 py-3 text-gray-600">{user.last_page || '/app'}</td>
                        <td className="px-4 py-3 text-gray-600">{user.ip_address}</td>
                        <td className="px-4 py-3">
                          <Badge variant="default" className="bg-green-500">
                            <span className="w-2 h-2 bg-white rounded-full mr-1 animate-pulse"></span>
                            Online
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'logins' && (
        <div className="space-y-6">
          {/* Login Summary */}
          <Card data-testid="login-summary-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-500" />
                Login History (Last 30 Days)
              </CardTitle>
              <CardDescription>
                Total: {loginHistory?.total_logins || 0} logins from {loginHistory?.unique_users || 0} users
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">User</th>
                      <th className="px-4 py-3 text-left font-medium">Email</th>
                      <th className="px-4 py-3 text-left font-medium">Date & Time</th>
                      <th className="px-4 py-3 text-left font-medium">Location</th>
                      <th className="px-4 py-3 text-left font-medium">IP Address</th>
                      <th className="px-4 py-3 text-left font-medium">Device</th>
                      <th className="px-4 py-3 text-left font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {loginHistory?.logins?.map((login, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{login.user_name || 'Unknown'}</td>
                        <td className="px-4 py-3 text-gray-600">{login.identifier}</td>
                        <td className="px-4 py-3 text-gray-600">{formatDate(login.timestamp)}</td>
                        <td className="px-4 py-3 text-gray-600">
                          {[login.city, login.region, login.country].filter(Boolean).join(', ') || 'Unknown'}
                        </td>
                        <td className="px-4 py-3 text-gray-600">{login.ip_address}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            {login.device_type === 'Mobile' ? (
                              <Smartphone className="h-4 w-4 text-gray-400" />
                            ) : (
                              <Monitor className="h-4 w-4 text-gray-400" />
                            )}
                            <span className="text-gray-600">{login.device_type}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={login.status === 'SUCCESS' ? "default" : "destructive"}>
                            {login.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* User Summary */}
          <Card data-testid="user-login-summary">
            <CardHeader>
              <CardTitle>User Login Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-64">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">Email</th>
                      <th className="px-4 py-3 text-left font-medium">Name</th>
                      <th className="px-4 py-3 text-left font-medium">Login Count</th>
                      <th className="px-4 py-3 text-left font-medium">Last Login</th>
                      <th className="px-4 py-3 text-left font-medium">Locations</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {loginHistory?.user_summary?.map((user, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-600">{user.email}</td>
                        <td className="px-4 py-3 font-medium">{user.name}</td>
                        <td className="px-4 py-3 text-gray-600">{user.login_count}</td>
                        <td className="px-4 py-3 text-gray-600">{formatDate(user.last_login)}</td>
                        <td className="px-4 py-3 text-gray-600">{user.locations?.join(', ') || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'new-users' && (
        <Card data-testid="new-users-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-orange-500" />
              New Users (Last 30 Days)
            </CardTitle>
            <CardDescription>{newUsers.length} new signups</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Name</th>
                    <th className="px-4 py-3 text-left font-medium">Email</th>
                    <th className="px-4 py-3 text-left font-medium">Signup Date</th>
                    <th className="px-4 py-3 text-left font-medium">Credits</th>
                    <th className="px-4 py-3 text-left font-medium">Reels Generated</th>
                    <th className="px-4 py-3 text-left font-medium">Stories Generated</th>
                    <th className="px-4 py-3 text-left font-medium">Last Login</th>
                    <th className="px-4 py-3 text-left font-medium">IP Address</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {newUsers.map((user, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium">{user.name}</td>
                      <td className="px-4 py-3 text-gray-600">{user.email}</td>
                      <td className="px-4 py-3 text-gray-600">{formatDate(user.created_at)}</td>
                      <td className="px-4 py-3 text-gray-600">{user.credits?.toLocaleString()}</td>
                      <td className="px-4 py-3 text-gray-600">{user.activity?.reels_generated || 0}</td>
                      <td className="px-4 py-3 text-gray-600">{user.activity?.stories_generated || 0}</td>
                      <td className="px-4 py-3 text-gray-600">{formatDate(user.last_login) || 'Never'}</td>
                      <td className="px-4 py-3 text-gray-600">{user.last_ip || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'generations' && (
        <div className="space-y-6">
          {/* Generation Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-3xl font-bold text-indigo-600">{generationReport?.summary?.total_generations || 0}</p>
                <p className="text-sm text-gray-500">Total Generations</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-3xl font-bold text-green-600">{generationReport?.summary?.successful || 0}</p>
                <p className="text-sm text-gray-500">Successful</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-3xl font-bold text-red-600">{generationReport?.summary?.failed || 0}</p>
                <p className="text-sm text-gray-500">Failed</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 text-center">
                <p className="text-3xl font-bold text-purple-600">{generationReport?.summary?.success_rate || '0%'}</p>
                <p className="text-sm text-gray-500">Success Rate</p>
              </CardContent>
            </Card>
          </div>

          {/* Generation Jobs */}
          <Card data-testid="generation-jobs-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-purple-500" />
                Generation Jobs (Last 7 Days)
              </CardTitle>
              <CardDescription>All content generation jobs with output status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">Type</th>
                      <th className="px-4 py-3 text-left font-medium">User</th>
                      <th className="px-4 py-3 text-left font-medium">Email</th>
                      <th className="px-4 py-3 text-left font-medium">Topic/Content</th>
                      <th className="px-4 py-3 text-left font-medium">Date & Time</th>
                      <th className="px-4 py-3 text-left font-medium">Output Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {generationReport?.jobs?.map((job, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Badge variant="outline" className={job.type === 'reel' ? 'border-indigo-500' : 'border-purple-500'}>
                            {job.type === 'reel' ? '🎬 Reel' : '📚 Story'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 font-medium">{job.user_name}</td>
                        <td className="px-4 py-3 text-gray-600">{job.user_email}</td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{job.topic || 'N/A'}</td>
                        <td className="px-4 py-3 text-gray-600">{formatDate(job.created_at)}</td>
                        <td className="px-4 py-3">
                          {job.success ? (
                            <Badge variant="default" className="bg-green-500">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Success
                            </Badge>
                          ) : (
                            <Badge variant="destructive">
                              <XCircle className="h-3 w-3 mr-1" />
                              Failed
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'experience' && (
        <div className="space-y-6">
          {/* Feature Usage Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card data-testid="reel-usage-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🎬 Reel Generator Usage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Jobs</span>
                    <span className="font-bold">{featureUsage?.features?.reel_generator?.total_jobs || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Successful</span>
                    <span className="font-bold text-green-600">{featureUsage?.features?.reel_generator?.successful || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Success Rate</span>
                    <span className="font-bold">{featureUsage?.features?.reel_generator?.success_rate || '0%'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="story-usage-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  📚 Story Generator Usage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Jobs</span>
                    <span className="font-bold">{featureUsage?.features?.story_generator?.total_jobs || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Successful</span>
                    <span className="font-bold text-green-600">{featureUsage?.features?.story_generator?.successful || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Success Rate</span>
                    <span className="font-bold">{featureUsage?.features?.story_generator?.success_rate || '0%'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* User Experience Ratings */}
          <Card data-testid="user-ratings-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5 text-yellow-500" />
                User Experience Ratings
              </CardTitle>
              <CardDescription>
                Average Rating: {featureUsage?.user_experience?.average_rating || 0}/5 
                ({featureUsage?.user_experience?.total_ratings || 0} ratings)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-6">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star 
                    key={star} 
                    className={`h-8 w-8 ${
                      star <= (featureUsage?.user_experience?.average_rating || 0) 
                        ? 'text-yellow-500 fill-yellow-500' 
                        : 'text-gray-300'
                    }`} 
                  />
                ))}
                <span className="text-2xl font-bold ml-2">
                  {featureUsage?.user_experience?.average_rating || 0}/5
                </span>
              </div>

              {featureUsage?.user_experience?.ratings_breakdown?.length > 0 && (
                <div className="overflow-x-auto max-h-64">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">User</th>
                        <th className="px-4 py-3 text-left font-medium">Rating</th>
                        <th className="px-4 py-3 text-left font-medium">Feature</th>
                        <th className="px-4 py-3 text-left font-medium">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {featureUsage?.user_experience?.ratings_breakdown?.map((rating, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-600">{rating.user_email || 'Anonymous'}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1">
                              {[...Array(5)].map((_, j) => (
                                <Star 
                                  key={j} 
                                  className={`h-4 w-4 ${
                                    j < rating.rating ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'
                                  }`} 
                                />
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-600">{rating.feature || 'N/A'}</td>
                          <td className="px-4 py-3 text-gray-600">{formatDate(rating.timestamp)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default UserActivityDashboard;
