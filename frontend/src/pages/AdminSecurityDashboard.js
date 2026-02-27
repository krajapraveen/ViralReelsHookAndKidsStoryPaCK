import React, { useState, useEffect, useCallback } from 'react';
import { 
  Shield, AlertTriangle, Lock, Unlock, Ban, CheckCircle, 
  RefreshCw, Search, Filter, ChevronDown, Eye, Activity,
  TrendingUp, TrendingDown, Users, Globe, Clock, Zap,
  AlertCircle, XCircle, ShieldAlert, ShieldCheck, ArrowLeft
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminSecurityDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data states
  const [securityStats, setSecurityStats] = useState(null);
  const [blockedIPs, setBlockedIPs] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [suspiciousUsers, setSuspiciousUsers] = useState([]);
  const [realtimeActivity, setRealtimeActivity] = useState([]);
  const [ipActivitySearch, setIpActivitySearch] = useState('');
  const [ipActivity, setIpActivity] = useState([]);
  
  // Modal states
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [blockFormData, setBlockFormData] = useState({ ip: '', reason: '', duration: 24 });
  
  const token = localStorage.getItem('token');

  const fetchSecurityData = useCallback(async () => {
    setRefreshing(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      
      // Fetch all data in parallel
      const [statsRes, blockedRes, logsRes, suspiciousRes, activityRes] = await Promise.all([
        fetch(`${API_URL}/api/security/ip/stats?days=7`, { headers }),
        fetch(`${API_URL}/api/security/ip/blocked?page=1&size=20`, { headers }),
        fetch(`${API_URL}/api/admin/audit/logs?page=1&size=20`, { headers }),
        fetch(`${API_URL}/api/admin/audit/suspicious-users?days=7`, { headers }),
        fetch(`${API_URL}/api/admin/audit/real-time-activity?limit=30`, { headers })
      ]);
      
      if (statsRes.ok) setSecurityStats(await statsRes.json());
      if (blockedRes.ok) {
        const data = await blockedRes.json();
        setBlockedIPs(data.blocked_ips || []);
      }
      if (logsRes.ok) {
        const data = await logsRes.json();
        setAuditLogs(data.logs || []);
      }
      if (suspiciousRes.ok) {
        const data = await suspiciousRes.json();
        setSuspiciousUsers(data.suspicious_users || []);
      }
      if (activityRes.ok) {
        const data = await activityRes.json();
        setRealtimeActivity(data.all_events || []);
      }
      
    } catch (error) {
      console.error('Failed to fetch security data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    fetchSecurityData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchSecurityData, 30000);
    return () => clearInterval(interval);
  }, [fetchSecurityData]);

  const handleBlockIP = async () => {
    try {
      const response = await fetch(`${API_URL}/api/security/ip/block`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ip_address: blockFormData.ip,
          reason: blockFormData.reason,
          duration_hours: blockFormData.duration
        })
      });
      
      if (response.ok) {
        setShowBlockModal(false);
        setBlockFormData({ ip: '', reason: '', duration: 24 });
        fetchSecurityData();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to block IP');
      }
    } catch (error) {
      console.error('Block IP failed:', error);
    }
  };

  const handleUnblockIP = async (ipAddress) => {
    if (!confirm(`Are you sure you want to unblock ${ipAddress}?`)) return;
    
    try {
      const response = await fetch(`${API_URL}/api/security/ip/unblock?ip_address=${ipAddress}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        fetchSecurityData();
      }
    } catch (error) {
      console.error('Unblock IP failed:', error);
    }
  };

  const searchIPActivity = async () => {
    if (!ipActivitySearch) return;
    
    try {
      const response = await fetch(
        `${API_URL}/api/security/ip/activity/${ipActivitySearch}?limit=50`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        setIpActivity(data.activities || []);
      }
    } catch (error) {
      console.error('IP activity search failed:', error);
    }
  };

  const getThreatLevelColor = (level) => {
    switch (level) {
      case 'CRITICAL': return 'bg-red-500';
      case 'HIGH': return 'bg-orange-500';
      case 'MEDIUM': return 'bg-yellow-500';
      case 'LOW': return 'bg-green-500';
      default: return 'bg-slate-500';
    }
  };

  const getEventTypeIcon = (type) => {
    if (type?.includes('LOGIN_FAILED')) return <XCircle className="w-4 h-4 text-red-400" />;
    if (type?.includes('BLOCKED')) return <Ban className="w-4 h-4 text-orange-400" />;
    if (type?.includes('SUCCESS')) return <CheckCircle className="w-4 h-4 text-green-400" />;
    if (type?.includes('SECURITY')) return <ShieldAlert className="w-4 h-4 text-yellow-400" />;
    return <Activity className="w-4 h-4 text-slate-400" />;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-12 h-12 text-violet-500 mx-auto mb-4 animate-pulse" />
          <p className="text-slate-400">Loading Security Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="admin-security-dashboard">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/dashboard" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <Shield className="w-8 h-8 text-violet-400" />
              <div>
                <h1 className="text-xl font-bold">Security Command Center</h1>
                <p className="text-slate-400 text-sm">Real-time threat monitoring & protection</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge 
                className={`${getThreatLevelColor(securityStats?.threat_level || 'LOW')} text-white`}
                data-testid="threat-level-badge"
              >
                Threat Level: {securityStats?.threat_level || 'LOW'}
              </Badge>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={fetchSecurityData}
                disabled={refreshing}
                data-testid="refresh-btn"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button 
                size="sm" 
                className="bg-red-600 hover:bg-red-700"
                onClick={() => setShowBlockModal(true)}
                data-testid="block-ip-btn"
              >
                <Ban className="w-4 h-4 mr-2" />
                Block IP
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Active Blocks"
            value={securityStats?.active_blocks || 0}
            icon={<Ban className="w-5 h-5" />}
            trend={securityStats?.active_blocks > 0 ? 'up' : 'neutral'}
            color="red"
            testId="active-blocks-stat"
          />
          <StatCard
            title="Security Events (7d)"
            value={securityStats?.total_security_events || 0}
            icon={<AlertTriangle className="w-5 h-5" />}
            trend={securityStats?.total_security_events > 50 ? 'up' : 'down'}
            color="yellow"
            testId="security-events-stat"
          />
          <StatCard
            title="Failed Logins"
            value={securityStats?.login_failures || 0}
            icon={<XCircle className="w-5 h-5" />}
            trend={securityStats?.login_failures > 10 ? 'up' : 'down'}
            color="orange"
            testId="failed-logins-stat"
          />
          <StatCard
            title="Whitelisted IPs"
            value={securityStats?.whitelisted_count || 0}
            icon={<ShieldCheck className="w-5 h-5" />}
            trend="neutral"
            color="green"
            testId="whitelisted-stat"
          />
        </div>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-slate-800 border border-slate-700">
            <TabsTrigger value="overview" className="data-[state=active]:bg-violet-600">
              <Activity className="w-4 h-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="blocked" className="data-[state=active]:bg-violet-600">
              <Ban className="w-4 h-4 mr-2" />
              Blocked IPs
            </TabsTrigger>
            <TabsTrigger value="suspicious" className="data-[state=active]:bg-violet-600">
              <AlertTriangle className="w-4 h-4 mr-2" />
              Suspicious Users
            </TabsTrigger>
            <TabsTrigger value="activity" className="data-[state=active]:bg-violet-600">
              <Clock className="w-4 h-4 mr-2" />
              Activity Log
            </TabsTrigger>
            <TabsTrigger value="investigate" className="data-[state=active]:bg-violet-600">
              <Search className="w-4 h-4 mr-2" />
              Investigate IP
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Real-time Activity Feed */}
              <Card className="bg-slate-900 border-slate-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    Real-time Activity
                  </CardTitle>
                  <CardDescription>Latest security events</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {realtimeActivity.slice(0, 15).map((event, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-start gap-3 p-2 bg-slate-800/50 rounded-lg"
                      >
                        {getEventTypeIcon(event.event_type)}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white truncate">
                            {event.event_type?.replace(/_/g, ' ')}
                          </p>
                          <p className="text-xs text-slate-400">
                            {event.ip_address || event.user_email || 'System'}
                          </p>
                        </div>
                        <span className="text-xs text-slate-500">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                    {realtimeActivity.length === 0 && (
                      <p className="text-slate-500 text-center py-8">No recent activity</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Top Offending IPs */}
              <Card className="bg-slate-900 border-slate-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Globe className="w-5 h-5 text-red-400" />
                    Top Flagged IPs
                  </CardTitle>
                  <CardDescription>IPs with most security incidents</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {securityStats?.top_offending_ips?.map((ip, idx) => (
                      <div 
                        key={idx}
                        className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            ip.count > 10 ? 'bg-red-500/20 text-red-400' :
                            ip.count > 5 ? 'bg-orange-500/20 text-orange-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {idx + 1}
                          </div>
                          <div>
                            <p className="font-mono text-sm">{ip.ip}</p>
                            <p className="text-xs text-slate-400">{ip.count} incidents</p>
                          </div>
                        </div>
                        <Button 
                          size="sm" 
                          variant="destructive"
                          onClick={() => {
                            setBlockFormData({ ip: ip.ip, reason: 'Flagged for suspicious activity', duration: 24 });
                            setShowBlockModal(true);
                          }}
                        >
                          Block
                        </Button>
                      </div>
                    ))}
                    {(!securityStats?.top_offending_ips || securityStats.top_offending_ips.length === 0) && (
                      <p className="text-slate-500 text-center py-8">No flagged IPs</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Event Breakdown */}
              <Card className="bg-slate-900 border-slate-800 lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5 text-violet-400" />
                    Security Event Breakdown (7 days)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(securityStats?.event_breakdown || {}).map(([event, count]) => (
                      <div key={event} className="p-4 bg-slate-800/50 rounded-lg">
                        <p className="text-2xl font-bold text-white">{count}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {event.replace('SECURITY_', '').replace(/_/g, ' ')}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Blocked IPs Tab */}
          <TabsContent value="blocked">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle>Blocked IP Addresses</CardTitle>
                <CardDescription>Manage blocked IPs and their status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {blockedIPs.map((ip, idx) => (
                    <div 
                      key={idx}
                      className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                      data-testid={`blocked-ip-${ip.ip_address}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${ip.active !== false ? 'bg-red-500/20' : 'bg-slate-700'}`}>
                          {ip.active !== false ? (
                            <Lock className="w-5 h-5 text-red-400" />
                          ) : (
                            <Unlock className="w-5 h-5 text-slate-400" />
                          )}
                        </div>
                        <div>
                          <p className="font-mono text-white">{ip.ip_address}</p>
                          <p className="text-sm text-slate-400">{ip.reason}</p>
                          <p className="text-xs text-slate-500">
                            Blocked: {new Date(ip.blocked_at).toLocaleString()}
                            {ip.expires_at && ` • Expires: ${new Date(ip.expires_at).toLocaleString()}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={ip.active !== false ? 'destructive' : 'secondary'}>
                          {ip.active !== false ? 'Active' : 'Expired'}
                        </Badge>
                        {ip.active !== false && (
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => handleUnblockIP(ip.ip_address)}
                          >
                            <Unlock className="w-4 h-4 mr-1" />
                            Unblock
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  {blockedIPs.length === 0 && (
                    <div className="text-center py-12 text-slate-500">
                      <ShieldCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No blocked IPs</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Suspicious Users Tab */}
          <TabsContent value="suspicious">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle>Suspicious User Activity</CardTitle>
                <CardDescription>Users with multiple security flags in the last 7 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {suspiciousUsers.map((user, idx) => (
                    <div 
                      key={idx}
                      className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${
                          user.risk_level === 'HIGH' ? 'bg-red-500/20' :
                          user.risk_level === 'MEDIUM' ? 'bg-orange-500/20' :
                          'bg-yellow-500/20'
                        }`}>
                          <Users className={`w-5 h-5 ${
                            user.risk_level === 'HIGH' ? 'text-red-400' :
                            user.risk_level === 'MEDIUM' ? 'text-orange-400' :
                            'text-yellow-400'
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium text-white">{user.email}</p>
                          <p className="text-sm text-slate-400">
                            {user.event_count} events • {user.unique_ips} unique IPs
                          </p>
                          <div className="flex gap-1 mt-1 flex-wrap">
                            {user.event_types?.slice(0, 3).map((type, i) => (
                              <Badge key={i} variant="outline" className="text-xs">
                                {type.replace('SECURITY_', '').replace(/_/g, ' ')}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      <Badge className={`${
                        user.risk_level === 'HIGH' ? 'bg-red-500' :
                        user.risk_level === 'MEDIUM' ? 'bg-orange-500' :
                        'bg-yellow-500'
                      } text-white`}>
                        {user.risk_level} RISK
                      </Badge>
                    </div>
                  ))}
                  {suspiciousUsers.length === 0 && (
                    <div className="text-center py-12 text-slate-500">
                      <ShieldCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No suspicious users detected</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Activity Log Tab */}
          <TabsContent value="activity">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle>Security Audit Log</CardTitle>
                <CardDescription>Complete security event history</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {auditLogs.map((log, idx) => (
                    <div 
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                      {getEventTypeIcon(log.event_type)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-white">
                            {log.event_type?.replace(/_/g, ' ')}
                          </p>
                          <Badge variant="outline" className={`text-xs ${
                            log.severity === 'CRITICAL' ? 'border-red-500 text-red-400' :
                            log.severity === 'WARNING' ? 'border-yellow-500 text-yellow-400' :
                            'border-slate-600 text-slate-400'
                          }`}>
                            {log.severity}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-400 mt-1">
                          {log.user_email || log.ip_address || 'System Event'}
                          {log.details && Object.keys(log.details).length > 0 && (
                            <span className="ml-2 text-slate-500">
                              • {JSON.stringify(log.details).slice(0, 50)}...
                            </span>
                          )}
                        </p>
                      </div>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                  ))}
                  {auditLogs.length === 0 && (
                    <p className="text-slate-500 text-center py-12">No audit logs available</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Investigate IP Tab */}
          <TabsContent value="investigate">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle>IP Address Investigation</CardTitle>
                <CardDescription>Search for activity from a specific IP address</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-3 mb-6">
                  <Input
                    placeholder="Enter IP address (e.g., 192.168.1.1)"
                    value={ipActivitySearch}
                    onChange={(e) => setIpActivitySearch(e.target.value)}
                    className="bg-slate-800 border-slate-700 max-w-md"
                    data-testid="ip-search-input"
                  />
                  <Button onClick={searchIPActivity} data-testid="search-ip-btn">
                    <Search className="w-4 h-4 mr-2" />
                    Search
                  </Button>
                </div>

                {ipActivity.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-slate-400">
                        Found {ipActivity.length} events for <span className="font-mono text-white">{ipActivitySearch}</span>
                      </p>
                      <Button 
                        variant="destructive" 
                        size="sm"
                        onClick={() => {
                          setBlockFormData({ ip: ipActivitySearch, reason: 'Manual investigation', duration: 24 });
                          setShowBlockModal(true);
                        }}
                      >
                        <Ban className="w-4 h-4 mr-2" />
                        Block This IP
                      </Button>
                    </div>
                    
                    <div className="max-h-[400px] overflow-y-auto space-y-2">
                      {ipActivity.map((activity, idx) => (
                        <div key={idx} className="p-3 bg-slate-800/50 rounded-lg">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {getEventTypeIcon(activity.activity_type)}
                              <span className="font-medium">{activity.activity_type}</span>
                            </div>
                            <span className="text-xs text-slate-500">
                              {new Date(activity.timestamp).toLocaleString()}
                            </span>
                          </div>
                          {activity.details && (
                            <p className="text-sm text-slate-400 mt-2">{activity.details}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {ipActivity.length === 0 && ipActivitySearch && (
                  <div className="text-center py-12 text-slate-500">
                    <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No activity found for this IP</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Block IP Modal */}
      {showBlockModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Ban className="w-5 h-5 text-red-400" />
              Block IP Address
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-1 block">IP Address</label>
                <Input
                  placeholder="192.168.1.1"
                  value={blockFormData.ip}
                  onChange={(e) => setBlockFormData({ ...blockFormData, ip: e.target.value })}
                  className="bg-slate-800 border-slate-700"
                  data-testid="modal-ip-input"
                />
              </div>
              
              <div>
                <label className="text-sm text-slate-400 mb-1 block">Reason</label>
                <Input
                  placeholder="Reason for blocking"
                  value={blockFormData.reason}
                  onChange={(e) => setBlockFormData({ ...blockFormData, reason: e.target.value })}
                  className="bg-slate-800 border-slate-700"
                />
              </div>
              
              <div>
                <label className="text-sm text-slate-400 mb-1 block">Duration (hours)</label>
                <Input
                  type="number"
                  min="1"
                  max="720"
                  value={blockFormData.duration}
                  onChange={(e) => setBlockFormData({ ...blockFormData, duration: parseInt(e.target.value) })}
                  className="bg-slate-800 border-slate-700"
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <Button 
                variant="outline" 
                className="flex-1"
                onClick={() => setShowBlockModal(false)}
              >
                Cancel
              </Button>
              <Button 
                className="flex-1 bg-red-600 hover:bg-red-700"
                onClick={handleBlockIP}
                data-testid="confirm-block-btn"
              >
                Block IP
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Stat Card Component
const StatCard = ({ title, value, icon, trend, color, testId }) => {
  const colorClasses = {
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    violet: 'bg-violet-500/20 text-violet-400 border-violet-500/30'
  };

  return (
    <Card className={`bg-slate-900 border ${colorClasses[color].split(' ')[2]}`} data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className={`p-2 rounded-lg ${colorClasses[color].split(' ').slice(0, 2).join(' ')}`}>
            {icon}
          </div>
          {trend === 'up' && <TrendingUp className="w-4 h-4 text-red-400" />}
          {trend === 'down' && <TrendingDown className="w-4 h-4 text-green-400" />}
        </div>
        <p className="text-3xl font-bold text-white mt-3">{value}</p>
        <p className="text-sm text-slate-400">{title}</p>
      </CardContent>
    </Card>
  );
};

export default AdminSecurityDashboard;
