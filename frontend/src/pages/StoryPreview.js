import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import BrowserVideoExport from '../components/BrowserVideoExport';
import {
  ArrowLeft, Download, Play, Pause, Image, Mic, FileText,
  Film, Package, Eye, AlertCircle, ChevronRight, ChevronLeft,
  Volume2, VolumeX, Loader2, CheckCircle, ExternalLink
} from 'lucide-react';
import api from '../utils/api';

export default function StoryPreview() {
  const { jobId } = useParams();
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showExport, setShowExport] = useState(false);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [playingAudio, setPlayingAudio] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    fetchPreview();
  }, [jobId]);

  const fetchPreview = async () => {
    try {
      const res = await api.get(`/api/pipeline/preview/${jobId}`);
      if (res.data.success) {
        setPreview(res.data.preview);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load preview');
    } finally {
      setLoading(false);
    }
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
    audio.onended = () => setPlayingAudio(null);
  };

  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause();
    };
  }, []);

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

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-[#0a0f1f] to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white" data-testid="preview-title">
                {preview.title || 'Story Preview'}
              </h1>
              <div className="flex items-center gap-3 text-sm">
                <span className={statusColor} data-testid="preview-status">
                  {preview.status === 'PARTIAL' ? 'Assets Available' : preview.status}
                </span>
                <span className="text-slate-500">
                  {preview.scenes_with_images}/{preview.total_scenes} images
                </span>
                <span className="text-slate-500">
                  {preview.scenes_with_audio}/{preview.total_scenes} audio
                </span>
              </div>
            </div>
          </div>

          {/* Download Actions */}
          <div className="flex items-center gap-2">
            {/* Browser Export Button — always available when scenes have images */}
            {preview.scenes?.some(s => s.image_url) && !preview.final_video_url && (
              <Button
                onClick={() => setShowExport(!showExport)}
                className={showExport ? 'bg-purple-700' : 'bg-purple-600 hover:bg-purple-700'}
                data-testid="browser-export-toggle-btn"
              >
                <Film className="w-4 h-4 mr-2" />
                {showExport ? 'Hide Export' : 'Export MP4'}
              </Button>
            )}
            {preview.final_video_url && (
              <a href={preview.final_video_url} target="_blank" rel="noopener noreferrer">
                <Button className="bg-emerald-600 hover:bg-emerald-700" data-testid="download-video-btn">
                  <Film className="w-4 h-4 mr-2" />
                  Download Video
                </Button>
              </a>
            )}
            {preview.fallback_video_url && !preview.final_video_url && (
              <a href={preview.fallback_video_url} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="border-amber-500/50 text-amber-400 hover:bg-amber-500/10" data-testid="download-fallback-btn">
                  <Film className="w-4 h-4 mr-2" />
                  Server Slideshow
                </Button>
              </a>
            )}
            {preview.story_pack_url && (
              <a href={preview.story_pack_url} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10" data-testid="download-pack-btn">
                  <Package className="w-4 h-4 mr-2" />
                  Story Pack ZIP
                </Button>
              </a>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
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

        {/* Fallback Banner */}
        {preview.status === 'PARTIAL' && (
          <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl" data-testid="fallback-banner">
            <div className="flex items-start gap-3">
              <Package className="w-6 h-6 text-amber-400 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-amber-300 font-semibold">Your story assets are ready</h3>
                <p className="text-amber-200/70 text-sm mt-1">
                  The cinematic server render encountered an issue, but all your story assets are preserved.
                  You have three options:
                </p>
                <div className="mt-3 grid sm:grid-cols-3 gap-2">
                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                    <p className="text-emerald-400 text-xs font-semibold">Instant Preview</p>
                    <p className="text-emerald-300/60 text-[10px]">Watch scenes below with audio</p>
                  </div>
                  <div className="p-2 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                    <p className="text-purple-400 text-xs font-semibold">Export MP4</p>
                    <p className="text-purple-300/60 text-[10px]">Render video in your browser</p>
                  </div>
                  <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                    <p className="text-amber-400 text-xs font-semibold">Story Pack ZIP</p>
                    <p className="text-amber-300/60 text-[10px]">All images, audio, and text</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Viewer */}
          <div className="lg:col-span-2 space-y-4">
            {/* Scene Image Viewer */}
            {currentScene && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="scene-viewer">
                {/* Scene Image */}
                <div className="relative aspect-video bg-slate-900 flex items-center justify-center">
                  {currentScene.image_url ? (
                    <img
                      src={currentScene.image_url}
                      alt={currentScene.title}
                      className="w-full h-full object-contain"
                      data-testid={`scene-image-${activeScene}`}
                    />
                  ) : (
                    <div className="text-center text-slate-500">
                      <Image className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>Image not generated</p>
                    </div>
                  )}

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
                    {activeScene < (preview.scenes?.length || 0) - 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setActiveScene(activeScene + 1)}
                        className="bg-black/50 hover:bg-black/70 text-white rounded-full"
                        data-testid="next-scene-btn"
                      >
                        <ChevronRight className="w-6 h-6" />
                      </Button>
                    )}
                  </div>

                  {/* Scene Counter */}
                  <div className="absolute bottom-3 right-3 px-3 py-1 bg-black/60 rounded-full text-white text-sm">
                    {activeScene + 1} / {preview.scenes?.length || 0}
                  </div>
                </div>

                {/* Scene Info */}
                <div className="p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-white" data-testid="scene-title">
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

                  <p className="text-slate-300 leading-relaxed" data-testid="scene-narration">
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
                      {scene.image_url ? (
                        <img src={scene.image_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Image className="w-4 h-4 text-slate-600" />
                        </div>
                      )}
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

            {/* Quick Downloads */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 space-y-3">
              <h4 className="text-white font-medium text-sm">Downloads</h4>
              {preview.final_video_url && (
                <a href={preview.final_video_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300">
                  <Film className="w-4 h-4" /> Final Video (MP4)
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </a>
              )}
              {preview.fallback_video_url && (
                <a href={preview.fallback_video_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300">
                  <Film className="w-4 h-4" /> Slideshow Video (MP4)
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </a>
              )}
              {preview.story_pack_url && (
                <a href={preview.story_pack_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300">
                  <Package className="w-4 h-4" /> Story Pack (ZIP)
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </a>
              )}
              {currentScene?.image_url && (
                <a href={currentScene.image_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-300">
                  <Image className="w-4 h-4" /> Scene {activeScene + 1} Image
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </a>
              )}
              {currentScene?.audio_url && (
                <a href={currentScene.audio_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-300">
                  <Mic className="w-4 h-4" /> Scene {activeScene + 1} Audio
                  <ExternalLink className="w-3 h-3 ml-auto" />
                </a>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
