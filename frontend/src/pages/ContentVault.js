import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Sparkles, Lock, Unlock, Crown, ArrowLeft, Coins, LogOut,
  Lightbulb, Video, BookOpen, MessageSquare, Copy, Check,
  ChevronRight, Star
} from 'lucide-react';
import api from '../utils/api';

export default function ContentVault() {
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  const [vaultData, setVaultData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNiche, setSelectedNiche] = useState('all');
  const [copied, setCopied] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchVaultData();
  }, [selectedNiche]);

  const fetchVaultData = async () => {
    try {
      const [creditsRes, vaultRes] = await Promise.all([
        api.get('/api/credits/balance'),
        api.get(`/api/content/vault${selectedNiche !== 'all' ? `?niche=${selectedNiche}` : ''}`)
      ]);
      setCredits(creditsRes.data.balance);
      setUserPlan(vaultRes.data.plan || 'free');
      setVaultData(vaultRes.data);
    } catch (error) {
      toast.error('Failed to load content vault');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied to clipboard!');
    setTimeout(() => setCopied(null), 2000);
  };

  const niches = ['all', 'luxury', 'relationship', 'health', 'motivation', 'business', 'parenting'];

  const planColors = {
    free: 'bg-slate-100 text-slate-700',
    starter: 'bg-blue-100 text-blue-700',
    pro: 'bg-purple-100 text-purple-700',
    lifetime: 'bg-amber-100 text-amber-700'
  };

  const planIcons = {
    free: Lock,
    starter: Unlock,
    pro: Crown,
    lifetime: Star
  };

  const PlanIcon = planIcons[userPlan] || Lock;

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-500" />
              <span className="text-xl font-bold">Content Vault</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 rounded-full px-4 py-2 ${planColors[userPlan]}`}>
              <PlanIcon className="w-4 h-4" />
              <span className="font-semibold capitalize">{userPlan} Plan</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2">
              <Coins className="w-4 h-4 text-purple-500" />
              <span className="font-semibold">{credits} Credits</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Upgrade Banner for Free Users */}
        {userPlan === 'free' && (
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 mb-8 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-2">🔓 Unlock 500+ Premium Ideas</h2>
                <p className="text-purple-100">
                  You're viewing {vaultData?.access_level?.hooks || 20} of {vaultData?.total_hooks || 500}+ viral hooks. 
                  Upgrade to Pro for full access + weekly updates!
                </p>
              </div>
              <Link to="/app/billing">
                <Button className="bg-white text-purple-600 hover:bg-purple-50">
                  <Crown className="w-4 h-4 mr-2" />
                  Upgrade Now
                </Button>
              </Link>
            </div>
          </div>
        )}

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-600 mb-1">
              <Lightbulb className="w-4 h-4 text-yellow-500" />
              <span className="text-sm">Viral Hooks</span>
            </div>
            <div className="text-2xl font-bold">
              {vaultData?.viral_hooks?.length || 0}
              <span className="text-sm text-slate-400 ml-1">/ {vaultData?.total_hooks || 500}</span>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-600 mb-1">
              <Video className="w-4 h-4 text-blue-500" />
              <span className="text-sm">Reel Structures</span>
            </div>
            <div className="text-2xl font-bold">
              {vaultData?.reel_structures?.length || 0}
              <span className="text-sm text-slate-400 ml-1">/ {vaultData?.total_structures || 200}</span>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-600 mb-1">
              <BookOpen className="w-4 h-4 text-green-500" />
              <span className="text-sm">Kids Themes</span>
            </div>
            <div className="text-2xl font-bold">
              {vaultData?.kids_themes?.length || 0}
              <span className="text-sm text-slate-400 ml-1">/ {vaultData?.total_themes || 100}</span>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-slate-600 mb-1">
              <MessageSquare className="w-4 h-4 text-purple-500" />
              <span className="text-sm">Moral Templates</span>
            </div>
            <div className="text-2xl font-bold">
              {vaultData?.moral_templates?.length || 0}
              <span className="text-sm text-slate-400 ml-1">/ {vaultData?.total_morals || 50}</span>
            </div>
          </div>
        </div>

        {/* Niche Filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {niches.map(niche => (
            <Button
              key={niche}
              variant={selectedNiche === niche ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedNiche(niche)}
              className={selectedNiche === niche ? 'bg-purple-500 hover:bg-purple-600' : ''}
            >
              {niche.charAt(0).toUpperCase() + niche.slice(1)}
            </Button>
          ))}
        </div>

        {/* Viral Hooks Section */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-500" />
            Viral Hooks
            {userPlan === 'free' && <Lock className="w-4 h-4 text-slate-400 ml-2" />}
          </h3>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {vaultData?.viral_hooks?.map((hook, idx) => (
              <div 
                key={idx} 
                className={`rounded-lg p-4 border ${
                  idx >= (vaultData?.access_level?.hooks || 20) ? 'bg-slate-100 border-slate-200 opacity-50' : 'bg-yellow-50 border-yellow-200'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded capitalize">{hook.niche}</span>
                  {idx < (vaultData?.access_level?.hooks || 20) ? (
                    <Button variant="ghost" size="sm" onClick={() => copyToClipboard(hook.hook, `hook-${idx}`)}>
                      {copied === `hook-${idx}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </Button>
                  ) : (
                    <Lock className="w-4 h-4 text-slate-400" />
                  )}
                </div>
                <p className="font-medium text-slate-800">{hook.hook}</p>
              </div>
            ))}
          </div>
          
          {userPlan === 'free' && (
            <div className="mt-6 text-center">
              <p className="text-slate-500 mb-3">Upgrade to unlock {(vaultData?.total_hooks || 500) - (vaultData?.access_level?.hooks || 20)}+ more viral hooks</p>
              <Link to="/app/billing">
                <Button className="bg-purple-500 hover:bg-purple-600">
                  <Crown className="w-4 h-4 mr-2" />
                  Unlock Full Vault
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Reel Structures Section */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Video className="w-5 h-5 text-blue-500" />
            Reel Structures
          </h3>
          
          <div className="grid md:grid-cols-2 gap-4">
            {vaultData?.reel_structures?.map((structure, idx) => (
              <div key={idx} className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h4 className="font-bold text-blue-800 mb-2">{structure.name}</h4>
                <div className="flex flex-wrap gap-2 mb-2">
                  {structure.structure?.map((step, sIdx) => (
                    <span key={sIdx} className="text-xs bg-white border border-blue-200 px-2 py-1 rounded flex items-center gap-1">
                      <ChevronRight className="w-3 h-3 text-blue-400" />
                      {step}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-blue-600">Best for: {structure.best_for}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Kids Themes & Morals */}
        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-green-500" />
              Kids Story Themes
            </h3>
            <div className="space-y-3">
              {vaultData?.kids_themes?.map((theme, idx) => (
                <div key={idx} className="bg-green-50 rounded-lg p-3 border border-green-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-green-800">{theme.theme}</span>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">{theme.age_group}</span>
                  </div>
                  <p className="text-sm text-green-700">{theme.moral}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-purple-500" />
              Moral Templates
            </h3>
            <div className="space-y-3">
              {vaultData?.moral_templates?.map((moral, idx) => (
                <div key={idx} className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">{moral.theme}</span>
                    <Button variant="ghost" size="sm" onClick={() => copyToClipboard(moral.moral, `moral-${idx}`)}>
                      {copied === `moral-${idx}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    </Button>
                  </div>
                  <p className="text-sm text-purple-800 font-medium">"{moral.moral}"</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Lifetime Access Upsell */}
        <div className="mt-8 bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold mb-2">💎 Lifetime Vault Access</h3>
              <p className="text-amber-100">
                One-time payment of ₹999 for permanent access to current content.
                <br />
                <span className="text-sm opacity-80">(Future updates require Pro subscription)</span>
              </p>
            </div>
            <Link to="/app/billing">
              <Button className="bg-white text-amber-600 hover:bg-amber-50">
                Get Lifetime Access
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
