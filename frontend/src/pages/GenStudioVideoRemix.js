import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Sparkles, Scissors, ArrowLeft, Coins, Loader2, Download,
  Settings, Clock, AlertTriangle, RefreshCw, Upload, Video, X
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api from '../utils/api';

export default function VideoRemix() {
  const [credits, setCredits] = useState(0);
  const [remixPrompt, setRemixPrompt] = useState('');
  const [templateStyle, setTemplateStyle] = useState('dynamic');
  const [addWatermark, setAddWatermark] = useState(true);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState({ step: 0, message: '' });
  const [result, setResult] = useState(null);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchCredits();
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await api.get('/api/credits/balance');
      setCredits(response.data.balance);
    } catch (error) {
      toast.error('Failed to load credits');
    }
  };

  const handleVideoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
    if (!validTypes.includes(file.type)) {
      toast.error('Invalid video type. Use MP4, WebM, or MOV');
      return;
    }

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      toast.error('Video too large. Maximum size is 50MB');
      return;
    }

    setSelectedVideo(file);
    
    // Create preview URL
    const previewUrl = URL.createObjectURL(file);
    setVideoPreview(previewUrl);
  };

  const removeVideo = () => {
    if (videoPreview) {
      URL.revokeObjectURL(videoPreview);
    }
    setSelectedVideo(null);
    setVideoPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleGenerate = async () => {
    if (!selectedVideo) {
      toast.error('Please select a video to remix');
      return;
    }

    if (!remixPrompt.trim()) {
      toast.error('Please describe how you want to remix the video');
      return;
    }

    if (!consentConfirmed) {
      toast.error('Please confirm you have rights/consent for this content');
      return;
    }

    if (credits < 12) {
      toast.error('Need 12 credits for video remix');
      return;
    }

    setGenerating(true);
    setProgress({ step: 1, message: 'Uploading video...' });
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('video', selectedVideo);
      formData.append('remix_prompt', remixPrompt.trim());
      formData.append('template_style', templateStyle);
      formData.append('add_watermark', addWatermark);
      formData.append('consent_confirmed', consentConfirmed);

      const response = await api.post('/api/genstudio/video-remix', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const jobId = response.data.jobId;
      setCredits(response.data.remainingCredits);
      setProgress({ step: 2, message: 'Remixing with AI... (1-3 min)' });
      
      // Poll for job completion
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.get(`/api/genstudio/job/${jobId}`);
          const job = statusRes.data;
          
          if (job.status === 'completed') {
            clearInterval(pollInterval);
            setProgress({ step: 3, message: 'Video remixed!' });
            setResult({
              ...response.data,
              status: 'completed',
              outputUrls: job.outputUrls
            });
            toast.success('Video remixed successfully!');
            setGenerating(false);
          } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            toast.error(job.error || 'Video remix failed');
            setGenerating(false);
          }
        } catch (pollError) {
          console.error('Polling error:', pollError);
        }
      }, 5000);
      
      setTimeout(() => {
        clearInterval(pollInterval);
        if (generating) {
          toast.error('Video remix timed out. Check history for status.');
          setGenerating(false);
        }
      }, 600000);

    } catch (error) {
      console.error('Generation error:', error);
      const message = error.response?.data?.detail || 'Remix failed';
      toast.error(message);
      setGenerating(false);
      setProgress({ step: 0, message: '' });
    }
  };

  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        if (response.status === 410) {
          toast.error('Download link expired');
          return;
        }
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'remixed-video.mp4';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      toast.success('Video downloaded!');
    } catch (error) {
      toast.error('Download failed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-red-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-rose-500 flex items-center justify-center">
                  <Scissors className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Video Remix</h1>
                  <p className="text-xs text-slate-400">Remix videos with new styles</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <span className="font-bold text-white">{credits}</span>
                <span className="text-slate-400 text-sm">credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input Panel */}
          <div className="space-y-6">
            {/* Video Upload */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Upload Video</h3>
              
              {videoPreview ? (
                <div className="relative">
                  <video 
                    src={videoPreview}
                    controls
                    className="w-full max-h-64 rounded-lg bg-slate-800"
                  />
                  <button
                    onClick={removeVideo}
                    className="absolute top-2 right-2 p-1 bg-red-500 rounded-full hover:bg-red-600 transition-colors"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center cursor-pointer hover:border-red-500/50 hover:bg-slate-800/50 transition-all"
                >
                  <Upload className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                  <p className="text-slate-400 mb-2">Click to upload a video</p>
                  <p className="text-xs text-slate-500">MP4, WebM, MOV (max 50MB)</p>
                </div>
              )}
              
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                onChange={handleVideoSelect}
                className="hidden"
              />
            </div>

            {/* Remix Prompt */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Remix Instructions</h3>
              <Textarea
                placeholder="Describe how you want to remix this video... Example: 'Add cinematic color grading, slow-motion effect, dramatic music vibe, film grain overlay'"
                value={remixPrompt}
                onChange={(e) => setRemixPrompt(e.target.value)}
                className="min-h-[120px] bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
              />
              <p className="text-xs text-slate-500 mt-2">{remixPrompt.length}/1000 characters</p>
            </div>

            {/* Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-slate-400" />
                Style Settings
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Template Style</label>
                  <Select value={templateStyle} onValueChange={setTemplateStyle}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dynamic">Dynamic (Fast cuts, energetic)</SelectItem>
                      <SelectItem value="smooth">Smooth (Gentle flow, cinematic)</SelectItem>
                      <SelectItem value="dramatic">Dramatic (Intense mood, dark)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">Add Watermark</p>
                    <p className="text-xs text-slate-500">Required for free plan</p>
                  </div>
                  <button
                    onClick={() => setAddWatermark(!addWatermark)}
                    className={`w-12 h-6 rounded-full transition-colors ${addWatermark ? 'bg-red-500' : 'bg-slate-600'}`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${addWatermark ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentConfirmed}
                  onChange={(e) => setConsentConfirmed(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800 text-red-500"
                />
                <div>
                  <p className="text-sm font-medium text-yellow-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Content Rights Confirmation
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    I confirm that I own or have rights to this video and it does not contain prohibited content.
                  </p>
                </div>
              </label>
            </div>

            {/* Generate Button */}
            <Button
              onClick={handleGenerate}
              disabled={generating || !consentConfirmed || !selectedVideo || !remixPrompt.trim()}
              className="w-full h-14 bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-lg font-semibold"
            >
              {generating ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {progress.message}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Remix Video (12 credits)
                </span>
              )}
            </Button>

            {/* Progress Bar */}
            {generating && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div className="flex justify-between text-sm text-slate-400 mb-2">
                  <span>{progress.message}</span>
                  <span>{Math.min(progress.step * 33, 100)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-red-500 to-rose-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(progress.step * 33, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Remixing typically takes 2-5 minutes.
                </p>
              </div>
            )}
          </div>

          {/* Right: Result Panel */}
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 min-h-[500px] flex flex-col">
              <h3 className="text-sm font-semibold text-white mb-4">Remixed Video</h3>
              
              {result ? (
                <div className="flex-1 flex flex-col">
                  <div className="relative flex-1 bg-slate-800 rounded-lg overflow-hidden">
                    <video 
                      src={`${process.env.REACT_APP_BACKEND_URL}${result.outputUrls[0]}`}
                      controls
                      className="w-full h-full object-contain"
                    />
                  </div>
                  
                  <div className="mt-4 space-y-3">
                    {/* Expiry Notice */}
                    <div className="flex items-center gap-2 text-yellow-400 text-sm bg-yellow-500/10 rounded-lg px-3 py-2">
                      <Clock className="w-4 h-4" />
                      <span>Download within 15 minutes before it expires!</span>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        onClick={() => handleDownload(result.outputUrls[0], `genstudio-remix-${result.jobId}.mp4`)}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Video
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => { setResult(null); removeVideo(); setRemixPrompt(''); }}
                        className="border-slate-600 text-slate-300"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        New
                      </Button>
                    </div>
                    
                    <p className="text-xs text-slate-500 text-center">
                      Credits used: {result.creditsUsed} • Remaining: {result.remainingCredits}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-center">
                  <div>
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
                      <Video className="w-10 h-10 text-slate-600" />
                    </div>
                    <p className="text-slate-400">Your remixed video will appear here</p>
                    <p className="text-xs text-slate-500 mt-2">Upload a video and describe the remix</p>
                  </div>
                </div>
              )}
            </div>

            {/* Tips */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">💡 Remix Ideas</h3>
              <ul className="text-xs text-slate-400 space-y-2">
                <li>• <strong>Color Grading:</strong> "Apply cinematic teal and orange look"</li>
                <li>• <strong>Speed Effects:</strong> "Add slow motion to key moments"</li>
                <li>• <strong>Style Transfer:</strong> "Make it look like a vintage film"</li>
                <li>• <strong>Mood Change:</strong> "Transform to dramatic, dark aesthetic"</li>
                <li>• <strong>Effects:</strong> "Add film grain, lens flares, light leaks"</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
