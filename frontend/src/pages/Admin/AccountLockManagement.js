import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Lock, Unlock, Users, Shield, AlertTriangle,
  Search, RefreshCw, Clock, UserX, UserCheck, Settings,
  Calendar, Filter, ChevronDown, CheckCircle, XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AccountLockManagement = () => {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [lockedAccounts, setLockedAccounts] = useState([]);
  const [autoLockConfig, setAutoLockConfig] = useState(null);
  const [lockHistory, setLockHistory] = useState([]);
  const [search, setSearch] = useState('');
  const [filterLocked, setFilterLocked] = useState(null);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [activeTab, setActiveTab] = useState('users');
  
  // Lock modal state
  const [showLockModal, setShowLockModal] = useState(false);
  const [lockTarget, setLockTarget] = useState(null);
  const [lockReason, setLockReason] = useState('');
  const [lockDuration, setLockDuration] = useState('');
  
  // Config modal state
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [configForm, setConfigForm] = useState({
    enabled: true,
    max_failed_attempts: 5,
    lockout_duration_minutes: 30,
    suspicious_ip_threshold: 10
  });

  useEffect(() => {
    fetchData();
  }, [filterLocked, search]);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [usersRes, lockedRes, configRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/api/account-management/users?filter_locked=${filterLocked !== null ? filterLocked : ''}&search=${search}`, { headers }),
        fetch(`${API_URL}/api/account-management/currently-locked`, { headers }),
        fetch(`${API_URL}/api/account-management/auto-lock/config`, { headers }),
        fetch(`${API_URL}/api/account-management/lockout-history?days=30`, { headers })
      ]);

      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users || []);
      }

      if (lockedRes.ok) {
        const data = await lockedRes.json();
        setLockedAccounts(data.locked_accounts || []);
      }

      if (configRes.ok) {
        const data = await configRes.json();
        setAutoLockConfig(data.config);
        setConfigForm(data.config);
      }

      if (historyRes.ok) {
        const data = await historyRes.json();
        setLockHistory(data.history || []);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load account data');
    } finally {
      setLoading(false);
    }
  };

  const handleLockAccount = async () => {
    if (!lockTarget || !lockReason) {
      toast.error('Please provide a reason for locking');
      return;
    }

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_URL}/api/account-management/lock`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: lockTarget.id,
          reason: lockReason,
          duration_hours: lockDuration ? parseInt(lockDuration) : null
        })
      });

      if (response.ok) {
        toast.success(`Account ${lockTarget.email} locked successfully`);
        setShowLockModal(false);
        setLockTarget(null);
        setLockReason('');
        setLockDuration('');
        fetchData();
      } else {
        toast.error('Failed to lock account');
      }
    } catch (error) {
      toast.error('Error locking account');
    }
  };

  const handleUnlockAccount = async (user) => {
    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_URL}/api/account-management/unlock`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: user.id,
          reason: 'Manual unlock by admin'
        })
      });

      if (response.ok) {
        toast.success(`Account ${user.email} unlocked successfully`);
        fetchData();
      } else {
        toast.error('Failed to unlock account');
      }
    } catch (error) {
      toast.error('Error unlocking account');
    }
  };

  const handleBulkLock = async () => {
    if (selectedUsers.length === 0) {
      toast.error('Please select users to lock');
      return;
    }

    const reason = window.prompt('Enter reason for bulk lock:');
    if (!reason) return;

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_URL}/api/account-management/bulk-lock`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_ids: selectedUsers,
          reason: reason,
          duration_hours: null
        })
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
        setSelectedUsers([]);
        fetchData();
      } else {
        toast.error('Failed to bulk lock accounts');
      }
    } catch (error) {
      toast.error('Error in bulk lock');
    }
  };

  const handleBulkUnlock = async () => {
    if (selectedUsers.length === 0) {
      toast.error('Please select users to unlock');
      return;
    }

    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_URL}/api/account-management/bulk-unlock`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedUsers)
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
        setSelectedUsers([]);
        fetchData();
      } else {
        toast.error('Failed to bulk unlock accounts');
      }
    } catch (error) {
      toast.error('Error in bulk unlock');
    }
  };

  const handleSaveConfig = async () => {
    const token = localStorage.getItem('token');
    try {
      const response = await fetch(`${API_URL}/api/account-management/auto-lock/config`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(configForm)
      });

      if (response.ok) {
        toast.success('Auto-lock configuration saved');
        setShowConfigModal(false);
        fetchData();
      } else {
        toast.error('Failed to save configuration');
      }
    } catch (error) {
      toast.error('Error saving configuration');
    }
  };

  const toggleSelectUser = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const selectAllUsers = () => {
    if (selectedUsers.length === users.length) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(users.map(u => u.id));
    }
  };

  const getRoleBadge = (role) => {
    const colors = {
      'ADMIN': 'bg-purple-100 text-purple-700',
      'QA': 'bg-blue-100 text-blue-700',
      'DEMO': 'bg-orange-100 text-orange-700',
      'USER': 'bg-gray-100 text-gray-700'
    };
    return colors[role?.toUpperCase()] || colors['USER'];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

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
              <Shield className="h-6 w-6 text-indigo-500" />
              Account Lock Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              Lock/Unlock user accounts for www.visionary-suite.com
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => setShowConfigModal(true)}>
            <Settings className="h-4 w-4 mr-2" />
            Auto-Lock Settings
          </Button>
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4 text-center">
            <Users className="h-8 w-8 mx-auto text-blue-500 mb-2" />
            <div className="text-3xl font-bold text-gray-900 dark:text-white">{users.length}</div>
            <p className="text-sm text-gray-500">Total Users</p>
          </CardContent>
        </Card>
        <Card className="border-red-200">
          <CardContent className="pt-4 text-center">
            <Lock className="h-8 w-8 mx-auto text-red-500 mb-2" />
            <div className="text-3xl font-bold text-red-600">{lockedAccounts.length}</div>
            <p className="text-sm text-gray-500">Currently Locked</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <UserCheck className="h-8 w-8 mx-auto text-green-500 mb-2" />
            <div className="text-3xl font-bold text-green-600">{users.length - lockedAccounts.length}</div>
            <p className="text-sm text-gray-500">Active Accounts</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-amber-500 mb-2" />
            <div className="text-3xl font-bold text-amber-600">
              {lockHistory.filter(h => h.action === 'ACCOUNT_LOCKED').length}
            </div>
            <p className="text-sm text-gray-500">Locks (30 days)</p>
          </CardContent>
        </Card>
      </div>

      {/* Auto-Lock Config Status */}
      {autoLockConfig && (
        <Card className={`mb-6 ${autoLockConfig.enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className={`h-5 w-5 ${autoLockConfig.enabled ? 'text-green-500' : 'text-gray-400'}`} />
                <div>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    Auto-Lock Protection
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Lock after {autoLockConfig.max_failed_attempts} failed attempts for {autoLockConfig.lockout_duration_minutes} minutes
                  </p>
                </div>
              </div>
              <Badge variant={autoLockConfig.enabled ? "default" : "secondary"}>
                {autoLockConfig.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {['users', 'locked', 'history'].map(tab => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "outline"}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'users' && <Users className="h-4 w-4 mr-2" />}
            {tab === 'locked' && <Lock className="h-4 w-4 mr-2" />}
            {tab === 'history' && <Clock className="h-4 w-4 mr-2" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === 'locked' && lockedAccounts.length > 0 && (
              <Badge variant="destructive" className="ml-2">{lockedAccounts.length}</Badge>
            )}
          </Button>
        ))}
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>All Users</CardTitle>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search users..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
                <select
                  className="border rounded-md px-3 py-2 text-sm"
                  value={filterLocked === null ? '' : filterLocked.toString()}
                  onChange={(e) => setFilterLocked(e.target.value === '' ? null : e.target.value === 'true')}
                >
                  <option value="">All Users</option>
                  <option value="true">Locked Only</option>
                  <option value="false">Active Only</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Bulk Actions */}
            {selectedUsers.length > 0 && (
              <div className="flex items-center gap-3 mb-4 p-3 bg-indigo-50 rounded-lg">
                <span className="text-sm font-medium">{selectedUsers.length} selected</span>
                <Button size="sm" variant="destructive" onClick={handleBulkLock}>
                  <Lock className="h-4 w-4 mr-1" />
                  Bulk Lock
                </Button>
                <Button size="sm" variant="outline" onClick={handleBulkUnlock}>
                  <Unlock className="h-4 w-4 mr-1" />
                  Bulk Unlock
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSelectedUsers([])}>
                  Clear
                </Button>
              </div>
            )}

            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2">
                    <input
                      type="checkbox"
                      checked={selectedUsers.length === users.length && users.length > 0}
                      onChange={selectAllUsers}
                      className="rounded"
                    />
                  </th>
                  <th className="text-left py-3 px-2">User</th>
                  <th className="text-left py-3 px-2">Role</th>
                  <th className="text-left py-3 px-2">Status</th>
                  <th className="text-left py-3 px-2">Joined</th>
                  <th className="text-right py-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-2">
                      <input
                        type="checkbox"
                        checked={selectedUsers.includes(u.id)}
                        onChange={() => toggleSelectUser(u.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="py-3 px-2">
                      <div>
                        <p className="font-medium">{u.name}</p>
                        <p className="text-sm text-gray-500">{u.email}</p>
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadge(u.role)}`}>
                        {u.role || 'USER'}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      {u.isLocked ? (
                        <div className="flex items-center gap-1 text-red-600">
                          <Lock className="h-4 w-4" />
                          <span className="text-sm font-medium">Locked</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-4 w-4" />
                          <span className="text-sm font-medium">Active</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-2 text-sm text-gray-500">
                      {u.createdAt ? new Date(u.createdAt).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {u.isLocked ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-green-600 hover:bg-green-50"
                          onClick={() => handleUnlockAccount(u)}
                        >
                          <Unlock className="h-4 w-4 mr-1" />
                          Unlock
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 hover:bg-red-50"
                          onClick={() => {
                            setLockTarget(u);
                            setShowLockModal(true);
                          }}
                        >
                          <Lock className="h-4 w-4 mr-1" />
                          Lock
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Locked Accounts Tab */}
      {activeTab === 'locked' && (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <Lock className="h-5 w-5" />
              Currently Locked Accounts
            </CardTitle>
            <CardDescription>Accounts that are currently locked from accessing the system</CardDescription>
          </CardHeader>
          <CardContent>
            {lockedAccounts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <UserCheck className="h-12 w-12 mx-auto mb-3 text-green-500" />
                <p>No accounts are currently locked</p>
              </div>
            ) : (
              <div className="space-y-3">
                {lockedAccounts.map((lock, i) => (
                  <div key={i} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{lock.email}</p>
                        <p className="text-sm text-gray-600">
                          Locked: {lock.lockedAt ? new Date(lock.lockedAt).toLocaleString() : 'Unknown'}
                        </p>
                        <p className="text-sm text-gray-600">
                          By: {lock.lockedBy || 'System'} | Reason: {lock.reason || 'N/A'}
                        </p>
                        {lock.lockUntil && (
                          <p className="text-sm text-amber-600">
                            Expires: {new Date(lock.lockUntil).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <Button
                        variant="outline"
                        className="text-green-600 hover:bg-green-50"
                        onClick={() => handleUnlockAccount({ id: lock.userId, email: lock.email })}
                      >
                        <Unlock className="h-4 w-4 mr-1" />
                        Unlock
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-indigo-500" />
              Lock/Unlock History (Last 30 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lockHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No lock/unlock events in the last 30 days</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {lockHistory.map((event, i) => (
                  <div key={i} className={`p-3 rounded-lg flex items-center justify-between ${
                    event.action.includes('LOCK') && !event.action.includes('UNLOCK')
                      ? 'bg-red-50 border border-red-100'
                      : 'bg-green-50 border border-green-100'
                  }`}>
                    <div className="flex items-center gap-3">
                      {event.action.includes('LOCK') && !event.action.includes('UNLOCK') ? (
                        <Lock className="h-5 w-5 text-red-500" />
                      ) : (
                        <Unlock className="h-5 w-5 text-green-500" />
                      )}
                      <div>
                        <p className="font-medium text-sm">
                          {event.action.replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs text-gray-600">
                          {event.target_user_email || `${event.user_count || 0} users`} by {event.admin_email}
                        </p>
                        {event.reason && (
                          <p className="text-xs text-gray-500">Reason: {event.reason}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      {new Date(event.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Lock Modal */}
      {showLockModal && lockTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Lock className="h-5 w-5 text-red-500" />
              Lock Account
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Locking: <strong>{lockTarget.email}</strong>
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Reason *</label>
                <Input
                  placeholder="Enter reason for locking..."
                  value={lockReason}
                  onChange={(e) => setLockReason(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Duration (hours)</label>
                <Input
                  type="number"
                  placeholder="Leave empty for permanent lock"
                  value={lockDuration}
                  onChange={(e) => setLockDuration(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">Leave empty to lock until manual unlock</p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="outline" onClick={() => setShowLockModal(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleLockAccount}>
                <Lock className="h-4 w-4 mr-1" />
                Lock Account
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Config Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Settings className="h-5 w-5 text-indigo-500" />
              Auto-Lock Configuration
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Enable Auto-Lock</label>
                <input
                  type="checkbox"
                  checked={configForm.enabled}
                  onChange={(e) => setConfigForm({ ...configForm, enabled: e.target.checked })}
                  className="rounded"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Failed Attempts</label>
                <Input
                  type="number"
                  value={configForm.max_failed_attempts}
                  onChange={(e) => setConfigForm({ ...configForm, max_failed_attempts: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Lockout Duration (minutes)</label>
                <Input
                  type="number"
                  value={configForm.lockout_duration_minutes}
                  onChange={(e) => setConfigForm({ ...configForm, lockout_duration_minutes: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Suspicious IP Threshold</label>
                <Input
                  type="number"
                  value={configForm.suspicious_ip_threshold}
                  onChange={(e) => setConfigForm({ ...configForm, suspicious_ip_threshold: parseInt(e.target.value) })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="outline" onClick={() => setShowConfigModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveConfig}>
                Save Configuration
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountLockManagement;
