import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Loader2, BookOpen, Users, Sparkles, Heart, Star,
  Film, ChevronRight, Play, Eye, RefreshCcw, Bell,
  Share2, Copy, Check, Zap, ArrowRight, Command, User
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

  useEffect(() => {
    if (characterId) {
      fetchCharacter();
      fetchCharacterStories();
      checkFollowing();
    }
  }, [characterId]);

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
      toast.success(res.data.following ? `Following ${data?.character?.name}!` : 'Unfollowed');
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

  const { character, visual_bible, social_proof, sample_scenes, relationships } = data;
  const personality = character.personality_summary || '';
  const traits = personality.split(',').map(t => t.trim()).filter(Boolean).slice(0, 5);
  const storiesCount = social_proof.total_stories || 0;
  const contCount = social_proof.total_continuations || 0;

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
            <button onClick={copyLink} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-white/[0.08] rounded-lg flex items-center gap-1.5">
              {copied ? <Check className="w-3 h-3 text-green-400" /> : <Share2 className="w-3 h-3" />} {copied ? 'Copied!' : 'Share'}
            </button>
            <button onClick={() => handleContinue('continue')} className="px-4 py-1.5 text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 rounded-lg flex items-center gap-1.5" data-testid="header-continue-btn">
              <Play className="w-3 h-3" /> Continue Story
            </button>
          </div>
        </div>
      </header>

      {/* ═══ HERO — CHARACTER AS A PRODUCT ═══ */}
      <section className="relative" data-testid="character-hero">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-violet-600/[0.06] rounded-full blur-[180px] pointer-events-none" />

        <div className="relative max-w-5xl mx-auto px-4 pt-10 pb-8">
          <div className="flex flex-col md:flex-row gap-8 items-start">
            {/* Left: Avatar + Identity */}
            <div className="flex flex-col items-center md:items-start md:w-64 flex-shrink-0">
              <div className="relative w-28 h-28 mb-4">
                <div className="absolute inset-0 rounded-full bg-violet-500/20 animate-ping" style={{ animationDuration: '3s' }} />
                <div className="relative w-28 h-28 rounded-full bg-gradient-to-br from-violet-500/30 to-rose-500/30 border-2 border-violet-400/40 flex items-center justify-center overflow-hidden shadow-2xl shadow-violet-500/10">
                  {character.portrait_url ? (
                    <img src={character.portrait_url} alt={character.name} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-4xl font-black text-violet-300">{character.name?.[0]?.toUpperCase() || '?'}</span>
                  )}
                </div>
              </div>

              <p className="text-violet-400/80 text-[10px] font-bold uppercase tracking-[0.2em] mb-1" data-testid="character-role">
                {character.role || 'AI Character'}
              </p>
              <h1 className="text-3xl font-black text-white mb-2" data-testid="character-name">{character.name}</h1>
              <p className="text-sm text-slate-400 leading-relaxed mb-4 text-center md:text-left">
                {visual_bible?.canonical_description || personality || `A mysterious ${character.role || 'character'} with untold stories...`}
              </p>

              {/* STATS ROW */}
              <div className="flex items-center gap-3 text-xs mb-4" data-testid="character-stats">
                <span className="flex items-center gap-1 text-slate-400"><Film className="w-3 h-3 text-violet-400" /><strong className="text-white">{storiesCount}</strong> stories</span>
                <span className="flex items-center gap-1 text-slate-400"><Users className="w-3 h-3 text-rose-400" /><strong className="text-white">{followerCount}</strong> followers</span>
                <span className="flex items-center gap-1 text-slate-400"><RefreshCcw className="w-3 h-3 text-cyan-400" /><strong className="text-white">{contCount}</strong> continuations</span>
              </div>

              {/* FOLLOW BUTTON */}
              <button
                onClick={handleFollow}
                disabled={followLoading}
                className={`w-full h-10 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                  following
                    ? 'bg-white/[0.06] border border-violet-500/30 text-violet-300 hover:bg-red-500/10 hover:text-red-300 hover:border-red-500/30'
                    : 'bg-violet-600 hover:bg-violet-500 text-white'
                }`}
                data-testid="follow-btn"
              >
                {followLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                  <>
                    <Bell className="w-4 h-4" />
                    {following ? 'Following' : `Follow ${character.name}`}
                  </>
                )}
              </button>
            </div>

            {/* Right: CTAs + Actions */}
            <div className="flex-1 space-y-4">
              {/* PRIMARY: Continue Story */}
              <button
                onClick={() => handleContinue('continue')}
                className="w-full group relative overflow-hidden rounded-2xl p-5 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
                data-testid="continue-story-cta"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                    <Play className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <span className="text-lg font-bold text-white block">Continue {character.name}'s Story</span>
                    <span className="text-sm text-white/70">{contCount > 0 ? `${contCount} people already continued` : 'Pick up where it left off'}</span>
                  </div>
                  <ArrowRight className="w-5 h-5 text-white/40 group-hover:text-white group-hover:translate-x-1 transition-all" />
                </div>
              </button>

              {/* SECONDARY: Twist / Funny / Episode */}
              <div className="grid grid-cols-3 gap-2" data-testid="secondary-ctas">
                <button onClick={() => handleContinue('twist')} className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/[0.04] hover:bg-amber-500/[0.08] transition-all text-center" data-testid="twist-btn">
                  <Sparkles className="w-5 h-5 text-amber-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Add Twist</span>
                </button>
                <button onClick={() => handleContinue('funny')} className="p-4 rounded-xl border border-pink-500/20 bg-pink-500/[0.04] hover:bg-pink-500/[0.08] transition-all text-center" data-testid="funny-btn">
                  <Star className="w-5 h-5 text-pink-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Make Funny</span>
                </button>
                <button onClick={() => handleContinue('episode')} className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/[0.04] hover:bg-purple-500/[0.08] transition-all text-center" data-testid="episode-btn">
                  <Film className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                  <span className="text-xs font-bold text-white block">Next Episode</span>
                </button>
              </div>

              {/* CREATE YOUR OWN */}
              <button
                onClick={() => handleContinue('continue')}
                className="w-full group rounded-xl border border-white/[0.08] hover:border-violet-500/20 bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all"
                data-testid="create-own-btn"
              >
                <div className="flex items-center gap-3">
                  <Sparkles className="w-5 h-5 text-violet-400" />
                  <div className="flex-1">
                    <span className="text-sm font-semibold text-white block">Create your own story with {character.name}</span>
                    <span className="text-[11px] text-slate-500">Same character, your imagination</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-violet-400 transition-colors" />
                </div>
              </button>

              {/* Traits */}
              {traits.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {traits.map((trait, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 text-xs bg-white/[0.04] text-slate-300 px-3 py-1.5 rounded-full border border-white/[0.06]">
                      <Heart className="w-3 h-3 text-violet-400" /> {trait}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ═══ CHARACTER FEED — Latest stories featuring this character ═══ */}
      <section className="py-8 px-4 border-t border-white/[0.04]" data-testid="character-feed">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Film className="w-5 h-5 text-violet-400" />
              {character.name}'s Stories
            </h2>
            <span className="text-xs text-slate-500">{stories.length} stories</span>
          </div>

          {stories.length > 0 ? (
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
                      <h3 className="text-sm font-bold text-white leading-tight mb-1 line-clamp-2">{story.title || 'Untitled'}</h3>
                      <p className="text-[10px] text-white/50 mb-2">{story.animation_style?.replace(/_/g, ' ')}</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); continueStory(story); }}
                        className="w-full h-7 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-[11px] font-bold flex items-center justify-center gap-1 hover:opacity-90 transition-opacity"
                        data-testid={`continue-feed-${idx}`}
                      >
                        <Play className="w-3 h-3" /> Continue
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
              <BookOpen className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500 mb-3">No stories yet featuring {character.name}</p>
              <button onClick={() => handleContinue('continue')} className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold flex items-center gap-2 mx-auto" data-testid="first-story-btn">
                <Play className="w-4 h-4" /> Create the first story
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ═══ SCENE MOMENTS + RELATIONSHIPS ═══ */}
      <section className="py-8 px-4 border-t border-white/[0.04]">
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-6">
          {/* Recent Story Moments */}
          {sample_scenes?.length > 0 && (
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5" data-testid="sample-scenes">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-violet-400" /> Recent Moments
              </h3>
              <div className="space-y-2">
                {sample_scenes.map((scene, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                    <div className="w-6 h-6 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-[10px] text-violet-400 font-bold">{i + 1}</span>
                    </div>
                    <div>
                      <p className="text-xs text-slate-300 leading-relaxed">{scene.summary}</p>
                      {scene.emotion && <span className="text-[10px] text-slate-600 mt-1 inline-flex items-center gap-1"><Heart className="w-2.5 h-2.5" /> {scene.emotion}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relationships */}
          {relationships?.length > 0 && (
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5" data-testid="relationships-section">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" /> Connections
              </h3>
              <div className="space-y-2">
                {relationships.map((rel, i) => (
                  <Link key={i} to={`/character/${rel.character_id}`} className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04] hover:border-cyan-500/20 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs text-white font-bold">{rel.name?.[0]?.toUpperCase()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-white font-medium">{rel.name}</span>
                      <p className="text-[10px] text-slate-500">{rel.relationship_type}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ═══ BOTTOM CTA ═══ */}
      <section className="py-12 px-4 border-t border-white/[0.04]" data-testid="bottom-cta">
        <div className="max-w-xl mx-auto text-center">
          <h2 className="text-2xl font-black text-white mb-2">{character.name}'s story isn't over</h2>
          <p className="text-sm text-slate-400 mb-6">You decide what happens next. No account required.</p>
          <button
            onClick={() => handleContinue('continue')}
            className="h-12 px-8 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base hover:shadow-[0_0_40px_-8px_rgba(139,92,246,0.5)] transition-all hover:scale-[1.02] flex items-center gap-2 mx-auto"
            data-testid="bottom-continue-btn"
          >
            <Play className="w-5 h-5" /> Continue {character.name}'s Story <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
