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
  Download, Zap, Send, Flame, Check, Trophy, Lightbulb
} from 'lucide-react';
import HelpGuide from '../components/HelpGuide';
import CreditStatusBadge from '../components/CreditStatusBadge';
import NotificationBell from '../components/NotificationBell';
import DailyRewardsModal from '../components/DailyRewardsModal';
import DelayedCreditsBanner from '../components/DelayedCreditsBanner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

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
  { keywords: ['challenge', 'content plan', 'planner'], route: '/app/content-challenge-planner', label: 'Content Planner' },
  { keywords: ['reply', 'comment'], route: '/app/comment-reply-bank', label: 'Comment Reply Bank' },
  { keywords: ['story', 'tale', 'fiction', 'adventure'], route: '/app/stories', label: 'Story Generator' },
  { keywords: ['idea', 'trending', 'daily'], route: '/app/daily-viral-ideas', label: 'Daily Viral Ideas' },
];

/* ─── Templates ─── */
const TEMPLATES = [
  { title: 'Superhero Rescue', desc: 'Cinematic story video', route: '/app/story-video-studio', prompt: 'A brave superhero saves the city from a giant robot attack.', icon: Film, grad: 'from-indigo-500 to-blue-600' },
  { title: 'Bedtime Story', desc: 'Magical tale for kids', route: '/app/bedtime-story-builder', prompt: 'A tiny mouse discovers a magical garden behind the old oak tree.', icon: Moon, grad: 'from-purple-500 to-indigo-600' },
  { title: 'Viral Reel', desc: 'Hooks + hashtags', route: '/app/reels', prompt: '5 morning habits that changed my life — motivational fitness reel', icon: Video, grad: 'from-pink-500 to-rose-600' },
  { title: 'Comic Adventure', desc: 'Full comic storybook', route: '/app/comic-storybook', prompt: 'A space explorer cat discovers an alien planet made of yarn.', icon: Library, grad: 'from-emerald-500 to-teal-600' },
  { title: 'Instagram Bio', desc: '5 optimized bios', route: '/app/instagram-bio-generator', prompt: 'Fitness coach helping busy moms get strong in 20 min/day', icon: Users, grad: 'from-pink-500 to-rose-600' },
  { title: 'Brand Story', desc: 'Complete narrative', route: '/app/brand-story-builder', prompt: 'Eco-friendly water bottle startup that plants trees', icon: Sparkles, grad: 'from-cyan-500 to-blue-600' },
];

/* ─── Tool categories ─── */
const TOOL_CATEGORIES = {
  'Video Tools': [
    { name: 'Story Video Studio', route: '/app/story-video-studio', icon: Film, cost: '50 cr' },
    { name: 'Reel Generator', route: '/app/reels', icon: Video, cost: '10 cr' },
    { name: 'Episode Creator', route: '/app/story-episode-creator', icon: Film, cost: '15 cr' },
    { name: 'Promo Videos', route: '/app/promo-videos', icon: Zap, cost: '30 cr' },
  ],
  'Image Tools': [
    { name: 'Photo to Comic', route: '/app/photo-to-comic', icon: ImageIcon, cost: '15 cr' },
    { name: 'Coloring Book', route: '/app/coloring-book', icon: Palette, cost: '15 cr' },
    { name: 'Reaction GIF', route: '/app/gif-maker', icon: Film, cost: '8 cr' },
    { name: 'Thumbnail Text', route: '/app/thumbnail-generator', icon: Type, cost: '5 cr' },
  ],
  'Story Tools': [
    { name: 'Comic Storybook', route: '/app/comic-storybook', icon: Library, cost: '25 cr' },
    { name: 'Bedtime Stories', route: '/app/bedtime-story-builder', icon: Moon, cost: '10 cr' },
    { name: 'Story Hooks', route: '/app/story-hook-generator', icon: BookOpen, cost: '8 cr' },
    { name: 'Story Generator', route: '/app/stories', icon: BookOpen, cost: '10 cr' },
  ],
  'Social Tools': [
    { name: 'Caption Rewriter', route: '/app/caption-rewriter', icon: Type, cost: '5 cr' },
    { name: 'Bio Generator', route: '/app/instagram-bio-generator', icon: Users, cost: '5 cr' },
    { name: 'Reply Bank', route: '/app/comment-reply-bank', icon: MessageSquare, cost: '5 cr' },
    { name: 'Brand Story', route: '/app/brand-story-builder', icon: Sparkles, cost: '18 cr' },
    { name: 'Offer Generator', route: '/app/offer-generator', icon: Coins, cost: '20 cr' },
    { name: 'Viral Ideas', route: '/app/daily-viral-ideas', icon: TrendingUp, cost: 'Free' },
    { name: 'Challenge Planner', route: '/app/content-challenge-planner', icon: Calendar, cost: '10 cr' },
    { name: 'Tone Switcher', route: '/app/tone-switcher', icon: Wand2, cost: '5 cr' },
  ],
};

export default function Dashboard() {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const [showDailyRewards, setShowDailyRewards] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [activeCategory, setActiveCategory] = useState('Video Tools');
  const [engagement, setEngagement] = useState(null);
  const [trending, setTrending] = useState([]);
  const navigate = useNavigate();

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };

    try {
      const cached = localStorage.getItem('user');
      if (cached) { const u = JSON.parse(cached); setUser(u); if (u.credits !== undefined) setCredits(u.credits); }
    } catch {}

    try {
      const r = await authAPI.getCurrentUser();
      const u = r.data?.user || r.data;
      if (u) { setUser(u); localStorage.setItem('user', JSON.stringify(u)); if (u.credits !== undefined) setCredits(u.credits); }
    } catch {}

    try {
      const r = await walletAPI.getWallet();
      if (r.data?.balanceCredits !== undefined) setCredits(r.data.balanceCredits);
      else if (r.data?.availableCredits !== undefined) setCredits(r.data.availableCredits);
    } catch {}

    try {
      const r = await generationAPI.getGenerations(null, 0, 5);
      setRecentGenerations(r.data.generations || []);
    } catch {}

    try {
      const r = await axios.get(`${API}/api/engagement/dashboard`, { headers });
      setEngagement(r.data);
    } catch {}

    try {
      const r = await axios.get(`${API}/api/engagement/trending`);
      setTrending(r.data.trending || []);
    } catch {}
  };

  const handleLogout = () => { localStorage.removeItem('token'); localStorage.removeItem('user'); navigate('/login'); };

  const handlePromptChange = (text) => {
    setPromptText(text);
    if (text.length < 3) { setSuggestions([]); return; }
    const lower = text.toLowerCase();
    setSuggestions(INTENT_MAP.filter(i => i.keywords.some(k => lower.includes(k))).slice(0, 3));
  };

  const handlePromptSubmit = () => {
    if (!promptText.trim()) return;
    const lower = promptText.toLowerCase();
    for (const intent of INTENT_MAP) {
      if (intent.keywords.some(k => lower.includes(k))) { navigate(intent.route, { state: { prompt: promptText } }); return; }
    }
    navigate('/app/story-video-studio', { state: { prompt: promptText } });
  };

  const completeChallenge = async () => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/api/engagement/challenge/complete`, {}, { headers: { Authorization: `Bearer ${token}` } });
      if (r.data.success) {
        toast.success(`Challenge complete! +${r.data.reward} credits`);
        setCredits(r.data.new_balance);
        setEngagement(prev => prev ? { ...prev, challenge: { ...prev.challenge, completed: true } } : prev);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Already completed');
    }
  };

  const isAdmin = user?.role === 'ADMIN' || user?.role === 'admin';
  const creditPercent = useMemo(() => credits >= 999999 ? 100 : Math.min(100, Math.round((credits / 500) * 100)), [credits]);

  const streakDays = engagement?.streak?.current || 0;

  return (
    <div className="min-h-screen bg-[#060B1A]">
      {/* ─── HEADER ─── */}
      <header className="bg-[#0A1128]/90 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link to="/app" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight hidden sm:inline">Visionary Suite</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {[['Create', '/app'], ['Gallery', '/gallery'], ['Tools', '/app/creator-tools'], ['Pricing', '/pricing']].map(([label, href]) => (
              <Link key={href} to={href} className="px-3 py-1.5 text-sm text-white/50 hover:text-white rounded-lg hover:bg-white/[0.04] transition-colors">{label}</Link>
            ))}
          </nav>

          <div className="flex items-center gap-1.5">
            {isAdmin && <Link to="/app/admin"><Button variant="ghost" size="sm" className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/10" data-testid="admin-dashboard-btn"><Shield className="w-4 h-4" /></Button></Link>}
            <Button variant="ghost" size="sm" onClick={() => setShowDailyRewards(true)} className="text-amber-400 hover:text-amber-300 hover:bg-amber-500/10" data-testid="daily-rewards-btn"><Gift className="w-4 h-4" /></Button>
            <NotificationBell />
            <CreditStatusBadge credits={credits} onCreditsUpdate={(b) => setCredits(b)} />
            <Link to="/app/profile"><Button variant="ghost" size="sm" className="text-white/40 hover:text-white hover:bg-white/[0.04]" data-testid="profile-btn"><User className="w-4 h-4" /></Button></Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-white/30 hover:text-white hover:bg-white/[0.04]" data-testid="logout-btn"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
        <DelayedCreditsBanner onCreditsAdded={(b) => setCredits(b)} />

        {/* ─── Welcome ─── */}
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight" data-testid="dashboard-welcome">
            {user?.name ? `Welcome back, ${user.name}` : 'Welcome back'}
          </h1>
          <p className="text-white/30 mt-0.5 text-sm">What would you like to create today?</p>
        </div>

        {/* ─── 2-COLUMN LAYOUT ─── */}
        <div className="flex gap-6">
          {/* ═══════ LEFT COLUMN — Main Content ═══════ */}
          <div className="flex-1 min-w-0 space-y-6">

            {/* ─── HERO PROMPT ─── */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="universal-prompt-section">
              <div className="flex items-center gap-2.5 mb-3">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <span className="text-sm font-semibold text-white/70">Create Anything with AI</span>
              </div>
              <div className="flex gap-2.5">
                <div className="flex-1 relative">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
                  <input
                    type="text" value={promptText}
                    onChange={(e) => handlePromptChange(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
                    placeholder="Describe what you want to create..."
                    className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl pl-10 pr-4 py-3 text-white placeholder-white/20 text-sm focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20 transition-colors"
                    data-testid="universal-prompt-input"
                  />
                  {suggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1.5 bg-[#111827] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-10" data-testid="prompt-suggestions">
                      {suggestions.map((s, i) => (
                        <button key={i} onClick={() => navigate(s.route, { state: { prompt: promptText } })} className="w-full text-left px-4 py-2.5 hover:bg-white/[0.04] transition-colors flex items-center gap-3 border-b border-white/[0.04] last:border-0">
                          <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                          <span className="text-sm text-white/80">{s.label}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <Button onClick={handlePromptSubmit} className="bg-gradient-to-r from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 text-white px-5 rounded-xl" data-testid="universal-prompt-submit">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {['Story video', 'Comic from photo', 'Viral reel', 'Bedtime story'].map((ex) => (
                  <button key={ex} onClick={() => { setPromptText(ex); handlePromptChange(ex); }} className="text-xs text-white/20 bg-white/[0.02] border border-white/[0.05] rounded-lg px-2.5 py-1 hover:bg-white/[0.05] hover:text-white/40 transition-colors">{ex}</button>
                ))}
              </div>
            </div>

            {/* ─── 3 ACTION CARDS ─── */}
            <div className="grid sm:grid-cols-3 gap-3" data-testid="hero-creation-section">
              {[
                { title: 'Story Video', desc: 'Cinematic AI videos with voiceover', route: '/app/story-video-studio', icon: Film, grad: 'from-indigo-600 to-blue-700', shadow: 'shadow-indigo-500/15', tags: ['6 Styles', 'AI Voice', '50 cr'], testId: 'hero-story-video-card' },
                { title: 'Photo to Comic', desc: 'Transform photos into comic art', route: '/app/photo-to-comic', icon: ImageIcon, grad: 'from-pink-600 to-rose-700', shadow: 'shadow-pink-500/15', tags: ['AI Art', 'Styles', '15 cr'], testId: 'hero-photo-comic-card' },
                { title: 'Reel Generator', desc: 'Viral hooks, scripts & hashtags', route: '/app/reels', icon: Video, grad: 'from-violet-600 to-purple-700', shadow: 'shadow-violet-500/15', tags: ['Hooks', 'Hashtags', '10 cr'], testId: 'hero-reel-card' },
              ].map((c) => (
                <Link key={c.route} to={c.route} className="group">
                  <div className={`relative rounded-2xl bg-gradient-to-br ${c.grad} p-5 overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg ${c.shadow} h-full`} data-testid={c.testId}>
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.06),transparent)] pointer-events-none" />
                    <div className="relative">
                      <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center mb-3"><c.icon className="w-5 h-5 text-white" /></div>
                      <h3 className="text-lg font-bold text-white mb-1">{c.title}</h3>
                      <p className="text-white/50 text-xs mb-2.5 leading-relaxed">{c.desc}</p>
                      <div className="flex gap-1.5">{c.tags.map(t => <span key={t} className="text-[10px] text-white/30 bg-white/10 rounded-full px-2 py-0.5">{t}</span>)}</div>
                    </div>
                    <ArrowRight className="absolute bottom-5 right-5 w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors" />
                  </div>
                </Link>
              ))}
            </div>

            {/* ─── INSPIRATION TEMPLATES ─── */}
            <div data-testid="templates-section">
              <h2 className="text-sm font-semibold text-white/50 mb-3">Inspiration</h2>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {TEMPLATES.map((t, i) => (
                  <Link key={i} to={t.route} state={{ prompt: t.prompt }}>
                    <div className="group rounded-xl border border-white/[0.05] bg-[#0B1220] p-3 hover:border-white/[0.1] hover:bg-[#0F172A] transition-all h-full" data-testid={`template-${i}`}>
                      <div className={`w-7 h-7 rounded-md bg-gradient-to-br ${t.grad} flex items-center justify-center mb-2`}><t.icon className="w-3.5 h-3.5 text-white" /></div>
                      <h3 className="text-xs font-medium text-white/80 mb-0.5 leading-tight">{t.title}</h3>
                      <p className="text-[10px] text-white/25 leading-snug">{t.desc}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            {/* ─── RECENT CREATIONS ─── */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="recent-creations-section">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-white/50">Recent Creations</h2>
                <Link to="/app/history"><Button variant="ghost" size="sm" className="text-white/30 hover:text-white text-xs h-7" data-testid="view-all-history-btn">View All <ChevronRight className="w-3 h-3 ml-0.5" /></Button></Link>
              </div>
              {recentGenerations.length === 0 ? (
                <div className="text-center py-10" data-testid="empty-creations">
                  <div className="w-14 h-14 mx-auto rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-center mb-3"><Sparkles className="w-6 h-6 text-white/15" /></div>
                  <p className="text-white/25 text-sm mb-3">No creations yet</p>
                  <Link to="/app/story-video-studio"><Button size="sm" className="bg-gradient-to-r from-indigo-500 to-blue-600 text-white text-xs rounded-lg">Create Your First Video</Button></Link>
                </div>
              ) : (
                <div className="space-y-1.5" data-testid="recent-generations-list">
                  {recentGenerations.map((gen) => (
                    <div key={gen.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${gen.type === 'REEL' ? 'bg-violet-500/10' : 'bg-indigo-500/10'}`}>
                        {gen.type === 'REEL' ? <Video className="w-4 h-4 text-violet-400" /> : <BookOpen className="w-4 h-4 text-indigo-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white/70 truncate">{gen.type} Generation</div>
                        <div className="text-[10px] text-white/20">{new Date(gen.createdAt).toLocaleDateString()}</div>
                      </div>
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${gen.status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400' : gen.status === 'FAILED' ? 'bg-red-500/10 text-red-400' : 'bg-white/[0.04] text-white/30'}`}>{gen.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ─── TOOL CATEGORIES ─── */}
            <div data-testid="tool-categories-section">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white/50">Creator Tools</h2>
                <Link to="/app/creator-tools" className="text-xs text-indigo-400/70 hover:text-indigo-300 flex items-center gap-0.5">All tools <ChevronRight className="w-3 h-3" /></Link>
              </div>
              <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
                {Object.keys(TOOL_CATEGORIES).map((cat) => (
                  <button key={cat} onClick={() => setActiveCategory(cat)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${activeCategory === cat ? 'bg-indigo-500/12 text-indigo-400 border border-indigo-500/25' : 'text-white/30 hover:text-white/50 hover:bg-white/[0.03] border border-transparent'}`}
                    data-testid={`category-tab-${cat.replace(/\s/g, '-').toLowerCase()}`}
                  >{cat}</button>
                ))}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {TOOL_CATEGORIES[activeCategory]?.map((tool) => (
                  <Link key={tool.route} to={tool.route}>
                    <div className="rounded-xl border border-white/[0.05] bg-[#0B1220] p-3.5 hover:border-white/[0.1] hover:bg-[#0F172A] transition-all group" data-testid={`tool-${tool.name.replace(/\s/g, '-').toLowerCase()}`}>
                      <tool.icon className="w-5 h-5 text-white/25 mb-2 group-hover:text-indigo-400 transition-colors" />
                      <h3 className="text-xs font-medium text-white/70 mb-0.5">{tool.name}</h3>
                      <span className="text-[10px] text-white/20">{tool.cost}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            {/* ─── TRENDING CREATIONS ─── */}
            {trending.length > 0 && (
              <div data-testid="trending-section">
                <h2 className="text-sm font-semibold text-white/50 mb-3">Trending on Visionary Suite</h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {trending.map((t) => (
                    <Link key={t.job_id} to={`/app/story-video-studio?remix=${t.job_id}`}>
                      <div className="rounded-xl border border-white/[0.05] bg-[#0B1220] overflow-hidden hover:border-white/[0.1] transition-all group">
                        {t.thumbnail_url ? (
                          <img src={t.thumbnail_url} alt={t.title} className="w-full aspect-video object-cover" loading="lazy" />
                        ) : (
                          <div className="w-full aspect-video bg-white/[0.02] flex items-center justify-center"><Film className="w-6 h-6 text-white/10" /></div>
                        )}
                        <div className="p-2.5">
                          <h3 className="text-xs font-medium text-white/60 truncate">{t.title}</h3>
                          <div className="flex items-center gap-1.5 mt-1">
                            <span className="text-[10px] text-white/20">{t.animation_style}</span>
                            {t.remix_count > 0 && <span className="text-[10px] text-indigo-400/50">{t.remix_count} remixes</span>}
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ═══════ RIGHT SIDEBAR — Utility Panel ═══════ */}
          <aside className="hidden lg:block w-[320px] flex-shrink-0 space-y-4" data-testid="sidebar-panel">

            {/* ─── Credits ─── */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="credits-panel">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Credits</span>
                <Link to="/app/billing" className="text-[10px] text-indigo-400/60 hover:text-indigo-300">Top up</Link>
              </div>
              <div className="text-3xl font-bold text-white mb-0.5">{credits >= 999999 ? '∞' : credits.toLocaleString()}</div>
              <p className="text-[10px] text-white/20 mb-3">remaining</p>
              <div className="w-full h-1.5 rounded-full bg-white/[0.04] overflow-hidden mb-4">
                <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-blue-500 transition-all duration-700" style={{ width: `${creditPercent}%` }} />
              </div>
              <div className="flex gap-2">
                <Link to="/app/billing" className="flex-1"><Button size="sm" className="w-full bg-gradient-to-r from-indigo-500 to-blue-600 text-white text-xs rounded-lg h-8"><CreditCard className="w-3 h-3 mr-1" /> Buy</Button></Link>
                <Link to="/app/subscription"><Button variant="outline" size="sm" className="border-white/[0.08] text-white/40 hover:text-white text-xs rounded-lg h-8"><Crown className="w-3 h-3 mr-1" /> Plans</Button></Link>
              </div>
            </div>

            {/* ─── Creator Level ─── */}
            {engagement?.level && (
              <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="creator-level-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Trophy className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Creator Level</span>
                </div>
                <div className="text-lg font-bold text-white mb-0.5">{engagement.level.level}</div>
                <p className="text-[10px] text-white/20 mb-2">{engagement.level.creation_count} creations</p>
                <div className="w-full h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-700" style={{ width: `${engagement.level.progress}%` }} />
                </div>
                <p className="text-[10px] text-white/15 mt-1.5">Next level at {engagement.level.next_level_at} creations</p>
              </div>
            )}

            {/* ─── Daily Challenge ─── */}
            {engagement?.challenge && (
              <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="daily-challenge-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Daily Challenge</span>
                </div>
                <p className="text-sm text-white/70 mb-3 leading-relaxed">{engagement.challenge.prompt}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-emerald-400/70">+{engagement.challenge.reward} credits</span>
                  {engagement.challenge.completed ? (
                    <span className="text-xs text-emerald-400 flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Done</span>
                  ) : (
                    <Button size="sm" onClick={completeChallenge} className="bg-gradient-to-r from-orange-500 to-rose-500 text-white text-xs rounded-lg h-7 px-3" data-testid="challenge-try-now-btn">
                      Try Now
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* ─── Creation Streak ─── */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="streak-panel">
              <div className="flex items-center gap-2 mb-3">
                <Flame className="w-4 h-4 text-orange-400" />
                <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Streak</span>
              </div>
              <div className="flex items-center gap-1 mb-2">
                {[1, 2, 3, 4, 5, 6, 7].map((day) => (
                  <div key={day} className={`w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold ${day <= streakDays ? 'bg-orange-500/15 text-orange-400 border border-orange-500/30' : 'bg-white/[0.02] text-white/15 border border-white/[0.04]'}`}>
                    {day <= streakDays ? <Check className="w-3 h-3" /> : day}
                  </div>
                ))}
              </div>
              <p className="text-xs text-white/30">{streakDays > 0 ? `${streakDays} day streak` : 'Create something to start!'}</p>
              {streakDays >= 3 && <p className="text-[10px] text-emerald-400/50 mt-1">Next milestone: {streakDays < 7 ? '7 days (+25 cr)' : streakDays < 14 ? '14 days (+50 cr)' : streakDays < 30 ? '30 days (+100 cr)' : '60 days (+250 cr)'}</p>}
            </div>

            {/* ─── AI Ideas ─── */}
            {engagement?.ideas && (
              <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="ai-ideas-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-4 h-4 text-yellow-400" />
                  <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Ideas For You</span>
                </div>
                <div className="space-y-1.5">
                  {engagement.ideas.map((idea, i) => (
                    <Link key={i} to={`/app/${idea.tool}`} state={{ prompt: idea.text }}>
                      <div className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-white/[0.03] transition-colors group">
                        <ArrowRight className="w-3 h-3 text-indigo-400/40 flex-shrink-0 group-hover:text-indigo-400" />
                        <span className="text-xs text-white/40 group-hover:text-white/70 transition-colors">{idea.text}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* ─── Activity Feed ─── */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#0B1220] p-5" data-testid="activity-feed">
              <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Activity</span>
              {recentGenerations.length === 0 ? (
                <p className="text-xs text-white/15 mt-3">No activity yet</p>
              ) : (
                <div className="space-y-2.5 mt-3">
                  {recentGenerations.slice(0, 4).map((gen, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${gen.status === 'SUCCEEDED' ? 'bg-emerald-400' : gen.status === 'FAILED' ? 'bg-red-400' : 'bg-white/15'}`} />
                      <span className="text-xs text-white/40 flex-1 truncate">{gen.type} generated</span>
                      <span className="text-[10px] text-white/15">{new Date(gen.createdAt).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ─── Quick Links ─── */}
            <div className="space-y-0.5 pt-2">
              {[
                ['/app/referral', Users, 'Referrals'],
                ['/app/analytics', BarChart3, 'Analytics'],
                ['/app/payment-history', Receipt, 'Payments'],
                ['/user-manual', HelpCircle, 'Help Center'],
              ].map(([href, Icon, label]) => (
                <Link key={href} to={href} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-white/20 hover:text-white/50 hover:bg-white/[0.02] transition-colors">
                  <Icon className="w-3.5 h-3.5" /><span className="text-xs">{label}</span>
                </Link>
              ))}
            </div>
          </aside>
        </div>
      </div>

      <HelpGuide pageId="dashboard" />
      <DailyRewardsModal isOpen={showDailyRewards} onClose={() => setShowDailyRewards(false)} />

      <footer className="border-t border-white/[0.03] py-3 mt-8">
        <div className="max-w-[1400px] mx-auto px-4 flex items-center justify-center">
          <div className="flex items-center gap-2 bg-emerald-500/5 border border-emerald-500/15 rounded-full px-3 py-1">
            <Shield className="w-3 h-3 text-emerald-400/40" />
            <span className="text-emerald-400/40 text-[10px]">Protected by OWASP Standards</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
