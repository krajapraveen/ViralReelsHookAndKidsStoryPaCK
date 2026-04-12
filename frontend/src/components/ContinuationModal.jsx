import React, { useState } from 'react';
import { Play, GitBranch, ArrowRight, Loader2, BookOpen, Swords, X } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * ContinuationModal — Pre-generation confirmation for Episode vs Branch.
 * Episode: Linear continuation of the same storyline.
 * Branch: Competing fork that rivals the parent for #1 ranking.
 */
export default function ContinuationModal({
  isOpen,
  onClose,
  mode = 'episode', // 'episode' | 'branch'
  parentJob,
  onJobCreated,
  isWar = false, // if true, uses /api/war/enter instead
  preset = null, // { title, instruction } — pre-fills the form
}) {
  const [title, setTitle] = useState('');
  const [storyText, setStoryText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Reset form when preset changes
  React.useEffect(() => {
    if (preset) {
      setTitle(preset.title || '');
      setStoryText(preset.instruction || '');
    } else {
      setTitle('');
      setStoryText('');
    }
  }, [preset]);

  if (!isOpen || !parentJob) return null;

  const parentTitle = parentJob.title || 'Untitled';
  const parentStory = parentJob.story_text || '';
  const isEpisode = mode === 'episode';

  const defaultTitle = isEpisode
    ? `${parentTitle} — Episode ${(parentJob.episode_number || 1) + 1}`
    : `${parentTitle} — My Version`;

  const placeholder = isEpisode
    ? `Continue the story from where "${parentTitle}" left off. What happens next? Keep the same characters, world, and tone...`
    : `Create your own version of "${parentTitle}". Take the story in a different direction. Surprise everyone...`;

  const handleSubmit = async () => {
    const finalTitle = title.trim() || defaultTitle;
    const finalStory = storyText.trim();

    if (finalStory.length < 50) {
      toast.error('Story must be at least 50 characters');
      return;
    }

    setSubmitting(true);
    try {
      let endpoint;
      let payload;

      if (isWar) {
        endpoint = '/api/war/enter';
        payload = {
          title: finalTitle,
          story_text: finalStory,
          animation_style: parentJob.animation_style || 'cartoon_2d',
          voice_preset: parentJob.voice_preset || 'narrator_warm',
          quality_mode: parentJob.quality_mode || 'balanced',
        };
      } else {
        endpoint = isEpisode ? '/api/stories/continue-episode' : '/api/stories/continue-branch';
        payload = {
          parent_job_id: parentJob.job_id,
          title: finalTitle,
          story_text: finalStory,
          animation_style: parentJob.animation_style || 'cartoon_2d',
          age_group: parentJob.age_group || 'kids_5_8',
          voice_preset: parentJob.voice_preset || 'narrator_warm',
          quality_mode: parentJob.quality_mode || 'balanced',
        };
      }

      const res = await api.post(endpoint, payload);

      if (res.data?.success) {
        // Track branch/episode creation
        try {
          api.post('/api/funnel/track', {
            event: 'cta_clicked',
            data: {
              type: isEpisode ? 'continue_episode' : 'launch_branch',
              parent_job_id: parentJob.job_id,
              new_job_id: res.data.job_id,
              source: isWar ? 'war_entry' : 'continuation_modal',
            },
          }).catch(() => {});
        } catch {}

        if (!isEpisode) {
          toast.success('You\'ve entered the battle! Your version is generating...');
        } else {
          toast.success('Episode generation started!');
        }
        onJobCreated?.(res.data);
        onClose();
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to create. Try again.';
      toast.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="continuation-modal">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        data-testid={`continuation-modal-${mode}`}>
        {/* Header */}
        <div className={`px-6 pt-6 pb-4 ${isEpisode
          ? 'bg-gradient-to-r from-violet-600/20 to-blue-600/20'
          : 'bg-gradient-to-r from-rose-600/20 to-orange-600/20'
        }`}>
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
            data-testid="close-continuation-modal"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isEpisode
              ? 'bg-violet-500/20' : 'bg-rose-500/20'
            }`}>
              {isEpisode
                ? <Play className="w-5 h-5 text-violet-400" />
                : <GitBranch className="w-5 h-5 text-rose-400" />
              }
            </div>
            <div>
              <h2 className="text-lg font-bold text-white" data-testid="continuation-modal-title">
                {isEpisode ? 'Continue Next Episode' : 'Fork This Story'}
              </h2>
              <p className="text-xs text-white/50">
                {isEpisode
                  ? 'Extend the timeline — same characters, next chapter'
                  : 'Create a competing version — battle for #1 spot'
                }
              </p>
            </div>
          </div>

          {/* Context: parent story */}
          <div className="bg-black/20 rounded-lg p-3 mt-2">
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="w-3.5 h-3.5 text-white/40" />
              <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">
                {isEpisode ? 'Continuing from' : 'Competing with'}
              </span>
            </div>
            <p className="text-sm text-white/70 font-medium">{parentTitle}</p>
            {parentStory && (
              <p className="text-xs text-white/30 mt-1 italic line-clamp-2">
                "...{parentStory.slice(-150)}"
              </p>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Title */}
          <div>
            <label className="text-xs font-semibold text-white/60 mb-1.5 block">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={defaultTitle}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-white/30 focus:border-white/20 focus:outline-none"
              data-testid="continuation-title-input"
            />
          </div>

          {/* Story prompt */}
          <div>
            <label className="text-xs font-semibold text-white/60 mb-1.5 block">
              {isEpisode ? 'What happens next?' : 'Your competing version'}
            </label>
            <Textarea
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              placeholder={placeholder}
              rows={5}
              className="bg-white/5 border-white/10 text-white placeholder-white/30 resize-none focus:border-white/20"
              data-testid="continuation-story-input"
            />
            <p className="text-[10px] text-white/30 mt-1">
              {storyText.length}/10000 characters (min 50)
            </p>
          </div>

          {/* Mode-specific callout */}
          {!isEpisode && (
            <div className="flex items-start gap-2 bg-rose-500/5 border border-rose-500/10 rounded-lg p-3"
              data-testid="branch-competition-callout">
              <Swords className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-rose-300/80">
                Your version will compete head-to-head with the original.
                Views, shares, and new continuations determine the winner.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex gap-3">
          <Button
            variant="outline"
            onClick={onClose}
            className="flex-1 border-white/10 text-white/50 hover:text-white"
            data-testid="cancel-continuation-btn"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || storyText.trim().length < 50}
            className={`flex-1 font-bold ${isEpisode
              ? 'bg-violet-600 hover:bg-violet-700 text-white'
              : 'bg-rose-600 hover:bg-rose-700 text-white'
            }`}
            data-testid="submit-continuation-btn"
          >
            {submitting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> {isEpisode ? 'Creating...' : 'Entering battle...'}</>
            ) : (
              <>{isEpisode ? 'Start Episode' : 'Launch Branch'} <ArrowRight className="w-4 h-4 ml-2" /></>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
