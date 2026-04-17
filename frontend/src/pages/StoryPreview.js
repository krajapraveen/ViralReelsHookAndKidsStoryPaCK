import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import BrowserVideoExport from '../components/BrowserVideoExport';
import {
  ArrowLeft, Download, Play, Pause, Image, Mic, FileText,
  Film, Package, Eye, AlertCircle, ChevronRight, ChevronLeft,
  Volume2, VolumeX, Loader2, CheckCircle, ExternalLink, ArrowRight, Zap, Lock, RefreshCw
} from 'lucide-react';
import { SafeImage } from '../components/SafeImage';
import { trackLoop } from '../utils/growthTracker';
import api from '../utils/api';
import EntitledDownloadButton from '../components/EntitledDownloadButton';
import { useMediaEntitlement } from '../contexts/MediaEntitlementContext';
import ShareButtons from '../components/ShareButtons';
import SmartUpgradePrompt from '../components/SmartUpgradePrompt';
import { ProtectedContentContainer as ProtectedContent } from '../components/ProtectedContent';

export default function StoryPreview() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showExport, setShowExport] = useState(false);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [playingAudio, setPlayingAudio] = useState(null);
  const [showContinueOverlay, setShowContinueOverlay] = useState(false);
  const [videoTriggerActive, setVideoTriggerActive] = useState(false);
  const [videoEnded, setVideoEnded] = useState(false);
  const audioRef = useRef(null);
  const videoPlayerRef = useRef(null);

  useEffect(() => {
    fetchPreview();
  }, [jobId]);

  const fetchPreview = async () => {
    try {
      const res = await api.get(`/api/story-engine/preview/${jobId}`);
      if (res.data.success) {
        setPreview(res.data.preview);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  // Engagement tracking helper (fire-and-forget, throttled by backend)
  const trackEvent = useCallback(async (eventType, value = null) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      await api.post(`/api/analytics/track-event/${jobId}`, { event_type: eventType, value });
    } catch {}
  }, [jobId]);

  const handleContinueStory = () => {
    if (!preview) return;
    trackLoop('continue', { story_id: jobId, story_title: preview.title, source_surface: 'story_preview', hook_variant: preview.cliffhanger || '' });
    const lastScene = preview.scenes?.[preview.scenes.length - 1];
    const cliffhanger = preview.cliffhanger || lastScene?.narration_text || '';
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: `[Continuation of "${preview.title}"]\n\n${(preview.story_text || '').slice(0, 500)}...\n\nDirection: Continue with higher stakes and tension. Keep the same characters and world.`,
      timestamp: Date.now(),
      source_tool: 'story-preview',
      remixFrom: {
        tool: 'story-video-studio',
        prompt: preview.story_text || '',
        settings: { animation_style: preview.animation_style, age_group: preview.age_group, voice_preset: preview.voice_preset },
        title: preview.title?.startsWith('From:') ? preview.title : `From: ${preview.title}`,
        parentId: jobId,
        hook_text: cliffhanger,
        characters: preview.characters || [],
      },
    }));
    trackEvent('continue_clicked');
    navigate('/app/story-video-studio');
  };

  const playAudio = (url, sceneIndex) => {
    if (playingAudio === sceneIndex) {
      audioRef.current?.pause();
      setPlayingAudio(null);
      return;
    }
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.play();
    setPlayingAudio(sceneIndex);
    trackEvent('preview_played');
    audio.onended = () => setPlayingAudio(null);
  };

  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause();
    };
  }, []);

  // Video trigger zone: show cliffhanger text in last 2 seconds, CTA on end
  const handleVideoTimeUpdate = useCallback(() => {
    const v = videoPlayerRef.current;
    if (!v || !v.duration) return;
    const remaining = v.duration - v.currentTime;
    if (remaining <= 2.0 && !videoTriggerActive) {
      setVideoTriggerActive(true);
    } else if (remaining > 2.0 && videoTriggerActive) {
      setVideoTriggerActive(false);
    }
  }, [videoTriggerActive]);

  const handleVideoEnded = useCallback(() => {
    setVideoEnded(true);
    setVideoTriggerActive(false);
    trackLoop('watch_complete', { story_id: jobId, story_title: preview?.title, source_surface: 'story_preview' });
    trackEvent('watch_complete');
  }, [jobId, preview, trackEvent]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Preview Not Available</h2>
          <p className="text-slate-400">{error}</p>
          <Link to="/app"><Button variant="outline">Back to Dashboard</Button></Link>
        </div>
      </div>
    );
  }

  if (!preview) return null;

  const currentScene = preview.scenes?.[activeScene];
  const statusColor = preview.status === 'COMPLETED' ? 'text-emerald-400' :
    preview.status === 'PARTIAL' ? 'text-amber-400' :
    preview.status === 'PROCESSING' ? 'text-blue-400' : 'text-red-400';

  const isReady = preview.status === 'COMPLETED' || preview.status === 'PARTIAL';

  return (
    <ProtectedContent className="min-h-screen bg-gradient-to-b from-slate-950 via-[#0a0f1f] to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-4 min-w-0 pr-24 sm:pr-32">
            <Link to="/app">
              <Button variant="ghost" size="icon" className="text-white flex-shrink-0">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-base sm:text-xl font-bold text-white truncate" data-testid="preview-title">
                {preview.title || 'Story Preview'}
              </h1>
              <div className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm">
                <span className={statusColor} data-testid="preview-status">
                  {preview.status === 'COMPLETED' ? 'Ready' : preview.status === 'PARTIAL' ? 'Assets Available' : preview.status}
                </span>
                <span className="text-slate-500">
                  {preview.scenes_with_images}/{preview.total_scenes} img
                </span>
                <span className="text-slate-500">
                  {preview.scenes_with_audio}/{preview.total_scenes} audio
                </span>
              </div>
            </div>
          </div>

          {/* Actions — Continue is PRIMARY */}
          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <Button
              onClick={handleContinueStory}
              className="bg-gradient-to-r from-violet-600 to-rose-600 hover:opacity-90 text-white font-bold shadow-lg shadow-violet-500/20 text-xs sm:text-sm h-8 sm:h-10 px-2.5 sm:px-4"
              size="sm"
              data-testid="header-continue-btn"
            >
              <Play className="w-3.5 h-3.5 sm:mr-2" />
              <span className="hidden sm:inline">What Happens Next?</span>
            </Button>
            {preview.scenes?.some(s => s.image_url) && (
              <Button
                onClick={() => { setShowExport(!showExport); if (!showExport) trackEvent('export_started'); }}
                variant="outline"
                size="sm"
                className={`border-slate-600 text-slate-300 hover:bg-slate-800 hidden sm:flex ${showExport ? 'bg-slate-800' : ''}`}
                data-testid="browser-export-toggle-btn"
              >
                <Film className="w-4 h-4 sm:mr-2" />
                <span className="hidden md:inline">{showExport ? 'Hide Export' : 'Export'}</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-8 vs-safe-bottom">
        {/* Browser Video Export Panel */}
        {showExport && (
          <div className="mb-6 animate-in fade-in slide-in-from-top-2">
            <BrowserVideoExport
              scenes={preview.scenes || []}
              title={preview.title}
              jobId={jobId}
              onClose={() => setShowExport(false)}
            />
          </div>
        )}

        {/* Story Continue Hook Banner */}
        {isReady && (
          <div className="mb-6 p-5 bg-gradient-to-r from-violet-500/10 to-rose-500/10 border border-violet-500/20 rounded-xl" data-testid="ready-banner">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-violet-500/20 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-violet-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-white font-bold text-lg">This story isn't finished...</h3>
                <p className="text-slate-400 text-sm mt-1">
                  {preview.cliffhanger
                    ? `"${preview.cliffhanger.slice(0, 200)}${preview.cliffhanger.length > 200 ? '...' : ''}"`
                    : 'The best stories leave you wanting more. What happens next is up to you.'
                  }
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={handleContinueStory}
                    className="inline-flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 shadow-lg shadow-violet-500/20"
                    data-testid="banner-continue-btn"
                  >
                    <Play className="w-4 h-4" /> Continue This Story <ArrowRight className="w-4 h-4" />
                  </button>
                  <span className="text-xs text-slate-500">Your prompt will be pre-filled</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Viewer */}
          <div className="lg:col-span-2 space-y-4">
            {/* Immersive Video Player — CTA synchronized to tension peak */}
            {preview.final_video_url && (
              <div className="relative rounded-xl overflow-hidden border border-slate-700/50 bg-black" data-testid="video-player-section" style={{ touchAction: 'manipulation' }}>
                <div className="relative aspect-video">
                  <video
                    ref={videoPlayerRef}
                    src={preview.final_video_url}
                    controls
                    controlsList="nodownload noplaybackrate"
                    disablePictureInPicture
                    playsInline
                    className="w-full h-full object-contain"
                    style={{ maxWidth: '100%', maxHeight: '100%', touchAction: 'manipulation' }}
                    onTimeUpdate={handleVideoTimeUpdate}
                    onEnded={handleVideoEnded}
                    data-testid="story-video-player"
                  />
                  {/* Trigger zone: cliffhanger text fades in during last 2s */}
                  {videoTriggerActive && !videoEnded && (preview.trigger_text || preview.cliffhanger) && (
                    <div className="absolute inset-0 pointer-events-none flex items-end justify-center pb-16 z-10"
                      style={{ animation: 'fadeUp .5s ease-out' }} data-testid="video-trigger-text">
                      <p className="text-white text-lg sm:text-xl font-bold italic text-center px-6 drop-shadow-2xl"
                        style={{ textShadow: '0 2px 20px rgba(0,0,0,.8)' }}>
                        {preview.trigger_text || preview.cliffhanger}
                      </p>
                    </div>
                  )}
                  {/* CTA overlay: appears instantly on video end — zero delay */}
                  {videoEnded && (
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-black/90 to-black/60 flex flex-col items-center justify-center z-20"
                      style={{ animation: 'fadeUp .3s ease-out' }} data-testid="video-end-cta">
                      <p className="text-xs font-black text-violet-400 uppercase tracking-[0.2em] mb-2">The story isn't over</p>
                      {preview.cliffhanger && (
                        <p className="text-sm sm:text-base text-slate-200 italic text-center px-8 mb-1 leading-relaxed max-w-lg">
                          "{preview.cliffhanger}"
                        </p>
                      )}
                      <p className="text-sm font-bold text-amber-400 mb-5">What happens next?</p>
                      <button
                        onClick={handleContinueStory}
                        className="inline-flex items-center gap-2 h-12 px-8 rounded-xl text-white font-bold text-sm shadow-lg shadow-violet-500/30 hover:scale-[1.03] active:scale-[0.97] transition-transform"
                        style={{ background: 'linear-gradient(135deg, #6C5CE7, #00C2FF)', boxShadow: '0 0 30px rgba(108,92,231,.4)' }}
                        data-testid="video-end-continue-btn"
                      >
                        <Play className="w-4 h-4 fill-white" /> Continue This Story <ArrowRight className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setVideoEnded(false); if (videoPlayerRef.current) { videoPlayerRef.current.currentTime = 0; videoPlayerRef.current.play(); } }}
                        className="mt-3 text-xs text-white/40 hover:text-white/70 transition-colors"
                        data-testid="video-replay-btn"
                      >
                        Replay video
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Scene Image Viewer */}
            {currentScene && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="scene-viewer">
                {/* Scene Image */}
                <div className="relative aspect-video bg-slate-900 flex items-center justify-center">
                  <SafeImage
                    src={currentScene.image_url}
                    alt={currentScene.title || `Scene ${activeScene + 1}`}
                    aspectRatio="16/9"
                    titleOverlay={currentScene.title}
                    className="w-full h-full"
                    data-testid={`scene-image-${activeScene}`}
                  />

                  {/* Scene Navigation Overlay */}
                  <div className="absolute inset-y-0 left-0 flex items-center pl-2">
                    {activeScene > 0 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setActiveScene(activeScene - 1)}
                        className="bg-black/50 hover:bg-black/70 text-white rounded-full"
                        data-testid="prev-scene-btn"
                      >
                        <ChevronLeft className="w-6 h-6" />
                      </Button>
                    )}
                  </div>
                  <div className="absolute inset-y-0 right-0 flex items-center pr-2">
                    {activeScene < (preview.scenes?.length || 0) - 1 ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setActiveScene(activeScene + 1)}
                        className="bg-black/50 hover:bg-black/70 text-white rounded-full"
                        data-testid="next-scene-btn"
                      >
                        <ChevronRight className="w-6 h-6" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowContinueOverlay(true)}
                        className="bg-violet-600/80 hover:bg-violet-600 text-white rounded-full animate-pulse"
                        data-testid="last-scene-continue-btn"
                      >
                        <ArrowRight className="w-6 h-6" />
                      </Button>
                    )}
                  </div>

                  {/* Continue Overlay — triggers on last scene */}
                  {showContinueOverlay && activeScene >= (preview.scenes?.length || 1) - 1 && (
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-black/90 to-black/70 backdrop-blur-sm flex flex-col items-center justify-center z-20 animate-in fade-in duration-500" data-testid="scene-continue-overlay">
                      <p className="text-xs font-bold text-violet-400 uppercase tracking-widest mb-3">This wasn't the end...</p>
                      {preview.cliffhanger && (
                        <p className="text-sm sm:text-base text-slate-200 italic text-center px-6 mb-2 leading-relaxed max-w-md">
                          "{preview.cliffhanger.length > 180 ? '...' + preview.cliffhanger.slice(-180) : preview.cliffhanger}"
                        </p>
                      )}
                      <p className="text-sm font-bold text-amber-400 mb-5">What happens next?</p>
                      <div className="flex gap-3">
                        <button
                          onClick={handleContinueStory}
                          className="inline-flex items-center gap-2 h-11 px-7 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 shadow-lg shadow-violet-500/30"
                          data-testid="overlay-continue-story-btn"
                        >
                          <Play className="w-4 h-4" /> Continue This Story <ArrowRight className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setShowContinueOverlay(false)}
                          className="inline-flex items-center gap-2 h-11 px-5 rounded-xl border border-white/20 text-white/60 text-sm hover:bg-white/5"
                          data-testid="overlay-dismiss-btn"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Scene Counter */}
                  <div className="absolute bottom-3 right-3 px-3 py-1 bg-black/60 rounded-full text-white text-sm">
                    {activeScene + 1} / {preview.scenes?.length || 0}
                  </div>
                </div>

                {/* Scene Info */}
                <div className="p-3 sm:p-5 space-y-2 sm:space-y-3">
                  <div className="flex items-start sm:items-center justify-between gap-2">
                    <h3 className="text-sm sm:text-lg font-semibold text-white" data-testid="scene-title">
                      Scene {currentScene.scene_number}: {currentScene.title}
                    </h3>
                    {currentScene.audio_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => playAudio(currentScene.audio_url, activeScene)}
                        className={`border-purple-500/50 ${playingAudio === activeScene ? 'bg-purple-500/20 text-purple-300' : 'text-purple-400'}`}
                        data-testid="play-audio-btn"
                      >
                        {playingAudio === activeScene ? (
                          <><Pause className="w-4 h-4 mr-1" /> Playing</>
                        ) : (
                          <><Play className="w-4 h-4 mr-1" /> Listen</>
                        )}
                      </Button>
                    )}
                  </div>

                  <p className="text-sm sm:text-base text-slate-300 leading-relaxed" data-testid="scene-narration">
                    {currentScene.narration_text}
                  </p>

                  {/* Asset indicators */}
                  <div className="flex items-center gap-4 pt-2 border-t border-slate-700/50">
                    <span className={`flex items-center gap-1 text-xs ${currentScene.has_image ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Image className="w-3.5 h-3.5" />
                      {currentScene.has_image ? 'Image ready' : 'No image'}
                    </span>
                    <span className={`flex items-center gap-1 text-xs ${currentScene.has_audio ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Mic className="w-3.5 h-3.5" />
                      {currentScene.has_audio ? `Audio (${currentScene.duration?.toFixed(1)}s)` : 'No audio'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Story Text */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5">
              <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                <FileText className="w-5 h-5 text-purple-400" />
                Story Text
              </h3>
              <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto" data-testid="story-text">
                {preview.story_text}
              </p>
            </div>
          </div>

          {/* Scene Thumbnails Sidebar */}
          <div className="space-y-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-400" />
              Scenes ({preview.total_scenes})
            </h3>

            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {preview.scenes?.map((scene, idx) => (
                <button
                  key={scene.scene_number}
                  onClick={() => setActiveScene(idx)}
                  className={`w-full text-left rounded-lg border transition-all ${
                    idx === activeScene
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-slate-700/50 bg-slate-800/30 hover:border-slate-600'
                  }`}
                  data-testid={`scene-thumb-${idx}`}
                >
                  <div className="flex gap-3 p-3">
                    {/* Mini thumbnail */}
                    <div className="w-20 h-14 rounded bg-slate-900 flex-shrink-0 overflow-hidden">
                      <SafeImage
                        src={scene.image_url}
                        alt={scene.title || `Scene ${idx + 1}`}
                        aspectRatio="16/10"
                        titleOverlay={scene.title}
                        data-testid={`scene-list-thumb-${idx}`}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate">
                        {scene.scene_number}. {scene.title}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                        {scene.narration_text?.slice(0, 80)}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {scene.has_image && <CheckCircle className="w-3 h-3 text-emerald-400" />}
                        {scene.has_audio && <Volume2 className="w-3 h-3 text-blue-400" />}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {/* Continue Story — PRIMARY ACTION */}
            <div className="bg-gradient-to-br from-violet-500/10 to-rose-500/10 rounded-xl border border-violet-500/20 p-4 space-y-3">
              <h4 className="text-white font-bold text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-violet-400" />
                What Happens Next?
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                {preview.cliffhanger
                  ? `"${preview.cliffhanger.slice(0, 120)}..."`
                  : 'Continue this story — your studio will be pre-filled.'
                }
              </p>
              <button
                onClick={handleContinueStory}
                className="w-full h-10 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-sm hover:opacity-90 flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20"
                data-testid="sidebar-continue-btn"
              >
                <Play className="w-4 h-4" /> Continue Story
              </button>
            </div>

            {/* Downloads (entitlement-gated) */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
              <h4 className="text-slate-400 font-medium text-sm">Downloads</h4>
              {(preview.final_video_url || preview.fallback_video_url || preview.story_pack_url) ? (
                <EntitledDownloadButton
                  assetId={jobId}
                  label="Download Video"
                  upgradeLabel="Upgrade to Download"
                  className="w-full"
                  data-testid="preview-download-btn"
                />
              ) : preview.status === 'PROCESSING' ? (
                <div className="flex items-center gap-2 text-sm text-blue-400" data-testid="download-processing">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Video is still processing...</span>
                </div>
              ) : (
                <div className="space-y-2" data-testid="download-not-available">
                  <p className="text-slate-500 text-xs">This video is no longer available for download.</p>
                  <p className="text-slate-600 text-[11px]">The file may have expired from temporary storage. You can regenerate it.</p>
                  <button
                    onClick={() => {
                      navigate('/app/story-video-studio', {
                        state: {
                          prefill: { title: preview.title, prompt: preview.story_text },
                          freshSession: true,
                        },
                      });
                    }}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-violet-600/20 border border-violet-500/30 rounded-lg text-violet-300 text-xs font-medium hover:bg-violet-600/30 transition-colors"
                    data-testid="regenerate-btn"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Regenerate Video
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Share + Upgrade prompts */}
      {preview.status === 'COMPLETED' && (
        <>
          <div className="max-w-7xl mx-auto px-4 pb-4">
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4" data-testid="preview-share-section">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Share this creation</p>
              <ShareButtons url={`${window.location.origin}/v/${preview.slug || jobId}`} title={preview.title} />
            </div>
          </div>
          <SmartUpgradePrompt trigger="generation_complete" />
        </>
      )}
    </ProtectedContent>
  );
}
