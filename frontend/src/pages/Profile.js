import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  Sparkles, ArrowLeft, User, Mail, Shield, Bell, 
  CreditCard, Clock, Save, Trash2, Download,
  Lock, Eye, EyeOff, CheckCircle, AlertCircle, Loader2, Play
} from 'lucide-react';
import { useAppTour } from '../components/AppTour';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [stats, setStats] = useState({ totalGenerations: 0, creditsUsed: 0 });
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    marketingEmails: false,
    generationAlerts: true,
    paymentAlerts: true,
    weeklyDigest: false
  });

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const [userRes, statsRes] = await Promise.all([
        api.get('/api/auth/me'),
        api.get('/api/generate/generations?page=0&size=1').catch(() => ({ data: { totalElements: 0 } }))
      ]);
      
      setUser(userRes.data);
      setFormData(prev => ({
        ...prev,
        name: userRes.data.name || '',
        email: userRes.data.email || ''
      }));
      
      // Load preferences from API or localStorage
      try {
        const prefsRes = await api.get('/api/privacy/my-data');
        if (prefsRes.data.success && prefsRes.data.data.consent) {
          const consent = prefsRes.data.data.consent;
          setPreferences(prev => ({
            ...prev,
            marketingEmails: consent.marketing || false,
            emailNotifications: true
          }));
        }
      } catch (e) {
        // Fall back to localStorage
        const savedPrefs = localStorage.getItem('emailPreferences');
        if (savedPrefs) {
          setPreferences(JSON.parse(savedPrefs));
        }
      }
      
      setStats({
        totalGenerations: statsRes.data.totalElements || 0,
        creditsUsed: 0
      });
    } catch (error) {
      toast.error('Failed to load profile');
      navigate('/app');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await api.put('/api/auth/profile', {
        name: formData.name
      });
      
      setUser(prev => ({ ...prev, name: formData.name }));
      toast.success('Profile updated successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    if (!formData.currentPassword) {
      toast.error('Please enter your current password');
      return;
    }
    
    if (formData.newPassword !== formData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    
    if (formData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setSavingPassword(true);
    try {
      const response = await api.put('/api/auth/password', {
        currentPassword: formData.currentPassword,
        newPassword: formData.newPassword
      });
      
      if (response.data.success) {
        toast.success('Password changed successfully!');
        setFormData(prev => ({
          ...prev,
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        }));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setSavingPassword(false);
    }
  };

  const handleSavePreferences = async () => {
    setSavingPrefs(true);
    try {
      // Save to API
      await api.post('/api/privacy/consent', {
        marketing: preferences.marketingEmails,
        analytics: true,
        thirdParty: false
      });
      
      // Also save locally
      localStorage.setItem('emailPreferences', JSON.stringify(preferences));
      toast.success('Notification preferences saved!');
    } catch (error) {
      // Fall back to local storage only
      localStorage.setItem('emailPreferences', JSON.stringify(preferences));
      toast.success('Preferences saved locally');
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleExportData = async () => {
    try {
      const response = await api.get('/api/privacy/export');
      if (response.data.success) {
        const blob = new Blob([JSON.stringify(response.data.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `creatorstudio-data-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Your data has been exported!');
      }
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return;
    }
    
    const confirmation = window.prompt('Type DELETE to confirm account deletion:');
    if (confirmation !== 'DELETE') {
      toast.error('Account deletion cancelled');
      return;
    }

    try {
      await api.delete('/api/privacy/delete-now');
      localStorage.removeItem('token');
      toast.success('Account deleted successfully');
      navigate('/');
    } catch (error) {
      toast.error('Failed to delete account');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold text-white">Profile Settings</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Profile Overview */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center text-white text-3xl font-bold shadow-lg shadow-indigo-500/20">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white">{user?.name}</h2>
              <p className="text-slate-400">{user?.email}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  user?.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                }`}>
                  {user?.role || 'USER'}
                </span>
                <span className="text-sm text-slate-500">
                  Member since {new Date(user?.createdAt || Date.now()).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-indigo-400">{user?.credits || 0}</div>
              <div className="text-sm text-slate-500">Credits Available</div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-slate-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center">
              <Clock className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{stats.totalGenerations}</div>
              <div className="text-sm text-slate-500">Total Generations</div>
            </div>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-slate-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{user?.credits || 0}</div>
              <div className="text-sm text-slate-500">Credits Balance</div>
            </div>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-slate-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <div className="text-lg font-bold text-green-400">Active</div>
              <div className="text-sm text-slate-500">Account Status</div>
            </div>
          </div>
        </div>

        {/* Update Profile */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-indigo-400" />
            Profile Information
          </h3>
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name" className="text-slate-300 mb-2 block">Full Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Your name"
                  className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500"
                  data-testid="profile-name-input"
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-slate-300 mb-2 block">Email Address</Label>
                <Input
                  id="email"
                  value={formData.email}
                  disabled
                  className="bg-slate-800/30 border-slate-700 text-slate-400"
                />
                <p className="text-xs text-slate-500 mt-1">Email cannot be changed</p>
              </div>
            </div>
            <Button type="submit" disabled={saving} className="bg-indigo-500 hover:bg-indigo-600 text-white" data-testid="save-profile-btn">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </form>
        </div>

        {/* Change Password */}
        {!user?.googleId && user?.authProvider !== 'google' && (
          <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-indigo-400" />
              Change Password
            </h3>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <Label htmlFor="currentPassword" className="text-slate-300 mb-2 block">Current Password</Label>
                <div className="relative">
                  <Input
                    id="currentPassword"
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={formData.currentPassword}
                    onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
                    placeholder="Enter current password"
                    className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="newPassword" className="text-slate-300 mb-2 block">New Password</Label>
                  <div className="relative">
                    <Input
                      id="newPassword"
                      type={showNewPassword ? 'text' : 'password'}
                      value={formData.newPassword}
                      onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
                      placeholder="Enter new password"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
                <div>
                  <Label htmlFor="confirmPassword" className="text-slate-300 mb-2 block">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={formData.confirmPassword}
                      onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                      placeholder="Confirm new password"
                      className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-indigo-500 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
              </div>
              <Button type="submit" disabled={savingPassword} variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
                {savingPassword ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Lock className="w-4 h-4 mr-2" />}
                {savingPassword ? 'Changing...' : 'Change Password'}
              </Button>
            </form>
          </div>
        )}

        {/* Notification Preferences */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Bell className="w-5 h-5 text-indigo-400" />
            Email Notifications
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">All Email Notifications</div>
                <div className="text-sm text-slate-500">Master toggle for all email notifications</div>
              </div>
              <Switch
                checked={preferences.emailNotifications}
                onCheckedChange={(checked) => setPreferences({ ...preferences, emailNotifications: checked })}
              />
            </div>
            <div className="flex items-center justify-between py-3 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">Generation Alerts</div>
                <div className="text-sm text-slate-500">Get notified when your content is ready</div>
              </div>
              <Switch
                checked={preferences.generationAlerts}
                onCheckedChange={(checked) => setPreferences({ ...preferences, generationAlerts: checked })}
                disabled={!preferences.emailNotifications}
              />
            </div>
            <div className="flex items-center justify-between py-3 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">Payment Receipts</div>
                <div className="text-sm text-slate-500">Receive payment confirmations and receipts</div>
              </div>
              <Switch
                checked={preferences.paymentAlerts}
                onCheckedChange={(checked) => setPreferences({ ...preferences, paymentAlerts: checked })}
                disabled={!preferences.emailNotifications}
              />
            </div>
            <div className="flex items-center justify-between py-3 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">Weekly Digest</div>
                <div className="text-sm text-slate-500">Weekly summary of your activity</div>
              </div>
              <Switch
                checked={preferences.weeklyDigest}
                onCheckedChange={(checked) => setPreferences({ ...preferences, weeklyDigest: checked })}
                disabled={!preferences.emailNotifications}
              />
            </div>
            <div className="flex items-center justify-between py-3">
              <div>
                <div className="font-medium text-white">Marketing & Updates</div>
                <div className="text-sm text-slate-500">Tips, features, and promotional offers</div>
              </div>
              <Switch
                checked={preferences.marketingEmails}
                onCheckedChange={(checked) => setPreferences({ ...preferences, marketingEmails: checked })}
                disabled={!preferences.emailNotifications}
              />
            </div>
            <Button onClick={handleSavePreferences} disabled={savingPrefs} variant="outline" size="sm" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
              {savingPrefs ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Save Preferences
            </Button>
          </div>
        </div>

        {/* Data & Privacy */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-400" />
            Data & Privacy
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
              <div>
                <div className="font-medium text-white">Export Your Data</div>
                <div className="text-sm text-slate-500">Download all your data in JSON format</div>
              </div>
              <Button variant="outline" size="sm" onClick={handleExportData} className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white" data-testid="export-data-btn">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
            <Link to="/app/privacy" className="block">
              <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl hover:bg-slate-800/50 transition-colors">
                <div>
                  <div className="font-medium text-white">Privacy Settings</div>
                  <div className="text-sm text-slate-500">Manage your privacy preferences</div>
                </div>
                <ArrowLeft className="w-4 h-4 rotate-180 text-slate-400" />
              </div>
            </Link>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-red-900/50 p-6">
          <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Danger Zone
          </h3>
          <div className="p-4 bg-red-950/30 rounded-xl border border-red-900/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-red-300">Delete Account</div>
                <div className="text-sm text-red-400/70">Permanently delete your account and all data</div>
              </div>
              <Button 
                variant="destructive" 
                size="sm" 
                onClick={handleDeleteAccount}
                className="bg-red-600 hover:bg-red-700"
                data-testid="delete-account-btn"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Account
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
