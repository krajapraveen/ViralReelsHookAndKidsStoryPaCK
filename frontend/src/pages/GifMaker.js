import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Upload, Wand2, Loader2, Download, Share2, RefreshCw, Trash2, Sparkles, Image, Heart, Smile, PartyPopper, ThumbsUp, Music, Hand, Lock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';

export default function GifMaker() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [emotions, setEmotions] = useState({});
  const [styles, setStyles] = useState({});
  const [backgrounds, setBackgrounds] = useState({});
  const [creditCosts, setCreditCosts] = useState({});
  const [pricing, setPricing] = useState({ generate: 10, download: 15 });
  
  // Generation state
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedEmotion, setSelectedEmotion] = useState('happy');
  const [selectedStyle, setSelectedStyle] = useState('cartoon');
  const [selectedBackground, setSelectedBackground] = useState('transparent');
  const [addText, setAddText] = useState('');
  const [animationIntensity, setAnimationIntensity] = useState('medium');
  
  // Batch mode
  const [batchMode, setBatchMode] = useState(false);
  const [selectedEmotions, setSelectedEmotions] = useState([]);
  
  // Results
  const [currentJob, setCurrentJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [pollingInterval, setPollingInterval] = useState(null);

  const emotionIcons = {
    happy: '😀',
    sad: '😢',
    excited: '🤩',
    laughing: '😂',
    surprised: '😲',
    thinking: '🤔',
    dancing: '🕺',
    waving: '👋',
    jumping: '🦘',
    hearts: '❤️',
    thumbsup: '👍',
    celebrate: '🎉'
  };

  useEffect(() => {
    fetchCredits();
    fetchEmotions();
    fetchHistory();
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await api.get('/api/credits/balance');
      setCredits(response.data.credits);
    } catch (error) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchEmotions = async () => {
    try {
      const response = await api.get('/api/gif-maker/emotions');
      setEmotions(response.data.emotions || {});
      setStyles(response.data.styles || {});
      setBackgrounds(response.data.backgrounds || {});
      setCreditCosts(response.data.credits || {});
      if (response.data.pricing) {
        setPricing(response.data.pricing);
      }
    } catch (error) {
      console.error('Failed to fetch emotions');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await api.get('/api/gif-maker/history?size=12');
      setHistory(response.data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch history');
    }
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Image too large. Max 10MB.');
        e.target.value = ''; // Clear file input
        return;
      }
      
      // CRITICAL: Reset ALL previous state when new photo uploaded
      // Clear previous photo and preview
      if (photoPreview) {
        URL.revokeObjectURL(photoPreview); // Clean up memory
      }
      
      // Reset generation state
      setCurrentJob(null);
      stopGifPolling();
      setLoading(false);
      
      // Clear toast tracking for fresh generation
      toastShownRef.current = {};
      
      // Set new photo
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
      
      // Keep emotion/style selection but clear any cached results
      console.log('New photo uploaded - state reset');
    }
  };

  // Clear file input and reset state
  const clearPhoto = () => {
    if (photoPreview) {
      URL.revokeObjectURL(photoPreview);
    }
    setPhoto(null);
    setPhotoPreview(null);
    setCurrentJob(null);
    stopGifPolling();
    setLoading(false);
    toastShownRef.current = {};
    
    // Clear file input element
    const fileInput = document.getElementById('gif-photo-input');
    if (fileInput) fileInput.value = '';
  };

  // Track which jobs have shown toast using ref to prevent loops
  const toastShownRef = React.useRef({});
  const pollingRef = React.useRef(null);
  const isPollingRef = React.useRef(false);

  const stopGifPolling = useCallback(() => {
    isPollingRef.current = false;
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [pollingInterval]);

  const pollJobStatus = useCallback(async (jobId) => {
    // Prevent polling if already stopped
    if (!isPollingRef.current) return;
    
    try {
      const response = await api.get(`/api/gif-maker/job/${jobId}`);
      setCurrentJob(response.data);
      
      if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
        // Stop polling immediately
        stopGifPolling();
        setLoading(false);
        fetchCredits();
        fetchHistory();
        
        // Only show toast once per job using ref (not state)
        if (!toastShownRef.current[jobId]) {
          toastShownRef.current[jobId] = true;
          if (response.data.status === 'COMPLETED') {
            toast.success('GIF generated successfully!');
          } else {
            toast.error('Generation failed. Please try again.');
          }
        }
      }
    } catch (error) {
      console.error('Poll error:', error);
    }
  }, [stopGifPolling]);

  const generateGif = async () => {
    if (!photo) {
      toast.error('Please upload a photo');
      return;
    }
    
    if (!selectedEmotion) {
      toast.error('Please select an emotion/GIF template');
      return;
    }
    
    const cost = pricing.generate || 10;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    // CRITICAL: Clear previous results and stop any existing polling
    setCurrentJob(null);
    stopGifPolling();
    setLoading(true);
    toastShownRef.current = {}; // Reset toast tracking
    
    try {
      const formData = new FormData();
      
      // CRITICAL: Always append fresh file and parameters
      formData.append('photo', photo, photo.name); // Include filename
      formData.append('emotion', selectedEmotion);
      formData.append('style', selectedStyle);
      formData.append('background', selectedBackground);
      formData.append('animation_intensity', animationIntensity);
      formData.append('timestamp', Date.now().toString()); // Prevent caching
      if (addText) formData.append('add_text', addText);
      
      const response = await api.post('/api/gif-maker/generate', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache'
        }
      });
      
      setCurrentJob({ id: response.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Generation started!');
      
      // Start fresh polling
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.jobId), 2000);
      pollingRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate GIF');
    }
  };

  // Handle download with credit check
  const handleDownload = async (jobId) => {
    try {
      const response = await api.post(`/api/gif-maker/download/${jobId}`);
      
      if (response.data.success) {
        toast.success(response.data.alreadyPurchased ? 'Re-downloading...' : `Downloaded! ${response.data.creditsDeducted} credits used`);
        
        // Trigger download
        const url = response.data.downloadUrl?.startsWith('http') ? response.data.downloadUrl : `${process.env.REACT_APP_BACKEND_URL}${response.data.downloadUrl}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `gif_${jobId.slice(0, 8)}.gif`;
        link.click();
        
        fetchCredits();
        fetchHistory();
      } else {
        if (response.data.error === 'INSUFFICIENT_CREDITS') {
          toast.error(response.data.message);
        } else if (response.data.error === 'NO_SUBSCRIPTION') {
          toast.error('Please subscribe to download. Go to Settings > Subscription');
        }
      }
    } catch (error) {
      toast.error('Download failed. Please try again.');
    }
  };

  const generateBatch = async () => {
    if (!photo) {
      toast.error('Please upload a photo');
      return;
    }
    
    if (selectedEmotions.length < 2) {
      toast.error('Select at least 2 emotions for batch mode');
      return;
    }
    
    const cost = selectedEmotions.length <= 5 ? creditCosts.batch_5 : creditCosts.batch_10;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    // CRITICAL: Clear previous results
    setCurrentJob(null);
    stopGifPolling();
    setLoading(true);
    toastShownRef.current = {};
    
    try {
      const formData = new FormData();
      formData.append('photo', photo, photo.name);
      formData.append('emotions', selectedEmotions.join(','));
      formData.append('style', selectedStyle);
      formData.append('timestamp', Date.now().toString()); // Prevent caching
      
      const response = await api.post('/api/gif-maker/generate-batch', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Cache-Control': 'no-cache'
        }
      });
      
      setCurrentJob({ id: response.data.batchId, status: 'QUEUED', type: 'batch' });
      toast.success('Batch generation started!');
      
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.batchId), 2000);
      pollingRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate batch');
    }
  };

  const toggleEmotionSelection = (emotion) => {
    if (selectedEmotions.includes(emotion)) {
      setSelectedEmotions(selectedEmotions.filter(e => e !== emotion));
    } else if (selectedEmotions.length < 10) {
      setSelectedEmotions([...selectedEmotions, emotion]);
    }
  };

  const deleteJob = async (jobId) => {
    try {
      await api.delete(`/api/gif-maker/job/${jobId}`);
      toast.success('Deleted');
      fetchHistory();
      if (currentJob?.id === jobId) setCurrentJob(null);
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-pink-900/20 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span>Dashboard</span>
              </Link>
              <div className="flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-pink-400" />
                <h1 className="text-2xl font-bold text-white">GIF Maker</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-gradient-to-r from-pink-500/20 to-purple-500/20 border border-pink-500/30 rounded-full px-4 py-2">
                <span className="text-pink-300 font-medium">{credits.toLocaleString()} Credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Turn Your Photos into <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-purple-400">Fun Reaction GIFs</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Create your own WhatsApp reaction GIFs! Kids-safe animated stickers from your photos.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Controls */}
          <div className="space-y-6">
            {/* Photo Upload */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5 text-pink-400" />
                Upload Your Photo
              </h3>
              
              <div 
                className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-pink-500 transition-colors cursor-pointer"
                onClick={() => document.getElementById('gif-photo-input').click()}
              >
                {photoPreview ? (
                  <div className="relative">
                    <img src={photoPreview} alt="Preview" className="max-h-48 mx-auto rounded-lg" />
                    <Button
                      variant="destructive"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        clearPhoto();
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <Upload className="w-12 h-12 mx-auto text-slate-500 mb-4" />
                    <p className="text-slate-400">Click to upload or drag and drop</p>
                    <p className="text-sm text-slate-500">PNG, JPG, WEBP up to 10MB</p>
                  </>
                )}
              </div>
              <input
                id="gif-photo-input"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handlePhotoChange}
                data-testid="gif-photo-input"
              />
            </div>

            {/* Mode Toggle */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Generation Mode</h3>
                <div className="flex gap-2">
                  <Button 
                    variant={!batchMode ? "default" : "outline"}
                    size="sm"
                    onClick={() => setBatchMode(false)}
                    className={!batchMode ? "bg-pink-600" : ""}
                  >
                    Single
                  </Button>
                  <Button 
                    variant={batchMode ? "default" : "outline"}
                    size="sm"
                    onClick={() => setBatchMode(true)}
                    className={batchMode ? "bg-pink-600" : ""}
                  >
                    Batch
                  </Button>
                </div>
              </div>

              {!batchMode ? (
                /* Single Mode - Emotion Selection */
                <div>
                  <label className="block text-sm text-slate-400 mb-3">Select Emotion</label>
                  <div className="grid grid-cols-4 gap-3">
                    {Object.entries(emotions).map(([key, emotion]) => (
                      <button
                        key={key}
                        onClick={() => setSelectedEmotion(key)}
                        className={`p-3 rounded-lg border-2 transition-all ${
                          selectedEmotion === key 
                            ? 'border-pink-500 bg-pink-500/20' 
                            : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                        }`}
                        data-testid={`emotion-${key}`}
                      >
                        <span className="text-2xl block mb-1">{emotionIcons[key] || '😀'}</span>
                        <span className="text-xs text-slate-300">{emotion.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Batch Mode - Multiple Selection */
                <div>
                  <label className="block text-sm text-slate-400 mb-3">
                    Select Multiple Emotions ({selectedEmotions.length}/10)
                  </label>
                  <div className="grid grid-cols-4 gap-3">
                    {Object.entries(emotions).map(([key, emotion]) => (
                      <button
                        key={key}
                        onClick={() => toggleEmotionSelection(key)}
                        className={`p-3 rounded-lg border-2 transition-all ${
                          selectedEmotions.includes(key) 
                            ? 'border-pink-500 bg-pink-500/20' 
                            : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                        }`}
                      >
                        <span className="text-2xl block mb-1">{emotionIcons[key] || '😀'}</span>
                        <span className="text-xs text-slate-300">{emotion.name}</span>
                        {selectedEmotions.includes(key) && (
                          <span className="absolute -top-1 -right-1 w-4 h-4 bg-pink-500 rounded-full text-xs text-white">✓</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Style & Options */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-lg font-bold text-white mb-4">Style & Options</h3>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Style</label>
                  <Select value={selectedStyle} onValueChange={setSelectedStyle}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white" data-testid="gif-style-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      {Object.entries(styles).map(([key, style]) => (
                        <SelectItem key={key} value={key} className="text-white">{style.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Background</label>
                  <Select value={selectedBackground} onValueChange={setSelectedBackground}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      {Object.entries(backgrounds).map(([key, name]) => (
                        <SelectItem key={key} value={key} className="text-white">{name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {!batchMode && (
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Add Text (optional)</label>
                  <Input
                    placeholder="Text to add to the GIF..."
                    value={addText}
                    onChange={(e) => setAddText(e.target.value)}
                    className="bg-slate-700 border-slate-600 text-white"
                    data-testid="gif-text-input"
                  />
                </div>
              )}

              {/* Animation Intensity */}
              <div>
                <label className="block text-sm text-slate-400 mb-2">Animation Intensity</label>
                <Select value={animationIntensity} onValueChange={setAnimationIntensity}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="simple" className="text-white">Simple (4 frames - Faster)</SelectItem>
                    <SelectItem value="medium" className="text-white">Medium (8 frames - Balanced)</SelectItem>
                    <SelectItem value="complex" className="text-white">Complex (12 frames - Detailed)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Generate Button */}
            <Button 
              onClick={batchMode ? generateBatch : generateGif}
              disabled={loading || !photo || (batchMode && selectedEmotions.length < 2)}
              className="w-full py-6 text-lg bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
              data-testid="generate-gif-btn"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> <span className="text-white">Generating...</span></>
              ) : (
                <><Wand2 className="w-5 h-5 mr-2" /> <span className="text-white">Generate {batchMode ? `${selectedEmotions.length} GIFs` : 'GIF'} ({pricing.generate} credits)</span></>
              )}
            </Button>

            {/* Credit Info */}
            <div className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-4">
              <p className="text-pink-300 text-sm">
                <Sparkles className="w-4 h-4 inline mr-2" />
                Generate: <strong>{pricing.generate} credits</strong> | Download: <strong>{pricing.download} credits</strong>
              </p>
            </div>
          </div>

          {/* Right: Results */}
          <div className="space-y-6">
            {/* Current Result */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h3 className="text-xl font-bold text-white mb-4">Your GIF</h3>
              
              {currentJob ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      currentJob.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                      currentJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                      currentJob.status === 'QUEUED' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-yellow-500/20 text-yellow-400 animate-pulse'
                    }`}>
                      {currentJob.status === 'PROCESSING' ? 'GENERATING...' : currentJob.status}
                    </span>
                    {currentJob.progressMessage && (
                      <span className="text-slate-400 text-sm flex items-center gap-2">
                        {currentJob.status === 'PROCESSING' && (
                          <Loader2 className="w-4 h-4 animate-spin text-pink-400" />
                        )}
                        {currentJob.progressMessage}
                      </span>
                    )}
                  </div>
                  
                  {/* Enhanced Progress Bar */}
                  {(currentJob.status === 'PROCESSING' || currentJob.status === 'QUEUED') && (
                    <div className="space-y-3 bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-400">Progress</span>
                        <span className="text-pink-400 font-bold">{currentJob.progress || 0}%</span>
                      </div>
                      <div className="relative">
                        <Progress value={currentJob.progress || 0} className="h-3" />
                        <div 
                          className="absolute top-0 left-0 h-3 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full transition-all duration-500"
                          style={{ width: `${currentJob.progress || 0}%` }}
                        />
                      </div>
                      
                      {/* Step Indicators */}
                      <div className="flex justify-between text-xs text-slate-500 mt-2">
                        <span className={currentJob.progress >= 5 ? 'text-green-400' : ''}>Initialize</span>
                        <span className={currentJob.progress >= 30 ? 'text-green-400' : ''}>Generate</span>
                        <span className={currentJob.progress >= 85 ? 'text-green-400' : ''}>Assemble</span>
                        <span className={currentJob.progress >= 100 ? 'text-green-400' : ''}>Done</span>
                      </div>
                      
                      {/* Estimated Time */}
                      {currentJob.progress < 100 && currentJob.progress > 0 && (
                        <p className="text-xs text-slate-500 text-center mt-2">
                          Estimated time remaining: ~{Math.max(1, Math.round((100 - currentJob.progress) / 10))}s
                        </p>
                      )}
                    </div>
                  )}
                  
                  {currentJob.resultUrl && (
                    <div 
                      className="rounded-lg overflow-hidden border border-slate-600 bg-slate-700 relative"
                      onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}
                    >
                      <img 
                        src={currentJob.resultUrl?.startsWith('http') ? currentJob.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${currentJob.resultUrl}`} 
                        alt="Generated GIF" 
                        className="w-full max-w-sm mx-auto select-none pointer-events-none"
                        draggable="false"
                      />
                      {!currentJob.downloaded && (
                        <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                          <div className="bg-slate-800/90 rounded-lg p-3 text-center">
                            <Lock className="w-6 h-6 mx-auto mb-2 text-pink-400" />
                            <p className="text-xs text-slate-300">Pay to download</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {currentJob.results && currentJob.results.length > 0 && (
                    <div 
                      className="grid grid-cols-3 gap-4"
                      onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}
                    >
                      {currentJob.results.map((result, i) => (
                        <div key={i} className="rounded-lg overflow-hidden border border-slate-600 bg-slate-700">
                          <img 
                            src={result.url?.startsWith('http') ? result.url : `${process.env.REACT_APP_BACKEND_URL}${result.url}`} 
                            alt={result.emotion} 
                            className="w-full select-none pointer-events-none"
                            draggable="false"
                          />
                          <div className="p-2 text-center">
                            <span className="text-xl">{result.emoji}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {currentJob.status === 'COMPLETED' && (currentJob.resultUrl || currentJob.results) && (
                    <div className="flex gap-2">
                      <Button 
                        className="flex-1 bg-pink-600 hover:bg-pink-700 text-white"
                        onClick={() => handleDownload(currentJob.id)}
                      >
                        <Download className="w-4 h-4 mr-2" /> 
                        <span className="text-white">Download ({currentJob.downloaded ? 'Free' : `${pricing.download} credits`})</span>
                      </Button>
                      <Button 
                        variant="outline" 
                        className="flex-1"
                        onClick={() => {
                          navigator.clipboard.writeText(`${window.location.origin}/api/gif-maker/share/${currentJob.id}`);
                          toast.success('Share link copied!');
                        }}
                      >
                        <Share2 className="w-4 h-4 mr-2" /> <span className="text-white">Share</span>
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <p>Your GIF will appear here</p>
                  <p className="text-sm mt-2">Upload a photo and select an emotion to start</p>
                </div>
              )}
            </div>

            {/* History */}
            {history.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-lg font-bold text-white mb-4">Recent GIFs</h3>
                <div className="grid grid-cols-3 gap-3">
                  {history.slice(0, 9).map((job) => {
                    const getImageUrl = (url) => {
                      if (!url) return null;
                      if (url.startsWith('http')) return url;
                      return `${process.env.REACT_APP_BACKEND_URL}${url}`;
                    };
                    
                    const imageUrl = getImageUrl(job.resultUrl) || getImageUrl(job.results?.[0]?.url);
                    
                    return (
                      <div key={job.id} className="relative group rounded-lg overflow-hidden border border-slate-600">
                        {imageUrl ? (
                          <img 
                            src={imageUrl} 
                            alt="GIF" 
                            className="w-full aspect-square object-cover"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextSibling.style.display = 'flex';
                            }}
                          />
                        ) : null}
                        <div 
                          className={`w-full aspect-square bg-gradient-to-br from-pink-500/30 to-purple-500/30 ${imageUrl ? 'hidden' : 'flex'} items-center justify-center`}
                        >
                          <span className="text-2xl">{emotionIcons[job.emotion] || '🎨'}</span>
                          <span className="text-xs text-white ml-1">{job.emotion || 'happy'}</span>
                        </div>
                        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                          {imageUrl && (
                            <Button size="sm" variant="ghost" onClick={() => window.open(imageUrl, '_blank')}>
                              <Download className="w-4 h-4" />
                            </Button>
                          )}
                          <Button size="sm" variant="ghost" onClick={() => deleteJob(job.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Safety Notice */}
        <div className="mt-8 bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <p className="text-sm text-green-300 text-center">
            ✅ <strong>Kids-Safe Platform:</strong> This platform generates only kid-friendly, family-safe GIFs. 
            Content involving violence, adult themes, or inappropriate material is automatically blocked.
          </p>
        </div>
      </main>
    </div>
  );
}
