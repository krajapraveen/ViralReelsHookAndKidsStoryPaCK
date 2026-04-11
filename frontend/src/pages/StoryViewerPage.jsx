import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Play, Pause, GitBranch, Share2, BookOpen,
  ChevronRight, Swords, Eye, Volume2, VolumeX
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { SafeImage } from '../components/SafeImage';
import { toast } from 'sonner';
import api from '../utils/api';
import ContinuationModal from '../components/ContinuationModal';

/**
 * StoryViewerPage — Consumption-first story experience.
 * Route: /app/story-viewer/:jobId
 *
 * This is the "Netflix mode" — watch/read the story, navigate episodes,
 * then optionally remix or continue.
 */
export default function StoryViewerPage() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [continuationMode, setContinuationMode] = useState(null);
  const [siblings, setSiblings] = useState([]);
  const videoRef = useRef(null);

  const resolvedJobId = jobId || searchParams.get('projectId');

  useEffect(() => {
    if (!resolvedJobId) return;
    (async () => {
      try {
        const res = await api.get(`/api/stories/viewer/${resolvedJobId}`);
        if (res.data?.success) {
          setJob(res.data.job);
          // Fetch siblings (other episodes in the chain)
          if (res.data.job.story_chain_id || res.data.job.root_story_id) {
            const chainId = res.data.job.root_story_id || res.data.job.story_chain_id;
            try {
              const chainRes = await api.get(`/api/stories/${chainId}/chain`);
              if (chainRes.data?.success) {
                setSiblings(chainRes.data.episodes || []);
              }
            } catch {}
          }
          // Track view
          api.post('/api/stories/increment-metric', {
            job_id: resolvedJobId, metric: 'views'
          }).catch(() => {});
        }
      } catch {
        toast.error('Story not found');
        navigate('/app');
      } finally {
        setLoading(false);
      }
    })();
  }, [resolvedJobId, navigate]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setPlaying(!playing);
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !muted;
    setMuted(!muted);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" data-testid="viewer-loading">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (!job) return null;

  const title = job.title || 'Untitled';
  const storyText = job.story_text || '';
  const outputUrl = job.output_url;
  const thumbnailUrl = job.thumbnail_url;
  const sceneProgress = job.scene_progress || [];
  const hasVideo = !!outputUrl;
  const chainDepth = job.chain_depth || 0;
  const continuationType = job.continuation_type || 'original';
  const currentEpIndex = siblings.findIndex(s => s.job_id === resolvedJobId);
  const nextEpisode = currentEpIndex >= 0 && currentEpIndex < siblings.length - 1 ? siblings[currentEpIndex + 1] : null;
  const prevEpisode = currentEpIndex > 0 ? siblings[currentEpIndex - 1] : null;

  return (
    <div className="min-h-screen bg-slate-950" data-testid="story-viewer">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-white/40 hover:text-white" data-testid="viewer-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold text-white truncate" data-testid="viewer-title">{title}</h1>
            {chainDepth > 0 && (
              <p className="text-xs text-white/40">
                {continuationType === 'episode' ? `Episode ${chainDepth + 1}` : 'Branch'}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setContinuationMode('episode')}
              className="border-violet-500/20 text-violet-400 hover:bg-violet-500/10 text-xs"
              data-testid="viewer-next-episode-btn"
            >
              <Play className="w-3.5 h-3.5 mr-1" /> Next Episode
            </Button>
            <Button
              size="sm"
              onClick={() => setContinuationMode('branch')}
              className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
              data-testid="viewer-remix-btn"
            >
              <GitBranch className="w-3.5 h-3.5 mr-1" /> Remix
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        {/* ═══ VIDEO PLAYER ═══ */}
        {hasVideo ? (
          <div className="relative bg-black aspect-video" data-testid="video-player-container">
            <video
              ref={videoRef}
              src={outputUrl}
              poster={thumbnailUrl}
              className="w-full h-full object-contain"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => {
                setPlaying(false);
                // Auto-advance hint
                if (nextEpisode) {
                  toast.info(
                    <div className="flex items-center gap-2">
                      <span>Next: {nextEpisode.title}</span>
                      <button
                        className="text-violet-400 font-bold text-xs underline"
                        onClick={() => navigate(`/app/story-viewer/${nextEpisode.job_id}`)}
                      >
                        Play
                      </button>
                    </div>,
                    { duration: 8000 }
                  );
                }
              }}
              playsInline
              data-testid="video-element"
            />
            {/* Play overlay */}
            {!playing && (
              <button
                onClick={togglePlay}
                className="absolute inset-0 flex items-center justify-center bg-black/20 transition-opacity"
                data-testid="play-overlay"
              >
                <div className="w-16 h-16 rounded-full bg-white/15 backdrop-blur-md border border-white/20 flex items-center justify-center hover:bg-white/25 transition-colors">
                  <Play className="w-7 h-7 text-white fill-white ml-1" />
                </div>
              </button>
            )}
            {/* Controls */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4 flex items-center justify-between">
              <button onClick={togglePlay} className="text-white/80 hover:text-white" data-testid="play-pause-btn">
                {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 fill-white" />}
              </button>
              <button onClick={toggleMute} className="text-white/80 hover:text-white" data-testid="mute-btn">
                {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
            </div>
          </div>
        ) : thumbnailUrl ? (
          <div className="relative aspect-video bg-slate-900 flex items-center justify-center" data-testid="thumbnail-container">
            <SafeImage src={thumbnailUrl} alt={title} className="w-full h-full object-cover" />
          </div>
        ) : null}

        {/* ═══ CONTENT AREA ═══ */}
        <div className="px-4 py-6 space-y-6">

          {/* Title + Meta */}
          <div data-testid="story-meta">
            <h2 className="text-2xl font-black text-white mb-2">{title}</h2>
            <div className="flex items-center gap-3 text-xs text-white/40">
              {job.creator_name && <span className="text-white/60">by {job.creator_name}</span>}
              {job.animation_style && <span className="capitalize">{job.animation_style.replace(/_/g, ' ')}</span>}
              {job.total_views > 0 && <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {job.total_views} views</span>}
              {(job.battle_score || 0) > 0 && <span className="text-amber-400 font-semibold">{job.battle_score?.toFixed(1)} pts</span>}
            </div>
          </div>

          {/* Attribution — derivative lineage */}
          {job.derivative_label && job.source_story_title && (
            <div className="flex items-center gap-2 text-xs bg-violet-500/5 border border-violet-500/10 rounded-lg px-3 py-2"
              data-testid="attribution-badge">
              <GitBranch className="w-3.5 h-3.5 text-violet-400" />
              <span className="text-violet-300">
                {job.derivative_label === 'continued_from' && 'Continued from'}
                {job.derivative_label === 'remixed_from' && 'Remixed from'}
                {job.derivative_label === 'styled_from' && 'Styled from'}
                {job.derivative_label === 'converted_from' && 'Converted from'}
                {' '}
                <span className="font-semibold text-violet-200">"{job.source_story_title}"</span>
                {job.source_creator_name && (
                  <span className="text-white/40"> by {job.source_creator_name}</span>
                )}
              </span>
            </div>
          )}

          {/* Story Text — Readable format */}
          {storyText && (
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-5" data-testid="story-text-section">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-violet-400" />
                <span className="text-xs font-bold text-white/40 uppercase tracking-wider">Story</span>
              </div>
              <p className="text-sm text-white/70 leading-relaxed whitespace-pre-line">{storyText}</p>
            </div>
          )}

          {/* Scene Gallery */}
          {sceneProgress.length > 0 && sceneProgress.some(s => s.image_url) && (
            <div data-testid="scene-gallery">
              <h3 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3">Scenes</h3>
              <div className="grid grid-cols-3 gap-2">
                {sceneProgress.filter(s => s.image_url).map((scene, i) => (
                  <div key={i} className="aspect-video rounded-lg overflow-hidden bg-slate-800">
                    <SafeImage src={scene.image_url} alt={scene.title || `Scene ${i + 1}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ═══ EPISODE NAVIGATION ═══ */}
          {siblings.length > 1 && (
            <div data-testid="episode-navigation">
              <h3 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3">Episodes</h3>
              <div className="space-y-2">
                {siblings.map((ep, i) => {
                  const isCurrent = ep.job_id === resolvedJobId;
                  return (
                    <button
                      key={ep.job_id}
                      onClick={() => !isCurrent && navigate(`/app/story-viewer/${ep.job_id}`)}
                      className={`w-full rounded-lg border p-3 flex items-center gap-3 text-left transition-all ${
                        isCurrent
                          ? 'border-violet-500/30 bg-violet-500/[0.08]'
                          : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'
                      }`}
                      data-testid={`episode-nav-${i}`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        isCurrent ? 'bg-violet-500/20' : 'bg-white/5'
                      }`}>
                        {isCurrent
                          ? <Play className="w-4 h-4 text-violet-400 fill-violet-400" />
                          : <span className="text-xs font-bold text-white/40">{i + 1}</span>
                        }
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-semibold truncate ${isCurrent ? 'text-violet-300' : 'text-white/70'}`}>
                          {ep.title || 'Untitled'}
                        </p>
                        <p className="text-[10px] text-white/30">
                          {ep.continuation_type === 'original' ? 'Origin' : `Episode ${ep.chain_depth || i}`}
                        </p>
                      </div>
                      {!isCurrent && <ChevronRight className="w-4 h-4 text-white/20 flex-shrink-0" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* ═══ ACTION BUTTONS ═══ */}
          <div className="space-y-3 pt-2" data-testid="viewer-actions">
            {/* Primary: Next Episode */}
            {nextEpisode && (
              <button
                onClick={() => navigate(`/app/story-viewer/${nextEpisode.job_id}`)}
                className="w-full group relative overflow-hidden rounded-xl p-4 text-left transition-all hover:scale-[1.01]"
                data-testid="next-episode-cta"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-violet-600 to-blue-600 opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10 flex items-center gap-3">
                  <Play className="w-5 h-5 text-white fill-white" />
                  <div className="flex-1">
                    <span className="text-sm font-bold text-white block">Next: {nextEpisode.title}</span>
                    <span className="text-xs text-white/60">Continue watching</span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-white/40 group-hover:text-white transition-colors" />
                </div>
              </button>
            )}

            {/* Secondary: Continue creating */}
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={() => setContinuationMode('episode')}
                variant="outline"
                className="w-full border-violet-500/20 text-violet-400 hover:bg-violet-500/10"
                data-testid="create-episode-btn"
              >
                <Play className="w-4 h-4 mr-2" /> Create Episode
              </Button>
              <Button
                onClick={() => setContinuationMode('branch')}
                variant="outline"
                className="w-full border-rose-500/20 text-rose-400 hover:bg-rose-500/10"
                data-testid="create-branch-btn"
              >
                <GitBranch className="w-4 h-4 mr-2" /> Fork / Remix
              </Button>
            </div>

            {/* Battle link */}
            {(job.total_children || 0) > 0 && (
              <Button
                onClick={() => navigate(`/app/story-battle/${job.root_story_id || job.story_chain_id || resolvedJobId}`)}
                variant="outline"
                className="w-full border-amber-500/20 text-amber-400 hover:bg-amber-500/10"
                data-testid="view-battle-from-viewer"
              >
                <Swords className="w-4 h-4 mr-2" /> View Story Battle
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Continuation Modal */}
      <ContinuationModal
        isOpen={!!continuationMode}
        onClose={() => setContinuationMode(null)}
        mode={continuationMode || 'episode'}
        parentJob={{
          job_id: resolvedJobId,
          title: title,
          story_text: storyText,
          animation_style: job.animation_style,
          age_group: job.age_group,
          voice_preset: job.voice_preset,
          quality_mode: job.quality_mode,
          episode_number: job.episode_number,
        }}
        onJobCreated={(data) => {
          if (data?.job_id) {
            navigate(`/app/story-video-pipeline?projectId=${data.job_id}`);
          }
        }}
      />
    </div>
  );
}
