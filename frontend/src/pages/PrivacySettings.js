import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import api from '../utils/api';
import { toast } from 'sonner';
import { 
  Sparkles, ArrowLeft, Shield, Eye, Download, Trash2, 
  FileText, Lock, CheckCircle, Loader2, AlertCircle
} from 'lucide-react';

export default function PrivacySettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [dataOverview, setDataOverview] = useState(null);
  const navigate = useNavigate();

  const [consent, setConsent] = useState({
    marketing: true,
    analytics: true,
    thirdParty: false
  });

  useEffect(() => {
    fetchPrivacyData();
  }, []);

  const fetchPrivacyData = async () => {
    try {
      const response = await api.get('/api/privacy/my-data');
      if (response.data.success) {
        setDataOverview(response.data.data);
        if (response.data.data.consent) {
          setConsent(response.data.data.consent);
        }
      }
    } catch (error) {
      toast.error('Failed to load privacy data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConsent = async () => {
    setSaving(true);
    try {
      await api.post('/api/privacy/consent', consent);
      toast.success('Privacy preferences saved!');
    } catch (error) {
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      const response = await api.get('/api/privacy/export');
      if (response.data.success) {
        const blob = new Blob([JSON.stringify(response.data.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `creatorstudio-my-data-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('Your data has been exported!');
      }
    } catch (error) {
      toast.error('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm('Are you absolutely sure you want to delete your account? This action CANNOT be undone.')) {
      return;
    }
    
    const confirmation = window.prompt('Type "DELETE" to confirm permanent account deletion:');
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
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading privacy settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/app/profile">
            <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Profile
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            <span className="text-xl font-bold text-white">Privacy Settings</span>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Your Data Overview */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Eye className="w-5 h-5 text-indigo-400" />
            Your Data Overview
          </h3>
          
          {dataOverview ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-800/30 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-indigo-400">{dataOverview.generationsCount}</div>
                <div className="text-sm text-slate-500 mt-1">Content Generated</div>
              </div>
              <div className="bg-slate-800/30 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-purple-400">{dataOverview.paymentsCount}</div>
                <div className="text-sm text-slate-500 mt-1">Payments Made</div>
              </div>
              <div className="bg-slate-800/30 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-green-400">{dataOverview.genstudioCount}</div>
                <div className="text-sm text-slate-500 mt-1">Studio Projects</div>
              </div>
              <div className="bg-slate-800/30 rounded-xl p-4 text-center">
                <div className="text-3xl font-bold text-blue-400">{dataOverview.profile?.credits || 0}</div>
                <div className="text-sm text-slate-500 mt-1">Credits Balance</div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Unable to load data overview</p>
            </div>
          )}
          
          <div className="mt-4 p-3 bg-slate-800/20 rounded-lg">
            <p className="text-xs text-slate-500">
              Your data is stored securely and only used to provide our services. 
              Member since: {dataOverview?.profile?.createdAt ? new Date(dataOverview.profile.createdAt).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>

        {/* Privacy Preferences */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5 text-indigo-400" />
            Privacy Preferences
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-4 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">Marketing Communications</div>
                <div className="text-sm text-slate-500">
                  Receive tips, feature updates, and promotional content via email
                </div>
              </div>
              <Switch
                checked={consent.marketing}
                onCheckedChange={(checked) => setConsent({ ...consent, marketing: checked })}
                data-testid="marketing-toggle"
              />
            </div>
            
            <div className="flex items-center justify-between py-4 border-b border-slate-800">
              <div>
                <div className="font-medium text-white">Usage Analytics</div>
                <div className="text-sm text-slate-500">
                  Help us improve by sharing anonymous usage data and error reports
                </div>
              </div>
              <Switch
                checked={consent.analytics}
                onCheckedChange={(checked) => setConsent({ ...consent, analytics: checked })}
                data-testid="analytics-toggle"
              />
            </div>
            
            <div className="flex items-center justify-between py-4">
              <div>
                <div className="font-medium text-white">Third-Party Data Sharing</div>
                <div className="text-sm text-slate-500">
                  Allow sharing data with our partners for personalized content (not recommended)
                </div>
              </div>
              <Switch
                checked={consent.thirdParty}
                onCheckedChange={(checked) => setConsent({ ...consent, thirdParty: checked })}
                data-testid="thirdparty-toggle"
              />
            </div>
          </div>
          
          <Button 
            onClick={handleSaveConsent} 
            disabled={saving}
            className="mt-4 bg-indigo-500 hover:bg-indigo-600"
            data-testid="save-privacy-btn"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Save Preferences
              </>
            )}
          </Button>
        </div>

        {/* Your Rights (GDPR/CCPA) */}
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            Your Rights (GDPR/CCPA)
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl">
              <div>
                <div className="font-medium text-white flex items-center gap-2">
                  <Download className="w-4 h-4 text-green-400" />
                  Export My Data
                </div>
                <div className="text-sm text-slate-500">
                  Download all your data in JSON format (GDPR Article 20)
                </div>
                <div className="text-xs text-slate-600 mt-1">
                  Your export may contain personal information. Internal IDs and payment gateway details are excluded for security.
                </div>
              </div>
              <Button 
                variant="outline" 
                onClick={handleExportData}
                disabled={exporting}
                className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
                data-testid="export-data-btn"
              >
                {exporting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Download className="w-4 h-4 mr-2" />
                )}
                {exporting ? 'Exporting...' : 'Export'}
              </Button>
            </div>
            
            <Link to="/privacy-policy" className="block">
              <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-xl hover:bg-slate-800/50 transition-colors">
                <div>
                  <div className="font-medium text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-400" />
                    Read Our Full Privacy Policy
                  </div>
                  <div className="text-sm text-slate-500">
                    Understand how we collect, use, and protect your data
                  </div>
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
                <div className="font-medium text-red-300 flex items-center gap-2">
                  <Trash2 className="w-4 h-4" />
                  Delete Account
                </div>
                <div className="text-sm text-red-400/70">
                  Permanently delete your account and all associated data. This action cannot be undone.
                </div>
              </div>
              <Button 
                variant="destructive"
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
