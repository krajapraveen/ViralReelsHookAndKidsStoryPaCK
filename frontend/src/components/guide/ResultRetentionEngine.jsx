import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import { trackFunnel } from '../../utils/funnelTracker';
import {
  Sparkles, ArrowRight, Film, RefreshCw, Share2,
  Flame, Target, Zap, TrendingUp, Users
} from 'lucide-react';

const REMIX_PRESETS = [
  { id: 'pixar', label: 'Pixar Style', emoji: '🎬', style: 'pixar_3d' },
  { id: 'anime', label: 'Anime', emoji: '🌸', style: 'anime' },
  { id: 'funny', label: 'Funny Version', emoji: '😂', tone: 'comedy' },
  { id: 'dark', label: 'Dark Mode', emoji: '🖤', tone: 'dark_thriller' },
  { id: 'kids', label: 'Kids Version', emoji: '🧸', tone: 'kids_friendly' },
  { id: 'epic', label: 'Epic Fantasy', emoji: '⚔️', style: 'fantasy_art' },
];

/**
 * Result Retention Engine — The complete addiction layer for the result screen.
 * Includes: Success Banner, What Next Panel, Remix Strip, Streak Bar, Social Proof.
 *
 * Props:
 *  - project: current project data
 *  - storyText: original story text
 *  - styleId: current style
 *  - onContinueStory: () => void
 *  - onRemix: (presetOverrides) => void
 *  - onNewStory: () => void
 *  - onShareClick: () => void
 */
export default function ResultRetentionEngine({
  project, storyText, styleId, onContinueStory, onRemix, onNewStory, onShareClick
}) {
  const navigate = useNavigate();
  const [streak, setStreak] = useState(null);
  const [socialProof, setSocialProof] = useState(null);

  useEffect(() => {
    api.get('/api/streaks/my').then(r => setStreak(r.data)).catch(() => {});
    api.get('/api/streaks/social-proof').then(r => setSocialProof(r.data)).catch(() => {});
  }, []);

  const handleRemix = useCallback((preset) => {
    trackFunnel('second_action', {
      source_page: 'studio',
      meta: { action: 'remix', preset: preset.id },
    });
    if (onRemix) onRemix(preset);
  }, [onRemix]);

  const handleNextAction = useCallback((action) => {
    trackFunnel('second_action', {
      source_page: 'studio',
      meta: { action },
    });
  }, []);

  const milestone = streak?.current_milestone;
  const progress = milestone
    ? Math.min(100, Math.round((streak.today_count / milestone.target) * 100))
    : 100;

  return (
    <div className="space-y-4" data-testid="result-retention-engine">
      {/* ── Success Banner with Social Proof ── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-600/20 via-indigo-600/20 to-pink-600/20 border border-purple-500/20 p-4" data-testid="success-banner">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(139,92,246,0.08),transparent_70%)]" />
        <div className="relative flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              Your story is ready!
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Creators like you make 5+ versions
            </p>
          </div>
          {socialProof && (
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1 text-slate-400">
                <Users className="w-3 h-3 text-indigo-400" />
                {socialProof.total_creators.toLocaleString()} creators
              </span>
              <span className="flex items-center gap-1 text-slate-400">
                <TrendingUp className="w-3 h-3 text-emerald-400" />
                {socialProof.total_generations.toLocaleString()} stories
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── What Next Panel ── */}
      <div className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-4" data-testid="what-next-panel">
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400" />
          What do you want to do next?
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => { handleNextAction('continue_story'); onContinueStory?.(); }}
            className="flex items-center gap-2.5 p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 hover:border-indigo-500/50 transition-all text-left group"
            data-testid="next-continue-story"
          >
            <ArrowRight className="w-4 h-4 flex-shrink-0 group-hover:translate-x-0.5 transition-transform" />
            <div>
              <p className="text-xs font-semibold">Continue Story</p>
              <p className="text-[10px] text-slate-500">Same characters</p>
            </div>
          </button>
          <button
            onClick={() => { handleNextAction('generate_video'); navigate('/app/story-video-studio'); }}
            className="flex items-center gap-2.5 p-3 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 hover:bg-purple-500/20 hover:border-purple-500/50 transition-all text-left group"
            data-testid="next-generate-video"
          >
            <Film className="w-4 h-4 flex-shrink-0 group-hover:scale-110 transition-transform" />
            <div>
              <p className="text-xs font-semibold">Turn into Video</p>
              <p className="text-[10px] text-slate-500">Full story video</p>
            </div>
          </button>
          <button
            onClick={() => { handleNextAction('remix_funny'); handleRemix(REMIX_PRESETS[2]); }}
            className="flex items-center gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 hover:border-amber-500/50 transition-all text-left group"
            data-testid="next-make-funny"
          >
            <span className="text-base group-hover:scale-110 transition-transform">😂</span>
            <div>
              <p className="text-xs font-semibold">Make it Funnier</p>
              <p className="text-[10px] text-slate-500">Comedy twist</p>
            </div>
          </button>
          <button
            onClick={() => { handleNextAction('new_version'); onNewStory?.(); }}
            className="relative flex items-center gap-2.5 p-3 rounded-xl bg-emerald-500/10 border-2 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/20 hover:border-emerald-500/60 transition-all text-left group"
            data-testid="next-create-another"
          >
            <RefreshCw className="w-4 h-4 flex-shrink-0 group-hover:rotate-180 transition-transform duration-500" />
            <div>
              <p className="text-xs font-semibold">Create Another</p>
              <p className="text-[10px] text-slate-500">Fresh story</p>
            </div>
            <span className="absolute -top-1.5 -right-1.5 text-[8px] font-bold bg-emerald-500 text-white px-1.5 py-0.5 rounded-full">
              GO
            </span>
          </button>
        </div>
      </div>

      {/* ── Remix Strip (Horizontal Scroll) ── */}
      <div data-testid="remix-strip">
        <p className="text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5 px-1">
          <Sparkles className="w-3 h-3 text-purple-400" />
          Try a different vibe:
        </p>
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {REMIX_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handleRemix(preset)}
              className="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-full bg-slate-800/80 border border-slate-700/50 text-slate-300 hover:bg-slate-700 hover:border-slate-600 hover:text-white transition-all text-xs whitespace-nowrap"
              data-testid={`remix-${preset.id}`}
            >
              <span>{preset.emoji}</span>
              <span>{preset.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Streak / Progress Bar ── */}
      {streak && (
        <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-3" data-testid="streak-bar">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-orange-400" />
              <span className="text-xs font-semibold text-white">
                {streak.today_count} stories today
              </span>
              {streak.streak_days > 1 && (
                <span className="text-[10px] bg-orange-500/20 text-orange-300 px-1.5 py-0.5 rounded-full font-medium">
                  {streak.streak_days}-day streak
                </span>
              )}
            </div>
            {milestone && (
              <span className="text-[10px] text-slate-500">
                <Target className="w-3 h-3 inline mr-0.5" />
                Next: {milestone.target} stories
              </span>
            )}
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          {milestone && (
            <p className="text-[10px] text-slate-500 mt-1.5">
              {milestone.target - streak.today_count} more to go — {milestone.label}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
