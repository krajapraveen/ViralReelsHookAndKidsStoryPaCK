import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Loader2, BookOpen, Users, Sparkles, Heart, Star,
  Film, ChevronRight, ArrowLeft, Shield, Zap
} from 'lucide-react';
import api from '../utils/api';

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
  const [ctaHover, setCtaHover] = useState(false);

  useEffect(() => {
    const fetchCharacter = async () => {
      try {
        const res = await api.get(`/api/public/character/${characterId}`);
        if (res.data.success) setData(res.data);
        else setError('Character not found');
      } catch {
        setError('Character not found');
      } finally {
        setLoading(false);
      }
    };
    if (characterId) fetchCharacter();
  }, [characterId]);

  const handleCreateStory = () => {
    if (!data?.remix_data) return;
    // Store remix_data in localStorage for StoryVideoStudio to pick up
    localStorage.setItem('remix_data', JSON.stringify(data.remix_data));
    navigate('/app/story-video-studio', { state: data.remix_data });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4">
        <p className="text-slate-400">{error || 'Character not found'}</p>
        <Button variant="ghost" onClick={() => navigate('/')} className="text-slate-400">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
        </Button>
      </div>
    );
  }

  const { character, visual_bible, social_proof, sample_scenes, relationships, remix_data } = data;
  const personality = character.personality_summary || '';
  const traits = personality.split(',').map(t => t.trim()).filter(Boolean).slice(0, 5);

  return (
    <div className="min-h-screen bg-slate-950" data-testid="public-character-page">
      {/* Hero Section — ABOVE THE FOLD */}
      <div className="relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-indigo-500/5 to-transparent" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-cyan-500/8 rounded-full blur-[120px]" />

        <div className="relative max-w-2xl mx-auto px-4 pt-16 pb-12 text-center">
          {/* Character Avatar */}
          <div className="w-28 h-28 rounded-full bg-gradient-to-br from-cyan-500/20 to-indigo-500/20 border-2 border-cyan-500/30 mx-auto mb-6 flex items-center justify-center">
            {character.portrait_url ? (
              <img src={character.portrait_url} alt={character.name} className="w-full h-full rounded-full object-cover" />
            ) : (
              <span className="text-4xl font-bold text-cyan-400">
                {character.name?.[0]?.toUpperCase() || '?'}
              </span>
            )}
          </div>

          {/* Name & Role */}
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" data-testid="character-name">
            Meet {character.name}
          </h1>
          <p className="text-sm text-cyan-400 font-medium uppercase tracking-wider mb-4">
            {character.role || 'Character'}
          </p>

          {/* Description */}
          <p className="text-base text-slate-300 max-w-lg mx-auto mb-8 leading-relaxed" data-testid="character-description">
            {visual_bible?.canonical_description || personality || `A ${character.role} character ready for new adventures.`}
          </p>

          {/* Social Proof */}
          {(social_proof.episode_count > 0 || social_proof.total_usage > 0) && (
            <div className="flex items-center justify-center gap-4 mb-8 text-sm" data-testid="social-proof">
              {social_proof.episode_count > 0 && (
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Film className="w-4 h-4 text-cyan-400" />
                  Used in <span className="text-white font-semibold">{social_proof.episode_count}</span> episodes
                </span>
              )}
              {social_proof.total_usage > 0 && (
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span className="text-white font-semibold">{social_proof.total_usage}</span> story moments
                </span>
              )}
            </div>
          )}
          {social_proof.series_title && (
            <p className="text-xs text-slate-500 mb-6 -mt-4">from "{social_proof.series_title}"</p>
          )}

          {/* PRIMARY CTA — MOST IMPORTANT */}
          <div className="space-y-3">
            <Button
              onClick={handleCreateStory}
              onMouseEnter={() => setCtaHover(true)}
              onMouseLeave={() => setCtaHover(false)}
              className="h-14 px-8 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-base rounded-xl shadow-lg shadow-cyan-500/20 transition-all"
              data-testid="create-story-cta"
            >
              <Sparkles className={`w-5 h-5 mr-2 transition-transform ${ctaHover ? 'scale-110' : ''}`} />
              Create Your Own Story With {character.name}
            </Button>
            <p className="text-xs text-slate-500">Start in 1 click. No signup required to begin.</p>
          </div>
        </div>
      </div>

      {/* ── BELOW THE FOLD ────────────────────────────────────── */}
      <div className="max-w-2xl mx-auto px-4 pb-20 space-y-8">

        {/* Personality Traits */}
        {traits.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid="personality-section">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Heart className="w-4 h-4 text-pink-400" /> Personality
            </h2>
            <div className="flex flex-wrap gap-2">
              {traits.map((trait, i) => {
                const Icon = TRAIT_ICONS[trait.toLowerCase()] || Star;
                return (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1.5 text-xs bg-slate-800/80 text-slate-300 px-3 py-1.5 rounded-full border border-slate-700/50"
                  >
                    <Icon className="w-3 h-3 text-cyan-400" />
                    {trait}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Goals & Fears */}
        {(character.core_goals || character.core_fears) && (
          <div className="grid grid-cols-2 gap-4">
            {character.core_goals && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <h3 className="text-xs font-medium text-emerald-400 mb-2">Goals</h3>
                <p className="text-sm text-slate-300">{character.core_goals}</p>
              </div>
            )}
            {character.core_fears && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <h3 className="text-xs font-medium text-amber-400 mb-2">Fears</h3>
                <p className="text-sm text-slate-300">{character.core_fears}</p>
              </div>
            )}
          </div>
        )}

        {/* Sample Scenes */}
        {sample_scenes?.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid="sample-scenes">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-indigo-400" /> Story Moments
            </h2>
            <div className="space-y-2.5">
              {sample_scenes.map((scene, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-lg border border-slate-800/50">
                  <div className="w-6 h-6 rounded-full bg-indigo-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-[10px] text-indigo-400 font-bold">{i + 1}</span>
                  </div>
                  <div>
                    <p className="text-xs text-slate-300 leading-relaxed">{scene.summary}</p>
                    {scene.emotion && (
                      <span className="text-[10px] text-slate-500 mt-1 inline-block">
                        Feeling: {scene.emotion}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Relationships */}
        {relationships?.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid="relationships-section">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" /> Connections
            </h2>
            <div className="space-y-2">
              {relationships.map((rel, i) => (
                <a
                  key={i}
                  href={`/character/${rel.character_id}`}
                  className="flex items-center gap-3 p-3 bg-slate-800/40 rounded-lg border border-slate-800/50 hover:border-cyan-500/30 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
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
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-400" /> Art Style
            </h2>
            <p className="text-xs text-slate-400">{visual_bible.style_lock}</p>
          </div>
        )}

        {/* Creator Credit */}
        {social_proof.creator_name && (
          <div className="text-center text-xs text-slate-600 pt-4">
            Created by <span className="text-slate-400">{social_proof.creator_name}</span>
          </div>
        )}

        {/* Bottom CTA */}
        <div className="text-center pt-4">
          <Button
            onClick={handleCreateStory}
            variant="outline"
            className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 h-11 px-6"
            data-testid="bottom-cta"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Start Your Story With {character.name}
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
