import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Progress } from '../components/ui/progress';
import api from '../utils/api';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';
import { 
  Sparkles, ArrowLeft, User, Mail, Shield, Bell, 
  CreditCard, Clock, Save, Trash2, Download, Image, Video, Mic,
  Lock, Eye, EyeOff, CheckCircle, AlertCircle, Loader2, Play,
  FileText, RefreshCw, Folder, HardDrive, AlertTriangle, XCircle
} from 'lucide-react';
import { useAppTour } from '../components/AppTour';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('space'); // Default to Users Space
  const [stats, setStats] = useState({ totalGenerations: 0, creditsUsed: 0 });
  const [userSpace, setUserSpace] = useState({
    generated: [],
    downloads: [],
    pending: [],
    failed: []
  });
  const [loadingSpace, setLoadingSpace] = useState(false);
  const navigate = useNavigate();
  const { restartTour } = useAppTour();

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
    fetchUserSpace();
  }, []);

  const fetchUserData = async () => {
    try {
      const [userRes, statsRes] = await Promise.all([
        api.get('/api/auth/me'),
        api.get('/api/generate?page=0&size=1').catch(() => ({ data: { total: 0 } }))
      ]);
      
      setUser(userRes.data);
      setFormData(prev => ({
        ...prev,
        name: userRes.data.name || '',
        email: userRes.data.email || ''
      }));
      
      setStats({
        totalGenerations: statsRes.data.total || 0,
        creditsUsed: 0
      });
    } catch (error) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const fetchUserSpace = async () => {
    setLoadingSpace(true);
    try {
      // Fetch all user data in parallel
      const [downloadsRes, projectsRes] = await Promise.all([
        api.get('/api/downloads/my-downloads').catch(() => ({ data: { downloads: [] } })),
        api.get('/api/story-video-studio/projects').catch(() => ({ data: { projects: [] } }))
      ]);

      // Process downloads
      const downloads = downloadsRes.data.downloads || [];
      
      // Process projects to extract generated content
      const projects = projectsRes.data.projects || [];
      const generated = [];
      const pending = [];
      const failed = [];

      projects.forEach(project => {
        const item = {
          id: project.project_id,
          title: project.title,
          type: 'story_video',
          status: project.status,
          createdAt: project.created_at,
          thumbnail: project.thumbnail_url
        };

        if (project.status === 'video_rendered') {
          generated.push({ ...item, videoUrl: project.final_video_url });
        } else if (project.status === 'failed' || project.error) {
          failed.push({ ...item, error: project.error || 'Generation failed' });
        } else if (['draft', 'scenes_generated', 'images_generated', 'voices_generated'].includes(project.status)) {
          pending.push(item);
        }
      });

      setUserSpace({
        generated,
        downloads: downloads.map(d => ({
          id: d.id,
          filename: d.filename,
          fileType: d.file_type,
          size: d.file_size,
          createdAt: d.created_at,
          expiresAt: d.expires_at,
          downloadUrl: d.download_url,
          expired: d.expired
        })),
        pending,
        failed
      });
    } catch (error) {
      console.error('Failed to fetch user space:', error);
    } finally {
      setLoadingSpace(false);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await api.put('/api/auth/profile', {
        name: formData.name
      });
      toast.success('Profile updated successfully');
      setUser(prev => ({ ...prev, name: formData.name }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTimeRemaining = (expiresAt) => {
    if (!expiresAt) return null;
    const diff = new Date(expiresAt) - new Date();
    if (diff <= 0) return 'Expired';
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins} min left`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m left`;
  };

  const getFileIcon = (type) => {
    if (type?.includes('image')) return Image;
    if (type?.includes('video')) return Video;
    if (type?.includes('audio')) return Mic;
    return FileText;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950/20 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <User className="w-6 h-6 text-purple-400" />
              My Profile
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1 bg-purple-500/20 rounded-full flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className="text-purple-400 font-medium">{user?.credits || 0} Credits</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Tab Navigation */}
        <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
          {[
            { id: 'space', label: 'My Space', icon: Folder },
            { id: 'profile', label: 'Profile Settings', icon: User },
            { id: 'security', label: 'Security', icon: Shield },
            { id: 'notifications', label: 'Notifications', icon: Bell }
          ].map(tab => (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'default' : 'ghost'}
              onClick={() => setActiveTab(tab.id)}
              className={activeTab === tab.id ? 'bg-purple-600' : 'text-slate-400'}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4 mr-2" />
              {tab.label}
            </Button>
          ))}
        </div>

        {/* Users Space Tab */}
        {activeTab === 'space' && (
          <div className="space-y-8" data-testid="users-space">
            {/* Stats Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{userSpace.generated.length}</p>
                    <p className="text-sm text-slate-400">Generated</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <Download className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{userSpace.downloads.length}</p>
                    <p className="text-sm text-slate-400">Downloads</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{userSpace.pending.length}</p>
                    <p className="text-sm text-slate-400">In Progress</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                    <XCircle className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{userSpace.failed.length}</p>
                    <p className="text-sm text-slate-400">Failed</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Refresh Button */}
            <div className="flex justify-end">
              <Button
                variant="outline"
                onClick={fetchUserSpace}
                disabled={loadingSpace}
                className="border-slate-600 text-slate-300"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loadingSpace ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>

            {/* Ready for Download Section */}
            {userSpace.downloads.filter(d => !d.expired).length > 0 && (
              <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-green-400 flex items-center gap-2 mb-4">
                  <CheckCircle className="w-5 h-5" />
                  Files Ready for Download
                </h3>
                <p className="text-green-200/80 text-sm mb-4">
                  Your files are ready! Download them before they expire.
                </p>
                <div className="space-y-3">
                  {userSpace.downloads.filter(d => !d.expired).map((download) => {
                    const FileIcon = getFileIcon(download.fileType);
                    const timeLeft = getTimeRemaining(download.expiresAt);
                    return (
                      <div 
                        key={download.id}
                        className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <FileIcon className="w-5 h-5 text-green-400" />
                          <div>
                            <p className="text-white font-medium">{download.filename}</p>
                            <p className="text-xs text-slate-400">
                              {formatFileSize(download.size)} • {timeLeft}
                            </p>
                          </div>
                        </div>
                        <a 
                          href={`${process.env.REACT_APP_BACKEND_URL}${download.downloadUrl}`}
                          download
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Download
                        </a>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Generated Content Section */}
            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Video className="w-5 h-5 text-purple-400" />
                Your Generated Content
              </h3>
              {userSpace.generated.length === 0 ? (
                <div className="text-center py-8">
                  <HardDrive className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No generated content yet</p>
                  <Link to="/app/story-video-studio">
                    <Button className="mt-4 bg-purple-600 hover:bg-purple-700">
                      <Sparkles className="w-4 h-4 mr-2" />
                      Create Your First Video
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="grid gap-4">
                  {userSpace.generated.map((item) => (
                    <div 
                      key={item.id}
                      className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700/30"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 bg-purple-500/20 rounded-lg flex items-center justify-center">
                          <Video className="w-8 h-8 text-purple-400" />
                        </div>
                        <div>
                          <p className="text-white font-medium">{item.title}</p>
                          <p className="text-sm text-slate-400">{formatDate(item.createdAt)}</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {item.videoUrl && (
                          <a 
                            href={item.videoUrl?.startsWith('http') ? item.videoUrl : `${process.env.REACT_APP_BACKEND_URL}${item.videoUrl}`}
                            download
                            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* In Progress Section */}
            {userSpace.pending.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-amber-400 flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5" />
                  In Progress
                </h3>
                <div className="space-y-3">
                  {userSpace.pending.map((item) => (
                    <div 
                      key={item.id}
                      className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                        <div>
                          <p className="text-white font-medium">{item.title}</p>
                          <p className="text-xs text-amber-400 capitalize">{item.status.replace('_', ' ')}</p>
                        </div>
                      </div>
                      <Link to="/app/story-video-studio">
                        <Button variant="outline" size="sm" className="border-amber-500/50 text-amber-400">
                          Continue
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Failed Generations Section */}
            {userSpace.failed.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-red-400 flex items-center gap-2 mb-4">
                  <AlertTriangle className="w-5 h-5" />
                  Failed Generations
                </h3>
                <p className="text-red-200/80 text-sm mb-4">
                  These generations failed. Credits have been refunded automatically.
                </p>
                <div className="space-y-3">
                  {userSpace.failed.map((item) => (
                    <div 
                      key={item.id}
                      className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <XCircle className="w-5 h-5 text-red-400" />
                        <div>
                          <p className="text-white font-medium">{item.title}</p>
                          <p className="text-xs text-red-400">{item.error}</p>
                        </div>
                      </div>
                      <Link to="/app/story-video-studio">
                        <Button variant="outline" size="sm" className="border-red-500/50 text-red-400">
                          Try Again
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Info Card */}
            <div className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/30">
              <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-blue-400" />
                Important Information
              </h4>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>• Generated files are available for <strong className="text-amber-400">30 minutes</strong> after creation</li>
                <li>• Download your files before they expire - expired files cannot be recovered</li>
                <li>• Failed generations are automatically refunded to your credit balance</li>
                <li>• Visit the Downloads page for all your files in one place</li>
              </ul>
            </div>
          </div>
        )}

        {/* Profile Settings Tab */}
        {activeTab === 'profile' && (
          <div className="max-w-2xl space-y-6">
            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white mb-4">Personal Information</h3>
              <div className="space-y-4">
                <div>
                  <Label className="text-slate-300">Full Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="mt-1 bg-slate-900/50 border-slate-600 text-white"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Email Address</Label>
                  <Input
                    value={formData.email}
                    disabled
                    className="mt-1 bg-slate-900/50 border-slate-600 text-slate-400"
                  />
                  <p className="text-xs text-slate-500 mt-1">Email cannot be changed</p>
                </div>
                <Button 
                  onClick={handleSaveProfile}
                  disabled={saving}
                  className="bg-purple-600 hover:bg-purple-700"
                  data-testid="save-profile-btn"
                >
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Changes
                </Button>
              </div>
            </div>

            {/* Account Stats */}
            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white mb-4">Account Statistics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <p className="text-slate-400 text-sm">Total Generations</p>
                  <p className="text-2xl font-bold text-white">{stats.totalGenerations}</p>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <p className="text-slate-400 text-sm">Credits Balance</p>
                  <p className="text-2xl font-bold text-purple-400">{user?.credits || 0}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="max-w-2xl">
            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Lock className="w-5 h-5 text-purple-400" />
                Change Password
              </h3>
              <div className="space-y-4">
                <div>
                  <Label className="text-slate-300">Current Password</Label>
                  <div className="relative">
                    <Input
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={formData.currentPassword}
                      onChange={(e) => setFormData(prev => ({ ...prev, currentPassword: e.target.value }))}
                      className="mt-1 bg-slate-900/50 border-slate-600 text-white pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                    >
                      {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <Label className="text-slate-300">New Password</Label>
                  <Input
                    type="password"
                    value={formData.newPassword}
                    onChange={(e) => setFormData(prev => ({ ...prev, newPassword: e.target.value }))}
                    className="mt-1 bg-slate-900/50 border-slate-600 text-white"
                  />
                </div>
                <div>
                  <Label className="text-slate-300">Confirm New Password</Label>
                  <Input
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                    className="mt-1 bg-slate-900/50 border-slate-600 text-white"
                  />
                </div>
                <Button className="bg-purple-600 hover:bg-purple-700">
                  <Lock className="w-4 h-4 mr-2" />
                  Update Password
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="max-w-2xl">
            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Bell className="w-5 h-5 text-purple-400" />
                Notification Preferences
              </h3>
              <div className="space-y-4">
                {[
                  { key: 'emailNotifications', label: 'Email Notifications', desc: 'Receive notifications via email' },
                  { key: 'generationAlerts', label: 'Generation Alerts', desc: 'Get notified when generations complete' },
                  { key: 'paymentAlerts', label: 'Payment Alerts', desc: 'Notifications about credits and payments' },
                  { key: 'marketingEmails', label: 'Marketing Emails', desc: 'Receive tips, updates and offers' },
                  { key: 'weeklyDigest', label: 'Weekly Digest', desc: 'Summary of your weekly activity' }
                ].map(pref => (
                  <div key={pref.key} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">{pref.label}</p>
                      <p className="text-sm text-slate-400">{pref.desc}</p>
                    </div>
                    <Switch
                      checked={preferences[pref.key]}
                      onCheckedChange={(checked) => setPreferences(prev => ({ ...prev, [pref.key]: checked }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      <HelpGuide pageId="profile" />
    </div>
  );
}
