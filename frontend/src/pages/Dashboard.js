import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { walletAPI, authAPI, generationAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Video, BookOpen, Clock, LogOut, CreditCard, History as HistoryIcon, Coins, Shield, Lightbulb, Lock, User, Copyright, Wand2, Library, Receipt, Palette, Film, Calendar, Type, Crown, BarChart3, HelpCircle } from 'lucide-react';
import HelpGuide from '../components/HelpGuide';

export default function Dashboard() {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    // Fetch user data first (most critical)
    try {
      const userRes = await authAPI.getCurrentUser();
      setUser(userRes.data);
      
      // Get credits from user data if available
      if (userRes.data?.credits !== undefined) {
        setCredits(userRes.data.credits);
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // Don't show error toast for user fetch - will redirect on 401
    }
    
    // Fetch credits from wallet as backup/primary (more reliable endpoint)
    try {
      const walletRes = await walletAPI.getWallet();
      if (walletRes.data?.balanceCredits !== undefined) {
        setCredits(walletRes.data.balanceCredits);
      } else if (walletRes.data?.availableCredits !== undefined) {
        setCredits(walletRes.data.availableCredits);
      }
    } catch (error) {
      // Silently fail - we may already have credits from user data
      console.error('Failed to fetch wallet:', error);
    }
    
    // Fetch recent generations (non-critical)
    try {
      const generationsRes = await generationAPI.getGenerations(null, 0, 5);
      setRecentGenerations(generationsRes.data.generations || []);
    } catch (error) {
      console.error('Failed to fetch generations:', error);
      // Don't show error for non-critical data
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const isAdmin = user?.role === 'ADMIN';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-400" />
            <span className="text-lg sm:text-xl font-bold text-white">CreatorStudio AI</span>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-4">
            {isAdmin && (
              <Link to="/app/admin">
                <Button variant="outline" size="sm" className="border-purple-500/50 text-purple-300 hover:bg-purple-500/20" data-testid="admin-dashboard-btn">
                  <Shield className="w-4 h-4 sm:mr-2" />
                  <span className="hidden sm:inline">Admin Panel</span>
                </Button>
              </Link>
            )}
            
            <Link to="/app/profile">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800" data-testid="profile-btn">
                <User className="w-4 h-4 sm:mr-2" />
                <span className="hidden sm:inline">Profile</span>
              </Button>
            </Link>
            
            <div className="flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-3 sm:px-4 py-2" data-testid="credit-balance" data-tour="credits-display">
              <Coins className="w-4 h-4 text-indigo-400" />
              <span className="font-semibold text-indigo-300 text-sm sm:text-base">{credits}</span>
            </div>
            
            <Button variant="ghost" onClick={handleLogout} className="text-slate-400 hover:text-white hover:bg-slate-800" data-testid="logout-btn">
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline ml-2">Logout</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="mb-8 sm:mb-12">
          <h1 className="text-2xl sm:text-4xl font-bold text-white mb-2" data-testid="dashboard-welcome">Welcome back{user?.name ? `, ${user.name}` : ''}!</h1>
          <p className="text-slate-400 text-base sm:text-lg">What would you like to create today?</p>
        </div>

        <div className="grid md:grid-cols-2 gap-4 sm:gap-6 mb-8 sm:mb-12">
          <Link to="/app/reels">
            <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-2xl p-6 sm:p-8 text-white hover:scale-105 transition-transform cursor-pointer shadow-xl shadow-indigo-500/20" data-testid="quick-action-reel" data-tour="reel-generator-card">
              <Video className="w-10 h-10 sm:w-12 sm:h-12 mb-4" />
              <h2 className="text-xl sm:text-2xl font-bold mb-2">Generate Reel Script</h2>
              <p className="text-indigo-200 mb-4 text-sm sm:text-base">Create viral reel scripts in 5-10 seconds</p>
              <div className="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-2 text-sm">
                <Coins className="w-4 h-4" />
                <span>10 credits per reel</span>
              </div>
            </div>
          </Link>

          <Link to="/app/stories">
            <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-2xl p-6 sm:p-8 text-white hover:scale-105 transition-transform cursor-pointer shadow-xl shadow-purple-500/20" data-testid="quick-action-story" data-tour="story-generator-card">
              <BookOpen className="w-10 h-10 sm:w-12 sm:h-12 mb-4" />
              <h2 className="text-xl sm:text-2xl font-bold mb-2">Create Kids Story Pack</h2>
              <p className="text-purple-200 mb-4 text-sm sm:text-base">Complete video production packages</p>
              <div className="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-2 text-sm">
                <Coins className="w-4 h-4" />
                <span>10 credits per story</span>
              </div>
            </div>
          </Link>
        </div>

        {/* GenStudio AI Highlight */}
        <Link to="/app/gen-studio">
          <div className="bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 rounded-2xl p-5 sm:p-6 mb-4 sm:mb-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-purple-500/20" data-testid="quick-action-gen-studio" data-tour="genstudio-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <Sparkles className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">🎨 GenStudio AI</h2>
                  <p className="text-white/80 text-xs sm:text-base">Text→Image • Text→Video • Image→Video • Brand Style Profiles • Video Remix</p>
                </div>
              </div>
              <div className="hidden md:block text-right">
                <span className="bg-white/20 rounded-full px-4 py-2 text-sm">NEW</span>
              </div>
            </div>
          </div>
        </Link>

        {/* Creator Tools Highlight */}
        <Link to="/app/creator-tools">
          <div className="bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 rounded-2xl p-5 sm:p-6 mb-4 sm:mb-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-pink-500/20" data-testid="quick-action-creator-tools" data-tour="creator-tools-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <Wand2 className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">⭐ Creator Tools</h2>
                  <p className="text-white/80 text-xs sm:text-base">30-Day Calendar • Carousel Generator • Hashtag Bank • Thumbnails • Trending Topics</p>
                </div>
              </div>
              <div className="hidden md:block text-right">
                <span className="bg-white/20 rounded-full px-4 py-2 text-sm">NEW</span>
              </div>
            </div>
          </div>
        </Link>

        {/* Coloring Book Highlight */}
        <Link to="/app/coloring-book">
          <div className="bg-gradient-to-r from-rose-500 via-fuchsia-500 to-violet-500 rounded-2xl p-5 sm:p-6 mb-4 sm:mb-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-fuchsia-500/20" data-testid="quick-action-coloring-book">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <Palette className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">🎨 Kids Coloring Book</h2>
                  <p className="text-white/80 text-xs sm:text-base">Create personalized printable story coloring books • Photo-to-outline conversion</p>
                </div>
              </div>
              <div className="hidden md:block text-right">
                <span className="bg-white/20 rounded-full px-4 py-2 text-sm">NEW</span>
              </div>
            </div>
          </div>
        </Link>

        {/* NEW: Comix AI & GIF Maker */}
        <div className="grid md:grid-cols-2 gap-4 mb-4 sm:mb-6">
          <Link to="/app/comix">
            <div className="bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 rounded-2xl p-5 sm:p-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-purple-500/20" data-testid="quick-action-comix">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <Sparkles className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">🦸 Comix AI</h2>
                  <p className="text-white/80 text-xs sm:text-base">Photo → Comic Characters • Panels • Story Mode • 9 Styles</p>
                </div>
              </div>
              <span className="inline-block mt-3 text-xs bg-white/20 rounded-full px-3 py-1">NEW FEATURE</span>
            </div>
          </Link>

          <Link to="/app/gif-maker">
            <div className="bg-gradient-to-r from-pink-500 via-rose-500 to-red-500 rounded-2xl p-5 sm:p-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-pink-500/20" data-testid="quick-action-gif-maker">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <Film className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">GIF Maker</h2>
                  <p className="text-white/80 text-xs sm:text-base">Photo to Reaction GIFs • 12 Emotions • Kids-Safe</p>
                </div>
              </div>
              <span className="inline-block mt-3 text-xs bg-white/20 rounded-full px-3 py-1">NEW FEATURE</span>
            </div>
          </Link>

          <Link to="/app/comic-storybook">
            <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-yellow-500 rounded-2xl p-5 sm:p-6 text-white hover:scale-[1.02] transition-transform cursor-pointer shadow-xl shadow-amber-500/20" data-testid="quick-action-comic-storybook">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-white/20 rounded-xl p-2 sm:p-3">
                  <BookOpen className="w-6 h-6 sm:w-8 sm:h-8" />
                </div>
                <div>
                  <h2 className="text-lg sm:text-2xl font-bold mb-1">Comic Story Book</h2>
                  <p className="text-white/80 text-xs sm:text-base">Story to 10-50 Page PDF • 14 Styles • Copyright-Free</p>
                </div>
              </div>
              <span className="inline-block mt-3 text-xs bg-white/20 rounded-full px-3 py-1">NEW FEATURE</span>
            </div>
          </Link>
        </div>

        {/* 3 New Standalone Apps */}
        <div className="grid md:grid-cols-3 gap-4 mb-8 sm:mb-12">
          {/* Story Series */}
          <Link to="/app/story-series">
            <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl p-4 sm:p-5 text-white hover:scale-[1.02] transition-transform cursor-pointer h-full" data-testid="quick-action-story-series">
              <div className="flex items-center gap-3 mb-2">
                <Film className="w-6 h-6" />
                <h3 className="font-bold">Story Series</h3>
              </div>
              <p className="text-white/80 text-xs sm:text-sm">Turn stories into 3-7 episode series with scene beats & cliffhangers</p>
              <span className="inline-block mt-2 text-xs bg-white/20 rounded-full px-2 py-1">NEW</span>
            </div>
          </Link>

          {/* Challenge Generator */}
          <Link to="/app/challenge-generator">
            <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-xl p-4 sm:p-5 text-white hover:scale-[1.02] transition-transform cursor-pointer h-full" data-testid="quick-action-challenge">
              <div className="flex items-center gap-3 mb-2">
                <Calendar className="w-6 h-6" />
                <h3 className="font-bold">Challenge Generator</h3>
              </div>
              <p className="text-white/80 text-xs sm:text-sm">7/30-day content challenges with hooks, CTAs & hashtags</p>
              <span className="inline-block mt-2 text-xs bg-white/20 rounded-full px-2 py-1">NEW</span>
            </div>
          </Link>

          {/* Tone Switcher */}
          <Link to="/app/tone-switcher">
            <div className="bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl p-4 sm:p-5 text-white hover:scale-[1.02] transition-transform cursor-pointer h-full" data-testid="quick-action-tone">
              <div className="flex items-center gap-3 mb-2">
                <Type className="w-6 h-6" />
                <h3 className="font-bold">Tone Switcher</h3>
              </div>
              <p className="text-white/80 text-xs sm:text-sm">AI-free text rewriter: Funny, Aggressive, Calm, Luxury, Motivational</p>
              <span className="inline-block mt-2 text-xs bg-white/20 rounded-full px-2 py-1">NEW</span>
            </div>
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-6 mb-8 sm:mb-12">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs sm:text-base">Available Credits</span>
              <Coins className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
            </div>
            <div className="text-xl sm:text-3xl font-bold text-white">{credits}</div>
          </div>

          <Link to="/app/history" className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 sm:p-6 hover:bg-slate-700/50 transition-colors">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs sm:text-base">Total Generations</span>
              <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
            </div>
            <div className="text-xl sm:text-3xl font-bold text-white">{recentGenerations.length}</div>
          </Link>

          <Link to="/app/billing" className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 sm:p-6 hover:bg-slate-700/50 transition-colors">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-xs sm:text-base">Buy Credits</span>
              <CreditCard className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
            </div>
            <div className="text-sm sm:text-lg font-semibold text-indigo-400">View Plans →</div>
          </Link>

          <Link to="/app/feature-requests" className="bg-gradient-to-br from-amber-500/20 to-yellow-500/20 border border-amber-500/30 rounded-xl p-4 sm:p-6 hover:bg-amber-500/30 transition-colors">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300 text-xs sm:text-base">Feature Requests</span>
              <Lightbulb className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
            </div>
            <div className="text-sm sm:text-lg font-semibold text-amber-400">Vote & Request →</div>
          </Link>
        </div>

        {/* Privacy & Settings Quick Link */}
        <div className="mb-8 sm:mb-12 flex gap-4 sm:gap-6 flex-wrap">
          <Link to="/app/subscription" className="inline-flex items-center gap-2 text-yellow-400 hover:text-yellow-300 transition-colors font-medium">
            <Crown className="w-4 h-4" />
            <span className="text-sm">Subscription</span>
          </Link>
          <Link to="/app/analytics" className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors font-medium">
            <BarChart3 className="w-4 h-4" />
            <span className="text-sm">Analytics</span>
          </Link>
          <Link to="/app/content-vault" className="inline-flex items-center gap-2 text-purple-400 hover:text-purple-300 transition-colors font-medium">
            <Library className="w-4 h-4" />
            <span className="text-sm">Content Vault</span>
          </Link>
          <Link to="/app/payment-history" className="inline-flex items-center gap-2 text-emerald-400 hover:text-emerald-300 transition-colors font-medium">
            <Receipt className="w-4 h-4" />
            <span className="text-sm">Payment History</span>
          </Link>
          <Link to="/user-manual" className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors font-medium">
            <HelpCircle className="w-4 h-4" />
            <span className="text-sm">Help & Guides</span>
          </Link>
          <Link to="/app/privacy" className="inline-flex items-center gap-2 text-slate-400 hover:text-indigo-400 transition-colors">
            <Lock className="w-4 h-4" />
            <span className="text-sm">Privacy & Data Settings</span>
          </Link>
          <Link to="/app/copyright" className="inline-flex items-center gap-2 text-slate-400 hover:text-indigo-400 transition-colors">
            <Copyright className="w-4 h-4" />
            <span className="text-sm">Copyright & Legal</span>
          </Link>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-5 sm:p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg sm:text-xl font-bold text-white">Recent Generations</h3>
            <Link to="/app/history">
              <Button variant="outline" size="sm" className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" data-testid="view-all-history-btn">
                <HistoryIcon className="w-4 h-4 mr-2" />
                View All
              </Button>
            </Link>
          </div>

          {recentGenerations.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <p>No generations yet. Start creating!</p>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4" data-testid="recent-generations-list">
              {recentGenerations.map((gen) => (
                <div key={gen.id} className="flex items-center justify-between p-3 sm:p-4 bg-slate-900/50 border border-slate-700/50 rounded-xl">
                  <div className="flex items-center gap-3 sm:gap-4">
                    {gen.type === 'REEL' ? (
                      <div className="w-8 h-8 sm:w-10 sm:h-10 bg-indigo-500/20 border border-indigo-500/30 rounded-lg flex items-center justify-center">
                        <Video className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 sm:w-10 sm:h-10 bg-purple-500/20 border border-purple-500/30 rounded-lg flex items-center justify-center">
                        <BookOpen className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400" />
                      </div>
                    )}
                    <div>
                      <div className="font-medium text-white text-sm sm:text-base">{gen.type} Generation</div>
                      <div className="text-xs sm:text-sm text-slate-400">{new Date(gen.createdAt).toLocaleString()}</div>
                    </div>
                  </div>
                  <div className={`px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium ${
                    gen.status === 'SUCCEEDED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    gen.status === 'FAILED' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                    'bg-slate-700/50 text-slate-400 border border-slate-600'
                  }`}>
                    {gen.status}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="dashboard" />
    </div>
  );
}
