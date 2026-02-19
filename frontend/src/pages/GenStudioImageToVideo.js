import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Sparkles, Play, ArrowLeft, Loader2, Download,
  Settings, Clock, AlertTriangle, RefreshCw, Upload, Image, X,
  Wallet, XCircle, AlertCircle
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';
import { v4 as uuidv4 } from 'uuid';

export default function ImageToVideo() {
  const [wallet, setWallet] = useState({ balanceCredits: 0, reservedCredits: 0, availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [motionPrompt, setMotionPrompt] = useState('');
  const [duration, setDuration] = useState(4);
  const [addWatermark, setAddWatermark] = useState(true);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);
  
  // Job state
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState({ step: 0, message: '' });
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  // Poll for job status
  useEffect(() => {
    let interval;
    if (currentJob && ['QUEUED', 'RUNNING'].includes(jobStatus)) {
      interval = setInterval(pollJobStatus, 3000);
    }
    return () => clearInterval(interval);
  }, [currentJob, jobStatus]);

  const fetchData = async () => {
    try {
      const [walletRes, pricingRes] = await Promise.all([
        walletAPI.getWallet(),
        walletAPI.getPricing()
      ]);
      setWallet(walletRes.data);
      setPricing(pricingRes.data.pricing);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const pollJobStatus = useCallback(async () => {
    if (!currentJob) return;
    
    try {
      const response = await walletAPI.getJob(currentJob);
      const job = response.data;
      setJobStatus(job.status);
      setProgress({
        step: job.progress || 0,
        message: job.progressMessage || `Status: ${job.status}`
      });
      
      if (job.status === 'SUCCEEDED') {
        setResult({
          jobId: job.jobId,
          outputUrls: job.outputUrls,
          creditsUsed: job.costCredits
        });
        setGenerating(false);
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success('Video generated successfully!');
      } else if (job.status === 'FAILED') {
        setGenerating(false);
        toast.error(job.errorMessage || 'Video generation failed');
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  }, [currentJob]);

  // Calculate cost based on duration
  const calculateCost = () => {
    const baseCost = pricing.IMAGE_TO_VIDEO?.baseCredits || 20;
    const perSecond = pricing.IMAGE_TO_VIDEO?.perSecond || 4;
    return baseCost + (duration * perSecond);
  };

  const cost = calculateCost();
  const canAfford = wallet.availableCredits >= cost;

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      toast.error('Invalid image type. Use PNG, JPEG, or WebP');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image too large. Maximum size is 10MB');
      return;
    }

    setSelectedImage(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleGenerate = async () => {
    if (!selectedImage) {
      toast.error('Please select an image to animate');
      return;
    }

    if (!motionPrompt.trim()) {
      toast.error('Please describe the motion you want');
      return;
    }

    if (!consentConfirmed) {
      toast.error('Please confirm you have rights/consent for this content');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${cost} credits. You have ${wallet.availableCredits} available.`);
      navigate('/app/billing');
      return;
    }

    setGenerating(true);
    setProgress({ step: 5, message: 'Uploading image...' });
    setResult(null);
    setCurrentJob(null);
    setJobStatus(null);

    try {
      // First upload image to get a reference
      const formData = new FormData();
      formData.append('image', selectedImage);
      formData.append('motion_prompt', motionPrompt.trim());
      formData.append('duration', duration);
      formData.append('add_watermark', addWatermark);
      formData.append('consent_confirmed', consentConfirmed);

      // Use existing endpoint which now creates a job internally
      const response = await api.post('/api/genstudio/image-to-video', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const jobId = response.data.jobId;
      setCurrentJob(jobId);
      setJobStatus('QUEUED');
      setProgress({ step: 15, message: 'Job created. Processing image animation...' });
      
      // Refresh wallet
      const walletRes = await walletAPI.getWallet();
      setWallet(walletRes.data);
      
      toast.info('Job created! Processing...', { description: `Cost: ${response.data.creditsUsed || cost} credits` });
      
      // Start polling with the old job endpoint (hybrid approach)
      const pollInterval = setInterval(async () => {
        try {
          // Try new wallet API first, fall back to old endpoint
          let job;
          try {
            const statusRes = await walletAPI.getJob(jobId);
            job = statusRes.data;
          } catch {
            const statusRes = await api.get(`/api/genstudio/job/${jobId}`);
            job = statusRes.data;
          }
          
          const status = job.status?.toUpperCase() || job.status;
          setJobStatus(status);
          setProgress({
            step: job.progress || (status === 'RUNNING' ? 50 : 20),
            message: job.progressMessage || `Status: ${status}`
          });
          
          if (status === 'SUCCEEDED' || job.status === 'completed') {
            clearInterval(pollInterval);
            setResult({
              jobId: jobId,
              outputUrls: job.outputUrls,
              creditsUsed: job.costCredits || job.creditsUsed
            });
            setGenerating(false);
            const walletRes = await walletAPI.getWallet();
            setWallet(walletRes.data);
            toast.success('Video generated successfully!');
          } else if (status === 'FAILED' || job.status === 'failed') {
            clearInterval(pollInterval);
            setGenerating(false);
            toast.error(job.errorMessage || job.error || 'Video generation failed');
            const walletRes = await walletAPI.getWallet();
            setWallet(walletRes.data);
          }
        } catch (pollError) {
          console.error('Polling error:', pollError);
        }
      }, 5000);
      
      // Timeout after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (generating) {
          toast.error('Video generation timed out. Check history for status.');
          setGenerating(false);
        }
      }, 600000);

    } catch (error) {
      console.error('Generation error:', error);
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
      setGenerating(false);
      setProgress({ step: 0, message: '' });
    }
  };

  const handleCancelJob = async () => {
    if (!currentJob || !['QUEUED'].includes(jobStatus)) return;
    
    try {
      await walletAPI.cancelJob(currentJob);
      setGenerating(false);
      setCurrentJob(null);
      setJobStatus(null);
      const walletRes = await walletAPI.getWallet();
      setWallet(walletRes.data);
      toast.info('Job cancelled. Credits released.');
    } catch (error) {
      toast.error('Failed to cancel job');
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
      link.download = filename || 'animated-video.mp4';
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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-green-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                  <Play className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Image → Video</h1>
                  <p className="text-xs text-slate-400">Animate your images with AI</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2" data-testid="wallet-balance">
                <Wallet className="w-4 h-4 text-green-400" />
                <div className="flex flex-col">
                  <span className="font-bold text-white text-sm">{wallet.availableCredits}</span>
                  <span className="text-xs text-slate-500">available</span>
                </div>
                {wallet.reservedCredits > 0 && (
                  <div className="border-l border-slate-600 pl-2 ml-2">
                    <span className="text-xs text-yellow-400">{wallet.reservedCredits} held</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Insufficient Credits Warning */}
        {!canAfford && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-sm font-medium text-red-300">Insufficient Credits</p>
              <p className="text-xs text-red-400">Need {cost} credits for {duration}s video, you have {wallet.availableCredits} available.</p>
            </div>
            <Link to="/app/billing" className="ml-auto">
              <Button size="sm" className="bg-red-600 hover:bg-red-700">Buy Credits</Button>
            </Link>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input Panel */}
          <div className="space-y-6">
            {/* Image Upload */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Upload className="w-4 h-4 text-green-400" />
                Source Image
              </h3>
              
              {imagePreview ? (
                <div className="relative">
                  <img 
                    src={imagePreview} 
                    alt="Selected" 
                    className="w-full h-64 object-contain bg-slate-800 rounded-lg"
                  />
                  <button
                    onClick={removeImage}
                    className="absolute top-2 right-2 p-2 bg-red-500 rounded-full hover:bg-red-600 transition-colors"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:border-green-500/50 hover:bg-slate-800/50 transition-all">
                  <Image className="w-12 h-12 text-slate-500 mb-3" />
                  <p className="text-sm text-slate-400">Click to upload image</p>
                  <p className="text-xs text-slate-500 mt-1">PNG, JPEG, WebP (Max 10MB)</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/webp"
                    onChange={handleImageSelect}
                    className="hidden"
                    data-testid="image-upload"
                  />
                </label>
              )}
            </div>

            {/* Motion Prompt */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Motion Description</h3>
              <Textarea
                placeholder="Describe the motion you want... Example: 'Gentle wind blowing through the hair, subtle eye movement, soft smile appearing'"
                value={motionPrompt}
                onChange={(e) => setMotionPrompt(e.target.value)}
                className="min-h-[120px] bg-slate-800 border-slate-700 text-white placeholder:text-slate-500"
                data-testid="motion-prompt"
              />
              <p className="text-xs text-slate-500 mt-2">{motionPrompt.length}/1000 characters</p>
            </div>

            {/* Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-slate-400" />
                Settings
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-slate-400 mb-2 block">Duration</label>
                  <Select value={duration.toString()} onValueChange={(v) => setDuration(parseInt(v))}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="4">4 seconds (Fast)</SelectItem>
                      <SelectItem value="8">8 seconds (Medium)</SelectItem>
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
                    className={`w-12 h-6 rounded-full transition-colors ${addWatermark ? 'bg-green-500' : 'bg-slate-600'}`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${addWatermark ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>
            </div>

            {/* Cost Display */}
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-green-300">Estimated Cost</p>
                  <p className="text-xs text-green-400">Base: 20 credits + {duration * 4} ({duration}s × 4)</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">{cost}</p>
                  <p className="text-xs text-slate-400">credits</p>
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
                  className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800 text-green-500"
                  data-testid="consent-checkbox"
                />
                <div>
                  <p className="text-sm font-medium text-yellow-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Content Rights Confirmation
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    I confirm that I own this image or have permission to animate it, and it does not contain prohibited content.
                  </p>
                </div>
              </label>
            </div>

            {/* Generate Button */}
            <Button
              onClick={handleGenerate}
              disabled={generating || !consentConfirmed || !selectedImage || !motionPrompt.trim() || !canAfford}
              className="w-full h-14 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-lg font-semibold disabled:opacity-50"
              data-testid="generate-btn"
            >
              {generating ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {progress.message || 'Processing...'}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Animate Image ({cost} credits)
                </span>
              )}
            </Button>

            {/* Progress/Job Status */}
            {generating && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div className="flex justify-between text-sm text-slate-400 mb-2">
                  <span className="flex items-center gap-2">
                    {jobStatus === 'QUEUED' && <Clock className="w-4 h-4 text-yellow-400" />}
                    {jobStatus === 'RUNNING' && <Loader2 className="w-4 h-4 text-green-400 animate-spin" />}
                    {progress.message}
                  </span>
                  <span>{progress.step}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 to-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${progress.step}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Image animation typically takes 1-3 minutes.
                </p>
                {jobStatus === 'QUEUED' && (
                  <div className="mt-3 flex justify-end">
                    <Button variant="ghost" size="sm" onClick={handleCancelJob} className="text-red-400 hover:text-red-300">
                      <XCircle className="w-4 h-4 mr-1" />
                      Cancel Job
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: Result Panel */}
          <div className="space-y-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 min-h-[500px] flex flex-col">
              <h3 className="text-sm font-semibold text-white mb-4">Animated Video</h3>
              
              {result ? (
                <div className="flex-1 flex flex-col">
                  <div className="relative flex-1 bg-slate-800 rounded-lg overflow-hidden">
                    <video 
                      src={`${process.env.REACT_APP_BACKEND_URL}${result.outputUrls[0]}`}
                      controls
                      className="w-full h-full object-contain"
                      data-testid="generated-video"
                    />
                  </div>
                  
                  <div className="mt-4 space-y-3">
                    <div className="flex items-center gap-2 text-yellow-400 text-sm bg-yellow-500/10 rounded-lg px-3 py-2">
                      <Clock className="w-4 h-4" />
                      <span>SECURITY: Download within 3 MINUTES before auto-deletion!</span>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        onClick={() => handleDownload(result.outputUrls[0], `animated-${result.jobId}.mp4`)}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                        data-testid="download-btn"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Video
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => { setResult(null); removeImage(); setMotionPrompt(''); setCurrentJob(null); setJobStatus(null); }}
                        className="border-slate-600 text-slate-300"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        New
                      </Button>
                    </div>
                    
                    <p className="text-xs text-slate-500 text-center">
                      Credits used: {result.creditsUsed} • Available: {wallet.availableCredits}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-center">
                  <div>
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
                      <Play className="w-10 h-10 text-slate-600" />
                    </div>
                    <p className="text-slate-400">Your animated video will appear here</p>
                    <p className="text-xs text-slate-500 mt-2">Upload an image, describe motion, and click Animate</p>
                  </div>
                </div>
              )}
            </div>

            {/* Tips */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3">Tips for Better Results</h3>
              <ul className="text-xs text-slate-400 space-y-2">
                <li>• Use high-quality, well-lit images</li>
                <li>• Describe natural movements: "gentle breeze", "slow pan"</li>
                <li>• Avoid complex multi-subject animations</li>
                <li>• Portraits work best for facial animations</li>
                <li>• Landscapes are great for parallax effects</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
