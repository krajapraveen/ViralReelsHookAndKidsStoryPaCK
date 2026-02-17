import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import { Video, Volume2, Music, Image, Subtitles, Download, Loader2, Check, X } from 'lucide-react';
import api from '../utils/api';

const videoAPI = {
  getVoices: () => api.get('/api/video/voices'),
  getMusic: () => api.get('/api/video/music'),
  getPricing: () => api.get('/api/video/pricing'),
  generateVideo: (data) => api.post('/api/video/generate', data),
  getExportStatus: (id) => api.get(`/api/video/export/${id}`),
  downloadVideo: (id) => api.get(`/api/video/export/${id}/download`, { responseType: 'blob' }),
};

export default function VideoExportPanel({ storyId, storyTitle, onClose }) {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exportId, setExportId] = useState(null);
  const [exportStatus, setExportStatus] = useState(null);
  const [voices, setVoices] = useState([]);
  const [musicOptions, setMusicOptions] = useState([]);
  const [pricing, setPricing] = useState(null);
  
  // Video settings
  const [settings, setSettings] = useState({
    resolution: '1080p',
    aspectRatio: 'landscape',
    sceneDuration: 10,
    voiceId: '21m00Tcm4TlvDq8ikWAM',
    includeSubtitles: true,
    includeMusic: true,
    musicId: 'happy',
    imageSource: 'ai'
  });

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    let interval;
    if (exportId && generating) {
      interval = setInterval(async () => {
        try {
          const response = await videoAPI.getExportStatus(exportId);
          setExportStatus(response.data);
          if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
            setGenerating(false);
            if (response.data.status === 'COMPLETED') {
              toast.success('Video ready for download!');
            } else {
              toast.error(response.data.error || 'Video generation failed');
            }
          }
        } catch (error) {
          console.error('Status check error:', error);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [exportId, generating]);

  const loadOptions = async () => {
    try {
      const [voicesRes, musicRes, pricingRes] = await Promise.all([
        videoAPI.getVoices(),
        videoAPI.getMusic(),
        videoAPI.getPricing()
      ]);
      setVoices(voicesRes.data.voices || []);
      setMusicOptions(musicRes.data.music || []);
      setPricing(pricingRes.data);
    } catch (error) {
      console.error('Failed to load options:', error);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const response = await videoAPI.generateVideo({
        story_id: storyId,
        resolution: settings.resolution,
        aspect_ratio: settings.aspectRatio,
        scene_duration: settings.sceneDuration,
        voice_id: settings.voiceId,
        include_subtitles: settings.includeSubtitles,
        include_music: settings.includeMusic,
        image_source: settings.imageSource
      });
      
      if (response.data.success) {
        setExportId(response.data.exportId);
        setGenerating(true);
        setExportStatus({ status: 'PROCESSING', progress: 0 });
        toast.success('Video generation started!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start video generation');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const response = await videoAPI.downloadVideo(exportId);
      const blob = new Blob([response.data], { type: 'video/mp4' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `${storyTitle || 'story'}_video.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Video downloaded!');
    } catch (error) {
      toast.error('Failed to download video');
    }
  };

  const getCost = () => {
    return settings.resolution === '1080p' ? 20 : 10;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
            <Video className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Export Video</h3>
            <p className="text-sm text-slate-500">Create MP4 from your story</p>
          </div>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Video Settings */}
      {!generating && !exportStatus?.status === 'COMPLETED' && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Resolution */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Image className="w-4 h-4" /> Resolution
            </Label>
            <Select value={settings.resolution} onValueChange={(v) => setSettings({...settings, resolution: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="720p">720p HD (₹99)</SelectItem>
                <SelectItem value="1080p">1080p Full HD (₹199)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Aspect Ratio */}
          <div className="space-y-2">
            <Label>Aspect Ratio</Label>
            <Select value={settings.aspectRatio} onValueChange={(v) => setSettings({...settings, aspectRatio: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="landscape">🖥️ Landscape (16:9) - YouTube</SelectItem>
                <SelectItem value="portrait">📱 Portrait (9:16) - Reels/Shorts</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Scene Duration */}
          <div className="space-y-2">
            <Label>Duration per Scene</Label>
            <Select value={String(settings.sceneDuration)} onValueChange={(v) => setSettings({...settings, sceneDuration: parseInt(v)})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5 seconds</SelectItem>
                <SelectItem value="10">10 seconds</SelectItem>
                <SelectItem value="15">15 seconds</SelectItem>
                <SelectItem value="20">20 seconds</SelectItem>
                <SelectItem value="25">25 seconds</SelectItem>
                <SelectItem value="30">30 seconds</SelectItem>
                <SelectItem value="60">1 minute</SelectItem>
                <SelectItem value="120">2 minutes</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Voice Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Volume2 className="w-4 h-4" /> Narrator Voice
            </Label>
            <Select value={settings.voiceId} onValueChange={(v) => setSettings({...settings, voiceId: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {voices.map((voice) => (
                  <SelectItem key={voice.id} value={voice.id}>
                    {voice.name} - {voice.description}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Image Source */}
          <div className="space-y-2">
            <Label>Scene Images</Label>
            <Select value={settings.imageSource} onValueChange={(v) => setSettings({...settings, imageSource: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ai">🤖 AI Generated (Gemini)</SelectItem>
                <SelectItem value="upload">📤 Upload Custom Images</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Music Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Music className="w-4 h-4" /> Background Music
            </Label>
            <Select value={settings.musicId} onValueChange={(v) => setSettings({...settings, musicId: v})} disabled={!settings.includeMusic}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {musicOptions.map((music) => (
                  <SelectItem key={music.id} value={music.id}>
                    🎵 {music.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Toggles */}
      {!generating && !exportStatus?.status === 'COMPLETED' && (
        <div className="flex flex-wrap gap-6">
          <div className="flex items-center gap-2">
            <Switch 
              checked={settings.includeSubtitles} 
              onCheckedChange={(v) => setSettings({...settings, includeSubtitles: v})}
            />
            <Label className="flex items-center gap-1">
              <Subtitles className="w-4 h-4" /> Subtitles
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch 
              checked={settings.includeMusic} 
              onCheckedChange={(v) => setSettings({...settings, includeMusic: v})}
            />
            <Label className="flex items-center gap-1">
              <Music className="w-4 h-4" /> Background Music
            </Label>
          </div>
        </div>
      )}

      {/* Progress */}
      {generating && exportStatus && (
        <div className="space-y-4 p-4 bg-purple-50 rounded-lg">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />
            <span className="font-medium text-purple-900">
              {exportStatus.statusMessage || 'Processing...'}
            </span>
          </div>
          <Progress value={exportStatus.progress || 0} className="h-3" />
          <p className="text-sm text-purple-700">{exportStatus.progress}% complete</p>
        </div>
      )}

      {/* Completed */}
      {exportStatus?.status === 'COMPLETED' && (
        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <Check className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-green-800">Video Ready!</span>
          </div>
          <Button onClick={handleDownload} className="w-full bg-green-600 hover:bg-green-700">
            <Download className="w-4 h-4 mr-2" /> Download Video
          </Button>
        </div>
      )}

      {/* Failed */}
      {exportStatus?.status === 'FAILED' && (
        <div className="p-4 bg-red-50 rounded-lg border border-red-200">
          <p className="text-red-700">{exportStatus.error || 'Video generation failed. Please try again.'}</p>
          <Button onClick={() => { setExportStatus(null); setExportId(null); }} variant="outline" className="mt-3">
            Try Again
          </Button>
        </div>
      )}

      {/* Generate Button */}
      {!generating && exportStatus?.status !== 'COMPLETED' && (
        <div className="flex items-center justify-between pt-4 border-t">
          <div>
            <p className="font-semibold text-lg">Cost: ₹{getCost()}</p>
            <p className="text-sm text-slate-500">
              {settings.resolution === '1080p' ? 'Full HD with premium quality' : 'HD quality video'}
            </p>
          </div>
          <Button 
            onClick={handleGenerate} 
            disabled={loading}
            className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Starting...</>
            ) : (
              <><Video className="w-4 h-4 mr-2" /> Generate Video</>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
