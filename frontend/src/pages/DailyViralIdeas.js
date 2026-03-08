import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, TrendingUp, Lock, Crown, BookOpen, Flame, Unlock } from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DailyViralIdeas = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [copied, setCopied] = useState(null);
  
  // Data
  const [freeIdea, setFreeIdea] = useState(null);
  const [fullPack, setFullPack] = useState([]);
  const [isPro, setIsPro] = useState(false);
  const [selectedNiche, setSelectedNiche] = useState('');

  useEffect(() => {
    fetchConfig();
    fetchFreeIdea();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/daily-viral-ideas/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchFreeIdea = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/daily-viral-ideas/free`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const data = await res.json();
        setIsPro(data.is_pro);
        if (data.is_pro && data.ideas?.length > 0) {
          setFullPack(data.ideas);
        } else if (data.ideas?.length > 0) {
          setFreeIdea(data.ideas[0]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUnlock = async () => {
    setUnlocking(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/daily-viral-ideas/unlock`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setFullPack(data.ideas);
        toast.success('Unlocked full pack!');
      } else {
        toast.error(data.detail || 'Failed to unlock');
      }
    } catch (e) {
      toast.error('Failed to unlock');
    } finally {
      setUnlocking(false);
    }
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied!');
  };

  const getTypeColor = (type) => {
    const colors = {
      'list': 'bg-blue-500/20 text-blue-400',
      'tutorial': 'bg-green-500/20 text-green-400',
      'review': 'bg-purple-500/20 text-purple-400',
      'story': 'bg-yellow-500/20 text-yellow-400',
      'analysis': 'bg-cyan-500/20 text-cyan-400',
      'educational': 'bg-pink-500/20 text-pink-400'
    };
    return colors[type] || 'bg-slate-500/20 text-slate-400';
  };

  const getNicheColor = (niche) => {
    const colors = {
      'Tech': 'from-blue-600 to-cyan-600',
      'Finance': 'from-green-600 to-emerald-600',
      'Fitness': 'from-red-600 to-orange-600',
      'Food': 'from-yellow-600 to-amber-600',
      'Travel': 'from-purple-600 to-pink-600',
      'Fashion': 'from-pink-600 to-rose-600',
      'Gaming': 'from-indigo-600 to-violet-600',
      'Education': 'from-teal-600 to-cyan-600',
      'Business': 'from-slate-600 to-gray-600',
      'Lifestyle': 'from-amber-600 to-yellow-600',
      'Health': 'from-emerald-600 to-green-600',
      'Entertainment': 'from-fuchsia-600 to-purple-600'
    };
    return colors[niche] || 'from-slate-600 to-gray-600';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const ideasToShow = fullPack.length > 0 ? fullPack : (freeIdea ? [freeIdea] : []);
  const filteredIdeas = selectedNiche 
    ? ideasToShow.filter(i => i.niche === selectedNiche)
    : ideasToShow;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Flame className="w-6 h-6 text-orange-400" />
                Daily Viral Idea Drop
              </h1>
              <p className="text-slate-400 text-sm">Fresh trending content ideas every day</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isPro && (
              <span className="flex items-center gap-1 px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm rounded-full">
                <Crown className="w-4 h-4" /> Pro
              </span>
            )}
            <button
              onClick={() => setShowManual(!showManual)}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg text-slate-300 hover:bg-slate-700 text-sm"
            >
              <BookOpen className="w-4 h-4" /> Guide
            </button>
          </div>
        </div>

        {/* User Manual */}
        {showManual && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
            <h3 className="text-lg font-bold text-white mb-4">How It Works</h3>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-2xl mb-2">Free</div>
                <p className="text-slate-300 text-sm">1 viral idea per day</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-2xl mb-2">5 Credits</div>
                <p className="text-slate-300 text-sm">Unlock full pack (10 ideas)</p>
              </div>
              <div className="bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-lg p-4">
                <div className="text-2xl mb-2 flex items-center gap-2">
                  <Crown className="w-5 h-5 text-amber-400" /> Pro
                </div>
                <p className="text-slate-300 text-sm">Unlimited daily access + early access</p>
              </div>
            </div>
          </div>
        )}

        {/* Pro Banner for non-Pro users */}
        {!isPro && fullPack.length === 0 && (
          <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Crown className="w-5 h-5 text-amber-400" /> Go Pro for Unlimited Access
                </h3>
                <p className="text-slate-400 text-sm mt-1">
                  Get unlimited daily ideas, early access (12 hours before others), and trending prediction badges
                </p>
              </div>
              <Link 
                to="/app/subscription"
                className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-medium rounded-lg"
              >
                Upgrade to Pro
              </Link>
            </div>
          </div>
        )}

        {/* Niche Filter */}
        {ideasToShow.length > 1 && (
          <div className="mb-6">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedNiche('')}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  !selectedNiche ? 'bg-orange-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                All Niches
              </button>
              {config?.niches?.map(niche => (
                <button
                  key={niche}
                  onClick={() => setSelectedNiche(niche)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    selectedNiche === niche ? 'bg-orange-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {niche}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Ideas Display */}
        <div className="space-y-4 mb-6">
          {filteredIdeas.length === 0 ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 text-center">
              <Sparkles className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">Your Daily Idea</h3>
              <p className="text-slate-400">Check back tomorrow for your free viral idea!</p>
            </div>
          ) : (
            filteredIdeas.map((idea, index) => (
              <div 
                key={index} 
                className={`bg-gradient-to-r ${getNicheColor(idea.niche)} p-[1px] rounded-2xl`}
              >
                <div className="bg-slate-900 rounded-2xl p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs font-medium px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                          {idea.niche}
                        </span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${getTypeColor(idea.type)}`}>
                          {idea.type}
                        </span>
                        {idea.trending_score >= 90 && (
                          <span className="text-xs font-medium px-2 py-0.5 bg-red-500/20 text-red-400 rounded flex items-center gap-1">
                            <TrendingUp className="w-3 h-3" /> Hot
                          </span>
                        )}
                      </div>
                      <p className="text-white text-lg font-medium">{idea.idea}</p>
                    </div>
                    <button
                      onClick={() => copyText(idea.idea, `idea-${index}`)}
                      className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
                    >
                      {copied === `idea-${index}` ? (
                        <Check className="w-5 h-5 text-green-400" />
                      ) : (
                        <Copy className="w-5 h-5 text-slate-400" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Unlock Button - Show only if free user with only 1 idea */}
        {!isPro && fullPack.length === 0 && freeIdea && (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-500/20 rounded-xl">
                  <Lock className="w-8 h-8 text-orange-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">9 More Ideas Locked</h3>
                  <p className="text-slate-400 text-sm">Unlock the full pack to see all trending ideas</p>
                </div>
              </div>
              <button
                onClick={handleUnlock}
                disabled={unlocking}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white font-medium rounded-xl disabled:opacity-50"
                data-testid="unlock-btn"
              >
                {unlocking ? (
                  <>
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                    Unlocking...
                  </>
                ) : (
                  <>
                    <Unlock className="w-5 h-5" />
                    Unlock Full Pack (5 Credits)
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Copyright 2026 Visionary Suite. All rights reserved.
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="daily-viral-ideas" />
    </div>
  );
};

export default DailyViralIdeas;
