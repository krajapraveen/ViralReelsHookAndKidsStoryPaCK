import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Upload, Wand2, Image, BookOpen, Palette, Loader2, Download, Copy, Check, RefreshCw, Trash2, Settings, Key, Sparkles, Grid3X3, Layers, Lock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Checkbox } from '../components/ui/checkbox';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';

export default function ComixAI() {
  const [credits, setCredits] = useState(0);
  const [activeTab, setActiveTab] = useState('character');
  const [loading, setLoading] = useState(false);
  const [styles, setStyles] = useState({});
  const [layouts, setLayouts] = useState({});
  const [creditCosts, setCreditCosts] = useState({});
  
  // Character generation state
  const [characterPhoto, setCharacterPhoto] = useState(null);
  const [characterPhotoPreview, setCharacterPhotoPreview] = useState(null);
  const [characterStyle, setCharacterStyle] = useState('classic');
  const [characterType, setCharacterType] = useState('portrait');
  const [customPrompt, setCustomPrompt] = useState('');
  const [removeBackground, setRemoveBackground] = useState(false);
  const [characterNegativePrompt, setCharacterNegativePrompt] = useState('');
  
  // Panel generation state
  const [sceneDescription, setSceneDescription] = useState('');
  const [panelStyle, setPanelStyle] = useState('classic');
  const [panelCount, setPanelCount] = useState('1');
  const [genre, setGenre] = useState('action');
  const [mood, setMood] = useState('exciting');
  const [includeSpeech, setIncludeSpeech] = useState(true);
  const [speechText, setSpeechText] = useState('');
  const [panelNegativePrompt, setPanelNegativePrompt] = useState('');
  
  // Story mode state
  const [storyPrompt, setStoryPrompt] = useState('');
  const [storyStyle, setStoryStyle] = useState('classic');
  const [storyPanelCount, setStoryPanelCount] = useState('6');
  const [storyGenre, setStoryGenre] = useState('adventure');
  const [autoDialogue, setAutoDialogue] = useState(true);
  const [characterImages, setCharacterImages] = useState([]);
  const [characterPreviews, setCharacterPreviews] = useState([]);
  const [storyNegativePrompt, setStoryNegativePrompt] = useState('');
  
  // Pricing state
  const [pricing, setPricing] = useState({ generate: 10, download: 15, download_story: 20 });
  
  // Separate job states for each tab
  const [characterJob, setCharacterJob] = useState(null);
  const [panelJob, setPanelJob] = useState(null);
  const [storyJob, setStoryJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [pollingInterval, setPollingInterval] = useState(null);

  useEffect(() => {
    fetchCredits();
    fetchStyles();
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

  const fetchStyles = async () => {
    try {
      const response = await api.get('/api/comix/styles');
      setStyles(response.data.styles || {});
      setLayouts(response.data.layouts || {});
      setCreditCosts(response.data.credits || {});
      if (response.data.pricing) {
        setPricing(response.data.pricing);
      }
    } catch (error) {
      console.error('Failed to fetch styles');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await api.get('/api/comix/history?size=10');
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
        e.target.value = ''; // Clear input
        return;
      }
      
      // CRITICAL: Reset previous state when new photo uploaded
      if (characterPhotoPreview) {
        URL.revokeObjectURL(characterPhotoPreview);
      }
      
      // Clear previous result
      setCharacterJob(null);
      stopPolling();
      toastShownRef.current = {};
      
      setCharacterPhoto(file);
      setCharacterPhotoPreview(URL.createObjectURL(file));
    }
  };

  // Clear character photo and reset state
  const clearCharacterPhoto = () => {
    if (characterPhotoPreview) {
      URL.revokeObjectURL(characterPhotoPreview);
    }
    setCharacterPhoto(null);
    setCharacterPhotoPreview(null);
    setCharacterJob(null);
    stopPolling();
    toastShownRef.current = {};
    
    const fileInput = document.getElementById('comix-character-photo-input');
    if (fileInput) fileInput.value = '';
  };

  // Handle character images for story mode
  const handleCharacterImagesChange = (e) => {
    const files = Array.from(e.target.files).slice(0, 5); // Max 5 images
    const validFiles = files.filter(f => f.size <= 10 * 1024 * 1024);
    
    if (validFiles.length < files.length) {
      toast.warning('Some images were too large (max 10MB each)');
    }
    
    // CRITICAL: Clear previous previews to prevent memory leaks
    characterPreviews.forEach(url => URL.revokeObjectURL(url));
    
    // Clear previous story result
    setStoryJob(null);
    stopPolling();
    toastShownRef.current = {};
    
    setCharacterImages(validFiles);
    setCharacterPreviews(validFiles.map(f => URL.createObjectURL(f)));
  };

  const removeCharacterImage = (index) => {
    setCharacterImages(prev => prev.filter((_, i) => i !== index));
    setCharacterPreviews(prev => prev.filter((_, i) => i !== index));
  };

  // Track if toast has been shown for current job
  const toastShownRef = React.useRef({});
  const pollingIntervalRef = React.useRef(null);
  const isPollingRef = React.useRef(false);

  const stopPolling = useCallback(() => {
    isPollingRef.current = false;
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [pollingInterval]);

  const pollJobStatus = useCallback(async (jobId, jobType) => {
    // Prevent polling if already stopped
    if (!isPollingRef.current) return;
    
    try {
      const response = await api.get(`/api/comix/job/${jobId}`);
      
      // Update the correct job state based on type
      if (jobType === 'character') {
        setCharacterJob(response.data);
      } else if (jobType === 'panel') {
        setPanelJob(response.data);
      } else if (jobType === 'story') {
        setStoryJob(response.data);
      }
      
      if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
        // Stop polling immediately
        stopPolling();
        setLoading(false);
        fetchCredits();
        fetchHistory();
        
        // Only show toast once per job using ref (not state)
        if (!toastShownRef.current[jobId]) {
          toastShownRef.current[jobId] = true;
          if (response.data.status === 'COMPLETED') {
            toast.success('Comic generated successfully!');
          } else {
            toast.error('Generation failed. Please try again.');
          }
        }
      }
    } catch (error) {
      console.error('Poll error:', error);
    }
  }, [stopPolling]);

  const generateCharacter = async () => {
    if (!characterPhoto) {
      toast.error('Please upload a photo');
      return;
    }
    
    const cost = pricing.generate || 10;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    // CRITICAL: Clear previous results and stop polling
    setCharacterJob(null);
    stopPolling();
    setLoading(true);
    toastShownRef.current = {};
    
    try {
      const formData = new FormData();
      formData.append('photo', characterPhoto, characterPhoto.name);
      formData.append('style', characterStyle);
      formData.append('character_type', characterType);
      formData.append('remove_background', removeBackground.toString());
      formData.append('timestamp', Date.now().toString()); // Prevent caching
      if (customPrompt) formData.append('custom_prompt', customPrompt);
      if (characterNegativePrompt) formData.append('negative_prompt', characterNegativePrompt);
      
      const response = await api.post('/api/comix/generate-character', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Cache-Control': 'no-cache'
        }
      });
      
      setCharacterJob({ id: response.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Generation started!');
      
      // Start fresh polling
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.jobId, 'character'), 2000);
      pollingIntervalRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate character');
    }
  };

  const generatePanel = async () => {
    if (!sceneDescription.trim()) {
      toast.error('Please describe the scene');
      return;
    }
    
    const cost = pricing.generate || 10;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    setLoading(true);
    setToastShown({});
    try {
      const formData = new FormData();
      formData.append('scene_description', sceneDescription);
      formData.append('style', panelStyle);
      formData.append('panel_count', panelCount);
      formData.append('genre', genre);
      formData.append('mood', mood);
      formData.append('include_speech_bubbles', includeSpeech.toString());
      if (speechText) formData.append('speech_text', speechText);
      if (panelNegativePrompt) formData.append('negative_prompt', panelNegativePrompt);
      
      const response = await api.post('/api/comix/generate-panel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setPanelJob({ id: response.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Panel generation started!');
      
      // Reset toast shown state for new job and start polling
      toastShownRef.current = {};
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.jobId, 'panel'), 2000);
      pollingIntervalRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate panel');
    }
  };

  const generateStory = async () => {
    if (!storyPrompt.trim()) {
      toast.error('Please enter a story idea');
      return;
    }
    
    const cost = pricing.generate || 10;
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      return;
    }
    
    setLoading(true);
    setToastShown({});
    try {
      const formData = new FormData();
      formData.append('story_prompt', storyPrompt);
      formData.append('style', storyStyle);
      formData.append('panel_count', storyPanelCount);
      formData.append('genre', storyGenre);
      formData.append('auto_dialogue', autoDialogue.toString());
      if (storyNegativePrompt) formData.append('negative_prompt', storyNegativePrompt);
      
      // Add character images if provided
      characterImages.forEach((img, i) => {
        formData.append('character_images', img);
      });
      
      const response = await api.post('/api/comix/generate-story', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setStoryJob({ id: response.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success(`Story generation started! ${characterImages.length > 0 ? `Using ${characterImages.length} character image(s)` : ''}`);
      
      // Reset toast shown state for new job and start polling
      toastShownRef.current = {};
      isPollingRef.current = true;
      const interval = setInterval(() => pollJobStatus(response.data.jobId, 'story'), 2000);
      pollingIntervalRef.current = interval;
      setPollingInterval(interval);
      
    } catch (error) {
      setLoading(false);
      toast.error(error.response?.data?.detail || 'Failed to generate story');
    }
  };

  // Handle download with credit check
  const handleDownload = async (jobId, jobType = 'character') => {
    try {
      const response = await api.post(`/api/comix/download/${jobId}`);
      
      if (response.data.success) {
        toast.success(response.data.alreadyPurchased ? 'Re-downloading...' : `Downloaded! ${response.data.creditsDeducted} credits used`);
        
        // Update downloaded status on job
        if (jobType === 'character') {
          setCharacterJob(prev => prev ? {...prev, downloaded: true} : null);
        } else if (jobType === 'panel') {
          setPanelJob(prev => prev ? {...prev, downloaded: true} : null);
        } else if (jobType === 'story') {
          setStoryJob(prev => prev ? {...prev, downloaded: true} : null);
        }
        
        // Trigger actual download for each URL
        response.data.downloadUrls?.forEach((url, i) => {
          const fullUrl = url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`;
          const link = document.createElement('a');
          link.href = fullUrl;
          link.download = `comic_${jobId.slice(0, 8)}_${i + 1}.png`;
          link.click();
        });
        
        fetchCredits();
      } else {
        // Show appropriate error based on subscription status
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

  const deleteJob = async (jobId) => {
    try {
      await api.delete(`/api/comix/job/${jobId}`);
      toast.success('Deleted');
      fetchHistory();
      // Clear the appropriate job state
      if (characterJob?.id === jobId) setCharacterJob(null);
      if (panelJob?.id === jobId) setPanelJob(null);
      if (storyJob?.id === jobId) setStoryJob(null);
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
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
                <Sparkles className="w-6 h-6 text-purple-400" />
                <h1 className="text-2xl font-bold text-white">Comix AI</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-full px-4 py-2">
                <span className="text-purple-300 font-medium">{credits.toLocaleString()} Credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="text-center mb-8">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Transform Photos into <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">Comic Art</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Create stunning comic characters, panels, and full stories from your photos. Choose from 9 unique styles.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-lg mx-auto grid-cols-3 mb-8 bg-slate-800/50">
            <TabsTrigger value="character" className="data-[state=active]:bg-purple-600 text-white data-[state=inactive]:text-slate-300" data-testid="tab-character">
              <Image className="w-4 h-4 mr-2" /> <span className="text-white">Character</span>
            </TabsTrigger>
            <TabsTrigger value="panel" className="data-[state=active]:bg-purple-600 text-white data-[state=inactive]:text-slate-300" data-testid="tab-panel">
              <Grid3X3 className="w-4 h-4 mr-2" /> <span className="text-white">Panels</span>
            </TabsTrigger>
            <TabsTrigger value="story" className="data-[state=active]:bg-purple-600 text-white data-[state=inactive]:text-slate-300" data-testid="tab-story">
              <BookOpen className="w-4 h-4 mr-2" /> <span className="text-white">Story Mode</span>
            </TabsTrigger>
          </TabsList>

          {/* Character Tab */}
          <TabsContent value="character">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Upload className="w-5 h-5 text-purple-400" />
                  Photo to Comic Character
                </h3>
                
                {/* Photo Upload */}
                <div className="mb-6">
                  <label className="block text-sm text-slate-400 mb-2">Upload Photo</label>
                  <div 
                    className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-purple-500 transition-colors cursor-pointer"
                    onClick={() => document.getElementById('photo-upload').click()}
                  >
                    {characterPhotoPreview ? (
                      <img src={characterPhotoPreview} alt="Preview" className="max-h-48 mx-auto rounded-lg" />
                    ) : (
                      <>
                        <Upload className="w-12 h-12 mx-auto text-slate-500 mb-4" />
                        <p className="text-slate-400">Click to upload or drag and drop</p>
                        <p className="text-sm text-slate-500">PNG, JPG, WEBP up to 10MB</p>
                      </>
                    )}
                  </div>
                  <input
                    id="photo-upload"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handlePhotoChange}
                    data-testid="character-photo-input"
                  />
                </div>

                {/* Style Selection */}
                <div className="mb-4">
                  <label className="block text-sm text-slate-400 mb-2">Comic Style</label>
                  <Select value={characterStyle} onValueChange={setCharacterStyle}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white" data-testid="character-style-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      {Object.entries(styles).map(([key, style]) => (
                        <SelectItem key={key} value={key} className="text-white hover:bg-slate-700">
                          {style.name} - {style.description}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Character Type */}
                <div className="mb-4">
                  <label className="block text-sm text-slate-400 mb-2">Character Type</label>
                  <Select value={characterType} onValueChange={setCharacterType}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white" data-testid="character-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="portrait" className="text-white hover:bg-slate-700">Portrait (10 credits)</SelectItem>
                      <SelectItem value="fullbody" className="text-white hover:bg-slate-700">Full Body (10 credits)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Options */}
                <div className="mb-4 flex items-center gap-2">
                  <Checkbox 
                    id="remove-bg" 
                    checked={removeBackground} 
                    onCheckedChange={setRemoveBackground}
                  />
                  <label htmlFor="remove-bg" className="text-sm text-slate-300">Remove background (transparent)</label>
                </div>

                {/* Custom Prompt */}
                <div className="mb-4">
                  <label className="block text-sm text-slate-400 mb-2">Custom Details (optional)</label>
                  <Input
                    placeholder="Add specific details like clothing, accessories..."
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    className="bg-slate-700 border-slate-600"
                    data-testid="character-custom-prompt"
                  />
                </div>

                {/* Negative Prompt */}
                <div className="mb-6">
                  <label className="block text-sm text-slate-400 mb-2">Negative Prompt (optional)</label>
                  <Input
                    placeholder="Exclude elements like: blurry, low quality, text..."
                    value={characterNegativePrompt}
                    onChange={(e) => setCharacterNegativePrompt(e.target.value)}
                    className="bg-slate-700 border-slate-600"
                    data-testid="character-negative-prompt"
                  />
                  <p className="text-xs text-slate-500 mt-1">Describe what you DON'T want in the image</p>
                </div>

                <Button 
                  onClick={generateCharacter}
                  disabled={loading || !characterPhoto}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                  data-testid="generate-character-btn"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating...</>
                  ) : (
                    <><Wand2 className="w-4 h-4 mr-2" /> <span className="text-white">Generate Character</span></>
                  )}
                </Button>
              </div>

              {/* Result Panel for Character */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4">Result</h3>
                {characterJob ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        characterJob.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        characterJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {characterJob.status}
                      </span>
                      {characterJob.progressMessage && characterJob.status === 'PROCESSING' && (
                        <span className="text-slate-400 text-sm">{characterJob.progressMessage}</span>
                      )}
                    </div>
                    
                    {/* Progress Bar */}
                    {characterJob.status === 'PROCESSING' && characterJob.progress !== undefined && (
                      <div className="space-y-2">
                        <Progress value={characterJob.progress} className="h-2" />
                        <p className="text-xs text-slate-400 text-center">{characterJob.progress}% complete</p>
                      </div>
                    )}
                    
                    {characterJob.resultUrl && (
                      <div 
                        className="rounded-lg overflow-hidden border border-slate-600 relative"
                        onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}
                      >
                        <img 
                          src={characterJob.resultUrl.startsWith('http') ? characterJob.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${characterJob.resultUrl}`} 
                          alt="Comic Character" 
                          className="w-full select-none pointer-events-none" 
                          draggable="false"
                        />
                        {!characterJob.downloaded && (
                          <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                            <div className="bg-slate-800/90 rounded-lg p-3 text-center">
                              <Lock className="w-6 h-6 mx-auto mb-2 text-purple-400" />
                              <p className="text-xs text-slate-300">Pay to download</p>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {characterJob.status === 'COMPLETED' && characterJob.resultUrl && (
                      <div className="flex gap-2">
                        <Button 
                          className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
                          onClick={() => handleDownload(characterJob.id, 'character')}
                        >
                          <Download className="w-4 h-4 mr-2" /> 
                          <span className="text-white">Download ({characterJob.downloaded ? 'Free' : `${pricing.download} credits`})</span>
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Your comic character will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Panel Tab */}
          <TabsContent value="panel">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <Grid3X3 className="w-5 h-5 text-purple-400" />
                  Comic Panel Generator
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Scene Description *</label>
                    <Textarea
                      placeholder="Describe the scene... e.g., 'A hero standing on a rooftop looking at the city skyline at sunset'"
                      value={sceneDescription}
                      onChange={(e) => setSceneDescription(e.target.value)}
                      className="bg-slate-700 border-slate-600 min-h-24"
                      data-testid="panel-scene-input"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Style</label>
                      <Select value={panelStyle} onValueChange={setPanelStyle}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
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
                      <label className="block text-sm text-slate-400 mb-2">Panel Count</label>
                      <Select value={panelCount} onValueChange={setPanelCount}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="1" className="text-white">1 Panel ({creditCosts.panel_single} cr)</SelectItem>
                          <SelectItem value="3" className="text-white">3 Panels ({creditCosts.panel_multi} cr)</SelectItem>
                          <SelectItem value="4" className="text-white">4 Panels ({creditCosts.panel_multi} cr)</SelectItem>
                          <SelectItem value="6" className="text-white">6 Panels ({creditCosts.panel_multi} cr)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Genre</label>
                      <Select value={genre} onValueChange={setGenre}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="action" className="text-white">Action</SelectItem>
                          <SelectItem value="comedy" className="text-white">Comedy</SelectItem>
                          <SelectItem value="drama" className="text-white">Drama</SelectItem>
                          <SelectItem value="fantasy" className="text-white">Fantasy</SelectItem>
                          <SelectItem value="sci-fi" className="text-white">Sci-Fi</SelectItem>
                          <SelectItem value="slice-of-life" className="text-white">Slice of Life</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Mood</label>
                      <Select value={mood} onValueChange={setMood}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="exciting" className="text-white">Exciting</SelectItem>
                          <SelectItem value="calm" className="text-white">Calm</SelectItem>
                          <SelectItem value="tense" className="text-white">Tense</SelectItem>
                          <SelectItem value="funny" className="text-white">Funny</SelectItem>
                          <SelectItem value="romantic" className="text-white">Romantic</SelectItem>
                          <SelectItem value="mysterious" className="text-white">Mysterious</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Checkbox id="include-speech" checked={includeSpeech} onCheckedChange={setIncludeSpeech} />
                    <label htmlFor="include-speech" className="text-sm text-slate-300">Include speech bubbles</label>
                  </div>

                  {includeSpeech && (
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Speech Text</label>
                      <Input
                        placeholder="What should the character say?"
                        value={speechText}
                        onChange={(e) => setSpeechText(e.target.value)}
                        className="bg-slate-700 border-slate-600"
                      />
                    </div>
                  )}

                  {/* Negative Prompt */}
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Negative Prompt (optional)</label>
                    <Input
                      placeholder="Exclude: blurry, distorted faces, extra limbs..."
                      value={panelNegativePrompt}
                      onChange={(e) => setPanelNegativePrompt(e.target.value)}
                      className="bg-slate-700 border-slate-600"
                      data-testid="panel-negative-prompt"
                    />
                    <p className="text-xs text-slate-500 mt-1">Describe what you DON'T want in the panels</p>
                  </div>

                  <Button 
                    onClick={generatePanel}
                    disabled={loading || !sceneDescription.trim()}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                    data-testid="generate-panel-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
                    <span className="text-white">Generate Panel{panelCount !== '1' ? 's' : ''}</span>
                  </Button>
                </div>
              </div>

              {/* Result Panel for Panels Tab */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4">Result</h3>
                {panelJob ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        panelJob.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        panelJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {panelJob.status}
                      </span>
                      {panelJob.progressMessage && panelJob.status === 'PROCESSING' && (
                        <span className="text-slate-400 text-sm">{panelJob.progressMessage}</span>
                      )}
                    </div>
                    
                    {panelJob.status === 'PROCESSING' && panelJob.progress !== undefined && (
                      <div className="space-y-2">
                        <Progress value={panelJob.progress} className="h-2" />
                        <p className="text-xs text-slate-400 text-center">{panelJob.progress}% complete</p>
                      </div>
                    )}
                    
                    {panelJob.resultUrls && panelJob.resultUrls.length > 0 && (
                      <div 
                        className="grid grid-cols-2 gap-4"
                        onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}
                      >
                        {panelJob.resultUrls.map((url, i) => (
                          <div key={i} className="rounded-lg overflow-hidden border border-slate-600 relative">
                            <img 
                              src={url?.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`}
                              alt={`Panel ${i+1}`} 
                              className="w-full select-none pointer-events-none"
                              draggable="false"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {panelJob.resultUrl && !panelJob.resultUrls && (
                      <div 
                        className="rounded-lg overflow-hidden border border-slate-600 relative"
                        onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}
                      >
                        <img 
                          src={panelJob.resultUrl?.startsWith('http') ? panelJob.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${panelJob.resultUrl}`}
                          alt="Comic Panel" 
                          className="w-full select-none pointer-events-none"
                          draggable="false"
                        />
                      </div>
                    )}
                    
                    {panelJob.status === 'COMPLETED' && (panelJob.resultUrl || panelJob.resultUrls) && (
                      <div className="flex gap-2">
                        <Button 
                          className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
                          onClick={() => handleDownload(panelJob.id, 'panel')}
                        >
                          <Download className="w-4 h-4 mr-2" /> 
                          <span className="text-white">Download ({panelJob.downloaded ? 'Free' : `${pricing.download} credits`})</span>
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <Grid3X3 className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Your comic panels will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Story Mode Tab */}
          <TabsContent value="story">
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                  Comic Story Mode
                </h3>
                <p className="text-slate-400 mb-6">Create a full comic story with multiple panels and auto-generated dialogue.</p>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Story Idea *</label>
                    <Textarea
                      placeholder="Describe your story idea... e.g., 'A young wizard discovers a magical book that can bring drawings to life'"
                      value={storyPrompt}
                      onChange={(e) => setStoryPrompt(e.target.value)}
                      className="bg-slate-700 border-slate-600 min-h-32 text-white"
                      data-testid="story-prompt-input"
                    />
                  </div>

                  {/* Character Images Upload */}
                  <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
                    <label className="block text-sm text-slate-300 mb-2 font-medium">
                      <Upload className="w-4 h-4 inline mr-2" />
                      Character Images (Optional - Max 5)
                    </label>
                    <p className="text-xs text-slate-400 mb-3">Upload photos of characters. The AI will use them as main characters throughout your comic story.</p>
                    
                    <div className="flex flex-wrap gap-2 mb-3">
                      {characterPreviews.map((preview, i) => (
                        <div key={i} className="relative w-16 h-16 rounded-lg overflow-hidden border border-purple-500">
                          <img src={preview} alt={`Character ${i+1}`} className="w-full h-full object-cover" />
                          <button 
                            onClick={() => removeCharacterImage(i)}
                            className="absolute -top-1 -right-1 bg-red-500 rounded-full p-0.5"
                          >
                            <Trash2 className="w-3 h-3 text-white" />
                          </button>
                        </div>
                      ))}
                      {characterImages.length < 5 && (
                        <label className="w-16 h-16 border-2 border-dashed border-slate-500 rounded-lg flex items-center justify-center cursor-pointer hover:border-purple-500 transition-colors">
                          <Upload className="w-5 h-5 text-slate-400" />
                          <input 
                            type="file" 
                            accept="image/*" 
                            multiple 
                            className="hidden" 
                            onChange={handleCharacterImagesChange}
                            data-testid="character-images-input"
                          />
                        </label>
                      )}
                    </div>
                    {characterImages.length > 0 && (
                      <p className="text-xs text-purple-300">{characterImages.length} character(s) will appear in all panels</p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Style</label>
                      <Select value={storyStyle} onValueChange={setStoryStyle}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
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
                      <label className="block text-sm text-slate-400 mb-2">Panels</label>
                      <Select value={storyPanelCount} onValueChange={setStoryPanelCount}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-800 border-slate-700">
                          <SelectItem value="4" className="text-white">4 Panels</SelectItem>
                          <SelectItem value="6" className="text-white">6 Panels</SelectItem>
                          <SelectItem value="9" className="text-white">9 Panels (Full Page)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Genre</label>
                    <Select value={storyGenre} onValueChange={setStoryGenre}>
                      <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="adventure" className="text-white">Adventure</SelectItem>
                        <SelectItem value="comedy" className="text-white">Comedy</SelectItem>
                        <SelectItem value="fantasy" className="text-white">Fantasy</SelectItem>
                        <SelectItem value="sci-fi" className="text-white">Sci-Fi</SelectItem>
                        <SelectItem value="mystery" className="text-white">Mystery</SelectItem>
                        <SelectItem value="slice-of-life" className="text-white">Slice of Life</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-2">
                    <Checkbox id="auto-dialogue" checked={autoDialogue} onCheckedChange={setAutoDialogue} />
                    <label htmlFor="auto-dialogue" className="text-sm text-slate-300">Auto-generate dialogue</label>
                  </div>

                  {/* Negative Prompt */}
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Negative Prompt (optional)</label>
                    <Input
                      placeholder="Exclude: blurry, deformed, bad anatomy..."
                      value={storyNegativePrompt}
                      onChange={(e) => setStoryNegativePrompt(e.target.value)}
                      className="bg-slate-700 border-slate-600"
                      data-testid="story-negative-prompt"
                    />
                    <p className="text-xs text-slate-500 mt-1">Describe what you DON'T want in the story panels</p>
                  </div>

                  <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                    <p className="text-purple-300 text-sm">
                      <Sparkles className="w-4 h-4 inline mr-2" />
                      Generate: <strong>{pricing.generate} credits</strong> | Download: <strong>{pricing.download_story} credits</strong>
                    </p>
                  </div>

                  <Button 
                    onClick={generateStory}
                    disabled={loading || !storyPrompt.trim()}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                    data-testid="generate-story-btn"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BookOpen className="w-4 h-4 mr-2" />}
                    <span className="text-white">Generate Comic Story</span>
                  </Button>
                </div>
              </div>

              {/* Story Result */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 max-h-[800px] overflow-y-auto">
                <h3 className="text-xl font-bold text-white mb-4">Your Comic Story</h3>
                {storyJob ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        storyJob.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                        storyJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {storyJob.status}
                      </span>
                      {storyJob.progressMessage && storyJob.status === 'PROCESSING' && (
                        <span className="text-slate-400 text-sm">{storyJob.progressMessage}</span>
                      )}
                    </div>
                    
                    {storyJob.status === 'PROCESSING' && storyJob.progress !== undefined && (
                      <div className="space-y-2">
                        <Progress value={storyJob.progress} className="h-2" />
                        <p className="text-xs text-slate-400 text-center">{storyJob.progress}% complete</p>
                      </div>
                    )}
                    
                    {storyJob.panels && storyJob.panels.length > 0 && (
                      <div onContextMenu={(e) => { e.preventDefault(); toast.info('Please use Download button to save'); }}>
                        {storyJob.panels.map((panel, i) => (
                          <div key={i} className="rounded-lg overflow-hidden border border-slate-600 bg-slate-700/50 mb-4">
                            <img 
                              src={panel.imageUrl?.startsWith('http') ? panel.imageUrl : `${process.env.REACT_APP_BACKEND_URL}${panel.imageUrl}`}
                              alt={`Panel ${i+1}`} 
                              className="w-full select-none pointer-events-none"
                              draggable="false"
                            />
                            <div className="p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-purple-400 font-medium">{panel.scene}</span>
                                <span className="text-slate-500 text-sm">Panel {panel.panelNumber}</span>
                              </div>
                              {panel.dialogue && (
                                <p className="text-slate-300 text-sm bg-slate-800 rounded px-3 py-2">{panel.dialogue}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {storyJob.status === 'COMPLETED' && storyJob.panels && storyJob.panels.length > 0 && (
                      <div className="flex gap-2 sticky bottom-0 bg-slate-800/90 p-3 rounded-lg">
                        <Button 
                          className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
                          onClick={() => handleDownload(storyJob.id, 'story')}
                        >
                          <Download className="w-4 h-4 mr-2" /> 
                          <span className="text-white">Download Story ({storyJob.downloaded ? 'Free' : `${pricing.download_story} credits`})</span>
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <BookOpen className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                    <p>Your comic story will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* History Section */}
        {history.length > 0 && (
          <div className="mt-12">
            <h3 className="text-xl font-bold text-white mb-4">Recent Creations</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {history.slice(0, 6).map((job) => (
                <div key={job.id} className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden group">
                  {job.resultUrl ? (
                    <img src={job.resultUrl} alt="Comic" className="w-full aspect-square object-cover" />
                  ) : job.panels?.[0]?.imageUrl ? (
                    <img src={job.panels[0].imageUrl} alt="Comic" className="w-full aspect-square object-cover" />
                  ) : (
                    <div className="w-full aspect-square bg-slate-700 flex items-center justify-center">
                      <Sparkles className="w-8 h-8 text-slate-500" />
                    </div>
                  )}
                  <div className="p-2">
                    <p className="text-xs text-slate-400 truncate">{job.type}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>{job.status}</span>
                      <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100" onClick={() => deleteJob(job.id)}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content Policy Notice */}
        <div className="mt-8 bg-slate-800/30 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400 text-center">
            ⚠️ <strong>Content Policy:</strong> Copyrighted characters (Marvel, DC, Disney, etc.) are not allowed. 
            All content must be original. User-uploaded photos must be owned by the user or used with permission.
          </p>
        </div>
      </main>
    </div>
  );
}
