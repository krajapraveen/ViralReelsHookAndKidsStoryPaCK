import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';
import api from '../utils/api';
import analytics from '../utils/analytics';
import { 
  ArrowLeft, Upload, Wand2, Loader2, Film, Image, Mic, 
  Play, Users, BookOpen, Sparkles, ChevronRight, ChevronDown,
  FileText, Download, Edit, Trash2, Eye, Clock, Coins,
  AlertTriangle, CheckCircle, Palette, Music, Video, Pause,
  Volume2, Maximize, Settings, RefreshCw
} from 'lucide-react';

const AGE_GROUPS = [
  { id: 'kids_3_5', name: 'Kids 3-5', description: 'Simple stories, bright colors' },
  { id: 'kids_5_8', name: 'Kids 5-8', description: 'Adventure stories, fun characters' },
  { id: 'kids_8_12', name: 'Kids 8-12', description: 'Complex plots, detailed scenes' },
  { id: 'teens', name: 'Teens 13+', description: 'Mature themes, cinematic style' },
  { id: 'adults', name: 'Adults', description: 'Professional, sophisticated' },
];

const LANGUAGES = [
  { id: 'english', name: 'English' },
  { id: 'hindi', name: 'Hindi' },
  { id: 'spanish', name: 'Spanish' },
  { id: 'french', name: 'French' },
  { id: 'german', name: 'German' },
  { id: 'telugu', name: 'Telugu' },
  { id: 'tamil', name: 'Tamil' },
];

export default function StoryVideoStudio() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  
  // State - Steps: 1: Input, 2: Scenes, 3: Characters, 4: Prompts, 5: Images, 6: Voice, 7: Music, 8: Video
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [styles, setStyles] = useState([]);
  const [pricing, setPricing] = useState(null);
  
  // Story input state
  const [storyText, setStoryText] = useState('');
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState('english');
  const [ageGroup, setAgeGroup] = useState('kids_5_8');
  const [styleId, setStyleId] = useState('storybook');
  
  // Project state
  const [project, setProject] = useState(null);
  const [expandedScene, setExpandedScene] = useState(null);
  const [expandedCharacter, setExpandedCharacter] = useState(null);
  
  // Phase 2: Image Generation
  const [imageProvider, setImageProvider] = useState('openai');
  const [generatedImages, setGeneratedImages] = useState([]);
  
  // Phase 3: Voice Generation
  const [voiceConfig, setVoiceConfig] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [userApiKey, setUserApiKey] = useState('');
  const [generatedVoices, setGeneratedVoices] = useState([]);
  
  // Phase 4: Music & Video
  const [musicLibrary, setMusicLibrary] = useState([]);
  const [selectedMusic, setSelectedMusic] = useState(null);
  const [musicVolume, setMusicVolume] = useState(0.3);
  const [includeWatermark, setIncludeWatermark] = useState(true);
  const [renderJob, setRenderJob] = useState(null);
  
  // Video Player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  // Fetch styles and pricing on mount
  useEffect(() => {
    fetchStyles();
    fetchPricing();
    fetchVoiceConfig();
    fetchMusicLibrary();
    analytics.trackFunnelStep('story_video_studio_view');
  }, []);
  
  const fetchStyles = async () => {
    try {
      const res = await api.get('/api/story-video-studio/styles');
      if (res.data.success) {
        setStyles(res.data.styles);
      }
    } catch (error) {
      console.error('Failed to fetch styles:', error);
    }
  };
  
  const fetchPricing = async () => {
    try {
      const res = await api.get('/api/story-video-studio/pricing');
      if (res.data.success) {
        setPricing(res.data.pricing);
      }
    } catch (error) {
      console.error('Failed to fetch pricing:', error);
    }
  };
  
  const fetchVoiceConfig = async () => {
    try {
      const res = await api.get('/api/story-video-studio/generation/voice/config');
      if (res.data.success) {
        setVoiceConfig(res.data);
      }
    } catch (error) {
      console.error('Failed to fetch voice config:', error);
    }
  };
  
  const fetchMusicLibrary = async () => {
    try {
      const res = await api.get('/api/story-video-studio/generation/music/library');
      if (res.data.success) {
        setMusicLibrary(res.data.music_tracks);
      }
    } catch (error) {
      console.error('Failed to fetch music library:', error);
    }
  };
  
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const allowedTypes = ['.txt', '.pdf', '.docx'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedTypes.includes(ext)) {
      toast.error(`Invalid file type. Allowed: ${allowedTypes.join(', ')}`);
      return;
    }
    
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    formData.append('age_group', ageGroup);
    formData.append('style_id', styleId);
    
    try {
      const res = await api.post('/api/story-video-studio/upload-story', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (res.data.success) {
        setProject(res.data.data);
        setTitle(res.data.data.title);
        setStoryText(res.data.data.original_story);
        toast.success('Story uploaded successfully!');
        setStep(2);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload story');
    } finally {
      setLoading(false);
    }
  };
  
  const createProject = async () => {
    if (storyText.length < 50) {
      toast.error('Story must be at least 50 characters');
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/projects/create', {
        story_text: storyText,
        title: title || 'Untitled Story',
        language,
        age_group: ageGroup,
        style_id: styleId
      });
      
      if (res.data.success) {
        setProject(res.data.data);
        toast.success('Project created! Now generating scenes...');
        await generateScenes(res.data.project_id);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };
  
  const generateScenes = async (projectId) => {
    setLoading(true);
    try {
      const res = await api.post(`/api/story-video-studio/projects/${projectId}/generate-scenes`);
      
      if (res.data.success) {
        setProject(prev => ({
          ...prev,
          ...res.data.data,
          status: 'scenes_generated'
        }));
        toast.success(`Generated ${res.data.data.scenes?.length || 0} scenes!`);
        analytics.trackGeneration('story_video_studio', res.data.data.credits_spent);
        setStep(2);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate scenes');
    } finally {
      setLoading(false);
    }
  };
  
  const getPromptPack = async () => {
    if (!project?.project_id) return;
    
    setLoading(true);
    try {
      const res = await api.get(`/api/story-video-studio/projects/${project.project_id}/prompt-pack`);
      
      if (res.data.success) {
        setProject(prev => ({
          ...prev,
          promptPack: res.data
        }));
        setStep(4);
        toast.success('Prompt pack ready!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to get prompt pack');
    } finally {
      setLoading(false);
    }
  };
  
  const downloadPromptPack = () => {
    if (!project?.promptPack) return;
    
    const data = JSON.stringify(project.promptPack, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.title || 'story'}_prompt_pack.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Prompt pack downloaded!');
  };
  
  // ============================================
  // PHASE 2: IMAGE GENERATION
  // ============================================
  
  const generateImages = async () => {
    if (!project?.project_id) return;
    
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/generation/images', {
        project_id: project.project_id,
        provider: imageProvider
      });
      
      if (res.data.success) {
        setGeneratedImages(res.data.images);
        setProject(prev => ({ ...prev, status: 'images_generated' }));
        toast.success(`Generated ${res.data.images_generated} images!`);
        analytics.trackGeneration('story_video_images', res.data.credits_spent);
        setStep(5); // Go to images display step
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate images');
    } finally {
      setLoading(false);
    }
  };
  
  // ============================================
  // PHASE 3: VOICE GENERATION
  // ============================================
  
  const generateVoices = async () => {
    if (!project?.project_id) return;
    
    // Check if BYO key is required
    if (voiceConfig?.mode === 'BYO_USER_KEY' && !userApiKey) {
      toast.error('Please provide your OpenAI API key for voice generation');
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/generation/voices', {
        project_id: project.project_id,
        voice_id: selectedVoice,
        user_api_key: userApiKey || undefined
      });
      
      if (res.data.success) {
        setGeneratedVoices(res.data.voices);
        setProject(prev => ({ ...prev, status: 'voices_generated' }));
        toast.success(`Generated ${res.data.voices_generated} voice tracks!`);
        analytics.trackGeneration('story_video_voices', res.data.credits_spent);
        setStep(7);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate voices');
    } finally {
      setLoading(false);
    }
  };
  
  // ============================================
  // PHASE 4: VIDEO ASSEMBLY
  // ============================================
  
  const assembleVideo = async () => {
    if (!project?.project_id) return;
    
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/generation/video/assemble', {
        project_id: project.project_id,
        include_watermark: includeWatermark,
        background_music_id: selectedMusic,
        music_volume: musicVolume
      });
      
      if (res.data.success) {
        setRenderJob(res.data);
        toast.success('Video rendering started!');
        // Start polling for status
        pollRenderStatus(res.data.job_id);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start video assembly');
      setLoading(false);
    }
  };
  
  const pollRenderStatus = async (jobId) => {
    const checkStatus = async () => {
      try {
        const res = await api.get(`/api/story-video-studio/generation/video/status/${jobId}`);
        if (res.data.success) {
          setRenderJob(res.data.job);
          
          if (res.data.job.status === 'COMPLETED') {
            setProject(prev => ({ 
              ...prev, 
              status: 'video_rendered',
              final_video_url: res.data.job.output_url 
            }));
            toast.success('Video rendered successfully!');
            setLoading(false);
            setStep(8);
          } else if (res.data.job.status === 'FAILED') {
            toast.error('Video rendering failed: ' + (res.data.job.error || 'Unknown error'));
            setLoading(false);
          } else {
            // Continue polling
            setTimeout(checkStatus, 3000);
          }
        }
      } catch (error) {
        console.error('Failed to check render status:', error);
        setTimeout(checkStatus, 5000);
      }
    };
    
    checkStatus();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app/dashboard">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Film className="w-6 h-6 text-purple-400" />
                Story → Video Studio
              </h1>
              <p className="text-sm text-slate-400">Transform stories into videos with AI</p>
            </div>
          </div>
          
          {/* Progress Steps */}
          <div className="hidden lg:flex items-center gap-1">
            {[
              { icon: FileText, label: 'Story' },
              { icon: BookOpen, label: 'Scenes' },
              { icon: Users, label: 'Characters' },
              { icon: Sparkles, label: 'Prompts' },
              { icon: Image, label: 'Images' },
              { icon: Mic, label: 'Voice' },
              { icon: Music, label: 'Music' },
              { icon: Film, label: 'Video' }
            ].map((item, idx) => (
              <div key={idx} className="flex items-center">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center ${
                  step > idx + 1 ? 'bg-green-500 text-white' :
                  step === idx + 1 ? 'bg-purple-500 text-white' :
                  'bg-slate-700 text-slate-400'
                }`}>
                  {step > idx + 1 ? <CheckCircle className="w-4 h-4" /> : <item.icon className="w-3 h-3" />}
                </div>
                {idx < 7 && <div className={`w-4 h-0.5 ${step > idx + 1 ? 'bg-green-500' : 'bg-slate-700'}`} />}
              </div>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Step 1: Story Input */}
        {step === 1 && (
          <div className="space-y-8">
            {/* Pricing Info */}
            {pricing && (
              <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Coins className="w-5 h-5 text-yellow-400" />
                  Credit Pricing
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <FileText className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{pricing.scene_generation}</p>
                    <p className="text-sm text-slate-400">Scene Generation</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <Image className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{pricing.image_per_scene}</p>
                    <p className="text-sm text-slate-400">Per Image</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <Mic className="w-6 h-6 text-green-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{pricing.voice_per_minute}</p>
                    <p className="text-sm text-slate-400">Voice/Minute</p>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                    <Film className="w-6 h-6 text-pink-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{pricing.video_render}</p>
                    <p className="text-sm text-slate-400">Video Render</p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="grid lg:grid-cols-2 gap-8">
              {/* Story Input */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                  Your Story
                </h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Title (Optional)</label>
                    <Input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="Enter story title..."
                      className="bg-slate-900/50 border-slate-600 text-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Story Text <span className="text-slate-500">(min 50 characters)</span>
                    </label>
                    <Textarea
                      value={storyText}
                      onChange={(e) => setStoryText(e.target.value)}
                      placeholder="Paste or type your story here..."
                      className="bg-slate-900/50 border-slate-600 text-white min-h-[300px]"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {storyText.length} / 50,000 characters
                    </p>
                  </div>
                  
                  <div className="flex items-center justify-center">
                    <span className="text-slate-500">— OR —</span>
                  </div>
                  
                  <div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept=".txt,.pdf,.docx"
                      className="hidden"
                    />
                    <Button
                      onClick={() => fileInputRef.current?.click()}
                      variant="outline"
                      className="w-full border-dashed border-2 border-slate-600 hover:border-purple-500 h-20"
                      disabled={loading}
                    >
                      <Upload className="w-5 h-5 mr-2" />
                      Upload TXT, PDF, or DOCX
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Settings */}
              <div className="space-y-6">
                {/* Language & Age Group */}
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                  <h2 className="text-lg font-semibold text-white mb-4">Settings</h2>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">Language</label>
                      <Select value={language} onValueChange={setLanguage}>
                        <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {LANGUAGES.map(lang => (
                            <SelectItem key={lang.id} value={lang.id}>{lang.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">Age Group</label>
                      <Select value={ageGroup} onValueChange={setAgeGroup}>
                        <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {AGE_GROUPS.map(age => (
                            <SelectItem key={age.id} value={age.id}>{age.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
                
                {/* Video Style Selection */}
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Palette className="w-5 h-5 text-pink-400" />
                    Video Style
                  </h2>
                  
                  <div className="grid grid-cols-2 gap-3">
                    {styles.map(style => (
                      <button
                        key={style.id}
                        onClick={() => setStyleId(style.id)}
                        className={`p-4 rounded-lg border-2 text-left transition-all ${
                          styleId === style.id 
                            ? 'border-purple-500 bg-purple-500/20' 
                            : 'border-slate-600 bg-slate-900/30 hover:border-slate-500'
                        }`}
                      >
                        <p className="font-medium text-white">{style.name}</p>
                        <p className="text-xs text-slate-400 mt-1">{style.description}</p>
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Generate Button */}
                <Button
                  onClick={createProject}
                  disabled={loading || storyText.length < 50}
                  className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 h-14 text-lg"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Generating Scenes...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-5 h-5 mr-2" />
                      Generate Scenes ({pricing?.scene_generation || 5} credits)
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
        
        {/* Step 2: Scenes */}
        {step === 2 && project && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{project.title}</h2>
                <p className="text-slate-400">{project.scenes?.length || 0} scenes generated</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button onClick={() => setStep(3)} className="bg-purple-500 hover:bg-purple-600">
                  View Characters
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
            
            <div className="space-y-4">
              {project.scenes?.map((scene, idx) => (
                <div 
                  key={idx} 
                  className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedScene(expandedScene === idx ? null : idx)}
                    className="w-full p-4 flex items-center justify-between text-left"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <span className="text-purple-400 font-bold">{scene.scene_number}</span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{scene.title}</h3>
                        <p className="text-sm text-slate-400">{scene.summary?.slice(0, 100)}...</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-slate-500 flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        ~{scene.estimated_duration}s
                      </span>
                      <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${
                        expandedScene === idx ? 'rotate-180' : ''
                      }`} />
                    </div>
                  </button>
                  
                  {expandedScene === idx && (
                    <div className="p-4 pt-0 border-t border-slate-700/50 space-y-4">
                      <div>
                        <label className="text-sm font-medium text-slate-400">Narration</label>
                        <p className="text-white mt-1">{scene.narration_text}</p>
                      </div>
                      
                      {scene.character_dialogue?.length > 0 && (
                        <div>
                          <label className="text-sm font-medium text-slate-400">Dialogue</label>
                          <div className="mt-2 space-y-2">
                            {scene.character_dialogue.map((d, i) => (
                              <div key={i} className="bg-slate-900/50 rounded-lg p-3">
                                <span className="text-purple-400 font-medium">{d.character}:</span>
                                <span className="text-white ml-2">"{d.dialogue}"</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div>
                        <label className="text-sm font-medium text-slate-400">Visual Prompt</label>
                        <p className="text-slate-300 mt-1 text-sm bg-slate-900/50 rounded-lg p-3">
                          {scene.visual_prompt}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-slate-400" />
                        <span className="text-sm text-slate-400">Characters:</span>
                        {scene.characters_in_scene?.map((c, i) => (
                          <span key={i} className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Step 3: Characters */}
        {step === 3 && project && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Character Bible</h2>
                <p className="text-slate-400">{project.characters?.length || 0} characters</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Scenes
                </Button>
                <Button onClick={getPromptPack} disabled={loading} className="bg-purple-500 hover:bg-purple-600">
                  {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                  Get Prompt Pack
                </Button>
              </div>
            </div>
            
            <div className="grid md:grid-cols-2 gap-4">
              {project.characters?.map((char, idx) => (
                <div 
                  key={idx}
                  className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                      <span className="text-white font-bold text-lg">{char.name?.charAt(0)}</span>
                    </div>
                    <Button variant="ghost" size="sm" className="text-slate-400">
                      <Edit className="w-4 h-4" />
                    </Button>
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-1">{char.name}</h3>
                  {char.age && <p className="text-sm text-slate-400 mb-4">Age: {char.age}</p>}
                  
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-slate-500 uppercase">Appearance</label>
                      <p className="text-slate-300 text-sm">{char.appearance}</p>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 uppercase">Clothing</label>
                      <p className="text-slate-300 text-sm">{char.clothing}</p>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 uppercase">Personality</label>
                      <p className="text-slate-300 text-sm">{char.personality}</p>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 uppercase">Voice Tone</label>
                      <p className="text-slate-300 text-sm">{char.voice_tone}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Step 4: Prompt Pack */}
        {step === 4 && project?.promptPack && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Prompt Pack Ready!</h2>
                <p className="text-slate-400">Your story is ready for image generation</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(3)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button onClick={downloadPromptPack} className="bg-green-500 hover:bg-green-600">
                  <Download className="w-4 h-4 mr-2" />
                  Download Prompt Pack
                </Button>
              </div>
            </div>
            
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <p className="text-3xl font-bold text-white">{project.promptPack.stats?.total_scenes}</p>
                <p className="text-slate-400">Scenes</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <p className="text-3xl font-bold text-white">{project.promptPack.stats?.total_characters}</p>
                <p className="text-slate-400">Characters</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <p className="text-3xl font-bold text-yellow-400">{project.promptPack.stats?.estimated_image_credits}</p>
                <p className="text-slate-400">Credits for Images</p>
              </div>
            </div>
            
            {/* Scene Prompts */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Scene Prompts</h3>
              <div className="space-y-4">
                {project.promptPack.scene_prompts?.map((sp, idx) => (
                  <div key={idx} className="bg-slate-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-purple-400 font-medium">Scene {sp.scene_number}: {sp.title}</span>
                      <Button variant="ghost" size="sm" onClick={() => {
                        navigator.clipboard.writeText(sp.prompt);
                        toast.success('Prompt copied!');
                      }}>
                        Copy
                      </Button>
                    </div>
                    <p className="text-sm text-slate-300">{sp.prompt}</p>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Image Generation Section */}
            <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-purple-500/30 flex items-center justify-center">
                    <Image className="w-6 h-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Phase 2: Generate Images</h3>
                    <p className="text-slate-400">Create AI images for each scene</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Select value={imageProvider} onValueChange={setImageProvider}>
                    <SelectTrigger className="w-40 bg-slate-900/50 border-slate-600 text-white">
                      <SelectValue placeholder="Provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI GPT Image</SelectItem>
                      <SelectItem value="gemini">Gemini Nano Banana</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button 
                    onClick={generateImages} 
                    disabled={loading}
                    className="bg-purple-500 hover:bg-purple-600"
                  >
                    {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Image className="w-4 h-4 mr-2" />}
                    Generate Images ({project.promptPack?.stats?.estimated_image_credits || 0} credits)
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Step 5: Images Generated */}
        {step === 5 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Scene Images</h2>
                <p className="text-slate-400">{generatedImages.length} images generated</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(4)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button onClick={() => setStep(6)} className="bg-purple-500 hover:bg-purple-600">
                  Continue to Voice
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {generatedImages.map((img, idx) => (
                <div key={idx} className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
                  {img.image_url ? (
                    <img 
                      src={`${process.env.REACT_APP_BACKEND_URL}${img.image_url}`}
                      alt={`Scene ${img.scene_number}`}
                      className="w-full aspect-video object-cover"
                    />
                  ) : img.error ? (
                    <div className="w-full aspect-video bg-red-500/20 flex items-center justify-center">
                      <p className="text-red-400 text-sm">{img.error}</p>
                    </div>
                  ) : (
                    <div className="w-full aspect-video bg-slate-700 flex items-center justify-center">
                      <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                    </div>
                  )}
                  <div className="p-3">
                    <p className="text-white font-medium">Scene {img.scene_number}</p>
                    <p className="text-xs text-slate-400">{img.provider}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Step 6: Voice Generation */}
        {step === 6 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Voice Generation</h2>
                <p className="text-slate-400">Add narration to your video</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(5)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </div>
            </div>
            
            {/* Voice Config */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Mic className="w-5 h-5 text-green-400" />
                Voice Settings
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Select Voice</label>
                  <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                    <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {voiceConfig?.available_voices?.map(v => (
                        <SelectItem key={v.id} value={v.id}>{v.name} - {v.description}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {voiceConfig?.mode === 'BYO_USER_KEY' && (
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Your OpenAI API Key
                      <span className="text-amber-400 ml-2">(Required)</span>
                    </label>
                    <Input
                      type="password"
                      value={userApiKey}
                      onChange={(e) => setUserApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="bg-slate-900/50 border-slate-600 text-white"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Your key is used directly and not stored. Get one at platform.openai.com
                    </p>
                  </div>
                )}
              </div>
              
              <div className="mt-6 flex justify-end">
                <Button 
                  onClick={generateVoices} 
                  disabled={loading || (voiceConfig?.mode === 'BYO_USER_KEY' && !userApiKey)}
                  className="bg-green-500 hover:bg-green-600"
                >
                  {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Mic className="w-4 h-4 mr-2" />}
                  Generate Voices ({pricing?.voice_per_minute || 10} credits/min)
                </Button>
              </div>
            </div>
            
            {/* Generated Voices */}
            {generatedVoices.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Generated Voice Tracks</h3>
                <div className="space-y-3">
                  {generatedVoices.map((voice, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-slate-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                          <Mic className="w-5 h-5 text-green-400" />
                        </div>
                        <div>
                          <p className="text-white font-medium">Scene {voice.scene_number}</p>
                          <p className="text-xs text-slate-400">{voice.duration?.toFixed(1)}s</p>
                        </div>
                      </div>
                      {voice.audio_url && (
                        <audio controls className="h-8">
                          <source src={`${process.env.REACT_APP_BACKEND_URL}${voice.audio_url}`} type="audio/mpeg" />
                        </audio>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex justify-end">
                  <Button onClick={() => setStep(7)} className="bg-purple-500 hover:bg-purple-600">
                    Continue to Music
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Step 7: Music Selection & Video Assembly */}
        {step === 7 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Music & Video Assembly</h2>
                <p className="text-slate-400">Add background music and render your video</p>
              </div>
              <Button variant="outline" onClick={() => setStep(6)}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </div>
            
            {/* Music Selection */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Music className="w-5 h-5 text-pink-400" />
                Background Music (Optional)
              </h3>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <button
                  onClick={() => setSelectedMusic(null)}
                  className={`p-4 rounded-lg border-2 text-left ${
                    !selectedMusic ? 'border-purple-500 bg-purple-500/20' : 'border-slate-600 bg-slate-900/30'
                  }`}
                >
                  <p className="font-medium text-white">No Music</p>
                  <p className="text-xs text-slate-400">Voice only</p>
                </button>
                {musicLibrary.map(track => (
                  <button
                    key={track.id}
                    onClick={() => setSelectedMusic(track.id)}
                    className={`p-4 rounded-lg border-2 text-left ${
                      selectedMusic === track.id ? 'border-purple-500 bg-purple-500/20' : 'border-slate-600 bg-slate-900/30'
                    }`}
                  >
                    <p className="font-medium text-white">{track.name}</p>
                    <p className="text-xs text-slate-400">{track.duration}s • {track.category}</p>
                  </button>
                ))}
              </div>
              
              {selectedMusic && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Music Volume: {Math.round(musicVolume * 100)}%
                  </label>
                  <Slider
                    value={[musicVolume * 100]}
                    onValueChange={([v]) => setMusicVolume(v / 100)}
                    max={100}
                    step={5}
                    className="w-full"
                  />
                </div>
              )}
            </div>
            
            {/* Watermark Option */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white">Watermark</h3>
                  <p className="text-slate-400 text-sm">
                    Remove watermark for {pricing?.watermark_removal || 15} extra credits
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-slate-300">Include Watermark</label>
                  <input
                    type="checkbox"
                    checked={includeWatermark}
                    onChange={(e) => setIncludeWatermark(e.target.checked)}
                    className="w-5 h-5 rounded border-slate-600"
                  />
                </div>
              </div>
            </div>
            
            {/* Render Button */}
            <Button 
              onClick={assembleVideo} 
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 h-14 text-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Rendering Video...
                </>
              ) : (
                <>
                  <Video className="w-5 h-5 mr-2" />
                  Render Final Video ({pricing?.video_render || 20} credits)
                </>
              )}
            </Button>
            
            {/* Render Progress */}
            {renderJob && renderJob.status !== 'COMPLETED' && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Rendering Progress</h3>
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    renderJob.status === 'PROCESSING' ? 'bg-blue-500/20 text-blue-400' :
                    renderJob.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                    'bg-amber-500/20 text-amber-400'
                  }`}>
                    {renderJob.status}
                  </span>
                </div>
                <Progress value={renderJob.progress || 0} className="h-3" />
                <p className="text-sm text-slate-400 mt-2">{renderJob.progress || 0}% complete</p>
                {renderJob.error && (
                  <p className="text-red-400 text-sm mt-2">{renderJob.error}</p>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Step 8: Final Video Player */}
        {step === 8 && project?.final_video_url && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{project.title}</h2>
                <p className="text-slate-400">Your video is ready!</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(7)}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button 
                  onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${project.final_video_url}`, '_blank')}
                  className="bg-green-500 hover:bg-green-600"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download Video
                </Button>
              </div>
            </div>
            
            {/* Custom Video Player */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden" data-testid="video-player-container">
              <div className="relative aspect-video bg-black">
                <video
                  ref={videoRef}
                  src={`${process.env.REACT_APP_BACKEND_URL}${project.final_video_url}`}
                  className="w-full h-full"
                  onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
                  onLoadedMetadata={(e) => setDuration(e.target.duration)}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  data-testid="video-element"
                />
                
                {/* Video Controls Overlay */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  <div className="flex items-center gap-4">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => {
                        if (videoRef.current) {
                          isPlaying ? videoRef.current.pause() : videoRef.current.play();
                        }
                      }}
                      data-testid="play-pause-btn"
                    >
                      {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                    </Button>
                    
                    <div className="flex-1">
                      <Progress 
                        value={duration ? (currentTime / duration) * 100 : 0} 
                        className="h-1 cursor-pointer"
                        onClick={(e) => {
                          if (videoRef.current && duration) {
                            const rect = e.target.getBoundingClientRect();
                            const percent = (e.clientX - rect.left) / rect.width;
                            videoRef.current.currentTime = percent * duration;
                          }
                        }}
                      />
                    </div>
                    
                    <span className="text-white text-sm font-mono">
                      {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')} / 
                      {Math.floor(duration / 60)}:{String(Math.floor(duration % 60)).padStart(2, '0')}
                    </span>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:bg-white/20"
                      onClick={() => {
                        if (videoRef.current) {
                          if (document.fullscreenElement) {
                            document.exitFullscreen();
                          } else {
                            videoRef.current.requestFullscreen();
                          }
                        }
                      }}
                      data-testid="fullscreen-btn"
                    >
                      <Maximize className="w-5 h-5" />
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Branding Footer */}
              <div className="px-4 py-3 bg-slate-900/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Film className="w-5 h-5 text-purple-400" />
                  <span className="text-white font-medium">Visionary Suite</span>
                </div>
                <p className="text-slate-400 text-sm">Created with AI Story → Video Studio</p>
              </div>
            </div>
            
            {/* Project Summary */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                <p className="text-2xl font-bold text-white">{project.scenes?.length || 0}</p>
                <p className="text-slate-400 text-sm">Scenes</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                <p className="text-2xl font-bold text-white">{project.characters?.length || 0}</p>
                <p className="text-slate-400 text-sm">Characters</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                <p className="text-2xl font-bold text-white">{Math.floor(duration / 60)}:{String(Math.floor(duration % 60)).padStart(2, '0')}</p>
                <p className="text-slate-400 text-sm">Duration</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 text-center">
                <p className="text-2xl font-bold text-yellow-400">{project.credits_spent || 0}</p>
                <p className="text-slate-400 text-sm">Credits Used</p>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-4">
              <Button 
                variant="outline" 
                className="flex-1"
                onClick={() => {
                  setStep(1);
                  setProject(null);
                  setStoryText('');
                  setTitle('');
                  setGeneratedImages([]);
                  setGeneratedVoices([]);
                  setRenderJob(null);
                }}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Create New Video
              </Button>
              <Button 
                className="flex-1 bg-purple-500 hover:bg-purple-600"
                onClick={() => navigate('/app/dashboard')}
              >
                Back to Dashboard
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
