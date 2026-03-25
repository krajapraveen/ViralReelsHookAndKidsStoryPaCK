import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Loader2, Users, Sparkles, Film, Play, Eye, RefreshCcw, Bell,
  Share2, Copy, Check, ArrowRight, Command, Flame, TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { SafeImage } from '../components/SafeImage';
import { trackPageView, trackRemixClick, setOrigin } from '../utils/growthAnalytics';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicCharacterPage() {
  const { characterId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [following, setFollowing] = useState(false);
  const [followLoading, setFollowLoading] = useState(false);
  const [stories, setStories] = useState([]);
  const [followerCount, setFollowerCount] = useState(0);
  const [copied, setCopied] = useState(false);
  const [showUrgency, setShowUrgency] = useState(false);

  useEffect(() => {
    if (characterId) {
      fetchCharacter();
      fetchCharacterStories();
      checkFollowing();
    }
  }, [characterId]);

  // Delayed urgency trigger — 5 seconds after page load
  useEffect(() => {
    const timer = setTimeout(() => setShowUrgency(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  const fetchCharacter = async () => {
    try {
      const res = await api.get(`/api/public/character/${characterId}`);
      if (res.data.success) {
        setData(res.data);
        trackPageView({
          source_page: `/character/${characterId}`,
          character_id: characterId,
          origin: 'public_character_page',
          meta: { character_name: res.data.character?.name },
        });
        setOrigin('public_character_page', { character_id: characterId });
      } else setError('Character not found');
    } catch {
      setError('Character not found');
    } finally {
      setLoading(false);
    }
  };

  const fetchCharacterStories = async () => {
    try {
      const res = await api.get(`/api/universe/character/${characterId}/stories`);
      if (res.data.success) {
        setStories(res.data.stories || []);
        setFollowerCount(res.data.follower_count || 0);
      }
    } catch {}
  };

  const checkFollowing = async () => {
    try {
      const res = await api.get(`/api/universe/following/${characterId}`);
      setFollowing(res.data.following);
    } catch {}
  };

  const handleFollow = async () => {
    setFollowLoading(true);
    try {
      const res = await api.post('/api/universe/follow', { character_id: characterId });
      setFollowing(res.data.following);
      setFollowerCount(prev => res.data.following ? prev + 1 : Math.max(0, prev - 1));
      if (res.data.following && entryStory) {
        toast.success(
          <div>
            <p className="font-bold">Following {data?.character?.name}!</p>
            <p className="text-xs mt-0.5 opacity-80">New story ready — continue now</p>
          </div>,
          { duration: 5000 }
        );
      } else if (res.data.following) {
        toast.success(`Following ${data?.character?.name}! You'll get notified of new episodes.`);
      } else {
        toast.success('Unfollowed');
      }
    } catch {
      toast.error('Log in to follow characters');
    } finally {
      setFollowLoading(false);
    }
  };

  const handleContinue = (type = 'continue') => {
    if (!data?.remix_data) return;
    const char = data.character;
    const base = data.remix_data.prompt || '';
    let prompt = base;
    let title = `Story with ${char.name}`;

    if (type === 'twist') {
      prompt = `[A TWIST in ${char.name}'s story]\n\n${base}\n\nDirection: Introduce an unexpected betrayal, reveal, or surprise that changes everything for ${char.name}.`;
      title = `Twist: ${char.name}'s Story`;
    } else if (type === 'funny') {
      prompt = `[Funny version of ${char.name}'s story]\n\n${base}\n\nDirection: Make this hilariously funny while keeping ${char.name}'s personality.`;
      title = `Funny: ${char.name}'s Story`;
    } else if (type === 'episode') {
      prompt = `[Next Episode for ${char.name}]\n\n${base}\n\nDirection: Create a new episode with higher stakes. ${char.name} faces a new challenge.`;
      title = `Episode: ${char.name}'s Story`;
    } else {
      prompt = `[Continue ${char.name}'s story]\n\n${base}\n\nDirection: Continue with higher stakes and tension. Keep ${char.name}'s personality and world consistent.`;
      title = `From: ${char.name}'s Story`;
    }

    trackRemixClick({
      source_page: `/character/${characterId}`,
      character_id: characterId,
      tool_type: 'story_video',
      origin: 'public_character_page',
      meta: { character_name: char.name, cta_type: type },
    });

    localStorage.setItem('remix_data', JSON.stringify({
      prompt,
      remixFrom: {
        ...data.remix_data.remixFrom,
        title,
        prompt,
      },
    }));
    navigate('/app/story-video-studio');
  };

  const continueStory = (story) => {
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: story.story_text || story.title || '',
      timestamp: Date.now(),
      source_tool: 'character-feed',
      remixFrom: {
        tool: 'story-video-studio',
        prompt: story.story_text || story.title,
        title: story.title,
        settings: { animation_style: story.animation_style },
        parentId: story.job_id,
      },
    }));
    navigate('/app/story-video-studio');
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success('Link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center gap-4">
        <p className="text-slate-400">{error || 'Character not found'}</p>
        <Link to="/explore"><button className="px-5 py-2 bg-violet-600 text-white rounded-lg text-sm">Explore Stories</button></Link>
      </div>
    );
  }

  const { character, visual_bible, social_proof } = data;
  const contCount = social_proof.total_continuations || 0;
  const storiesCount = social_proof.total_stories || 0;
  const hookQuote = character.hook_text
    || visual_bible?.canonical_description?.split('.')[0]
    || character.personality_summary?.split('.')[0]
    || `A mysterious ${character.role || 'character'} with untold stories`;

  // Auto-select entry story: latest or most-viewed
  const entryStory = stories.length > 0
    ? [...stories].sort((a, b) => (b.views || 0) - (a.views || 0))[0]
    : null;

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="public-character-page">
      {/* HEADER */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-4 h-13 flex items-center justify-between py-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Command className="w-3 h-3 text-white" />
            </div>
            <span className="text-xs font-semibold text-white hidden sm:inline">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-2">
            <button onClick={copyLink} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/[0.08] rounded-lg flex items-center gap-1.5" data-testid="share-btn">
              {copied ? <Check className="w-3 h-3 text-green-400" /> : <Share2 className="w-3 h-3" />} {copied ? 'Copied!' : 'Share'}
            </button>
            <button onClick={() => handleContinue('continue')} className="px-4 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-rose-600 hover:opacity-90 rounded-lg flex items-center gap-1.5" data-testid="header-continue-btn">
              <Play className="w-3 h-3" /> Continue Story
            </button>
          </div>
        </div>
      </header>

      {/* ═══ HERO — ACTION-FIRST, ABOVE THE FOLD ═══ */}
      <section className="relative" data-testid="character-hero">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-violet-600/[0.08] rounded-full blur-[180px] pointer-events-none" />

        <div className="relative max-w-3xl mx-auto px-4 pt-10 pb-6 text-center">
          {/* Avatar */}
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full bg-violet-500/20 animate-ping" style={{ animationDuration: '3s' }} />
            <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-violet-500/30 to-rose-500/30 border-2 border-violet-400/40 flex items-center justify-center overflow-hidden shadow-2xl shadow-violet-500/20">
              {character.portrait_url ? (
                <img src={character.portrait_url} alt={character.name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-3xl font-black text-violet-300">{character.name?.[0]?.toUpperCase() || '?'}</span>
              )}
            </div>
          </div>

          {/* Name */}
          <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 leading-tight" data-testid="character-name">
            {character.name}
          </h1>

          {/* Hook Quote */}
          <p className="text-lg sm:text-xl text-slate-300 italic leading-relaxed max-w-xl mx-auto mb-4" data-testid="hook-quote">
            "{hookQuote}..."
          </p>

          {/* Social Proof with counting animation */}
          <div className="flex items-center justify-center gap-4 mb-4" data-testid="social-proof-bar">
            {contCount > 0 && (
              <span className="inline-flex items-center gap-1.5 text-sm font-bold text-amber-400 bg-amber-500/10 px-3 py-1.5 rounded-full animate-pulse" style={{ animationDuration: '2s' }}>
                <Flame className="w-4 h-4" /> {contCount} people continued this
              </span>
            )}
            {storiesCount > 0 && (
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                <Film className="w-3.5 h-3.5 text-violet-400" /> {storiesCount} stories
              </span>
            )}
            {followerCount > 0 && (
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                <Users className="w-3.5 h-3.5 text-rose-400" /> {followerCount} followers
              </span>
            )}
          </div>

          {/* ENTRY STORY — "Start with this story" guidance */}
          {entryStory && (
            <div
              className="max-w-md mx-auto mb-5 p-3 rounded-xl bg-white/[0.03] border border-white/[0.08] cursor-pointer hover:border-violet-500/30 transition-all group"
              onClick={() => continueStory(entryStory)}
              data-testid="entry-story"
            >
              <div className="flex items-center gap-3">
                {entryStory.thumbnail_url && (
                  <div className="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0">
                    <SafeImage src={entryStory.thumbnail_url} alt={entryStory.title} className="w-full h-full object-cover" />
                  </div>
                )}
                <div className="flex-1 text-left min-w-0">
                  <p className="text-[10px] font-bold text-violet-400 uppercase tracking-wider mb-0.5">Start with this story</p>
                  <p className="text-sm text-white font-semibold truncate">{entryStory.title || 'Latest Story'}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
              </div>
            </div>
          )}

          {/* PRIMARY CTA — BIG, GLOWING, PULSING */}
          <button
            onClick={() => entryStory ? continueStory(entryStory) : handleContinue('continue')}
            className="group relative inline-flex items-center gap-3 h-14 px-10 rounded-2xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-lg shadow-[0_0_60px_-10px_rgba(139,92,246,0.5)] hover:shadow-[0_0_80px_-10px_rgba(139,92,246,0.7)] hover:scale-[1.03] active:scale-[0.98] transition-all mx-auto mb-3"
            style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
            data-testid="continue-story-cta"
          >
            <Play className="w-6 h-6" />
            Continue {character.name}'s Story
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Delayed urgency trigger */}
          {showUrgency && contCount > 0 && (
            <p className="text-xs text-amber-400/80 font-medium mb-3 animate-fade-in" data-testid="urgency-trigger">
              Continue before others do — {contCount} already have
            </p>
          )}

          {/* SECONDARY CTA */}
          <button
            onClick={() => handleContinue('continue')}
            className="inline-flex items-center gap-2 text-sm text-violet-300 hover:text-white transition-colors"
            data-testid="create-own-btn"
          >
            <Sparkles className="w-4 h-4" />
            Create your own version of {character.name}
          </button>
        </div>
      </section>

      {/* ═══ ACTION ROW — Twist / Funny / Episode + Follow ═══ */}
      <section className="px-4 pb-8">
        <div className="max-w-3xl mx-auto">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="action-row">
            <button onClick={() => handleContinue('twist')} className="group p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.1] hover:border-amber-500/40 transition-all text-center" data-testid="twist-btn">
              <Sparkles className="w-5 h-5 text-amber-400 mx-auto mb-1" />
              <span className="text-xs font-bold text-white block">Add Twist</span>
              <span className="text-[10px] text-slate-500">Unexpected turn</span>
            </button>
            <button onClick={() => handleContinue('funny')} className="group p-3.5 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.1] hover:border-pink-500/40 transition-all text-center" data-testid="funny-btn">
              <TrendingUp className="w-5 h-5 text-pink-400 mx-auto mb-1" />
              <span className="text-xs font-bold text-white block">Make Funny</span>
              <span className="text-[10px] text-slate-500">Comedy version</span>
            </button>
            <button onClick={() => handleContinue('episode')} className="group p-3.5 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.1] hover:border-purple-500/40 transition-all text-center" data-testid="episode-btn">
              <Film className="w-5 h-5 text-purple-400 mx-auto mb-1" />
              <span className="text-xs font-bold text-white block">Next Episode</span>
              <span className="text-[10px] text-slate-500">Higher stakes</span>
            </button>
            <button
              onClick={handleFollow}
              disabled={followLoading}
              className={`group p-3.5 rounded-xl border transition-all text-center ${
                following
                  ? 'border-violet-500/30 bg-violet-500/[0.06] hover:bg-red-500/[0.06] hover:border-red-500/30'
                  : 'border-cyan-500/20 bg-cyan-500/[0.04] hover:bg-cyan-500/[0.1] hover:border-cyan-500/40'
              }`}
              data-testid="follow-btn"
            >
              {followLoading ? <Loader2 className="w-5 h-5 text-violet-400 mx-auto mb-1 animate-spin" /> : (
                <Bell className={`w-5 h-5 mx-auto mb-1 ${following ? 'text-violet-400' : 'text-cyan-400'}`} />
              )}
              <span className="text-xs font-bold text-white block">{following ? 'Following' : 'Follow'}</span>
              <span className="text-[10px] text-slate-500">{following ? 'Getting new episodes' : 'Get new episodes instantly'}</span>
            </button>
          </div>
        </div>
      </section>

      {/* ═══ CHARACTER FEED ═══ */}
      {stories.length > 0 && (
        <section className="py-8 px-4 border-t border-white/[0.04]" data-testid="character-feed">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Flame className="w-5 h-5 text-amber-400" />
                {character.name}'s Latest Stories
              </h2>
              {stories.length > 4 && <span className="text-xs text-slate-500">{stories.length} total</span>}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3" data-testid="stories-grid">
              {stories.map((story, idx) => (
                <div key={story.job_id || idx} className="group rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02] hover:border-violet-500/30 transition-all cursor-pointer" data-testid={`story-card-${idx}`}>
                  <div className="relative aspect-[3/4] overflow-hidden bg-slate-900">
                    <SafeImage src={story.thumbnail_url} alt={story.title} aspectRatio="3/4" titleOverlay={story.title} fallbackType="gradient" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent" />
                    {story.views > 0 && (
                      <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded-md text-[10px] text-white/70">
                        <Eye className="w-2.5 h-2.5" /> {story.views}
                      </div>
                    )}
                    <div className="absolute bottom-0 left-0 right-0 p-3">
                      <h3 className="text-sm font-bold text-white leading-tight mb-2 line-clamp-2">{story.title || 'Untitled'}</h3>
                      <button
                        onClick={(e) => { e.stopPropagation(); continueStory(story); }}
                        className="w-full h-8 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-[11px] font-bold flex items-center justify-center gap-1 hover:opacity-90 transition-opacity"
                        data-testid={`continue-feed-${idx}`}
                      >
                        <Play className="w-3 h-3" /> Continue This Story
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {stories.length === 0 && (
        <section className="py-12 px-4 border-t border-white/[0.04]">
          <div className="max-w-xl mx-auto text-center">
            <p className="text-sm text-slate-500 mb-4">No stories yet featuring {character.name}</p>
            <button onClick={() => handleContinue('continue')} className="inline-flex items-center gap-2 h-11 px-6 bg-gradient-to-r from-violet-600 to-rose-600 text-white rounded-xl text-sm font-bold hover:opacity-90" data-testid="first-story-btn">
              <Play className="w-4 h-4" /> Be the first to create {character.name}'s story
            </button>
          </div>
        </section>
      )}

      {/* ═══ BOTTOM CTA ═══ */}
      <section className="py-12 px-4 border-t border-white/[0.04]" data-testid="bottom-cta">
        <div className="max-w-xl mx-auto text-center">
          <p className="text-sm text-amber-400 font-semibold mb-2 flex items-center justify-center gap-1.5">
            <Flame className="w-4 h-4" />
            {contCount > 0 ? `${contCount} people already continued` : 'Story still evolving'}
          </p>
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-2">{character.name}'s story isn't over</h2>
          <p className="text-sm text-slate-400 mb-6">You decide what happens next. No account required to start.</p>
          <button
            onClick={() => entryStory ? continueStory(entryStory) : handleContinue('continue')}
            className="h-13 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_50px_-8px_rgba(139,92,246,0.6)] transition-all hover:scale-[1.02] inline-flex items-center gap-2"
            data-testid="bottom-continue-btn"
          >
            <Play className="w-5 h-5" /> Continue {character.name}'s Story <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* CTA Glow Animation */}
      <style>{`
        @keyframes cta-glow {
          0%, 100% { box-shadow: 0 0 60px -10px rgba(139,92,246,0.5); }
          50% { box-shadow: 0 0 80px -5px rgba(139,92,246,0.7); }
        }
        .animate-fade-in {
          animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
