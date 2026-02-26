import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  Sparkles, Lock, Unlock, Crown, ArrowLeft, Coins, LogOut,
  Lightbulb, Video, BookOpen, MessageSquare, Copy, Check,
  ChevronRight, Star, RefreshCw
} from 'lucide-react';
import api from '../utils/api';

export default function ContentVault() {
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  const [vaultData, setVaultData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNiche, setSelectedNiche] = useState('all');
  const [copied, setCopied] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
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
      setRefreshing(false);
    }
  };

  const refreshContent = async () => {
    setRefreshing(true);
    toast.info('🔄 Getting fresh content...');
    await fetchVaultData();
    toast.success('✨ Fresh themes & templates loaded!');
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
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50">
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
          <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
            <Video className="w-5 h-5 text-blue-500" />
            Reel Structures
          </h3>
          
          {/* How to Use Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h4 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
              💡 How to Use These Structures
            </h4>
            <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
              <li><strong>Pick a structure</strong> that matches your content type</li>
              <li><strong>Follow the flow</strong> - each step is a section of your reel (3-5 seconds each)</li>
              <li><strong>Add your hook</strong> from the Viral Hooks section above</li>
              <li><strong>Record or script</strong> your content following the structure order</li>
              <li><strong>End with a CTA</strong> - "Follow for more", "Save this", or "Comment below"</li>
            </ol>
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            {vaultData?.reel_structures?.map((structure, idx) => (
              <div key={idx} className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200 hover:shadow-md transition-shadow">
                <h4 className="font-bold text-blue-800 mb-2">{structure.name}</h4>
                <div className="flex flex-wrap gap-2 mb-3">
                  {structure.structure?.map((step, sIdx) => (
                    <span key={sIdx} className="text-xs bg-white border border-blue-200 px-2 py-1 rounded flex items-center gap-1 shadow-sm">
                      <span className="w-4 h-4 bg-blue-500 text-white rounded-full flex items-center justify-center text-[10px] font-bold">{sIdx + 1}</span>
                      {step}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-blue-600 bg-white/50 rounded px-2 py-1">
                  <strong>Best for:</strong> {structure.best_for}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Kids Themes & Morals - with Refresh Button */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-700">📚 Story Creation Resources</h2>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={refreshContent}
            disabled={refreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Loading...' : 'Get Fresh Ideas'}
          </Button>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-green-500" />
              Kids Story Themes
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              💡 <strong>How to use:</strong> Pick a theme below, then go to Story Generator to create a story around it. Each theme includes a suggested moral lesson.
            </p>
            <div className="space-y-3">
              {vaultData?.kids_themes?.map((theme, idx) => (
                <div key={idx} className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-3 border border-green-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-green-800">{theme.theme}</span>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">{theme.age_group}</span>
                  </div>
                  <p className="text-sm text-green-700 italic">"{theme.moral}"</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="text-xl font-bold mb-2 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-purple-500" />
              Moral Templates
            </h3>
            <p className="text-sm text-slate-500 mb-4">
              💡 <strong>How to use:</strong> Copy any moral below and use it as the ending lesson for your story. Great for teaching values to kids!
            </p>
            <div className="space-y-3">
              {vaultData?.moral_templates?.map((moral, idx) => (
                <div key={idx} className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-3 border border-purple-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded font-medium">{moral.theme}</span>
                    <Button variant="ghost" size="sm" onClick={() => copyToClipboard(moral.moral, `moral-${idx}`)} className="h-7">
                      {copied === `moral-${idx}` ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
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
