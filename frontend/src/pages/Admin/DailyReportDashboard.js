import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Mail, Calendar, Users, Activity, AlertTriangle, 
  Shield, CreditCard, Clock, RefreshCw, Send, Eye, Download,
  CheckCircle, XCircle, Globe, Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DailyReportDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [report, setReport] = useState(null);
  const [scheduleStatus, setScheduleStatus] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [reportRes, scheduleRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/api/daily-report/preview`, { headers }),
        fetch(`${API_URL}/api/daily-report/schedule-status`, { headers }),
        fetch(`${API_URL}/api/daily-report/history?days=30`, { headers })
      ]);

      if (reportRes.ok) {
        const data = await reportRes.json();
        setReport(data.report);
      }

      if (scheduleRes.ok) {
        const data = await scheduleRes.json();
        setScheduleStatus(data.schedule);
      }

      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.history || []);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const sendReportNow = async () => {
    setSending(true);
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(`${API_URL}/api/daily-report/send-now`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Report sent to ${data.recipients.length} recipients`);
        fetchData();
      } else {
        toast.error('Failed to send report');
      }
    } catch (error) {
      toast.error('Error sending report');
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const visitors = report?.sections?.visitors || {};
  const activities = report?.sections?.activities || {};
  const failures = report?.sections?.failed_accesses || {};
  const rateLimits = report?.sections?.rate_limiting || {};
  const suspicious = report?.sections?.suspicious_ips || {};
  const credits = report?.sections?.free_credits_usage || {};

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/app/admin" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Mail className="h-6 w-6 text-indigo-500" />
              Daily Visitor Report
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Automated daily reports for www.visionary-suite.com
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={sendReportNow} disabled={sending}>
            <Send className="h-4 w-4 mr-2" />
            {sending ? 'Sending...' : 'Send Now'}
          </Button>
        </div>
      </div>

      {/* Schedule Status */}
      {scheduleStatus && (
        <Card className="mb-6 border-indigo-200 bg-indigo-50 dark:bg-indigo-900/20">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-indigo-500" />
                <div>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    Automated Daily Schedule
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Sends at {scheduleStatus.time}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <Badge variant={scheduleStatus.enabled ? "default" : "secondary"}>
                  {scheduleStatus.enabled ? "Enabled" : "Disabled"}
                </Badge>
                <p className="text-sm text-gray-500 mt-1">
                  Recipients: {scheduleStatus.recipients?.join(', ')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4 text-center">
            <Users className="h-8 w-8 mx-auto text-blue-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {visitors.total_visitors_today || 0}
            </div>
            <p className="text-sm text-gray-500">Total Visitors</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 text-center">
            <Zap className="h-8 w-8 mx-auto text-green-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {visitors.new_users_today || 0}
            </div>
            <p className="text-sm text-gray-500">New Users</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 text-center">
            <Activity className="h-8 w-8 mx-auto text-purple-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {activities.total_activities || 0}
            </div>
            <p className="text-sm text-gray-500">Activities</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 text-center">
            <XCircle className="h-8 w-8 mx-auto text-red-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {failures.total_failures || 0}
            </div>
            <p className="text-sm text-gray-500">Failed Accesses</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-amber-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {rateLimits.total_rate_limit_events || 0}
            </div>
            <p className="text-sm text-gray-500">Rate Limits</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 text-center">
            <Shield className="h-8 w-8 mx-auto text-red-600 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {suspicious.total_suspicious_ips || 0}
            </div>
            <p className="text-sm text-gray-500">Suspicious IPs</p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Visitors List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-500" />
              Today's Visitors
            </CardTitle>
            <CardDescription>Users who logged in today</CardDescription>
          </CardHeader>
          <CardContent>
            {visitors.visitors_list?.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {visitors.visitors_list.map((v, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <div>
                      <p className="font-medium text-sm">{v.name}</p>
                      <p className="text-xs text-gray-500">{v.email}</p>
                    </div>
                    <div className="text-right">
                      <Badge variant={v.is_new_user ? "default" : "secondary"} className="text-xs">
                        {v.is_new_user ? 'NEW' : 'Returning'}
                      </Badge>
                      <p className="text-xs text-gray-500 mt-1">{v.login_count_today} logins</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No visitors today</p>
            )}
          </CardContent>
        </Card>

        {/* Features Used */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-500" />
              Features Used
            </CardTitle>
            <CardDescription>Feature usage breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            {report?.sections?.features_used?.length > 0 ? (
              <div className="space-y-2">
                {report.sections.features_used.map((f, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <div>
                      <p className="font-medium text-sm">{f.feature}</p>
                      <p className="text-xs text-gray-500">{f.unique_users} users</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">{f.total_uses} uses</p>
                      <p className={`text-xs ${f.success_rate >= 90 ? 'text-green-500' : 'text-amber-500'}`}>
                        {f.success_rate}% success
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">No features used today</p>
            )}
          </CardContent>
        </Card>

        {/* Suspicious IPs */}
        {suspicious.total_suspicious_ips > 0 && (
          <Card className="border-red-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <Shield className="h-5 w-5" />
                Suspicious IPs Detected
              </CardTitle>
              <CardDescription>IPs with suspicious activity patterns</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {suspicious.suspicious_ips_list?.map((ip, i) => (
                  <div key={i} className="p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-mono font-bold">{ip.ip}</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {ip.reasons?.join(', ')}
                        </p>
                      </div>
                      <Badge variant="destructive">
                        Score: {ip.suspicion_score}/100
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Credits Usage */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-green-500" />
              Credits Usage
            </CardTitle>
            <CardDescription>Free credits consumed today</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center mb-4">
              <p className="text-4xl font-bold text-green-600">
                {credits.total_credits_used_today || 0}
              </p>
              <p className="text-sm text-gray-500">Total Credits Used</p>
            </div>
            {credits.by_user?.length > 0 && (
              <div className="space-y-2">
                {credits.by_user.slice(0, 5).map((u, i) => (
                  <div key={i} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
                    <div>
                      <p className="font-medium text-sm">{u.name}</p>
                      <p className="text-xs text-gray-500">{u.email}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-green-600">{u.total_credits_used}</p>
                      <p className="text-xs text-gray-500">{u.features_used?.length} features</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Report History */}
      {history.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-indigo-500" />
              Report History
            </CardTitle>
            <CardDescription>Previously sent daily reports</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {history.map((h, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="font-medium">Report for {h.report_date}</p>
                      <p className="text-xs text-gray-500">
                        Sent: {new Date(h.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">
                    {h.recipients?.length || 0} recipients
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DailyReportDashboard;
