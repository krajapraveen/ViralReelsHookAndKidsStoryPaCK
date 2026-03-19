import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Loader2, BookOpen, Users, Sparkles, Heart, Star,
  Film, ChevronRight, ArrowLeft, Shield, Zap, Play,
  Eye, RefreshCcw, MessageCircle
} from 'lucide-react';
import api from '../utils/api';
import { trackPageView, trackRemixClick, setOrigin } from '../utils/growthAnalytics';

const TRAIT_ICONS = {
  brave: Zap,
  kind: Heart,
  curious: Star,
  loyal: Shield,
};

export default function PublicCharacterPage() {
  const { characterId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCharacter = async () => {
      try {
        const res = await api.get(`/api/public/character/${characterId}`);
        if (res.data.success) {
          setData(res.data);
          trackPageView({
            source_page: `/character/${characterId}`,
            character_id: characterId,
            origin: 'public_character_page',
            origin_character_id: characterId,
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
    if (characterId) fetchCharacter();
  }, [characterId]);

  const trackAndNavigate = (ctaType) => {
    if (!data?.remix_data) return;
    trackRemixClick({
      source_page: `/character/${characterId}`,
      character_id: characterId,
      tool_type: 'story_video',
      origin: 'public_character_page',
      origin_character_id: characterId,
      meta: { character_name: data.character?.name, cta_type: ctaType },
    });
    localStorage.setItem('remix_data', JSON.stringify(data.remix_data));
    navigate('/app/story-video-studio', { state: data.remix_data });
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
        <Button variant="ghost" onClick={() => navigate('/')} className="text-slate-400">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
        </Button>
      </div>
    );
  }

  const { character, visual_bible, social_proof, sample_scenes, relationships } = data;
  const personality = character.personality_summary || '';
  const traits = personality.split(',').map(t => t.trim()).filter(Boolean).slice(0, 5);
  const hasStories = social_proof.episode_count > 0 || social_proof.total_usage > 0;

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="public-character-page">

      {/* ═══ HERO — IMMERSIVE CHARACTER HOOK ═══ */}
      <div className="relative overflow-hidden">
        {/* Dramatic ambient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-violet-600/10 rounded-full blur-[160px] pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[300px] bg-rose-500/8 rounded-full blur-[120px] pointer-events-none" />

        <div className="relative max-w-xl mx-auto px-5 pt-14 pb-10 text-center">
          {/* Avatar with pulse ring */}
          <div className="relative w-32 h-32 mx-auto mb-8">
            <div className="absolute inset-0 rounded-full bg-violet-500/20 animate-ping" style={{ animationDuration: '3s' }} />
            <div className="relative w-32 h-32 rounded-full bg-gradient-to-br from-violet-500/30 to-rose-500/30 border-2 border-violet-400/40 flex items-center justify-center overflow-hidden shadow-2xl shadow-violet-500/10">
              {character.portrait_url ? (
                <img src={character.portrait_url} alt={character.name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-5xl font-black text-violet-300">
                  {character.name?.[0]?.toUpperCase() || '?'}
                </span>
              )}
            </div>
          </div>

          {/* Emotional hook — NOT just a name */}
          <p className="text-violet-400/80 text-xs font-semibold uppercase tracking-[0.2em] mb-3" data-testid="character-role">
            {character.role || 'AI Character'}
          </p>
          <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 leading-tight" data-testid="character-name">
            {character.name}
          </h1>
          <p className="text-base sm:text-lg text-slate-300/90 max-w-md mx-auto mb-6 leading-relaxed" data-testid="character-description">
            {visual_bible?.canonical_description || personality || `A mysterious ${character.role || 'character'} with untold stories...`}
          </p>

          {/* Social Proof — LOUD */}
          {hasStories && (
            <div className="flex items-center justify-center gap-5 mb-8" data-testid="social-proof">
              {social_proof.episode_count > 0 && (
                <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-full px-4 py-2">
                  <Film className="w-4 h-4 text-violet-400" />
                  <span className="text-sm text-white font-bold">{social_proof.episode_count}</span>
                  <span className="text-xs text-slate-400">stories</span>
                </div>
              )}
              {social_proof.total_usage > 0 && (
                <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-full px-4 py-2">
                  <Eye className="w-4 h-4 text-amber-400" />
                  <span className="text-sm text-white font-bold">{social_proof.total_usage}</span>
                  <span className="text-xs text-slate-400">moments</span>
                </div>
              )}
            </div>
          )}
          {social_proof.series_title && (
            <p className="text-[11px] text-slate-500 -mt-4 mb-6">from the series "{social_proof.series_title}"</p>
          )}

          {/* ═══ DUAL CTA — THE HOOK ═══ */}
          <div className="space-y-3 max-w-sm mx-auto">
            {/* PRIMARY: Continue the story */}
            <button
              onClick={() => trackAndNavigate('continue_story')}
              className="w-full group relative overflow-hidden rounded-2xl p-4 text-left transition-all hover:scale-[1.02] active:scale-[0.99]"
              data-testid="continue-story-cta"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-violet-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
              <div className="relative z-10 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                  <Play className="w-5 h-5 text-white ml-0.5" />
                </div>
                <div className="flex-1">
                  <span className="text-base font-bold text-white block">Continue {character.name}'s Story</span>
                  <span className="text-xs text-white/60">Pick up where it left off — 1 click</span>
                </div>
                <ChevronRight className="w-5 h-5 text-white/40 group-hover:text-white/80 group-hover:translate-x-1 transition-all" />
              </div>
            </button>

            {/* SECONDARY: Create your own version */}
            <button
              onClick={() => trackAndNavigate('create_own')}
              className="w-full group rounded-2xl border border-white/10 hover:border-violet-500/30 bg-white/[0.02] hover:bg-white/[0.04] p-4 text-left transition-all"
              data-testid="create-own-cta"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-violet-400" />
                </div>
                <div className="flex-1">
                  <span className="text-sm font-semibold text-white block">Create Your Own Version</span>
                  <span className="text-xs text-slate-500">New story, same character — no signup needed</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-violet-400 transition-colors" />
              </div>
            </button>
          </div>

          <p className="text-[11px] text-slate-600 mt-4">No account required to start. Free to explore.</p>
        </div>
      </div>

      {/* ═══ BELOW THE FOLD — CHARACTER DEPTH ═══ */}
      <div className="max-w-xl mx-auto px-5 pb-20 space-y-6">

        {/* Scene Teasers — creates curiosity */}
        {sample_scenes?.length > 0 && (
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5" data-testid="sample-scenes">
            <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-violet-400" /> Recent Story Moments
            </h2>
            <div className="space-y-2.5">
              {sample_scenes.map((scene, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04] hover:border-violet-500/20 transition-colors">
                  <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-[11px] text-violet-400 font-bold">{i + 1}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-300 leading-relaxed">{scene.summary}</p>
                    {scene.emotion && (
                      <span className="text-[10px] text-slate-600 mt-1.5 inline-flex items-center gap-1">
                        <Heart className="w-2.5 h-2.5" /> {scene.emotion}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Open-loop teaser after scenes */}
            <button
              onClick={() => trackAndNavigate('scene_teaser')}
              className="mt-4 w-full py-3 text-center text-xs font-medium text-violet-400 bg-violet-500/5 hover:bg-violet-500/10 border border-violet-500/10 rounded-xl transition-colors"
              data-testid="scene-continue-cta"
            >
              What happens next? Continue the story...
            </button>
          </div>
        )}

        {/* Personality Traits */}
        {traits.length > 0 && (
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5" data-testid="personality-section">
            <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Heart className="w-4 h-4 text-rose-400" /> Personality
            </h2>
            <div className="flex flex-wrap gap-2">
              {traits.map((trait, i) => {
                const Icon = TRAIT_ICONS[trait.toLowerCase()] || Star;
                return (
                  <span key={i} className="inline-flex items-center gap-1.5 text-xs bg-white/[0.04] text-slate-300 px-3 py-1.5 rounded-full border border-white/[0.06]">
                    <Icon className="w-3 h-3 text-violet-400" />
                    {trait}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Goals & Fears */}
        {(character.core_goals || character.core_fears) && (
          <div className="grid grid-cols-2 gap-3">
            {character.core_goals && (
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4">
                <h3 className="text-[11px] font-semibold text-emerald-400 mb-2 uppercase tracking-wider">Drives</h3>
                <p className="text-xs text-slate-300 leading-relaxed">{character.core_goals}</p>
              </div>
            )}
            {character.core_fears && (
              <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4">
                <h3 className="text-[11px] font-semibold text-amber-400 mb-2 uppercase tracking-wider">Fears</h3>
                <p className="text-xs text-slate-300 leading-relaxed">{character.core_fears}</p>
              </div>
            )}
          </div>
        )}

        {/* Relationships */}
        {relationships?.length > 0 && (
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5" data-testid="relationships-section">
            <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" /> Connections
            </h2>
            <div className="space-y-2">
              {relationships.map((rel, i) => (
                <a key={i} href={`/character/${rel.character_id}`}
                  className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04] hover:border-cyan-500/20 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs text-white font-bold">{rel.name?.[0]?.toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-white font-medium">{rel.name}</span>
                    <p className="text-[10px] text-slate-500">{rel.relationship_type}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Visual Style */}
        {visual_bible?.style_lock && (
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5">
            <h2 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-400" /> Art Style
            </h2>
            <p className="text-xs text-slate-400">{visual_bible.style_lock}</p>
          </div>
        )}

        {/* Creator Credit */}
        {social_proof.creator_name && (
          <div className="text-center text-xs text-slate-600 pt-2">
            Created by <span className="text-slate-400">{social_proof.creator_name}</span>
          </div>
        )}

        {/* ═══ BOTTOM CTA — LAST CHANCE ═══ */}
        <div className="text-center pt-4 space-y-3">
          <button
            onClick={() => trackAndNavigate('bottom_cta')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-all hover:scale-[1.02]"
            data-testid="bottom-cta"
          >
            <Sparkles className="w-4 h-4" />
            Start Your Story With {character.name}
          </button>
          <p className="text-[10px] text-slate-600">
            1 click. No signup. Your version in 30 seconds.
          </p>
        </div>
      </div>
    </div>
  );
}
