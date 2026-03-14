import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { walletAPI, authAPI, generationAPI } from '../utils/api';
import { toast } from 'sonner';
import {
  Sparkles, Video, BookOpen, Clock, LogOut, CreditCard, Coins, Shield,
  Lock, User, Copyright, Wand2, Library, Receipt, Palette, Film, Calendar,
  Type, Crown, BarChart3, HelpCircle, TrendingUp, Gift, ChevronRight,
  Image as ImageIcon, Users, MessageSquare, Moon, Search, ArrowRight,
  Download, RefreshCw, Zap, Send, Eye, Flame, Bell
} from 'lucide-react';
import HelpGuide from '../components/HelpGuide';
import CreditStatusBadge from '../components/CreditStatusBadge';
import NotificationBell from '../components/NotificationBell';
import DailyRewardsModal from '../components/DailyRewardsModal';
import DelayedCreditsBanner from '../components/DelayedCreditsBanner';

/* ─── Intent keywords for universal prompt routing ─── */
const INTENT_MAP = [
  { keywords: ['video', 'story video', 'cinematic', 'animate', 'movie'], route: '/app/story-video-studio', label: 'Story Video Studio' },
  { keywords: ['reel', 'hook', 'script', 'viral', 'short'], route: '/app/reels', label: 'Reel Script Generator' },
  { keywords: ['comic', 'photo to comic', 'cartoon', 'transform photo'], route: '/app/photo-to-comic', label: 'Photo to Comic' },
  { keywords: ['coloring', 'colour', 'color book'], route: '/app/coloring-book', label: 'Coloring Book' },
  { keywords: ['gif', 'reaction', 'meme'], route: '/app/gif-maker', label: 'Reaction GIF' },
  { keywords: ['storybook', 'comic book', 'printable'], route: '/app/comic-storybook', label: 'Comic Story Builder' },
  { keywords: ['bio', 'instagram bio', 'profile'], route: '/app/instagram-bio-generator', label: 'Instagram Bio Generator' },
  { keywords: ['caption', 'rewrite', 'tone'], route: '/app/caption-rewriter', label: 'Caption Rewriter Pro' },
  { keywords: ['bedtime', 'sleep', 'kids story', 'children'], route: '/app/bedtime-story-builder', label: 'Bedtime Story Builder' },
  { keywords: ['thumbnail', 'youtube'], route: '/app/thumbnail-generator', label: 'Thumbnail Text Gen' },
  { keywords: ['brand', 'narrative', 'elevator'], route: '/app/brand-story-builder', label: 'Brand Story Builder' },
  { keywords: ['offer', 'discount', 'deal'], route: '/app/offer-generator', label: 'Offer Generator' },
  { keywords: ['challenge', 'content plan', 'planner'], route: '/app/content-challenge-planner', label: 'Content Challenge Planner' },
  { keywords: ['reply', 'comment'], route: '/app/comment-reply-bank', label: 'Comment Reply Bank' },
  { keywords: ['episode', 'series', 'sequel'], route: '/app/story-episode-creator', label: 'Story Episode Creator' },
  { keywords: ['story', 'tale', 'fiction', 'adventure'], route: '/app/stories', label: 'Story Generator' },
  { keywords: ['idea', 'trending', 'daily'], route: '/app/daily-viral-ideas', label: 'Daily Viral Ideas' },
];

/* ─── Templates ─── */
const TEMPLATES = [
  { title: 'Superhero Rescue Video', desc: 'A brave hero saves the city from a villain', route: '/app/story-video-studio', prompt: 'A brave superhero saves the city from a giant robot attack. The hero flies through skyscrapers and saves citizens.', icon: Film, color: 'indigo' },
  { title: 'Kids Bedtime Story', desc: 'Magical tale for children at bedtime', route: '/app/bedtime-story-builder', prompt: 'A tiny mouse discovers a magical garden behind the old oak tree where flowers sing and fireflies dance.', icon: Moon, color: 'purple' },
  { title: 'Viral Reel Script', desc: 'Hook + script + hashtags for Instagram', route: '/app/reels', prompt: '5 morning habits that changed my life — motivational fitness reel with strong hook', icon: Video, color: 'pink' },
  { title: 'Comic Adventure', desc: 'Turn an idea into a comic storybook', route: '/app/comic-storybook', prompt: 'A space explorer cat discovers an alien planet made entirely of yarn and must save it from unraveling.', icon: Library, color: 'emerald' },
  { title: 'Instagram Bio Pack', desc: '5 optimized bios with CTAs', route: '/app/instagram-bio-generator', prompt: 'Fitness coach helping busy moms get strong in 20 min/day', icon: Users, color: 'pink' },
  { title: 'Brand Story', desc: 'Complete brand narrative + pitch', route: '/app/brand-story-builder', prompt: 'Eco-friendly water bottle startup that plants a tree for every purchase', icon: Sparkles, color: 'cyan' },
];

/* ─── Tool categories ─── */
const TOOL_CATEGORIES = {
  'Video Tools': [
    { name: 'Story Video Studio', route: '/app/story-video-studio', icon: Film, cost: '50 credits', testId: 'tool-story-video' },
    { name: 'Reel Script Generator', route: '/app/reels', icon: Video, cost: '10 credits', testId: 'tool-reel' },
    { name: 'Story Episode Creator', route: '/app/story-episode-creator', icon: Film, cost: '15 credits', testId: 'tool-episode' },
    { name: 'Promo Videos', route: '/app/promo-videos', icon: Zap, cost: '30 credits', testId: 'tool-promo' },
  ],
  'Image Tools': [
    { name: 'Photo to Comic', route: '/app/photo-to-comic', icon: ImageIcon, cost: '15-45 credits', testId: 'tool-comic' },
    { name: 'Coloring Book', route: '/app/coloring-book', icon: Palette, cost: '15 credits', testId: 'tool-coloring' },
    { name: 'Reaction GIF', route: '/app/gif-maker', icon: Film, cost: '8 credits', testId: 'tool-gif' },
    { name: 'Thumbnail Text', route: '/app/thumbnail-generator', icon: Type, cost: '5 credits', testId: 'tool-thumbnail' },
  ],
  'Story Tools': [
    { name: 'Comic Story Builder', route: '/app/comic-storybook', icon: Library, cost: '25-60 credits', testId: 'tool-storybook' },
    { name: 'Bedtime Story Builder', route: '/app/bedtime-story-builder', icon: Moon, cost: '10 credits', testId: 'tool-bedtime' },
    { name: 'Story Hook Generator', route: '/app/story-hook-generator', icon: BookOpen, cost: '8 credits', testId: 'tool-hooks' },
    { name: 'Story Generator', route: '/app/stories', icon: BookOpen, cost: '10 credits', testId: 'tool-story' },
  ],
  'Social Tools': [
    { name: 'Caption Rewriter Pro', route: '/app/caption-rewriter', icon: Type, cost: '5 credits', testId: 'tool-caption' },
    { name: 'Instagram Bio Gen', route: '/app/instagram-bio-generator', icon: Users, cost: '5 credits', testId: 'tool-bio' },
    { name: 'Comment Reply Bank', route: '/app/comment-reply-bank', icon: MessageSquare, cost: '5-15 credits', testId: 'tool-reply' },
    { name: 'Brand Story Builder', route: '/app/brand-story-builder', icon: Sparkles, cost: '18 credits', testId: 'tool-brand' },
    { name: 'Offer Generator', route: '/app/offer-generator', icon: Coins, cost: '20 credits', testId: 'tool-offer' },
    { name: 'Daily Viral Ideas', route: '/app/daily-viral-ideas', icon: TrendingUp, cost: 'Free / 5 credits', testId: 'tool-viral' },
    { name: 'Challenge Planner', route: '/app/content-challenge-planner', icon: Calendar, cost: '10 credits', testId: 'tool-challenge' },
    { name: 'Tone Switcher', route: '/app/tone-switcher', icon: Wand2, cost: '5 credits', testId: 'tool-tone' },
  ],
};

const COLOR_MAP = {
  indigo: 'from-indigo-500 to-blue-600',
  purple: 'from-purple-500 to-indigo-600',
  pink: 'from-pink-500 to-rose-600',
  emerald: 'from-emerald-500 to-teal-600',
  cyan: 'from-cyan-500 to-blue-600',
};

export default function Dashboard() {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const [showDailyRewards, setShowDailyRewards] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [activeCategory, setActiveCategory] = useState('Video Tools');
  const navigate = useNavigate();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const cachedUser = localStorage.getItem('user');
      if (cachedUser) {
        const ud = JSON.parse(cachedUser);
        setUser(ud);
        if (ud.credits !== undefined) setCredits(ud.credits);
      }
    } catch (e) { /* ignore */ }

    try {
      const userRes = await authAPI.getCurrentUser();
      const userData = userRes.data?.user || userRes.data;
      if (userData) {
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
        if (userData.credits !== undefined) setCredits(userData.credits);
      }
    } catch (error) { console.error('Failed to fetch user:', error); }

    try {
      const walletRes = await walletAPI.getWallet();
      if (walletRes.data?.balanceCredits !== undefined) setCredits(walletRes.data.balanceCredits);
      else if (walletRes.data?.availableCredits !== undefined) setCredits(walletRes.data.availableCredits);
    } catch (error) { console.error('Failed to fetch wallet:', error); }

    try {
      const generationsRes = await generationAPI.getGenerations(null, 0, 5);
      setRecentGenerations(generationsRes.data.generations || []);
    } catch (error) { console.error('Failed to fetch generations:', error); }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  /* ─── Universal prompt intent detection ─── */
  const handlePromptChange = (text) => {
    setPromptText(text);
    if (text.length < 3) { setSuggestions([]); return; }
    const lower = text.toLowerCase();
    const matched = INTENT_MAP.filter(i => i.keywords.some(k => lower.includes(k)));
    setSuggestions(matched.length > 0 ? matched.slice(0, 3) : []);
  };

  const handlePromptSubmit = () => {
    if (!promptText.trim()) return;
    const lower = promptText.toLowerCase();
    // Find best match
    for (const intent of INTENT_MAP) {
      if (intent.keywords.some(k => lower.includes(k))) {
        navigate(intent.route, { state: { prompt: promptText } });
        return;
      }
    }
    // Default to story video studio for ambiguous prompts
    navigate('/app/story-video-studio', { state: { prompt: promptText } });
  };

  const isAdmin = user?.role === 'ADMIN' || user?.role === 'admin';

  const creditPercent = useMemo(() => {
    if (credits >= 999999) return 100;
    const max = 500;
    return Math.min(100, Math.round((credits / max) * 100));
  }, [credits]);

  return (
    <div className="min-h-screen bg-[#060B1A]">
      {/* ─── HEADER ─── */}
      <header className="bg-[#0A1128]/90 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link to="/app" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">Visionary Suite</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <Link to="/app" className="px-3 py-1.5 text-sm text-white/70 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors">Create</Link>
            <Link to="/gallery" className="px-3 py-1.5 text-sm text-white/70 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors">Gallery</Link>
            <Link to="/app/creator-tools" className="px-3 py-1.5 text-sm text-white/70 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors">Tools</Link>
            <Link to="/pricing" className="px-3 py-1.5 text-sm text-white/70 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors">Pricing</Link>
          </nav>

          <div className="flex items-center gap-2">
            {isAdmin && (
              <Link to="/app/admin">
                <Button variant="ghost" size="sm" className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/10" data-testid="admin-dashboard-btn">
                  <Shield className="w-4 h-4 sm:mr-1.5" />
                  <span className="hidden sm:inline text-xs">Admin</span>
                </Button>
              </Link>
            )}
            <Button variant="ghost" size="sm" onClick={() => setShowDailyRewards(true)} className="text-amber-400 hover:text-amber-300 hover:bg-amber-500/10" data-testid="daily-rewards-btn">
              <Gift className="w-4 h-4" />
            </Button>
            <NotificationBell />
            <CreditStatusBadge credits={credits} onCreditsUpdate={(b) => setCredits(b)} />
            <Link to="/app/profile">
              <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/[0.05]" data-testid="profile-btn">
                <User className="w-4 h-4" />
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-white/40 hover:text-white hover:bg-white/[0.05]" data-testid="logout-btn">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <DelayedCreditsBanner onCreditsAdded={(b) => setCredits(b)} />

        {/* ─── WELCOME ─── */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight" data-testid="dashboard-welcome">
            {user?.name ? `Welcome back, ${user.name}` : 'Welcome back'}
          </h1>
          <p className="text-white/40 mt-1">What would you like to create today?</p>
        </div>

        {/* ─── 1. HERO CREATION CARDS ─── */}
        <div className="grid md:grid-cols-3 gap-4 mb-8" data-testid="hero-creation-section">
          <Link to="/app/story-video-studio" className="group">
            <div className="relative h-full rounded-2xl bg-gradient-to-br from-indigo-600 to-blue-700 p-6 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/20" data-testid="hero-story-video-card">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.08),transparent)] pointer-events-none" />
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center mb-4">
                  <Film className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-1.5">Story Video</h3>
                <p className="text-white/60 text-sm leading-relaxed mb-3">Turn any story into a cinematic AI video with scenes, voiceover & music.</p>
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">6 Styles</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">AI Voice</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">50 credits</span>
                </div>
              </div>
              <ArrowRight className="absolute bottom-6 right-6 w-5 h-5 text-white/30 group-hover:text-white/60 transition-colors" />
            </div>
          </Link>

          <Link to="/app/photo-to-comic" className="group">
            <div className="relative h-full rounded-2xl bg-gradient-to-br from-pink-600 to-rose-700 p-6 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-pink-500/20" data-testid="hero-photo-comic-card">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.08),transparent)] pointer-events-none" />
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center mb-4">
                  <ImageIcon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-1.5">Photo to Comic</h3>
                <p className="text-white/60 text-sm leading-relaxed mb-3">Transform your photos into comic-style characters and panels.</p>
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">AI Art</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">Multiple Styles</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">15 credits</span>
                </div>
              </div>
              <ArrowRight className="absolute bottom-6 right-6 w-5 h-5 text-white/30 group-hover:text-white/60 transition-colors" />
            </div>
          </Link>

          <Link to="/app/reels" className="group">
            <div className="relative h-full rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 p-6 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-500/20" data-testid="hero-reel-card">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.08),transparent)] pointer-events-none" />
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center mb-4">
                  <Video className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-1.5">Reel Generator</h3>
                <p className="text-white/60 text-sm leading-relaxed mb-3">Viral hooks, scripts & hashtags for Instagram and TikTok reels.</p>
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">Viral Hooks</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">Hashtags</span>
                  <span className="bg-white/10 rounded-full px-2.5 py-0.5">10 credits</span>
                </div>
              </div>
              <ArrowRight className="absolute bottom-6 right-6 w-5 h-5 text-white/30 group-hover:text-white/60 transition-colors" />
            </div>
          </Link>
        </div>

        {/* ─── 2. UNIVERSAL AI PROMPT ─── */}
        <div className="relative mb-8 rounded-2xl border border-white/[0.06] bg-[#0F172A] p-6" data-testid="universal-prompt-section">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-white">Create Anything with AI</h2>
          </div>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                type="text"
                value={promptText}
                onChange={(e) => handlePromptChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
                placeholder="Describe what you want to create..."
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-11 pr-4 py-3.5 text-white placeholder-white/30 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                data-testid="universal-prompt-input"
              />
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-[#111827] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-10" data-testid="prompt-suggestions">
                  {suggestions.map((s, i) => (
                    <button key={i} onClick={() => { navigate(s.route, { state: { prompt: promptText } }); }} className="w-full text-left px-4 py-3 hover:bg-white/[0.04] transition-colors flex items-center gap-3 border-b border-white/[0.04] last:border-0">
                      <ArrowRight className="w-4 h-4 text-indigo-400" />
                      <div>
                        <span className="text-sm text-white font-medium">{s.label}</span>
                        <span className="text-xs text-white/40 ml-2">Best match for your prompt</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button onClick={handlePromptSubmit} className="bg-gradient-to-r from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 text-white px-6 rounded-xl shadow-lg shadow-indigo-500/20 transition-all" data-testid="universal-prompt-submit">
              <Send className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Generate</span>
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {['Superhero saves city', 'Kids bedtime story', 'Instagram reel about fitness', 'Comic adventure'].map((ex, i) => (
              <button key={i} onClick={() => { setPromptText(ex); handlePromptChange(ex); }} className="text-xs text-white/30 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-1.5 hover:bg-white/[0.06] hover:text-white/50 transition-colors">
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* ─── 3. TEMPLATES ─── */}
        <div className="mb-8" data-testid="templates-section">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white/80">Inspiration</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {TEMPLATES.map((t, i) => (
              <Link key={i} to={t.route} state={{ prompt: t.prompt }}>
                <div className="group rounded-xl border border-white/[0.06] bg-[#0F172A] p-4 hover:border-white/[0.12] hover:bg-[#111827] transition-all duration-200 h-full" data-testid={`template-${i}`}>
                  <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${COLOR_MAP[t.color]} flex items-center justify-center mb-3`}>
                    <t.icon className="w-4 h-4 text-white" />
                  </div>
                  <h3 className="text-sm font-medium text-white mb-1 leading-tight">{t.title}</h3>
                  <p className="text-xs text-white/30 leading-snug">{t.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* ─── 4. RECENT CREATIONS ─── */}
        <div className="mb-8 rounded-2xl border border-white/[0.06] bg-[#0F172A] p-6" data-testid="recent-creations-section">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-white/80">Recent Creations</h2>
            <Link to="/app/history">
              <Button variant="ghost" size="sm" className="text-white/40 hover:text-white text-xs" data-testid="view-all-history-btn">
                View All <ChevronRight className="w-3 h-3 ml-1" />
              </Button>
            </Link>
          </div>
          {recentGenerations.length === 0 ? (
            <div className="text-center py-12" data-testid="empty-creations">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-4">
                <Sparkles className="w-7 h-7 text-white/20" />
              </div>
              <p className="text-white/30 text-sm mb-4">No creations yet. Start your first project above!</p>
              <Link to="/app/story-video-studio">
                <Button size="sm" className="bg-gradient-to-r from-indigo-500 to-blue-600 text-white text-xs rounded-lg">
                  Create Your First Video
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2" data-testid="recent-generations-list">
              {recentGenerations.map((gen) => (
                <div key={gen.id} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${gen.type === 'REEL' ? 'bg-indigo-500/10' : 'bg-purple-500/10'}`}>
                    {gen.type === 'REEL' ? <Video className="w-5 h-5 text-indigo-400" /> : <BookOpen className="w-5 h-5 text-purple-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-white text-sm truncate">{gen.type} Generation</div>
                    <div className="text-xs text-white/30">{new Date(gen.createdAt).toLocaleString()}</div>
                  </div>
                  <div className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                    gen.status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400' :
                    gen.status === 'FAILED' ? 'bg-red-500/10 text-red-400' :
                    'bg-white/[0.05] text-white/40'
                  }`}>{gen.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ─── 5. TOOL CATEGORIES ─── */}
        <div className="mb-8" data-testid="tool-categories-section">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white/80">Creator Tools</h2>
            <Link to="/app/creator-tools" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1">
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          {/* Category tabs */}
          <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
            {Object.keys(TOOL_CATEGORIES).map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  activeCategory === cat
                    ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
                    : 'text-white/40 hover:text-white/60 hover:bg-white/[0.03] border border-transparent'
                }`}
                data-testid={`category-tab-${cat.replace(/\s/g, '-').toLowerCase()}`}
              >
                {cat}
              </button>
            ))}
          </div>
          {/* Tool grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {TOOL_CATEGORIES[activeCategory]?.map((tool) => (
              <Link key={tool.route} to={tool.route}>
                <div className="rounded-xl border border-white/[0.06] bg-[#0F172A] p-4 hover:border-white/[0.12] hover:bg-[#111827] transition-all duration-200 group" data-testid={tool.testId}>
                  <tool.icon className="w-6 h-6 text-white/40 mb-3 group-hover:text-indigo-400 transition-colors" />
                  <h3 className="text-sm font-medium text-white mb-0.5">{tool.name}</h3>
                  <span className="text-xs text-white/25">{tool.cost}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* ─── 6. CREDITS + ACTIVITY (side by side) ─── */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {/* Credits */}
          <div className="rounded-2xl border border-white/[0.06] bg-[#0F172A] p-6" data-testid="credits-panel">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white/80">Credits</h2>
              <Link to="/app/billing">
                <Button variant="ghost" size="sm" className="text-indigo-400 hover:text-indigo-300 text-xs">
                  Buy More <ArrowRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            </div>
            <div className="text-3xl font-bold text-white mb-1">{credits >= 999999 ? '∞' : credits.toLocaleString()}</div>
            <p className="text-xs text-white/30 mb-4">credits remaining</p>
            {/* Usage bar */}
            <div className="w-full h-2 rounded-full bg-white/[0.06] overflow-hidden mb-4">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-blue-500 transition-all duration-500" style={{ width: `${creditPercent}%` }} />
            </div>
            <div className="flex gap-2">
              <Link to="/app/billing" className="flex-1">
                <Button size="sm" className="w-full bg-gradient-to-r from-indigo-500 to-blue-600 text-white text-xs rounded-lg hover:from-indigo-600 hover:to-blue-700">
                  <CreditCard className="w-3.5 h-3.5 mr-1.5" /> Buy Credits
                </Button>
              </Link>
              <Link to="/app/subscription">
                <Button variant="outline" size="sm" className="border-white/[0.08] text-white/60 hover:text-white text-xs rounded-lg">
                  <Crown className="w-3.5 h-3.5 mr-1.5" /> Plans
                </Button>
              </Link>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="rounded-2xl border border-white/[0.06] bg-[#0F172A] p-6" data-testid="activity-feed">
            <h2 className="text-base font-semibold text-white/80 mb-4">Activity</h2>
            {recentGenerations.length === 0 ? (
              <p className="text-sm text-white/20 py-8 text-center">No activity yet</p>
            ) : (
              <div className="space-y-3">
                {recentGenerations.slice(0, 4).map((gen, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${gen.status === 'SUCCEEDED' ? 'bg-emerald-400' : gen.status === 'FAILED' ? 'bg-red-400' : 'bg-white/20'}`} />
                    <span className="text-sm text-white/60 flex-1 truncate">{gen.type} generated</span>
                    <span className="text-xs text-white/20">{new Date(gen.createdAt).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ─── 7. POPULAR TOOLS ─── */}
        <div className="mb-8" data-testid="popular-tools-section">
          <h2 className="text-base font-semibold text-white/80 mb-4">Popular</h2>
          <div className="flex flex-wrap gap-2">
            {[
              { name: 'Story Video Studio', route: '/app/story-video-studio', icon: Film },
              { name: 'Photo to Comic', route: '/app/photo-to-comic', icon: ImageIcon },
              { name: 'Reel Generator', route: '/app/reels', icon: Video },
              { name: 'Caption Rewriter', route: '/app/caption-rewriter', icon: Type },
              { name: 'Coloring Book', route: '/app/coloring-book', icon: Palette },
              { name: 'Blueprint Library', route: '/app/blueprint-library', icon: Library },
            ].map((t) => (
              <Link key={t.route} to={t.route}>
                <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/[0.06] bg-[#0F172A] hover:border-white/[0.12] hover:bg-[#111827] transition-all text-sm text-white/60 hover:text-white">
                  <t.icon className="w-4 h-4" />
                  <span>{t.name}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* ─── 8. QUICK LINKS ─── */}
        <div className="flex flex-wrap gap-x-6 gap-y-2 mb-8 text-xs">
          {isAdmin && (
            <Link to="/app/admin/security" className="text-white/25 hover:text-red-400 transition-colors flex items-center gap-1.5" data-testid="admin-security-link">
              <Shield className="w-3.5 h-3.5" /> Security Dashboard
            </Link>
          )}
          <Link to="/app/referral" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" /> Referrals
          </Link>
          <Link to="/app/analytics" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <BarChart3 className="w-3.5 h-3.5" /> Analytics
          </Link>
          <Link to="/app/payment-history" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Receipt className="w-3.5 h-3.5" /> Payment History
          </Link>
          <Link to="/app/promo-videos" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Film className="w-3.5 h-3.5" /> Promo Videos
          </Link>
          <Link to="/user-manual" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> Help
          </Link>
          <Link to="/app/privacy" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" /> Privacy
          </Link>
          <Link to="/app/copyright" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Copyright className="w-3.5 h-3.5" /> Copyright
          </Link>
          <Link to="/app/feature-requests" className="text-white/25 hover:text-white/60 transition-colors flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5" /> Feature Requests
          </Link>
        </div>
      </div>

      <HelpGuide pageId="dashboard" />
      <DailyRewardsModal isOpen={showDailyRewards} onClose={() => setShowDailyRewards(false)} />

      <footer className="border-t border-white/[0.04] py-4">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-center">
          <div className="flex items-center gap-2 bg-emerald-500/5 border border-emerald-500/20 rounded-full px-4 py-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-400/60" />
            <span className="text-emerald-400/60 text-xs">Protected by OWASP Standards</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
