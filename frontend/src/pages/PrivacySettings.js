import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import api from '../utils/api';
import { toast } from 'sonner';
import { ArrowLeft, Shield, Download, Trash2, Eye, Settings, Lock, FileText, AlertTriangle, Loader2 } from 'lucide-react';

export default function PrivacySettings() {
  const [loading, setLoading] = useState(false);
  const [userData, setUserData] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
  const [consent, setConsent] = useState({
    marketing: true,
    analytics: true,
    thirdParty: false
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await api.get('/api/privacy/my-data');
      if (response.data.success) {
        setUserData(response.data.data);
      }
    } catch (error) {
      console.log('Could not fetch user data');
    }
  };

  const handleExportData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/privacy/export');
      if (response.data.success) {
        const dataStr = JSON.stringify(response.data.data, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `my-data-export-${Date.now()}.json`;
        a.click();
        toast.success('Your data has been exported successfully!');
        setShowExportModal(false);
      }
    } catch (error) {
      toast.error('Failed to export data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deleteReason.trim()) {
      toast.error('Please provide a reason for account deletion');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/privacy/delete-request', { reason: deleteReason });
      toast.success('Account deletion request submitted. You will receive a confirmation email.');
      setShowDeleteModal(false);
      // Log out user
      localStorage.removeItem('token');
      navigate('/');
    } catch (error) {
      toast.error('Failed to submit deletion request. Please contact support.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateConsent = async () => {
    setLoading(true);
    try {
      await api.post('/api/privacy/consent', consent);
      toast.success('Privacy preferences updated successfully!');
    } catch (error) {
      toast.error('Failed to update preferences');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/app">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Dashboard
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            <span className="text-xl font-bold">Privacy & Data Settings</span>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Data Overview */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Eye className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Your Data Overview</h2>
              <p className="text-sm text-slate-500">Summary of data we store about you</p>
            </div>
          </div>

          {userData ? (
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="text-sm text-slate-500">Account Created</p>
                <p className="font-medium">{userData.profile?.createdAt ? new Date(userData.profile.createdAt).toLocaleDateString() : 'N/A'}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="text-sm text-slate-500">Email</p>
                <p className="font-medium">{userData.profile?.email || 'N/A'}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="text-sm text-slate-500">Total Generations</p>
                <p className="font-medium">{userData.generationsCount || 0}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="text-sm text-slate-500">Total Payments</p>
                <p className="font-medium">{userData.paymentsCount || 0}</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
              <p>Loading your data...</p>
            </div>
          )}
        </div>

        {/* Privacy Preferences */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Settings className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Privacy Preferences</h2>
              <p className="text-sm text-slate-500">Control how we use your data</p>
            </div>
          </div>

          <div className="space-y-4 mt-4">
            <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
              <div>
                <p className="font-medium">Marketing Communications</p>
                <p className="text-sm text-slate-500">Receive updates about new features and offers</p>
              </div>
              <input
                type="checkbox"
                checked={consent.marketing}
                onChange={(e) => setConsent({...consent, marketing: e.target.checked})}
                className="w-5 h-5 accent-indigo-500"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
              <div>
                <p className="font-medium">Usage Analytics</p>
                <p className="text-sm text-slate-500">Help us improve by sharing usage data</p>
              </div>
              <input
                type="checkbox"
                checked={consent.analytics}
                onChange={(e) => setConsent({...consent, analytics: e.target.checked})}
                className="w-5 h-5 accent-indigo-500"
              />
            </label>

            <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
              <div>
                <p className="font-medium">Third-Party Data Sharing</p>
                <p className="text-sm text-slate-500">Share anonymized data with partners</p>
              </div>
              <input
                type="checkbox"
                checked={consent.thirdParty}
                onChange={(e) => setConsent({...consent, thirdParty: e.target.checked})}
                className="w-5 h-5 accent-indigo-500"
              />
            </label>

            <Button onClick={handleUpdateConsent} disabled={loading} className="w-full mt-4 bg-indigo-500 hover:bg-indigo-600">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Preferences
            </Button>
          </div>
        </div>

        {/* Data Actions */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Your Rights (GDPR/CCPA)</h2>
              <p className="text-sm text-slate-500">Exercise your data protection rights</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <Button
              onClick={() => setShowExportModal(true)}
              variant="outline"
              className="h-auto py-4 flex-col gap-2 border-2 hover:border-green-500 hover:bg-green-50"
              data-testid="export-data-btn"
            >
              <Download className="w-6 h-6 text-green-600" />
              <span className="font-medium">Export My Data</span>
              <span className="text-xs text-slate-500">Download all your personal data</span>
            </Button>

            <Button
              onClick={() => setShowDeleteModal(true)}
              variant="outline"
              className="h-auto py-4 flex-col gap-2 border-2 hover:border-red-500 hover:bg-red-50"
              data-testid="delete-account-btn"
            >
              <Trash2 className="w-6 h-6 text-red-600" />
              <span className="font-medium">Delete My Account</span>
              <span className="text-xs text-slate-500">Permanently remove all your data</span>
            </Button>
          </div>
        </div>

        {/* Privacy Policy Link */}
        <div className="bg-slate-100 rounded-xl p-6 text-center">
          <Lock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-600 mb-2">
            We are committed to protecting your privacy and complying with GDPR and CCPA regulations.
          </p>
          <Link to="/privacy-policy" className="text-indigo-600 hover:underline font-medium">
            Read our full Privacy Policy
          </Link>
        </div>
      </div>

      {/* Export Modal */}
      <Dialog open={showExportModal} onOpenChange={setShowExportModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download className="w-5 h-5 text-green-600" />
              Export Your Data
            </DialogTitle>
            <DialogDescription>
              Download a copy of all personal data we have stored about you. This includes your profile, 
              credit history, generations, and payment records.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
              <p className="font-medium mb-1">What's included:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Profile information (name, email)</li>
                <li>Credit balance and transaction history</li>
                <li>Generation history summary</li>
                <li>Payment records summary</li>
                <li>Feature requests you've submitted</li>
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExportModal(false)}>Cancel</Button>
            <Button onClick={handleExportData} disabled={loading} className="bg-green-600 hover:bg-green-700">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
              Export Data
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Account Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              Delete Your Account
            </DialogTitle>
            <DialogDescription>
              This action cannot be undone. All your data will be permanently deleted after a 30-day grace period.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 mb-4">
              <p className="font-medium mb-1">Warning: This will delete:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Your account and profile</li>
                <li>All credit balance and history</li>
                <li>All generated content</li>
                <li>Payment history</li>
              </ul>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Reason for leaving (required):</label>
              <textarea
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Please tell us why you're leaving..."
                className="w-full p-3 border border-slate-300 rounded-lg resize-none h-24"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>Cancel</Button>
            <Button onClick={handleDeleteAccount} disabled={loading} className="bg-red-600 hover:bg-red-700">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Delete Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
