import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Play, Pause, Image, Mic, Film, Package, FileText, Sparkles,
  Download, ChevronLeft, ChevronRight, Bell, CheckCircle,
  Loader2, Volume2, Eye, Clock, Zap, SkipForward, Shield
} from 'lucide-react';
import { toast } from 'sonner';
import { SafeImage } from '../components/SafeImage';
import api from '../utils/api';

// Web Preview Player — plays scene images as slideshow with synced audio
function PreviewPlayer({ scenes, autoPlay = false }) {
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const audioRef = useRef(null);
  const timerRef = useRef(null);

  const scene = scenes[currentScene];
  const hasAudio = scene?.audio_url;
  const hasImage = scene?.image_url;

  const playScene = useCallback((idx) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    clearInterval(timerRef.current);

    const s = scenes[idx];
    if (!s) return;
    setCurrentScene(idx);

    if (s.audio_url) {
      const audio = new Audio(s.audio_url);
      audioRef.current = audio;
      
      audio.onended = () => {
        setAudioProgress(0);
        if (idx < scenes.length - 1) {
          playScene(idx + 1);
        } else {
          setIsPlaying(false);
        }
      };
      
      audio.ontimeupdate = () => {
        if (audio.duration) {
          setAudioProgress((audio.currentTime / audio.duration) * 100);
        }
      };

      audio.play().catch(() => {});
      setIsPlaying(true);
    }
  }, [scenes]);

  const togglePlay = () => {
    if (isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
    } else {
      playScene(currentScene);
    }
  };

  const nextScene = () => {
    if (currentScene < scenes.length - 1) {
      playScene(currentScene + 1);
    }
  };

  const prevScene = () => {
    if (currentScene > 0) {
      playScene(currentScene - 1);
    }
  };

  useEffect(() => {
    if (autoPlay && scenes.length > 0 && scenes[0].image_url && scenes[0].audio_url) {
      playScene(0);
    }
  }, [autoPlay, scenes, playScene]);

  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause();
      clearInterval(timerRef.current);
    };
  }, []);

  if (!scenes.length) return null;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="preview-player">
      {/* Image Display */}
      <div className="relative aspect-video bg-slate-900 flex items-center justify-center">
        {hasImage ? (
          <SafeImage src={scene.image_url} alt={scene.title} aspectRatio="16/9" titleOverlay={scene.title} />
        ) : (
          <div className="text-center text-slate-500">
            <Image className="w-12 h-12 mx-auto mb-2 opacity-40" />
            <p className="text-sm">Generating image...</p>
          </div>
        )}

        {/* Scene counter */}
        <div className="absolute top-3 right-3 px-3 py-1.5 bg-black/60 backdrop-blur-sm rounded-full text-white text-xs font-medium">
          {currentScene + 1} / {scenes.length}
        </div>

        {/* Playing indicator */}
        {isPlaying && (
          <div className="absolute top-3 left-3 flex items-center gap-1.5 px-3 py-1.5 bg-purple-600/80 backdrop-blur-sm rounded-full text-white text-xs">
            <Volume2 className="w-3 h-3 animate-pulse" /> Playing
          </div>
        )}
      </div>

      {/* Audio progress */}
      <div className="h-1 bg-slate-700">
        <div className="h-full bg-purple-500 transition-all duration-200" style={{ width: `${audioProgress}%` }} />
      </div>

      {/* Controls */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost" size="icon"
            onClick={prevScene}
            disabled={currentScene === 0}
            className="text-white disabled:text-slate-600"
            data-testid="player-prev"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>

          <Button
            onClick={togglePlay}
            disabled={!hasAudio}
            className={`rounded-full w-10 h-10 ${isPlaying ? 'bg-purple-600' : 'bg-white/10'}`}
            data-testid="player-play"
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </Button>

          <Button
            variant="ghost" size="icon"
            onClick={nextScene}
            disabled={currentScene >= scenes.length - 1}
            className="text-white disabled:text-slate-600"
            data-testid="player-next"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        <div className="text-right min-w-0 flex-1 pl-4">
          <p className="text-sm font-medium text-white truncate">{scene?.title || `Scene ${currentScene + 1}`}</p>
          <p className="text-xs text-slate-400 truncate">{scene?.narration_text?.slice(0, 60)}...</p>
        </div>
      </div>
    </div>
  );
}

// Scene Card — appears progressively as scenes are generated
function SceneCard({ scene, index, total }) {
  const hasImage = !!scene.image_url;
  const hasAudio = !!scene.audio_url;

  return (
    <div
      className="flex gap-3 p-3 rounded-lg border border-slate-700/50 bg-slate-800/30 animate-in fade-in slide-in-from-bottom-2"
      style={{ animationDelay: `${index * 100}ms` }}
      data-testid={`progressive-scene-${index}`}
    >
      {/* Thumbnail / placeholder */}
      <div className="w-24 h-16 rounded bg-slate-900 flex-shrink-0 overflow-hidden">
        {hasImage ? (
          <SafeImage src={scene.image_url} alt={scene.title || `Scene ${scene.scene_number}`} aspectRatio="16/10" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Loader2 className="w-4 h-4 text-slate-600 animate-spin" />
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-white truncate">
            {scene.scene_number}. {scene.title || `Scene ${scene.scene_number}`}
          </p>
          <span className="text-[10px] text-slate-500">{index + 1}/{total}</span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
          {scene.narration_text?.slice(0, 80)}
        </p>
        <div className="flex items-center gap-3 mt-1">
          {hasImage ? (
            <span className="text-[10px] text-emerald-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Image</span>
          ) : (
            <span className="text-[10px] text-slate-500 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Image</span>
          )}
          {hasAudio ? (
            <span className="text-[10px] text-emerald-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Audio</span>
          ) : scene.image_url ? (
            <span className="text-[10px] text-slate-500 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Audio</span>
          ) : (
            <span className="text-[10px] text-slate-600 flex items-center gap-1"><Clock className="w-3 h-3" /> Waiting</span>
          )}
        </div>
      </div>
    </div>
  );
}

// Main Progressive Generation Component
export default function ProgressiveGeneration({
  jobId,
  wsRef,
  initialProgress = 0,
  initialStage = 'scenes',
  onComplete,
  onExportReady,
  reuseInfo,
}) {
  const navigate = useNavigate();
  const [scenes, setScenes] = useState([]);
  const [stage, setStage] = useState(initialStage);
  const [progress, setProgress] = useState(initialProgress);
  const [message, setMessage] = useState('Analyzing your story...');
  const [previewReady, setPreviewReady] = useState(false);
  const [notifySubscribed, setNotifySubscribed] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [etaSeconds, setEtaSeconds] = useState(null);
  const [retryInfo, setRetryInfo] = useState(null);
  const [jobData, setJobData] = useState(null);
  const pollRef = useRef(null);
  const elapsedRef = useRef(null);

  // Handle WebSocket asset_ready events
  const handleAssetReady = useCallback((data) => {
    const { asset_type, scene_number, data: assetData } = data;

    if (asset_type === 'scene_ready') {
      setScenes(prev => {
        const exists = prev.find(s => s.scene_number === scene_number);
        if (exists) return prev;
        return [...prev, {
          scene_number,
          title: assetData.title,
          narration_text: assetData.narration_text,
          visual_prompt: assetData.visual_prompt,
          image_url: null,
          audio_url: null,
        }].sort((a, b) => a.scene_number - b.scene_number);
      });
    }

    if (asset_type === 'image_ready') {
      setScenes(prev => prev.map(s =>
        s.scene_number === scene_number
          ? { ...s, image_url: assetData.image_url }
          : s
      ));
      setStage('images');
    }

    if (asset_type === 'voice_ready') {
      setScenes(prev => prev.map(s =>
        s.scene_number === scene_number
          ? { ...s, audio_url: assetData.audio_url, duration: assetData.duration }
          : s
      ));
      setStage('voices');
    }

    if (asset_type === 'preview_ready') {
      setPreviewReady(true);
      setStage('preview');
    }
  }, []);

  // Handle WebSocket progress events
  const handleProgress = useCallback((data) => {
    if (data.progress) setProgress(data.progress);
    if (data.message) setMessage(data.message);
    if (data.stage) {
      const stageMap = {
        scene_generation: 'scenes',
        image_generation: 'images',
        voice_generation: 'voices',
        video_assembly: 'render',
        complete: 'complete',
      };
      setStage(stageMap[data.stage] || data.stage);
    }
    if (data.status === 'completed') {
      onComplete?.(data);
    }
    if (data.status === 'failed') {
      // Let parent handle failure — do not navigate
      onComplete?.({ status: 'FAILED', error: data.error || data.message, ...data.metadata });
    }
  }, [jobId, navigate, onComplete]);

  // Listen to WebSocket messages
  useEffect(() => {
    if (!wsRef?.current) return;
    const ws = wsRef.current;

    const handler = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.job_id !== jobId) return;
        if (data.type === 'asset_ready') handleAssetReady(data);
        else if (data.type === 'progress') handleProgress(data);
      } catch {}
    };

    ws.addEventListener('message', handler);
    return () => ws.removeEventListener('message', handler);
  }, [wsRef, jobId, handleAssetReady, handleProgress]);

  // Fallback: poll for status
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await api.get(`/api/story-engine/status/${jobId}`);
        const job = res.data?.job;
        if (!job) return;

        setProgress(job.progress || 0);
        setJobData(job);

        // ETA and elapsed from backend
        if (job.timing) {
          setElapsedSeconds(job.timing.elapsed_seconds || 0);
          setEtaSeconds(job.timing.eta_seconds);
        }
        // Retry info + notify state
        if (job.retry_info) setRetryInfo(job.retry_info);
        if (job.notification_opt_in) setNotifySubscribed(true);

        // Honest status
        const ri = job.retry_info;
        const engineState = job.engine_state || '';
        let statusMsg = job.current_step || message;
        if (ri?.current_attempt > 1 && !['COMPLETED','PARTIAL','FAILED'].includes(job.status)) {
          const failedStates = ['FAILED_PLANNING','FAILED_IMAGES','FAILED_TTS','FAILED_RENDER'];
          if (failedStates.includes(engineState)) {
            statusMsg = `Recovering — ${job.current_step}`;
          } else {
            statusMsg = `${job.current_step} (attempt ${ri.current_attempt}/${ri.max_attempts})`;
          }
        }
        if (ri?.heartbeat_detail?.includes?.('Recovered by daemon')) {
          statusMsg = `Recovering stuck job — retrying ${job.current_step}`;
        }
        setMessage(statusMsg);

        if (job.status === 'COMPLETED' || job.status === 'PARTIAL') {
          clearInterval(pollRef.current);
          clearInterval(elapsedRef.current);
          try {
            const preview = await api.get(`/api/story-engine/preview/${jobId}`);
            if (preview.data?.preview?.scenes) {
              setScenes(preview.data.preview.scenes.map(s => ({
                scene_number: s.scene_number, title: s.title,
                narration_text: s.narration_text, image_url: s.image_url,
                audio_url: s.audio_url, duration: s.duration,
              })));
              setPreviewReady(true);
              setStage(job.status === 'COMPLETED' ? 'complete' : 'preview');
            }
          } catch {}
          onComplete?.(job);
          return;
        }
        if (job.status === 'FAILED') {
          clearInterval(pollRef.current);
          clearInterval(elapsedRef.current);
          onComplete?.(job);
        }
      } catch {}
    };

    pollRef.current = setInterval(poll, 4000);
    poll();
    return () => clearInterval(pollRef.current);
  }, [jobId, navigate, onComplete]);

  // Elapsed time counter — ticks every second
  useEffect(() => {
    elapsedRef.current = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(elapsedRef.current);
  }, []);

  const handleNotifyMe = async () => {
    try {
      await api.post(`/api/notifications/generation/${jobId}/subscribe`);
      setNotifySubscribed(true);
      toast.success("We'll notify you when your video is ready!");
    } catch {
      setNotifySubscribed(true);
    }
  };

  // Determine status indicators
  const formatTime = (seconds) => {
    if (!seconds || seconds < 0) return null;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const imagesReady = scenes.filter(s => s.image_url).length;
  const audioReady = scenes.filter(s => s.audio_url).length;
  const totalScenes = scenes.length;

  const stageLabels = {
    scenes: message || 'Generating scenes...',
    images: imagesReady > 0 ? `Generating images (${imagesReady}/${totalScenes})` : (message || 'Generating images...'),
    voices: audioReady > 0 ? `Creating narration (${audioReady}/${totalScenes})` : (message || 'Creating narration...'),
    render: message || 'Rendering video...',
    preview: 'Preview ready!',
    complete: 'Done!',
  };

  const stageExplanations = [
    { key: 'scenes', label: 'Planning your story', desc: 'Breaking down the narrative into scenes', stageIds: ['PLANNING', 'BUILDING_CHARACTER_CONTEXT', 'PLANNING_SCENE_MOTION'] },
    { key: 'images', label: 'Generating visuals', desc: 'Creating images and video clips for each scene', stageIds: ['GENERATING_KEYFRAMES', 'GENERATING_SCENE_CLIPS'] },
    { key: 'voices', label: 'Creating narration', desc: 'Generating voice audio for the story', stageIds: ['GENERATING_AUDIO'] },
    { key: 'render', label: 'Rendering final video', desc: 'Stitching everything together into your video', stageIds: ['ASSEMBLING_VIDEO'] },
  ];

  const QUOTES = [
    "Every great story begins with a single spark of imagination.",
    "Creativity is intelligence having fun. — Albert Einstein",
    "The world always seems brighter when you've just made something.",
    "Art is not what you see, but what you make others see. — Edgar Degas",
    "Your story matters. That's why we're crafting it with care.",
    "The best time to create was yesterday. The next best time is now.",
    "Good things take time. Great things take a little longer.",
    "Imagination is the beginning of creation. — George Bernard Shaw",
  ];

  const [quoteIndex, setQuoteIndex] = useState(0);
  useEffect(() => {
    const qi = setInterval(() => {
      setQuoteIndex(prev => (prev + 1) % QUOTES.length);
    }, 12000);
    return () => clearInterval(qi);
  }, []);

  const currentStageIdx = ['scenes', 'images', 'voices', 'render', 'preview', 'complete'].indexOf(stage);
  const isDone = stage === 'complete' || stage === 'preview';

  return (
    <div className="space-y-5" data-testid="progressive-generation">

      {/* ═══ PROGRESS HERO CARD ═══ */}
      <div className="bg-slate-800/60 rounded-2xl border border-slate-700/50 p-6" data-testid="progress-hero">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${
              isDone ? 'bg-emerald-500/20' : 'bg-purple-500/20'
            }`}>
              {isDone ? (
                <CheckCircle className="w-6 h-6 text-emerald-400" />
              ) : (
                <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
              )}
            </div>
            <div>
              <h3 className="text-white font-semibold text-base" data-testid="progressive-stage-label">
                {stageLabels[stage] || message}
              </h3>
              {retryInfo?.current_attempt > 1 && (
                <p className="text-amber-400 text-xs mt-0.5">
                  Retrying ({retryInfo.current_attempt}/{retryInfo.max_attempts})
                </p>
              )}
            </div>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold text-white" data-testid="progressive-progress">
              {progress}%
            </span>
            {etaSeconds && etaSeconds > 0 && !isDone && (
              <p className="text-xs text-slate-400 mt-0.5" data-testid="eta-display">
                ~{formatTime(etaSeconds)} remaining
              </p>
            )}
          </div>
        </div>

        {/* Stage pipeline */}
        <div className="flex items-center gap-1 mb-2">
          {['scenes', 'images', 'voices', 'render'].map((s, i) => {
            const active = s === stage;
            const done = currentStageIdx > i;
            const reusedStages = reuseInfo?.reusable_stages || jobData?.reuse_info?.reused_stages || [];
            const stageIdMap = { scenes: ['PLANNING', 'BUILDING_CHARACTER_CONTEXT', 'PLANNING_SCENE_MOTION'], images: ['GENERATING_KEYFRAMES', 'GENERATING_SCENE_CLIPS'], voices: ['GENERATING_AUDIO'], render: ['ASSEMBLING_VIDEO'] };
            const isReusedStage = (stageIdMap[s] || []).every(sid => reusedStages.includes(sid));
            return (
              <div key={s} className="flex-1 flex items-center gap-1">
                <div className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${
                  isReusedStage ? 'bg-emerald-500/60' : done ? 'bg-emerald-500' : active ? 'bg-purple-500 animate-pulse' : 'bg-slate-700'
                }`} />
                {i < 3 && <div className="w-0.5" />}
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 mb-3">
          {['Scenes', 'Images', 'Audio', 'Export'].map((label, i) => {
            const stages = [['PLANNING', 'BUILDING_CHARACTER_CONTEXT', 'PLANNING_SCENE_MOTION'], ['GENERATING_KEYFRAMES', 'GENERATING_SCENE_CLIPS'], ['GENERATING_AUDIO'], ['ASSEMBLING_VIDEO']];
            const reusedStages = reuseInfo?.reusable_stages || jobData?.reuse_info?.reused_stages || [];
            const isReused = stages[i].every(sid => reusedStages.includes(sid));
            return <span key={label} className={isReused ? 'text-emerald-400/60' : ''}>{label}{isReused ? ' ✓' : ''}</span>;
          })}
        </div>

        <Progress value={progress} className="h-2" />

        {/* Elapsed + ETA bar */}
        {!isDone && (
          <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
            <span data-testid="elapsed-display">Elapsed: {formatTime(elapsedSeconds) || '0s'}</span>
            {etaSeconds && etaSeconds > 0 ? (
              <span>Estimated: ~{formatTime(etaSeconds)}</span>
            ) : elapsedSeconds > 5 ? (
              <span>Estimating time...</span>
            ) : null}
          </div>
        )}
      </div>

      {/* ═══ SAFE LEAVE + NOTIFY ═══ */}
      {!isDone && (
        <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4 flex items-center justify-between" data-testid="safe-leave-section">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <p className="text-slate-200 text-sm font-medium">You can safely leave this page</p>
              <p className="text-slate-400 text-xs">Your video will keep generating. We'll notify you when it's ready.</p>
            </div>
          </div>
          {!notifySubscribed ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleNotifyMe}
              className="border-purple-500/40 text-purple-300 hover:bg-purple-500/10 flex-shrink-0"
              data-testid="progressive-notify-btn"
            >
              <Bell className="w-3.5 h-3.5 mr-1.5" /> Notify Me
            </Button>
          ) : (
            <span className="text-emerald-400 text-xs flex items-center gap-1.5 flex-shrink-0" data-testid="notify-confirmed">
              <CheckCircle className="w-3.5 h-3.5" /> Notifications on
            </span>
          )}
        </div>
      )}

      {/* ═══ WHAT'S HAPPENING NOW ═══ */}
      {!isDone && (
        <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4" data-testid="whats-happening">
          <h4 className="text-slate-300 text-xs font-semibold uppercase tracking-wider mb-3">What's happening now</h4>
          {/* Reuse badge — show when stages are being fast-tracked */}
          {(reuseInfo?.reuse_mode || jobData?.reuse_info?.reuse_mode) && (reuseInfo?.reuse_mode || jobData?.reuse_info?.reuse_mode) !== 'fresh' && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2" data-testid="reuse-badge">
              <Zap className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-300 text-xs font-medium">
                {(reuseInfo?.reuse_mode || jobData?.reuse_info?.reuse_mode) === 'style_remix'
                  ? 'Style Remix — reusing story & audio from previous video'
                  : (reuseInfo?.reuse_mode || jobData?.reuse_info?.reuse_mode) === 'voice_remix'
                  ? 'Voice Remix — reusing visuals from previous video'
                  : (reuseInfo?.reuse_mode || jobData?.reuse_info?.reuse_mode) === 'continue'
                  ? 'Continuation — inheriting character design'
                  : 'Optimized — reusing previous checkpoints'}
              </span>
            </div>
          )}
          <div className="space-y-2.5">
            {stageExplanations.map((exp, i) => {
              const isActive = exp.key === stage || (stage === 'scenes' && exp.key === 'scenes');
              const isDoneStage = currentStageIdx > i;
              const reusedStages = reuseInfo?.reusable_stages || jobData?.reuse_info?.reused_stages || [];
              const isReused = exp.stageIds?.some(sid => reusedStages.includes(sid));
              return (
                <div key={exp.key} className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isReused ? 'bg-emerald-500/20' : isDoneStage ? 'bg-emerald-500/20' : isActive ? 'bg-purple-500/20' : 'bg-slate-700/50'
                  }`}>
                    {isReused ? (
                      <SkipForward className="w-3.5 h-3.5 text-emerald-400" />
                    ) : isDoneStage ? (
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    ) : isActive ? (
                      <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-slate-600" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className={`text-sm ${isReused ? 'text-emerald-300' : isDoneStage ? 'text-emerald-300' : isActive ? 'text-white font-medium' : 'text-slate-500'}`}>
                        {exp.label}
                      </p>
                      {isReused && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-medium" data-testid={`stage-reused-${exp.key}`}>
                          Reused
                        </span>
                      )}
                    </div>
                    {isActive && !isReused && <p className="text-xs text-slate-400">{exp.desc}</p>}
                    {isReused && <p className="text-xs text-emerald-400/60">Carried from previous video</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ PREVIEW PLAYER ═══ */}
      {previewReady && scenes.length > 0 && scenes[0].image_url && (
        <div className="animate-in fade-in slide-in-from-bottom-3" data-testid="progressive-preview-player">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Eye className="w-5 h-5 text-emerald-400" />
              Your Story Preview
            </h3>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/app/story-preview/${jobId}`)}
                className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10"
                data-testid="open-full-preview-btn"
              >
                <Eye className="w-4 h-4 mr-1" /> Full Preview
              </Button>
              {onExportReady && (
                <Button
                  size="sm"
                  onClick={onExportReady}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  data-testid="export-video-btn"
                >
                  <Film className="w-4 h-4 mr-1" /> Export Video
                </Button>
              )}
            </div>
          </div>
          <PreviewPlayer scenes={scenes} autoPlay={true} />
        </div>
      )}

      {/* ═══ SCENE CARDS ═══ */}
      {scenes.length > 0 && (
        <div>
          <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-purple-400" />
            Scenes ({imagesReady}/{totalScenes} images, {audioReady}/{totalScenes} audio)
          </h3>
          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {scenes.map((scene, idx) => (
              <SceneCard key={scene.scene_number} scene={scene} index={idx} total={totalScenes} />
            ))}
          </div>
        </div>
      )}

      {/* ═══ EXPLORE WHILE WAITING ═══ */}
      {!isDone && (
        <div className="space-y-4" data-testid="explore-while-waiting">
          {/* Inspirational Quote */}
          <div className="bg-gradient-to-r from-purple-900/20 to-indigo-900/20 rounded-xl border border-purple-500/10 p-5" data-testid="quote-card">
            <p className="text-slate-300 text-sm italic leading-relaxed transition-opacity duration-700">
              "{QUOTES[quoteIndex]}"
            </p>
          </div>

          {/* Explore Tools */}
          <div>
            <h4 className="text-slate-300 text-xs font-semibold uppercase tracking-wider mb-3">Explore while you wait</h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {[
                { label: 'My Space', desc: 'View your creations', href: '/app/personal-space', icon: '📂' },
                { label: 'Create New', desc: 'Start another story', href: '/app/story-video-studio', icon: '✨' },
                { label: 'Templates', desc: 'Browse templates', href: '/app/templates', icon: '📋' },
                { label: 'Dashboard', desc: 'Your dashboard', href: '/app/dashboard', icon: '📊' },
                { label: 'Characters', desc: 'Character studio', href: '/app/character-consistency-studio', icon: '🎭' },
                { label: 'Browse', desc: 'Discover content', href: '/', icon: '🔍' },
              ].map((tool) => (
                <button
                  key={tool.label}
                  onClick={() => navigate(tool.href)}
                  className="text-left p-3 rounded-xl bg-slate-800/40 border border-slate-700/30 hover:border-purple-500/30 hover:bg-slate-800/60 transition-all group"
                  data-testid={`explore-${tool.label.toLowerCase().replace(/\s/g, '-')}`}
                >
                  <div className="text-lg mb-1">{tool.icon}</div>
                  <p className="text-white text-sm font-medium group-hover:text-purple-300 transition-colors">{tool.label}</p>
                  <p className="text-slate-500 text-[11px]">{tool.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ BOTTOM ACTIONS (legacy) ═══ */}
      <div className="flex items-center gap-3 flex-wrap">
        {previewReady && (
          <Button
            variant="outline"
            onClick={() => navigate(`/app/story-preview/${jobId}`)}
            className="border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10"
            data-testid="progressive-view-preview-btn"
          >
            <Eye className="w-4 h-4 mr-2" /> View Full Preview
          </Button>
        )}
      </div>
    </div>
  );
}

export { PreviewPlayer, SceneCard };
