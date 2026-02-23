import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, RefreshCw, Search, Users, Coins, UserPlus, Edit, 
  Shield, ShieldCheck, ChevronLeft, ChevronRight, X, Check
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import api from '../utils/api';

export default function AdminUsersManagement() {
  const [users, setUsers] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, size: 50, total: 0, pages: 0 });
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  
  // Modals
  const [showResetModal, setShowResetModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // Reset credits form
  const [resetData, setResetData] = useState({ credits: 100, reason: '' });
  
  // Create user form
  const [createData, setCreateData] = useState({
    name: '',
    email: '',
    password: '',
    credits: 100,
    role: 'user'
  });

  const fetchUsers = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('size', pagination.size);
      if (searchTerm) params.append('search', searchTerm);
      if (roleFilter && roleFilter !== 'all') params.append('role', roleFilter);
      
      const response = await api.get(`/api/admin/users/list?${params.toString()}`);
      setUsers(response.data.users || []);
      setPagination(response.data.pagination || { page: 1, size: 50, total: 0, pages: 0 });
    } catch (error) {
      toast.error('Failed to fetch users');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, roleFilter, pagination.size]);

  useEffect(() => {
    fetchUsers(1);
  }, []);

  const handleSearch = () => {
    fetchUsers(1);
  };

  const handleResetCredits = async () => {
    if (!resetData.reason || resetData.reason.length < 5) {
      toast.error('Please provide a reason (min 5 characters)');
      return;
    }
    
    try {
      const response = await api.post('/api/admin/users/reset-credits', {
        user_id: selectedUser.id,
        credits: resetData.credits,
        reason: resetData.reason
      });
      
      toast.success(`Credits reset to ${resetData.credits} for ${selectedUser.email}`);
      setShowResetModal(false);
      setSelectedUser(null);
      setResetData({ credits: 100, reason: '' });
      fetchUsers(pagination.page);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset credits');
    }
  };

  const handleCreateUser = async () => {
    if (!createData.name || !createData.email || !createData.password) {
      toast.error('Please fill all required fields');
      return;
    }
    
    if (createData.password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    
    try {
      const response = await api.post('/api/admin/users/create', createData);
      toast.success(`User ${createData.email} created with ${createData.credits} credits`);
      setShowCreateModal(false);
      setCreateData({ name: '', email: '', password: '', credits: 100, role: 'user' });
      fetchUsers(1);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const setUnlimitedCredits = async (user) => {
    try {
      await api.post('/api/admin/users/reset-credits', {
        user_id: user.id,
        credits: 999999999,
        reason: 'Set unlimited credits'
      });
      toast.success(`Unlimited credits set for ${user.email}`);
      fetchUsers(pagination.page);
    } catch (error) {
      toast.error('Failed to set unlimited credits');
    }
  };

  const formatCredits = (credits) => {
    if (credits >= 999999999) return 'Unlimited';
    if (credits >= 1000000) return `${(credits / 1000000).toFixed(1)}M`;
    if (credits >= 1000) return `${(credits / 1000).toFixed(1)}K`;
    return credits.toLocaleString();
  };

  const getRoleBadge = (role) => {
    const styles = {
      admin: 'bg-red-500/20 text-red-300',
      qa: 'bg-purple-500/20 text-purple-300',
      user: 'bg-blue-500/20 text-blue-300'
    };
    return styles[role] || styles.user;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <Link to="/app/admin" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Admin</span>
              </Link>
              <div className="flex items-center gap-2">
                <Users className="w-6 h-6 text-purple-400" />
                <h1 className="text-xl sm:text-2xl font-bold text-white">User Management</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setShowCreateModal(true)}
                className="bg-purple-600 hover:bg-purple-700"
              >
                <UserPlus className="w-4 h-4 mr-2" /> Create User
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchUsers(pagination.page)}
                disabled={loading}
                className="border-slate-600 text-slate-300"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
            <p className="text-slate-400 text-sm">Total Users</p>
            <p className="text-2xl font-bold text-white">{pagination.total.toLocaleString()}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
            <p className="text-slate-400 text-sm">Admin Users</p>
            <p className="text-2xl font-bold text-red-400">{users.filter(u => u.role === 'admin').length}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
            <p className="text-slate-400 text-sm">QA Users</p>
            <p className="text-2xl font-bold text-purple-400">{users.filter(u => u.role === 'qa').length}</p>
          </div>
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
            <p className="text-slate-400 text-sm">Regular Users</p>
            <p className="text-2xl font-bold text-blue-400">{users.filter(u => u.role === 'user').length}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by email or name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10 bg-slate-700 border-slate-600 text-white w-full"
                  data-testid="search-users"
                />
              </div>
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-full sm:w-[140px] bg-slate-700 border-slate-600 text-white">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all" className="text-white">All Roles</SelectItem>
                <SelectItem value="admin" className="text-white">Admin</SelectItem>
                <SelectItem value="qa" className="text-white">QA</SelectItem>
                <SelectItem value="user" className="text-white">User</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700 w-full sm:w-auto">
              <Search className="w-4 h-4 mr-2" /> Search
            </Button>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-700/50">
                  <th className="text-left p-4 text-slate-300 font-medium">User</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Role</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Credits</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Joined</th>
                  <th className="text-left p-4 text-slate-300 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                      Loading...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400">
                      No users found
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="border-t border-slate-700/50 hover:bg-slate-700/30">
                      <td className="p-4">
                        <div>
                          <p className="text-white font-medium">{user.name || '-'}</p>
                          <p className="text-slate-400 text-sm">{user.email}</p>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getRoleBadge(user.role)}`}>
                          {user.role === 'admin' && <ShieldCheck className="w-3 h-3 inline mr-1" />}
                          {user.role === 'qa' && <Shield className="w-3 h-3 inline mr-1" />}
                          {user.role?.toUpperCase() || 'USER'}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Coins className="w-4 h-4 text-yellow-400" />
                          <span className={`font-medium ${user.credits >= 999999999 ? 'text-green-400' : 'text-white'}`}>
                            {formatCredits(user.credits || 0)}
                          </span>
                        </div>
                      </td>
                      <td className="p-4 text-slate-400 text-sm">
                        {user.createdAt ? new Date(user.createdAt).toLocaleDateString() : '-'}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedUser(user);
                              setResetData({ credits: user.credits || 100, reason: '' });
                              setShowResetModal(true);
                            }}
                            className="border-slate-600 text-slate-300 hover:text-white text-xs"
                          >
                            <Edit className="w-3 h-3 mr-1" /> Reset
                          </Button>
                          {user.credits < 999999999 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setUnlimitedCredits(user)}
                              className="border-green-500/50 text-green-400 hover:bg-green-500/20 text-xs"
                            >
                              Unlimited
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
            <div className="flex items-center justify-between p-4 border-t border-slate-700 flex-wrap gap-2">
              <p className="text-slate-400 text-sm">
                Showing {((pagination.page - 1) * pagination.size) + 1} - {Math.min(pagination.page * pagination.size, pagination.total)} of {pagination.total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === 1}
                  onClick={() => fetchUsers(pagination.page - 1)}
                  className="border-slate-600"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-slate-300 text-sm">
                  {pagination.page} / {pagination.pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pagination.page === pagination.pages}
                  onClick={() => fetchUsers(pagination.page + 1)}
                  className="border-slate-600"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Reset Credits Modal */}
      {showResetModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowResetModal(false)}>
          <div 
            className="bg-slate-800 rounded-xl max-w-md w-full p-6 border border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Coins className="w-5 h-5 text-yellow-400" /> Reset Credits
            </h3>
            <p className="text-slate-400 mb-4">
              Resetting credits for <span className="text-white font-medium">{selectedUser.email}</span>
            </p>
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm mb-1 block">New Credit Amount</label>
                <Input
                  type="number"
                  value={resetData.credits}
                  onChange={(e) => setResetData({ ...resetData, credits: parseInt(e.target.value) || 0 })}
                  className="bg-slate-700 border-slate-600 text-white"
                  min="0"
                  max="999999999"
                />
                <div className="flex gap-2 mt-2">
                  <Button size="sm" variant="outline" onClick={() => setResetData({ ...resetData, credits: 100 })} className="text-xs">100</Button>
                  <Button size="sm" variant="outline" onClick={() => setResetData({ ...resetData, credits: 1000 })} className="text-xs">1K</Button>
                  <Button size="sm" variant="outline" onClick={() => setResetData({ ...resetData, credits: 10000 })} className="text-xs">10K</Button>
                  <Button size="sm" variant="outline" onClick={() => setResetData({ ...resetData, credits: 999999999 })} className="text-xs text-green-400">Unlimited</Button>
                </div>
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Reason *</label>
                <Input
                  value={resetData.reason}
                  onChange={(e) => setResetData({ ...resetData, reason: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Reason for credit reset..."
                />
              </div>
              <div className="flex gap-3 pt-4">
                <Button variant="outline" className="flex-1 border-slate-600" onClick={() => setShowResetModal(false)}>
                  Cancel
                </Button>
                <Button className="flex-1 bg-yellow-600 hover:bg-yellow-700" onClick={handleResetCredits}>
                  <Check className="w-4 h-4 mr-2" /> Reset Credits
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowCreateModal(false)}>
          <div 
            className="bg-slate-800 rounded-xl max-w-md w-full p-6 border border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-purple-400" /> Create New User
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Full Name *</label>
                <Input
                  value={createData.name}
                  onChange={(e) => setCreateData({ ...createData, name: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Email *</label>
                <Input
                  type="email"
                  value={createData.email}
                  onChange={(e) => setCreateData({ ...createData, email: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="user@example.com"
                />
              </div>
              <div>
                <label className="text-slate-400 text-sm mb-1 block">Password *</label>
                <Input
                  type="password"
                  value={createData.password}
                  onChange={(e) => setCreateData({ ...createData, password: e.target.value })}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Min 8 characters"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 text-sm mb-1 block">Initial Credits</label>
                  <Input
                    type="number"
                    value={createData.credits}
                    onChange={(e) => setCreateData({ ...createData, credits: parseInt(e.target.value) || 0 })}
                    className="bg-slate-700 border-slate-600 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 text-sm mb-1 block">Role</label>
                  <Select value={createData.role} onValueChange={(v) => setCreateData({ ...createData, role: v })}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="user" className="text-white">User</SelectItem>
                      <SelectItem value="qa" className="text-white">QA</SelectItem>
                      <SelectItem value="admin" className="text-white">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <Button variant="outline" className="flex-1 border-slate-600" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button className="flex-1 bg-purple-600 hover:bg-purple-700" onClick={handleCreateUser}>
                  <UserPlus className="w-4 h-4 mr-2" /> Create User
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
