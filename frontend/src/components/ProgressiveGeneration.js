import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Play, Pause, Image, Mic, Film, Package, FileText, Sparkles,
  Download, ChevronLeft, ChevronRight, Bell, CheckCircle,
  Loader2, Volume2, Eye, Clock, Zap, SkipForward
} from 'lucide-react';
import { toast } from 'sonner';
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
          <img src={scene.image_url} alt={scene.title} className="w-full h-full object-contain" />
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
          <img src={scene.image_url} alt="" className="w-full h-full object-cover" />
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
}) {
  const navigate = useNavigate();
  const [scenes, setScenes] = useState([]);
  const [stage, setStage] = useState(initialStage);
  const [progress, setProgress] = useState(initialProgress);
  const [message, setMessage] = useState('Analyzing your story...');
  const [previewReady, setPreviewReady] = useState(false);
  const [notifySubscribed, setNotifySubscribed] = useState(false);
  const pollRef = useRef(null);

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
      // Check for fallback
      if (data.metadata?.fallback_status) {
        navigate(`/app/story-preview/${jobId}`);
      }
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

  // Fallback: poll for status if WebSocket is unavailable
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await api.get(`/api/pipeline/status/${jobId}`);
        const job = res.data?.job;
        if (!job) return;

        setProgress(job.progress || 0);
        if (job.current_step) setMessage(job.current_step);

        // Sync scenes from job data (fallback when WS misses events)
        if (job.status === 'COMPLETED' || job.status === 'PARTIAL') {
          clearInterval(pollRef.current);
          // Fetch full preview data
          try {
            const preview = await api.get(`/api/pipeline/preview/${jobId}`);
            if (preview.data?.preview?.scenes) {
              setScenes(preview.data.preview.scenes.map(s => ({
                scene_number: s.scene_number,
                title: s.title,
                narration_text: s.narration_text,
                image_url: s.image_url,
                audio_url: s.audio_url,
                duration: s.duration,
              })));
              setPreviewReady(true);
              setStage(job.status === 'COMPLETED' ? 'complete' : 'preview');
            }
          } catch {}
          if (job.status === 'COMPLETED') onComplete?.(job);
          return;
        }

        if (job.status === 'FAILED') {
          clearInterval(pollRef.current);
          if (job.fallback?.has_preview || job.fallback?.story_pack_url) {
            navigate(`/app/story-preview/${jobId}`);
          }
        }
      } catch {}
    };

    pollRef.current = setInterval(poll, 4000);
    poll(); // immediate
    return () => clearInterval(pollRef.current);
  }, [jobId, navigate, onComplete]);

  const handleNotifyMe = async () => {
    try {
      await api.post(`/api/pipeline/notify-when-ready/${jobId}`);
      setNotifySubscribed(true);
      toast.success("We'll notify you when it's ready!");
    } catch {
      toast.error('Could not subscribe');
    }
  };

  // Determine status indicators
  const imagesReady = scenes.filter(s => s.image_url).length;
  const audioReady = scenes.filter(s => s.audio_url).length;
  const totalScenes = scenes.length;

  const stageLabels = {
    scenes: 'Writing scenes...',
    images: `Generating images (${imagesReady}/${totalScenes})`,
    voices: `Creating narration (${audioReady}/${totalScenes})`,
    render: 'Rendering video...',
    preview: 'Preview ready!',
    complete: 'Done!',
  };

  return (
    <div className="space-y-6" data-testid="progressive-generation">
      {/* Progress Header */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              previewReady ? 'bg-emerald-500/20' : 'bg-purple-500/20'
            }`}>
              {previewReady ? (
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              ) : (
                <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
              )}
            </div>
            <div>
              <h3 className="text-white font-semibold" data-testid="progressive-stage-label">
                {stageLabels[stage] || message}
              </h3>
              <p className="text-xs text-slate-400">{message}</p>
            </div>
          </div>
          <span className="text-xl font-bold text-white" data-testid="progressive-progress">
            {progress}%
          </span>
        </div>

        {/* Stage pipeline indicator */}
        <div className="flex items-center gap-1 mb-3">
          {['scenes', 'images', 'voices', 'render'].map((s, i) => {
            const active = s === stage;
            const done = ['scenes', 'images', 'voices', 'render', 'preview', 'complete'].indexOf(stage) > i;
            return (
              <div key={s} className="flex-1 flex items-center gap-1">
                <div className={`h-1.5 flex-1 rounded-full transition-all ${
                  done ? 'bg-emerald-500' : active ? 'bg-purple-500 animate-pulse' : 'bg-slate-700'
                }`} />
                {i < 3 && <div className="w-0.5" />}
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Scenes</span><span>Images</span><span>Audio</span><span>Export</span>
        </div>

        <Progress value={progress} className="mt-3 h-2" />
      </div>

      {/* Preview Player — appears when preview is ready */}
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

      {/* Scene Cards — appear progressively */}
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

      {/* Actions */}
      <div className="flex items-center gap-3 flex-wrap">
        {!notifySubscribed ? (
          <Button
            variant="outline"
            onClick={handleNotifyMe}
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
            data-testid="progressive-notify-btn"
          >
            <Bell className="w-4 h-4 mr-2" /> Notify Me When Ready
          </Button>
        ) : (
          <span className="text-emerald-400 text-sm flex items-center gap-1.5">
            <CheckCircle className="w-4 h-4" /> We'll notify you when it's done
          </span>
        )}

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
