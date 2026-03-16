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
  Download, Zap, Send, Flame, Check, Trophy, Lightbulb,
  Activity, Eye, Globe, AlertTriangle, Heart, FileText,
  Command, Layers, RefreshCcw, Share2, Play
} from 'lucide-react';
import CreditStatusBadge from '../components/CreditStatusBadge';
import NotificationBell from '../components/NotificationBell';
import DailyRewardsModal from '../components/DailyRewardsModal';
import DelayedCreditsBanner from '../components/DelayedCreditsBanner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

/* ─── Intent keywords for universal prompt routing ─── */
const INTENT_MAP = [
  { keywords: ['video', 'story video', 'cinematic', 'animate', 'movie'], route: '/app/story-video-studio', label: 'Story Video Studio', icon: Film },
  { keywords: ['reel', 'hook', 'script', 'viral', 'short'], route: '/app/reels', label: 'Reel Script Generator', icon: Video },
  { keywords: ['comic', 'photo to comic', 'cartoon', 'transform photo'], route: '/app/photo-to-comic', label: 'Photo to Comic', icon: ImageIcon },
  { keywords: ['coloring', 'colour', 'color book'], route: '/app/coloring-book', label: 'Coloring Book', icon: Palette },
  { keywords: ['gif', 'reaction', 'meme'], route: '/app/gif-maker', label: 'Reaction GIF', icon: Film },
  { keywords: ['storybook', 'comic book', 'printable'], route: '/app/comic-storybook', label: 'Comic Story Builder', icon: Library },
  { keywords: ['bio', 'instagram bio', 'profile'], route: '/app/instagram-bio-generator', label: 'Instagram Bio Generator', icon: Users },
  { keywords: ['caption', 'rewrite', 'tone'], route: '/app/caption-rewriter', label: 'Caption Rewriter Pro', icon: Type },
  { keywords: ['bedtime', 'sleep', 'kids story', 'children'], route: '/app/bedtime-story-builder', label: 'Bedtime Story Builder', icon: Moon },
  { keywords: ['thumbnail', 'youtube'], route: '/app/thumbnail-generator', label: 'Thumbnail Text Gen', icon: ImageIcon },
  { keywords: ['brand', 'narrative', 'elevator'], route: '/app/brand-story-builder', label: 'Brand Story Builder', icon: Sparkles },
  { keywords: ['offer', 'discount', 'deal'], route: '/app/offer-generator', label: 'Offer Generator', icon: Coins },
  { keywords: ['challenge', 'content plan', 'planner'], route: '/app/content-challenge-planner', label: 'Content Planner', icon: Calendar },
  { keywords: ['reply', 'comment'], route: '/app/comment-reply-bank', label: 'Comment Reply Bank', icon: MessageSquare },
  { keywords: ['story', 'tale', 'fiction', 'adventure'], route: '/app/stories', label: 'Story Generator', icon: BookOpen },
  { keywords: ['idea', 'trending', 'daily'], route: '/app/daily-viral-ideas', label: 'Daily Viral Ideas', icon: TrendingUp },
];

/* ─── Creation Modes ─── */
const HERO_TOOL = { name: 'Story Video', desc: 'Turn any idea into a cinematic AI video with scenes, illustrations, voiceover, and music — ready in minutes.', route: '/app/story-video-studio', icon: Film, cost: '50 cr', accent: 'from-violet-500 to-indigo-600' };

const MORE_TOOLS = [
  { name: 'Reel Generator', desc: 'Viral hooks & scripts', route: '/app/reels', icon: Video, accent: 'from-pink-500 to-rose-600' },
  { name: 'Photo to Comic', desc: 'Transform any photo', route: '/app/photo-to-comic', icon: ImageIcon, accent: 'from-amber-500 to-orange-600' },
  { name: 'Comic Storybook', desc: 'Multi-page comic', route: '/app/comic-storybook', icon: Library, accent: 'from-emerald-500 to-teal-600' },
  { name: 'Bedtime Stories', desc: 'Magical tales for kids', route: '/app/bedtime-story-builder', icon: Moon, accent: 'from-blue-500 to-cyan-600' },
  { name: 'Reaction GIF', desc: 'Memes & reactions', route: '/app/gif-maker', icon: Zap, accent: 'from-red-500 to-orange-600' },
  { name: 'Caption Rewriter', desc: 'Rewrite in any tone', route: '/app/caption-rewriter', icon: Type, accent: 'from-cyan-500 to-blue-600' },
  { name: 'Brand Story', desc: 'Complete narrative', route: '/app/brand-story-builder', icon: Sparkles, accent: 'from-purple-500 to-pink-600' },
  { name: 'Daily Viral Ideas', desc: 'Trending prompts', route: '/app/daily-viral-ideas', icon: TrendingUp, accent: 'from-teal-500 to-emerald-600' },
];

const SUGGESTION_CHIPS = [
  { text: 'Create a kids story video', icon: Film },
  { text: 'Luxury lifestyle reel', icon: Video },
  { text: 'Dragon fantasy animation', icon: Sparkles },
  { text: 'Turn photo into comic', icon: ImageIcon },
];

export default function Dashboard() {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const [showDailyRewards, setShowDailyRewards] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [suggestions, setSuggestions] = useState([]);
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
    setSuggestions(INTENT_MAP.filter(i => i.keywords.some(k => lower.includes(k))).slice(0, 4));
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
    <div className="vs-page" data-testid="dashboard-page">
      {/* ─── HEADER ─── */}
      <header className="vs-glass sticky top-0 z-40 border-b border-[var(--vs-border-subtle)]">
        <div className="vs-container flex items-center justify-between h-14">
          <Link to="/app" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg vs-gradient-bg flex items-center justify-center">
              <Command className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-semibold text-white tracking-tight hidden sm:inline" style={{ fontFamily: 'var(--vs-font-heading)' }}>
              Visionary Suite
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {[
              ['Create', '/app'],
              ['Gallery', '/gallery'],
              ['Explore', '/gallery'],
              ['Pricing', '/pricing'],
            ].map(([label, href]) => (
              <Link key={label} to={href} className="px-3 py-1.5 text-sm text-[var(--vs-text-muted)] hover:text-white rounded-lg hover:bg-white/[0.04] transition-colors" style={{ fontFamily: 'var(--vs-font-body)' }}>
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-1.5">
            {isAdmin && (
              <Link to="/app/admin">
                <Button variant="ghost" size="sm" className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/10" data-testid="admin-dashboard-btn">
                  <Shield className="w-4 h-4" />
                </Button>
              </Link>
            )}
            <Button variant="ghost" size="sm" onClick={() => setShowDailyRewards(true)} className="text-amber-400 hover:text-amber-300 hover:bg-amber-500/10" data-testid="daily-rewards-btn">
              <Gift className="w-4 h-4" />
            </Button>
            <NotificationBell />
            <CreditStatusBadge credits={credits} onCreditsUpdate={(b) => setCredits(b)} />
            <Link to="/app/profile">
              <Button variant="ghost" size="sm" className="text-[var(--vs-text-muted)] hover:text-white hover:bg-white/[0.04]" data-testid="profile-btn">
                <User className="w-4 h-4" />
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-[var(--vs-text-muted)] hover:text-white hover:bg-white/[0.04]" data-testid="logout-btn">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="vs-container py-8">
        <DelayedCreditsBanner onCreditsAdded={(b) => setCredits(b)} />

        {/* ═══════ AI COMMAND CENTER ═══════ */}
        <div className="vs-fade-up-1 mb-10">
          {/* Welcome */}
          <div className="text-center mb-6">
            <h1 className="vs-h1 mb-1" data-testid="dashboard-welcome">
              {user?.name ? `Welcome back, ${user.name}` : 'What will you create today?'}
            </h1>
            <p className="text-[var(--vs-text-muted)] text-sm" style={{ fontFamily: 'var(--vs-font-body)' }}>
              Type a prompt or pick a creation mode below
            </p>
          </div>

          {/* ─── HERO PROMPT BOX ─── */}
          <div className="max-w-[800px] mx-auto" data-testid="command-center-prompt">
            <div className="relative">
              <div className="relative flex items-center">
                <Sparkles className="absolute left-5 w-5 h-5 text-[var(--vs-primary-from)] z-10" />
                <input
                  type="text"
                  value={promptText}
                  onChange={(e) => handlePromptChange(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
                  placeholder="What do you want to create today?"
                  className="vs-input h-[70px] pl-14 pr-[120px] text-base"
                  style={{ borderRadius: '14px', fontFamily: 'var(--vs-font-body)' }}
                  data-testid="universal-prompt-input"
                />
                <button
                  onClick={handlePromptSubmit}
                  className="vs-btn-primary absolute right-3 h-[46px] px-5 rounded-[10px]"
                  data-testid="universal-prompt-submit"
                >
                  <Send className="w-4 h-4 mr-1.5" />
                  Create
                </button>
              </div>

              {/* Suggestions dropdown */}
              {suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-[var(--vs-bg-panel)] border border-[var(--vs-border)] rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-20" data-testid="prompt-suggestions">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => navigate(s.route, { state: { prompt: promptText } })}
                      className="w-full text-left px-5 py-3 hover:bg-white/[0.04] transition-colors flex items-center gap-3 border-b border-[var(--vs-border-subtle)] last:border-0"
                    >
                      <s.icon className="w-4 h-4 text-[var(--vs-text-accent)] flex-shrink-0" />
                      <div>
                        <span className="text-sm text-white font-medium">{s.label}</span>
                        <span className="text-xs text-[var(--vs-text-muted)] ml-2">matched your prompt</span>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-[var(--vs-text-muted)] ml-auto" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {SUGGESTION_CHIPS.map((chip) => (
                <button
                  key={chip.text}
                  onClick={() => { setPromptText(chip.text); handlePromptChange(chip.text); }}
                  className="vs-chip"
                  data-testid={`suggestion-chip-${chip.text.slice(0, 15).replace(/\s/g, '-').toLowerCase()}`}
                >
                  <chip.icon className="w-3.5 h-3.5" />
                  {chip.text}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ═══════ HERO CREATION ═══════ */}
        <div className="vs-fade-up-2 vs-section" data-testid="creation-modes-section">
          {/* Story Video — The Hero */}
          <Link to={HERO_TOOL.route}>
            <div className="vs-card group cursor-pointer flex flex-col sm:flex-row items-center gap-6 p-6 mb-6 hover:border-[var(--vs-border-glow)] vs-glow-pulse" data-testid="hero-tool-card">
              <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${HERO_TOOL.accent} flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform`}>
                <HERO_TOOL.icon className="w-8 h-8 text-white" />
              </div>
              <div className="flex-1 text-center sm:text-left">
                <h2 className="vs-h2 mb-1" style={{ fontFamily: 'var(--vs-font-heading)' }}>{HERO_TOOL.name}</h2>
                <p className="text-[var(--vs-text-secondary)] text-sm leading-relaxed" style={{ fontFamily: 'var(--vs-font-body)' }}>{HERO_TOOL.desc}</p>
              </div>
              <button className="vs-btn-primary h-12 px-8 text-base font-semibold flex-shrink-0">
                <Wand2 className="w-4 h-4" /> Create Video
              </button>
            </div>
          </Link>

          {/* More Tools — collapsed grid */}
          <details className="group" data-testid="more-tools-section">
            <summary className="flex items-center gap-2 text-sm text-[var(--vs-text-muted)] cursor-pointer hover:text-white transition-colors mb-3 list-none">
              <ChevronRight className="w-4 h-4 group-open:rotate-90 transition-transform" />
              <span style={{ fontFamily: 'var(--vs-font-heading)' }}>More Tools</span>
              <span className="text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>{MORE_TOOLS.length}</span>
            </summary>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="more-tools-grid">
              {MORE_TOOLS.map(tool => (
                <Link key={tool.route + tool.name} to={tool.route}>
                  <div className="vs-card group cursor-pointer h-full py-3 px-3">
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${tool.accent} flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform`}>
                        <tool.icon className="w-4 h-4 text-white" />
                      </div>
                      <h3 className="text-sm font-semibold text-white truncate" style={{ fontFamily: 'var(--vs-font-heading)' }}>{tool.name}</h3>
                    </div>
                    <p className="text-xs text-[var(--vs-text-muted)] pl-[42px]">{tool.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </details>
        </div>

        {/* ═══════ 2-COLUMN: RECENT + SIDEBAR ═══════ */}
        <div className="vs-fade-up-3 flex gap-6">
          {/* ─── LEFT: Recent Creations + Trending ─── */}
          <div className="flex-1 min-w-0 space-y-[var(--vs-section-gap)]">

            {/* Recent Creations */}
            <div className="vs-panel p-5" data-testid="recent-creations-section">
              <div className="flex items-center justify-between mb-4">
                <h2 className="vs-h3">Recent Creations</h2>
                <Link to="/app/history">
                  <button className="vs-btn-secondary h-8 px-3 text-xs" data-testid="view-all-history-btn">
                    View All <ChevronRight className="w-3 h-3 ml-0.5" />
                  </button>
                </Link>
              </div>
              {recentGenerations.length === 0 ? (
                <div className="text-center py-12" data-testid="empty-creations">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-[var(--vs-bg-card)] border border-[var(--vs-border)] flex items-center justify-center mb-4">
                    <Sparkles className="w-7 h-7 text-[var(--vs-text-muted)]" />
                  </div>
                  <p className="text-[var(--vs-text-muted)] text-sm mb-4">No creations yet. Start your first one!</p>
                  <Link to="/app/story-video-studio">
                    <button className="vs-btn-primary" data-testid="create-first-btn">
                      <Film className="w-4 h-4" /> Create Story Video
                    </button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-2" data-testid="recent-generations-list">
                  {recentGenerations.map((gen) => (
                    <div key={gen.id} className="flex items-center gap-3 p-3 rounded-[var(--vs-card-radius)] bg-[var(--vs-bg-card)]/50 hover:bg-[var(--vs-bg-card)] transition-colors border border-transparent hover:border-[var(--vs-border)]">
                      <div className={`w-10 h-10 rounded-[10px] flex items-center justify-center flex-shrink-0 ${gen.type === 'REEL' ? 'bg-pink-500/10' : 'bg-violet-500/10'}`}>
                        {gen.type === 'REEL' ? <Video className="w-4.5 h-4.5 text-pink-400" /> : <BookOpen className="w-4.5 h-4.5 text-violet-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white font-medium truncate">{gen.type} Generation</div>
                        <div className="text-xs text-[var(--vs-text-muted)]">{new Date(gen.createdAt).toLocaleDateString()}</div>
                      </div>
                      <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                        gen.status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400' : gen.status === 'FAILED' ? 'bg-red-500/10 text-red-400' : 'bg-white/[0.04] text-[var(--vs-text-muted)]'
                      }`} style={{ fontFamily: 'var(--vs-font-mono)' }}>{gen.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Trending Creations */}
            {trending.length > 0 && (
              <div data-testid="trending-section">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="vs-h3">Trending Creations</h2>
                  <Link to="/gallery">
                    <button className="vs-btn-secondary h-8 px-3 text-xs">
                      Explore <ArrowRight className="w-3 h-3 ml-0.5" />
                    </button>
                  </Link>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {trending.map((t) => (
                    <Link key={t.job_id} to={`/app/story-video-studio?remix=${t.job_id}`}>
                      <div className="vs-card group p-0 overflow-hidden">
                        {t.thumbnail_url ? (
                          <img src={t.thumbnail_url} alt={t.title} className="w-full aspect-video object-cover" loading="lazy" />
                        ) : (
                          <div className="w-full aspect-video bg-[var(--vs-bg-elevated)] flex items-center justify-center">
                            <Film className="w-8 h-8 text-[var(--vs-text-muted)]" />
                          </div>
                        )}
                        <div className="p-3">
                          <h3 className="text-sm font-medium text-white truncate">{t.title}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-[var(--vs-text-muted)]">{t.animation_style}</span>
                            {t.remix_count > 0 && (
                              <span className="text-xs text-[var(--vs-text-accent)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>{t.remix_count} remixes</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Admin Panel - Collapsed */}
            {isAdmin && (
              <div className="vs-panel p-5" data-testid="admin-panel-section">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <Shield className="w-5 h-5 text-[var(--vs-text-accent)]" />
                    <h2 className="vs-h3">Admin Panel</h2>
                  </div>
                  <Link to="/app/admin">
                    <button className="vs-btn-secondary h-8 px-3 text-xs" data-testid="admin-panel-full-link">
                      Full Dashboard <ArrowRight className="w-3 h-3 ml-1" />
                    </button>
                  </Link>
                </div>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                  {[
                    { label: 'Users', icon: Users, to: '/app/admin/users', color: 'text-blue-400' },
                    { label: 'Revenue', icon: CreditCard, to: '/app/admin/revenue', color: 'text-emerald-400' },
                    { label: 'Analytics', icon: BarChart3, to: '/app/admin/realtime-analytics', color: 'text-amber-400' },
                    { label: 'Workers', icon: Zap, to: '/app/admin/workers', color: 'text-orange-400' },
                    { label: 'Security', icon: Shield, to: '/app/admin/security', color: 'text-red-400' },
                    { label: 'Health', icon: Heart, to: '/app/admin/system-health', color: 'text-rose-400' },
                  ].map(item => (
                    <Link key={item.to} to={item.to} className="group" data-testid={`admin-quick-${item.label.toLowerCase()}`}>
                      <div className="vs-card flex flex-col items-center gap-2 py-3 group-hover:border-[var(--vs-border-glow)]">
                        <item.icon className={`w-4.5 h-4.5 ${item.color} opacity-60 group-hover:opacity-100 transition-opacity`} />
                        <span className="text-xs text-[var(--vs-text-muted)] group-hover:text-white transition-colors text-center">{item.label}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ═══════ RIGHT SIDEBAR ═══════ */}
          <aside className="hidden lg:block w-[300px] flex-shrink-0 space-y-4" data-testid="sidebar-panel">

            {/* Credits */}
            <div className="vs-panel p-5" data-testid="credits-panel">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-[var(--vs-text-muted)] uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>Credits</span>
                <Link to="/app/billing" className="text-xs text-[var(--vs-text-accent)] hover:text-white transition-colors">Top up</Link>
              </div>
              <div className="text-3xl font-bold text-white mb-0.5" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                {credits >= 999999 ? '∞' : credits.toLocaleString()}
              </div>
              <p className="text-xs text-[var(--vs-text-muted)] mb-3">available</p>
              <div className="w-full h-1.5 rounded-full bg-[var(--vs-bg-card)] overflow-hidden mb-4">
                <div className="h-full rounded-full vs-gradient-bg transition-all duration-700" style={{ width: `${creditPercent}%` }} />
              </div>
              <div className="flex gap-2">
                <Link to="/app/billing" className="flex-1">
                  <button className="vs-btn-primary w-full text-xs h-9">
                    <CreditCard className="w-3.5 h-3.5" /> Buy Credits
                  </button>
                </Link>
                <Link to="/app/subscription">
                  <button className="vs-btn-secondary text-xs h-9">
                    <Crown className="w-3.5 h-3.5" />
                  </button>
                </Link>
              </div>
            </div>

            {/* Streak */}
            <div className="vs-panel p-5" data-testid="streak-panel">
              <div className="flex items-center gap-2 mb-3">
                <Flame className="w-4 h-4 text-orange-400" />
                <span className="text-xs font-semibold text-[var(--vs-text-muted)] uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>
                  {streakDays > 0 ? `${streakDays} Day Streak` : 'Start a Streak'}
                </span>
              </div>
              <div className="flex items-center gap-1 mb-2">
                {[1, 2, 3, 4, 5, 6, 7].map((day) => (
                  <div key={day} className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-all ${
                    day <= streakDays
                      ? 'bg-orange-500/15 text-orange-400 border border-orange-500/30'
                      : 'bg-[var(--vs-bg-card)] text-[var(--vs-text-muted)] border border-[var(--vs-border)]'
                  }`} style={{ fontFamily: 'var(--vs-font-mono)' }}>
                    {day <= streakDays ? <Check className="w-3 h-3" /> : day}
                  </div>
                ))}
              </div>
              <p className="text-xs text-[var(--vs-text-muted)]">{streakDays > 0 ? 'Keep creating daily!' : 'Create something to begin'}</p>
            </div>

            {/* Daily Challenge */}
            {engagement?.challenge && (
              <div className="vs-panel p-5 border-[var(--vs-border-glow)]" data-testid="daily-challenge-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Trophy className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold text-[var(--vs-text-muted)] uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>Daily Challenge</span>
                </div>
                <p className="text-sm text-white/80 mb-3 leading-relaxed" style={{ fontFamily: 'var(--vs-font-body)' }}>{engagement.challenge.prompt}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-emerald-400" style={{ fontFamily: 'var(--vs-font-mono)' }}>+{engagement.challenge.reward} cr</span>
                  {engagement.challenge.completed ? (
                    <span className="text-xs text-emerald-400 flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Done</span>
                  ) : (
                    <button onClick={completeChallenge} className="vs-btn-primary h-8 px-4 text-xs" data-testid="challenge-try-now-btn">Try Now</button>
                  )}
                </div>
              </div>
            )}

            {/* Creator Level */}
            {engagement?.level && (
              <div className="vs-panel p-5" data-testid="creator-level-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Crown className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold text-[var(--vs-text-muted)] uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>Creator Level</span>
                </div>
                <div className="text-lg font-bold text-white mb-0.5" style={{ fontFamily: 'var(--vs-font-heading)' }}>{engagement.level.level}</div>
                <p className="text-xs text-[var(--vs-text-muted)] mb-2" style={{ fontFamily: 'var(--vs-font-mono)' }}>{engagement.level.creation_count} creations</p>
                <div className="w-full h-1.5 rounded-full bg-[var(--vs-bg-card)] overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-700" style={{ width: `${engagement.level.progress}%` }} />
                </div>
                <p className="text-xs text-[var(--vs-text-muted)] mt-1.5">Next at {engagement.level.next_level_at}</p>
              </div>
            )}

            {/* AI Ideas */}
            {engagement?.ideas && (
              <div className="vs-panel p-5" data-testid="ai-ideas-panel">
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-4 h-4 text-yellow-400" />
                  <span className="text-xs font-semibold text-[var(--vs-text-muted)] uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>Ideas For You</span>
                </div>
                <div className="space-y-1">
                  {engagement.ideas.map((idea, i) => (
                    <Link key={i} to={`/app/${idea.tool}`} state={{ prompt: idea.text }}>
                      <div className="flex items-start gap-2.5 p-2.5 rounded-lg hover:bg-[var(--vs-bg-card)] transition-colors group">
                        <ArrowRight className="w-3.5 h-3.5 text-[var(--vs-text-accent)] flex-shrink-0 mt-0.5 opacity-50 group-hover:opacity-100" />
                        <span className="text-xs text-[var(--vs-text-secondary)] group-hover:text-white transition-colors leading-relaxed">{idea.text}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Links */}
            <div className="space-y-0.5 pt-2">
              {[
                ['/app/referral', Gift, 'Referral Program'],
                ['/app/downloads', Download, 'My Downloads'],
                ['/app/payment-history', Receipt, 'Payment History'],
                ['/user-manual', HelpCircle, 'Help Center'],
              ].map(([href, Icon, label]) => (
                <Link key={href} to={href} className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[var(--vs-text-muted)] hover:text-white hover:bg-white/[0.03] transition-colors">
                  <Icon className="w-4 h-4" /><span className="text-sm" style={{ fontFamily: 'var(--vs-font-body)' }}>{label}</span>
                </Link>
              ))}
            </div>
          </aside>
        </div>
      </div>

      <DailyRewardsModal isOpen={showDailyRewards} onClose={() => setShowDailyRewards(false)} />
    </div>
  );
}
