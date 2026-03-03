import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Shield, RefreshCw, Mail, Globe, Smartphone, Fingerprint,
  AlertTriangle, CheckCircle, XCircle, Clock, Users, Ban, Lock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import api from '../../utils/api';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AntiAbuseDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [blockedSignups, setBlockedSignups] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      // Fetch blocked signups
      const blockedRes = await fetch(`${API_URL}/api/admin/blocked-signups?days=30`, { headers });
      if (blockedRes.ok) {
        const data = await blockedRes.json();
        setBlockedSignups(data.blocked || []);
      }

      // Fetch stats
      const statsRes = await fetch(`${API_URL}/api/admin/anti-abuse-stats`, { headers });
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch anti-abuse data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getReasonIcon = (reason) => {
    switch (reason) {
      case 'disposable_email':
        return <Mail className="w-4 h-4 text-red-400" />;
      case 'ip_limit_exceeded':
        return <Globe className="w-4 h-4 text-orange-400" />;
      case 'device_limit_exceeded':
        return <Fingerprint className="w-4 h-4 text-purple-400" />;
      case 'phone_already_used':
        return <Smartphone className="w-4 h-4 text-blue-400" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    }
  };

  const getReasonBadge = (reason) => {
    const colors = {
      'disposable_email': 'bg-red-100 text-red-800 border-red-300',
      'ip_limit_exceeded': 'bg-orange-100 text-orange-800 border-orange-300',
      'device_limit_exceeded': 'bg-purple-100 text-purple-800 border-purple-300',
      'phone_already_used': 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return colors[reason] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6" data-testid="anti-abuse-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/app/admin" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="h-6 w-6 text-indigo-500" />
              Anti-Abuse Protection
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Monitor and manage signup abuse prevention
            </p>
          </div>
        </div>
        <Button onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Protection Status */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-sm text-green-600">Disposable Email</p>
                <p className="text-lg font-bold text-green-700">BLOCKING</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-sm text-green-600">IP Limiting</p>
                <p className="text-lg font-bold text-green-700">2/IP/Month</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-sm text-green-600">Device Fingerprint</p>
                <p className="text-lg font-bold text-green-700">1/Device</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-sm text-green-600">Phone Verify</p>
                <p className="text-lg font-bold text-green-700">OPTIONAL</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Clock className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-sm text-blue-600">Credit Release</p>
                <p className="text-lg font-bold text-blue-700">0 → 20 → 80</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* New Email Verification Layer */}
      <div className="mb-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-500 rounded-lg">
            <Mail className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-amber-800">NEW: Email Verification Required</h3>
            <p className="text-sm text-amber-700">Users must verify email within 24 hours to unlock credits. No credits given until verified.</p>
          </div>
          <Badge className="bg-amber-500 text-white">ACTIVE</Badge>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-4 text-center">
          <div className="bg-white/50 rounded-lg p-2">
            <p className="text-2xl font-bold text-amber-600">0</p>
            <p className="text-xs text-amber-700">Credits on Signup</p>
          </div>
          <div className="bg-white/50 rounded-lg p-2">
            <p className="text-2xl font-bold text-green-600">20</p>
            <p className="text-xs text-green-700">After Email Verified</p>
          </div>
          <div className="bg-white/50 rounded-lg p-2">
            <p className="text-2xl font-bold text-blue-600">+80</p>
            <p className="text-xs text-blue-700">Over 7 Days</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeTab === 'overview' ? 'default' : 'outline'}
          onClick={() => setActiveTab('overview')}
        >
          <Shield className="w-4 h-4 mr-2" />
          Overview
        </Button>
        <Button
          variant={activeTab === 'blocked' ? 'default' : 'outline'}
          onClick={() => setActiveTab('blocked')}
        >
          <Ban className="w-4 h-4 mr-2" />
          Blocked Signups ({blockedSignups.length})
        </Button>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* How It Works */}
          <Card>
            <CardHeader>
              <CardTitle>Protection Layers</CardTitle>
              <CardDescription>Multi-layer abuse prevention system</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border-2 border-amber-300">
                <Mail className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-amber-800">Email Verification Required (NEW)</h4>
                  <p className="text-sm text-amber-700">0 credits until email verified. Must verify within 24 hours or lose access.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                <Mail className="w-5 h-5 text-red-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-700">Disposable Email Blocking</h4>
                  <p className="text-sm text-red-600">Blocks 200+ temporary email services (mailinator, guerrillamail, etc.)</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                <Globe className="w-5 h-5 text-orange-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-orange-700">IP Address Limiting</h4>
                  <p className="text-sm text-orange-600">Maximum 2 accounts per IP address per month</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
                <Fingerprint className="w-5 h-5 text-purple-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-purple-700">Device Fingerprinting</h4>
                  <p className="text-sm text-purple-600">Tracks browser fingerprint - 1 account per device</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                <Smartphone className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-700">Phone Verification</h4>
                  <p className="text-sm text-blue-600">Optional OTP verification for high-risk signups</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-teal-50 rounded-lg">
                <Clock className="w-5 h-5 text-teal-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-teal-700">Delayed Credit Release</h4>
                  <p className="text-sm text-teal-600">20 credits on signup, 80 more released over 7 days</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Blocked Attempts</CardTitle>
              <CardDescription>Last 10 blocked signup attempts</CardDescription>
            </CardHeader>
            <CardContent>
              {blockedSignups.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                  <p>No blocked signups in the last 30 days</p>
                  <p className="text-sm">Your protection is working!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {blockedSignups.slice(0, 10).map((blocked, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        {getReasonIcon(blocked.reason)}
                        <div>
                          <p className="text-sm font-medium truncate max-w-[200px]">{blocked.email}</p>
                          <p className="text-xs text-gray-500">{blocked.ip_address}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge className={getReasonBadge(blocked.reason)}>
                          {blocked.reason?.replace(/_/g, ' ')}
                        </Badge>
                        <p className="text-xs text-gray-500 mt-1">{formatDate(blocked.timestamp)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'blocked' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Ban className="w-5 h-5 text-red-500" />
              Blocked Signup Attempts (Last 30 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {blockedSignups.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
                <p className="text-lg font-medium">No blocked signups!</p>
                <p className="text-sm">All signup attempts in the last 30 days were legitimate.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium">Email</th>
                      <th className="px-4 py-3 text-left font-medium">IP Address</th>
                      <th className="px-4 py-3 text-left font-medium">Reason</th>
                      <th className="px-4 py-3 text-left font-medium">Message</th>
                      <th className="px-4 py-3 text-left font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {blockedSignups.map((blocked, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{blocked.email}</td>
                        <td className="px-4 py-3 text-gray-600">{blocked.ip_address}</td>
                        <td className="px-4 py-3">
                          <Badge className={getReasonBadge(blocked.reason)}>
                            {blocked.reason?.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                          {blocked.message}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {formatDate(blocked.timestamp)}
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

      {/* Info Banner */}
      <div className="mt-6 p-4 bg-indigo-50 border border-indigo-200 rounded-xl">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-indigo-500 mt-0.5" />
          <div>
            <h4 className="font-medium text-indigo-900">Anti-Abuse System Active</h4>
            <p className="text-sm text-indigo-700 mt-1">
              This system prevents users from creating multiple accounts to abuse free credits.
              Users now receive 20 credits immediately on signup, with 80 more released over 7 days of activity.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AntiAbuseDashboard;
