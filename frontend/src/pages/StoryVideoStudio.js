import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import useWebSocketProgress from '../hooks/useWebSocketProgress';
import { RealTimeProgressPanel } from '../components/RealTimeProgressPanel';
import WaitingExperience from '../components/WaitingExperience';
import { 
  ArrowLeft, Upload, Wand2, Loader2, Film, Image, Mic, 
  Play, Users, BookOpen, Sparkles, ChevronRight, ChevronDown,
  FileText, Download, Edit, Trash2, Eye, Clock, Coins,
  AlertTriangle, AlertCircle, CheckCircle, Palette, Music, Video, Pause,
  Volume2, Maximize, Settings, RefreshCw, LayoutTemplate,
  Gamepad2, Share2, Facebook, Twitter, MessageCircle, Linkedin,
  Mail, Trophy, HelpCircle, Puzzle, Brain, Lightbulb, Copy,
  Wifi, WifiOff, ImageOff
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
  
  // NEW: Templates state
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showTemplates, setShowTemplates] = useState(false);
  const [templateCustomizations, setTemplateCustomizations] = useState({});
  
  // NEW: Waiting Games state
  const [showGames, setShowGames] = useState(false);
  const [triviaQuestions, setTriviaQuestions] = useState([]);
  const [currentTriviaIndex, setCurrentTriviaIndex] = useState(0);
  const [triviaScore, setTriviaScore] = useState(0);
  const [wordPuzzle, setWordPuzzle] = useState(null);
  const [puzzleGuess, setPuzzleGuess] = useState('');
  const [riddle, setRiddle] = useState(null);
  const [riddleGuess, setRiddleGuess] = useState('');
  const [gameTab, setGameTab] = useState('trivia');
  
  // NEW: Social Sharing state
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareLinks, setShareLinks] = useState({});
  
  // Error recovery state — prevents blank page on any unhandled error
  const [componentError, setComponentError] = useState(null);
  
  // NEW: WebSocket Real-Time Progress
  const [currentJobId, setCurrentJobId] = useState(null);
  const [wsProgress, setWsProgress] = useState(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStage, setGenerationStage] = useState('');
  const [showWaitingExperience, setShowWaitingExperience] = useState(false);
  
  // WebSocket progress callbacks
  const handleWsProgress = useCallback((data) => {
    setWsProgress(data);
    setGenerationProgress(data.progress || 0);
    setGenerationStage(data.stage || 'processing');
    // Show toast for key milestones
    if (data.current_step === 1 && data.stage !== 'complete') {
      toast.info(`${data.message}`);
    }
  }, []);
  
  const handleWsComplete = useCallback(async (data) => {
    setWsProgress({ ...data, status: 'completed' });
    setShowWaitingExperience(false);
    setGenerationProgress(100);
    
    // Verify the file was created successfully
    try {
      if (data.result_url) {
        // Handle both R2 cloud URLs (full https://) and local paths (/static/...)
        const checkUrl = data.result_url?.startsWith('http') 
          ? data.result_url 
          : `${process.env.REACT_APP_BACKEND_URL}${data.result_url}`;
        const response = await fetch(checkUrl, { method: 'HEAD' });
        
        if (response.ok) {
          toast.success('🎉 ' + (data.message || 'Generation complete!'));
          
          // Auto-redirect to downloads page after completion
          setTimeout(() => {
            toast.info('Redirecting to your downloads...');
            navigate('/app/downloads');
          }, 2000);
        } else {
          toast.error('File generation completed but file is not accessible. Credits have been refunded.');
        }
      } else {
        toast.success('🎉 ' + (data.message || 'Generation complete!'));
        setTimeout(() => navigate('/app/downloads'), 2000);
      }
    } catch (error) {
      toast.error('Error verifying download. Please check your downloads page.');
      navigate('/app/downloads');
    }
  }, [navigate]);
  
  const handleWsError = useCallback((data) => {
    setWsProgress({ ...data, status: 'failed' });
    setShowWaitingExperience(false);
    setGenerationProgress(0);
    // Show error with refund message
    toast.error(`${data.message || 'Generation failed'}. Your credits have been refunded.`);
  }, []);
  
  // WebSocket hook
  const { 
    isConnected: wsConnected, 
    subscribeToJob 
  } = useWebSocketProgress(
    currentJobId,
    handleWsProgress,
    handleWsComplete,
    handleWsError
  );
  
  // Fetch styles and pricing on mount
  useEffect(() => {
    fetchStyles();
    fetchPricing();
    fetchVoiceConfig();
    fetchMusicLibrary();
    fetchTemplates();
    analytics.trackFunnelStep('story_video_studio_view');
  }, []);
  
  // Load existing images when project changes and has images_generated status
  useEffect(() => {
    if (project?.project_id && 
        ['images_generated', 'voices_generated', 'video_rendered'].includes(project?.status)) {
      loadProjectImages(project.project_id);
    }
  }, [project?.project_id, project?.status]);
  
  const loadProjectImages = async (projectId) => {
    try {
      const res = await api.get(`/api/story-video-studio/generation/images/${projectId}`);
      if (res.data.success && res.data.images?.length > 0) {
        // Map scene_assets format to frontend format
        const images = res.data.images.map(img => ({
          scene_number: img.scene_number,
          image_url: img.url || img.image_url,
          provider: img.provider || 'openai'
        }));
        setGeneratedImages(images);
        
        // Set step based on project status if not already set
        if (project?.status === 'images_generated' && step < 5) {
          setStep(5);
        } else if (project?.status === 'voices_generated' && step < 6) {
          setStep(6);
        }
      }
    } catch (error) {
      console.error('Failed to load project images:', error);
    }
  };
  
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
  
  // NEW: Fetch templates
  const fetchTemplates = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/list');
      if (res.data.success) {
        setTemplates(res.data.templates);
      }
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };
  
  // NEW: Select template and pre-fill form
  const selectTemplate = (template) => {
    setSelectedTemplate(template);
    setTemplateCustomizations(template.fill_in_blanks);
    setAgeGroup(template.age_group);
    setStyleId(template.style);
    setTitle(template.name);
    setShowTemplates(false);
    toast.success(`Template "${template.name}" selected! Customize it below.`);
  };
  
  // NEW: Generate story from template
  const generateFromTemplate = async () => {
    if (!selectedTemplate) return;
    
    setLoading(true);
    try {
      const res = await api.post('/api/story-video-studio/templates/generate-from-template', {
        template_id: selectedTemplate.template_id,
        customizations: templateCustomizations
      });
      
      if (res.data.success) {
        setStoryText(res.data.generated_story);
        toast.success('Story generated from template!');
      }
    } catch (error) {
      toast.error('Failed to generate from template');
    } finally {
      setLoading(false);
    }
  };
  
  // NEW: Fetch waiting games
  const fetchTrivia = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/trivia?count=5');
      if (res.data.success) {
        setTriviaQuestions(res.data.questions);
        setCurrentTriviaIndex(0);
        setTriviaScore(0);
      }
    } catch (error) {
      console.error('Failed to fetch trivia:', error);
    }
  };
  
  const fetchWordPuzzle = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/word-puzzle');
      if (res.data.success) {
        setWordPuzzle(res.data);
        setPuzzleGuess('');
      }
    } catch (error) {
      console.error('Failed to fetch word puzzle:', error);
    }
  };
  
  const fetchRiddle = async () => {
    try {
      const res = await api.get('/api/story-video-studio/templates/waiting-games/riddle');
      if (res.data.success) {
        setRiddle(res.data);
        setRiddleGuess('');
      }
    } catch (error) {
      console.error('Failed to fetch riddle:', error);
    }
  };
  
  // NEW: Check trivia answer
  const checkTriviaAnswer = async (answerIndex) => {
    try {
      const res = await api.post(`/api/story-video-studio/templates/waiting-games/trivia/check?question_id=${currentTriviaIndex}&answer_index=${answerIndex}`);
      if (res.data.correct) {
        setTriviaScore(prev => prev + 1);
        toast.success('Correct! 🎉');
      } else {
        toast.error(`Wrong! The answer was: ${res.data.correct_answer}`);
      }
      
      if (currentTriviaIndex < triviaQuestions.length - 1) {
        setCurrentTriviaIndex(prev => prev + 1);
      } else {
        toast.success(`Game over! Your score: ${triviaScore + (res.data.correct ? 1 : 0)}/${triviaQuestions.length}`);
        fetchTrivia(); // Reload for new game
      }
    } catch (error) {
      toast.error('Failed to check answer');
    }
  };
  
  // NEW: Check word puzzle
  const checkWordPuzzle = async () => {
    if (!wordPuzzle || !puzzleGuess) return;
    
    try {
      const res = await api.post(`/api/story-video-studio/templates/waiting-games/word-puzzle/check?scrambled=${wordPuzzle.scrambled}&guess=${puzzleGuess}`);
      if (res.data.correct) {
        toast.success('Correct! 🎉 Great job!');
        fetchWordPuzzle();
      } else {
        toast.error(`Not quite! The answer was: ${res.data.answer}`);
      }
    } catch (error) {
      toast.error('Failed to check puzzle');
    }
  };
  
  // NEW: Social sharing
  const shareVideo = async (platform) => {
    if (!project?.final_video_url && !renderJob?.output_url) {
      toast.error('Video not ready for sharing');
      return;
    }
    
    const videoId = renderJob?.job_id || project?.project_id;
    
    try {
      const res = await api.post('/api/story-video-studio/templates/share', {
        video_id: videoId,
        platform: platform
      });
      
      if (res.data.success) {
        setShareLinks(res.data.share_links);
        if (res.data.share_links[platform]) {
          window.open(res.data.share_links[platform], '_blank');
          toast.success(`Opening ${platform} share dialog...`);
        }
      }
    } catch (error) {
      toast.error('Failed to generate share link');
    }
  };
  
  // NEW: Copy share link
  const copyShareLink = () => {
    const videoId = renderJob?.job_id || project?.project_id;
    const shareUrl = `${window.location.origin}/shared/video/${videoId}`;
    navigator.clipboard.writeText(shareUrl);
    toast.success('Link copied to clipboard!');
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
    
    setComponentError(null);
    setLoading(true);
    setGenerationStage('scene_generation');
    try {
      console.log('Creating project with data:', {
        story_text: storyText.substring(0, 50) + '...',
        title: title || 'Untitled Story',
        language,
        age_group: ageGroup,
        style_id: styleId
      });
      
      const res = await api.post('/api/story-video-studio/projects/create', {
        story_text: storyText,
        title: title || 'Untitled Story',
        language,
        age_group: ageGroup,
        style_id: styleId
      });
      
      console.log('Create project response:', res.data);
      
      if (res.data.success) {
        setProject(res.data.data);
        toast.success('Project created! Analyzing story and generating scenes... This may take 30-60 seconds.');
        await generateScenes(res.data.project_id);
      } else {
        console.error('Project creation returned success=false:', res.data);
        toast.error(res.data.message || res.data.detail || 'Failed to create project');
        setGenerationStage(null);
      }
    } catch (error) {
      console.error('Project creation error:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      
      let errorMessage = 'Failed to create project';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage);
      setGenerationStage(null);
    } finally {
      setLoading(false);
    }
  };
  
  const generateScenes = async (projectId) => {
    setLoading(true);
    setGenerationStage('scene_generation');
    setShowWaitingExperience(true);
    setGenerationProgress(10);
    
    try {
      console.log('Generating scenes for project:', projectId);
      
      // Show progress updates during scene generation
      const progressInterval = setInterval(() => {
        setGenerationProgress(prev => Math.min(prev + 5, 85));
      }, 3000);
      
      const res = await api.post(`/api/story-video-studio/projects/${projectId}/generate-scenes`, {}, {
        timeout: 120000 // 2 minute timeout for scene generation
      });
      
      clearInterval(progressInterval);
      setGenerationProgress(100);
      
      console.log('Scene generation response:', res.data);
      
      if (res.data.success) {
        setProject(prev => ({
          ...prev,
          ...res.data.data,
          status: 'scenes_generated'
        }));
        toast.success(`Generated ${res.data.data.scenes?.length || 0} scenes!`);
        analytics.trackGeneration('story_video_studio', res.data.data.credits_spent);
        setStep(2);
        setShowWaitingExperience(false);
        setGenerationStage(null);
      } else {
        console.error('Scene generation failed:', res.data);
        toast.error(res.data.message || 'Failed to generate scenes');
      }
    } catch (error) {
      console.error('Scene generation error:', error.response?.data || error.message);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Failed to generate scenes. Please try again.';
      toast.error(errorMessage);
      setShowWaitingExperience(false);
      setGenerationStage(null);
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
    
    const data = JSON.stringify(project?.promptPack || {}, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project?.title || 'story'}_prompt_pack.json`;
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
    setShowWaitingExperience(true);
    setGenerationStage('image_generation');
    setGenerationProgress(5);
    
    try {
      const res = await api.post('/api/story-video-studio/generation/images', {
        project_id: project.project_id,
        provider: imageProvider
      });
      
      if (res.data.success && res.data.job_id) {
        toast.info(`Image generation started for ${res.data.total_scenes} scenes...`);
        pollImageGenerationStatus(res.data.job_id);
      }
    } catch (error) {
      toast.error(`${error.response?.data?.detail || 'Failed to start image generation'}`);
      setLoading(false);
      setShowWaitingExperience(false);
    }
  };

  const pollImageGenerationStatus = (jobId) => {
    let failCount = 0;
    const checkStatus = async () => {
      try {
        const res = await api.get(`/api/story-video-studio/generation/images/status/${jobId}`);
        failCount = 0;
        if (res.data.success) {
          const job = res.data.job;
          setGenerationProgress(job.progress || 0);

          if (job.status === 'COMPLETED') {
            setGeneratedImages(job.images || []);
            setProject(prev => ({ ...prev, status: 'images_generated' }));
            toast.success(`Generated ${job.completed_scenes} images!`);
            analytics.trackGeneration('story_video_images', 0);
            setStep(5);
            setLoading(false);
            setShowWaitingExperience(false);
          } else if (job.status === 'FAILED') {
            toast.error(`Image generation failed: ${job.error || 'Unknown error'}. Credits have been refunded.`);
            setLoading(false);
            setShowWaitingExperience(false);
          } else {
            setTimeout(checkStatus, 3000);
          }
        }
      } catch (error) {
        failCount++;
        console.error('Failed to check image generation status:', error);
        if (failCount >= 10) {
          toast.error('Lost connection to image generation. Please check your project in History.');
          setLoading(false);
          setShowWaitingExperience(false);
        } else {
          setTimeout(checkStatus, 5000);
        }
      }
    };
    checkStatus();
  };
  
  // ============================================
  // PHASE 3: VOICE GENERATION
  // ============================================
  
  const generateVoices = async () => {
    if (!project?.project_id) return;
    
    if (voiceConfig?.mode === 'BYO_USER_KEY' && !userApiKey) {
      toast.error('Please provide your OpenAI API key for voice generation');
      return;
    }
    
    setLoading(true);
    setShowWaitingExperience(true);
    setGenerationStage('voice_generation');
    setGenerationProgress(5);
    
    try {
      const res = await api.post('/api/story-video-studio/generation/voices', {
        project_id: project.project_id,
        voice_id: selectedVoice,
        user_api_key: userApiKey || undefined
      });
      
      if (res.data.success && res.data.job_id) {
        toast.info(`Voice generation started for ${res.data.total_scenes} scenes...`);
        pollVoiceGenerationStatus(res.data.job_id);
      }
    } catch (error) {
      toast.error(`${error.response?.data?.detail || 'Failed to start voice generation'}`);
      setLoading(false);
      setShowWaitingExperience(false);
    }
  };

  const pollVoiceGenerationStatus = (jobId) => {
    let failCount = 0;
    const checkStatus = async () => {
      try {
        const res = await api.get(`/api/story-video-studio/generation/voices/status/${jobId}`);
        failCount = 0;
        if (res.data.success) {
          const job = res.data.job;
          setGenerationProgress(job.progress || 0);

          if (job.status === 'COMPLETED') {
            setGeneratedVoices(job.voices || []);
            setProject(prev => ({ ...prev, status: 'voices_generated' }));
            toast.success(`Generated ${job.completed_scenes} voice tracks!`);
            analytics.trackGeneration('story_video_voices', 0);
            setStep(7);
            setLoading(false);
            setShowWaitingExperience(false);
          } else if (job.status === 'FAILED') {
            toast.error(`Voice generation failed: ${job.error || 'Unknown error'}. Credits have been refunded.`);
            setLoading(false);
            setShowWaitingExperience(false);
          } else {
            setTimeout(checkStatus, 3000);
          }
        }
      } catch (error) {
        failCount++;
        console.error('Failed to check voice generation status:', error);
        if (failCount >= 10) {
          toast.error('Lost connection to voice generation. Please check your project in History.');
          setLoading(false);
          setShowWaitingExperience(false);
        } else {
          setTimeout(checkStatus, 5000);
        }
      }
    };
    checkStatus();
  };
  
  // ============================================
  // PHASE 4: VIDEO ASSEMBLY
  // ============================================
  
  const assembleVideo = async () => {
    if (!project?.project_id) return;
    
    setLoading(true);
    setShowWaitingExperience(true);
    setGenerationStage('video_assembly');
    setGenerationProgress(10);
    
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
      toast.error(`${error.response?.data?.detail || 'Failed to start video assembly'}. Credits have been refunded.`);
      setLoading(false);
      setShowWaitingExperience(false);
    }
  };
  
  const pollRenderStatus = async (jobId) => {
    const checkStatus = async () => {
      try {
        const res = await api.get(`/api/story-video-studio/generation/video/status/${jobId}`);
        if (res.data.success) {
          setRenderJob(res.data.job);
          setGenerationProgress(res.data.job.progress || 0);
          
          if (res.data.job.status === 'COMPLETED') {
            // Verify the video file exists - handle both R2 URLs and local paths
            const outputUrl = res.data.job.output_url;
            const videoUrl = outputUrl?.startsWith('http') ? outputUrl : `${process.env.REACT_APP_BACKEND_URL}${outputUrl}`;
            try {
              const checkResponse = await fetch(videoUrl, { method: 'HEAD' });
              if (checkResponse.ok) {
                setProject(prev => ({ 
                  ...prev, 
                  status: 'video_rendered',
                  final_video_url: res.data.job.output_url 
                }));
                toast.success('Video rendered successfully!');
                setLoading(false);
                setShowWaitingExperience(false);
                setStep(8);
                
                // Auto-redirect to downloads page after 2 seconds
                setTimeout(() => {
                  toast.info('Redirecting to your downloads...');
                  navigate('/app/downloads');
                }, 2000);
              } else {
                toast.error('Video generation completed but file is not accessible. Credits have been refunded.');
                setLoading(false);
                setShowWaitingExperience(false);
              }
            } catch {
              toast.success('Video rendered successfully!');
              setLoading(false);
              setShowWaitingExperience(false);
              setStep(8);
              setTimeout(() => navigate('/app/downloads'), 2000);
            }
          } else if (res.data.job.status === 'FAILED') {
            toast.error(`Video rendering failed: ${res.data.job.error || 'Unknown error'}. Credits have been refunded.`);
            setLoading(false);
            setShowWaitingExperience(false);
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

  // Handler to try other features while waiting
  const handleTryOtherFeature = () => {
    navigate('/app');
    toast.info('Your generation continues in the background. Check Downloads when done!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      {/* Error Recovery UI — prevents blank page if component encounters an error */}
      {componentError && (
        <div className="min-h-screen flex items-center justify-center p-8" data-testid="error-recovery">
          <div className="max-w-lg bg-slate-800/80 rounded-2xl border border-red-500/30 p-8 text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-red-500/20 rounded-full flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-xl font-bold text-white">Something went wrong</h2>
            <p className="text-slate-400 text-sm">{componentError}</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={() => { setComponentError(null); setStep(1); setLoading(false); setShowWaitingExperience(false); }} className="bg-purple-600 hover:bg-purple-700">
                Try Again
              </Button>
              <Link to="/app">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            </div>
          </div>
        </div>
      )}
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
          
          {/* WebSocket Status Indicator */}
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
              wsConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-400'
            }`}>
              {wsConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {wsConnected ? 'Live' : 'Offline'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Waiting Experience Overlay - Shows during generation */}
        {showWaitingExperience && loading && (
          <div className="mb-8">
            <WaitingExperience 
              progress={generationProgress}
              stage={generationStage}
              message={
                generationStage === 'scene_generation' ? (
                  generationProgress < 30 ? 'Analyzing your story...' :
                  generationProgress < 60 ? 'Creating characters and scenes...' :
                  generationProgress < 85 ? 'Writing dialogue and narration...' :
                  'Finalizing scene breakdown...'
                ) :
                generationStage === 'image_generation' ? 'Generating images...' :
                generationStage === 'voice_generation' ? 'Creating voice tracks...' :
                generationStage === 'video_assembly' ? (
                  generationProgress < 20 ? 'Preparing video assets...' :
                  generationProgress < 40 ? 'Downloading assets from cloud...' :
                  generationProgress < 60 ? 'Encoding video segments...' :
                  generationProgress < 80 ? 'Concatenating video...' :
                  generationProgress < 95 ? 'Uploading to cloud storage...' :
                  'Finalizing video...'
                ) :
                'Processing...'
              }
              onTryOtherFeature={handleTryOtherFeature}
              onRetry={async () => {
                // Retry the current job with improved error handling
                if (renderJob?.job_id) {
                  toast.info('Retrying video generation...');
                  try {
                    const response = await api.post(`/api/story-video-studio/generation/video/retry/${renderJob.job_id}`);
                    const data = response.data;
                    
                    // Update to new job ID if a fresh job was created
                    if (data.job_id && data.job_id !== renderJob.job_id) {
                      setRenderJob(prev => ({ ...prev, job_id: data.job_id }));
                      toast.success(`Retry initiated with fresh job (attempt #${data.retry_count || 1})`);
                    } else {
                      toast.success('Retry initiated successfully');
                    }
                  } catch (e) {
                    // Handle specific error types
                    const errorData = e.response?.data?.detail;
                    if (typeof errorData === 'object' && errorData.errorCode) {
                      // Structured error from backend
                      if (errorData.errorCode === 'MISSING_ASSETS') {
                        toast.error(errorData.message, { duration: 6000 });
                        // Optionally offer to regenerate assets
                        if (errorData.suggestion) {
                          toast.info(errorData.suggestion, { duration: 5000 });
                        }
                      } else {
                        toast.error(errorData.message || 'Retry failed');
                      }
                    } else if (typeof errorData === 'string') {
                      toast.error(errorData);
                    } else {
                      toast.error('Retry failed. Please try generating a fresh video.');
                    }
                  }
                }
              }}
              estimatedTime={
                generationStage === 'scene_generation' ? '30-60 seconds' :
                generationStage === 'image_generation' ? '1-2 minutes' :
                generationStage === 'voice_generation' ? '30 seconds' :
                generationStage === 'video_assembly' ? '15-30 seconds' :
                null
              }
            />
          </div>
        )}
        
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
            
            {/* NEW: Video Templates Browser */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <LayoutTemplate className="w-5 h-5 text-amber-400" />
                  Quick Start with Templates
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowTemplates(!showTemplates)}
                  className="text-amber-400 border-amber-400/30 hover:bg-amber-400/10"
                  data-testid="browse-templates-btn"
                >
                  {showTemplates ? 'Hide Templates' : 'Browse Templates'}
                </Button>
              </div>
              
              {showTemplates && (
                <div className="space-y-4">
                  <p className="text-slate-400 text-sm">Choose a pre-made story template and customize it to your needs!</p>
                  
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
                    {templates.map(template => (
                      <button
                        key={template.template_id}
                        onClick={() => selectTemplate(template)}
                        className={`p-4 rounded-lg border-2 text-left transition-all ${
                          selectedTemplate?.template_id === template.template_id
                            ? 'border-amber-500 bg-amber-500/20'
                            : 'border-slate-600 bg-slate-900/30 hover:border-amber-400/50'
                        }`}
                        data-testid={`template-${template.template_id}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">
                            {template.age_group}
                          </span>
                          <span className="text-xs text-slate-500">{template.scene_count} scenes</span>
                        </div>
                        <h4 className="font-medium text-white">{template.name}</h4>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{template.description}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 bg-slate-700/50 text-slate-400 rounded">
                            {template.style}
                          </span>
                          <span className="text-xs text-slate-500">{template.duration_estimate}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                  
                  {/* Template Customization */}
                  {selectedTemplate && (
                    <div className="mt-4 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                      <h4 className="font-medium text-amber-400 mb-3 flex items-center gap-2">
                        <Edit className="w-4 h-4" />
                        Customize "{selectedTemplate.name}"
                      </h4>
                      <div className="grid md:grid-cols-2 gap-3">
                        {Object.entries(selectedTemplate.fill_in_blanks).map(([key, defaultValue]) => (
                          <div key={key}>
                            <label className="block text-xs text-slate-400 mb-1 capitalize">
                              {key.replace(/_/g, ' ')}
                            </label>
                            <Input
                              value={templateCustomizations[key] || defaultValue}
                              onChange={(e) => setTemplateCustomizations(prev => ({
                                ...prev,
                                [key]: e.target.value
                              }))}
                              className="bg-slate-900/50 border-slate-600 text-white text-sm h-9"
                              placeholder={defaultValue}
                            />
                          </div>
                        ))}
                      </div>
                      <Button
                        onClick={generateFromTemplate}
                        disabled={loading}
                        className="mt-4 bg-amber-500 hover:bg-amber-600 text-black"
                        data-testid="generate-from-template-btn"
                      >
                        {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
                        Generate Story from Template
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
            
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
                <p className="text-3xl font-bold text-white">{project?.promptPack?.stats?.total_scenes || 0}</p>
                <p className="text-slate-400">Scenes</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <p className="text-3xl font-bold text-white">{project?.promptPack?.stats?.total_characters || 0}</p>
                <p className="text-slate-400">Characters</p>
              </div>
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <p className="text-3xl font-bold text-yellow-400">{project?.promptPack?.stats?.estimated_image_credits || 0}</p>
                <p className="text-slate-400">Credits for Images</p>
              </div>
            </div>
            
            {/* Scene Prompts */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Scene Prompts</h3>
              <div className="space-y-4">
                {project?.promptPack?.scene_prompts?.map((sp, idx) => (
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
              {/* Expiry Warning */}
              {generatedImages.length > 0 && (
                <div className="col-span-full mb-2 bg-amber-500/20 border border-amber-500/30 rounded-lg p-3 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                  <p className="text-amber-200 text-sm">
                    <strong>Download within 30 minutes!</strong> Generated files are automatically deleted to save space.
                  </p>
                </div>
              )}
              {generatedImages.map((img, idx) => {
                // Handle both R2 cloud URLs (full https://) and local paths (/static/...)
                const imageUrl = img.image_url?.startsWith('http') 
                  ? img.image_url 
                  : `${process.env.REACT_APP_BACKEND_URL}${img.image_url}`;
                
                return (
                <div key={idx} className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
                  {img.image_url ? (
                    <img 
                      src={imageUrl}
                      alt={`Scene ${img.scene_number}`}
                      className="w-full aspect-video object-cover"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div 
                    className="w-full aspect-video bg-slate-700/50 items-center justify-center flex-col gap-2 text-center p-4"
                    style={{ display: img.image_url ? 'none' : 'flex' }}
                  >
                    {img.error ? (
                      <p className="text-red-400 text-sm">{img.error}</p>
                    ) : img.image_url ? (
                      <>
                        <ImageOff className="w-8 h-8 text-slate-500" />
                        <p className="text-slate-400 text-xs">Image unavailable</p>
                        <p className="text-slate-500 text-xs">Try regenerating</p>
                      </>
                    ) : (
                      <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-white font-medium">Scene {img.scene_number}</p>
                    <p className="text-xs text-slate-400">{img.provider}</p>
                  </div>
                </div>
              )})}
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
                          <source src={voice.audio_url?.startsWith('http') ? voice.audio_url : `${process.env.REACT_APP_BACKEND_URL}${voice.audio_url}`} type="audio/mpeg" />
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
            
            {/* Render Progress - Now with Real-Time WebSocket Updates */}
            {(renderJob && renderJob.status !== 'COMPLETED') || wsProgress ? (
              <RealTimeProgressPanel
                progress={wsProgress || {
                  stage: renderJob?.status === 'PROCESSING' ? 'video_assembly' : 'preparing',
                  progress: renderJob?.progress || 0,
                  current_step: 1,
                  total_steps: 1,
                  message: renderJob?.status === 'PROCESSING' ? 'Rendering video...' : 'Preparing...',
                  status: renderJob?.status === 'FAILED' ? 'failed' : 
                          renderJob?.status === 'COMPLETED' ? 'completed' : 'running',
                  estimated_remaining: renderJob?.progress ? `~${Math.max(5, Math.floor((100 - renderJob.progress) / 10))}s` : null
                }}
                title="Video Generation Progress"
                steps={[
                  { stage: 'scene_generation', label: 'Generating Scenes', detail: '' },
                  { stage: 'image_generation', label: 'Creating Scene Images', detail: '' },
                  { stage: 'voice_generation', label: 'Recording Narration', detail: '' },
                  { stage: 'video_assembly', label: 'Rendering Final Video', detail: '' }
                ]}
                className="mb-6"
              />
            ) : null}
            
            {/* NEW: Waiting Games - Shows during video rendering */}
            {renderJob && renderJob.status !== 'COMPLETED' && renderJob.status !== 'FAILED' && (
              <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-xl border border-purple-500/30 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <Gamepad2 className="w-5 h-5 text-purple-400" />
                    Play While You Wait!
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowGames(!showGames);
                      if (!showGames && triviaQuestions.length === 0) {
                        fetchTrivia();
                        fetchWordPuzzle();
                        fetchRiddle();
                      }
                    }}
                    className="text-purple-400 border-purple-400/30"
                    data-testid="toggle-games-btn"
                  >
                    {showGames ? 'Hide Games' : 'Play Games'}
                  </Button>
                </div>
                
                {showGames && (
                  <div className="space-y-4">
                    {/* Game Tabs */}
                    <div className="flex gap-2">
                      {[
                        { id: 'trivia', label: 'Trivia', icon: Brain },
                        { id: 'puzzle', label: 'Word Puzzle', icon: Puzzle },
                        { id: 'riddle', label: 'Riddles', icon: Lightbulb }
                      ].map(tab => (
                        <button
                          key={tab.id}
                          onClick={() => setGameTab(tab.id)}
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                            gameTab === tab.id 
                              ? 'bg-purple-500 text-white' 
                              : 'bg-slate-800/50 text-slate-400 hover:text-white'
                          }`}
                          data-testid={`game-tab-${tab.id}`}
                        >
                          <tab.icon className="w-4 h-4" />
                          {tab.label}
                        </button>
                      ))}
                    </div>
                    
                    {/* Trivia Game */}
                    {gameTab === 'trivia' && triviaQuestions.length > 0 && (
                      <div className="bg-slate-900/50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm text-slate-400">
                            Question {currentTriviaIndex + 1} of {triviaQuestions.length}
                          </span>
                          <span className="flex items-center gap-1 text-amber-400">
                            <Trophy className="w-4 h-4" />
                            Score: {triviaScore}
                          </span>
                        </div>
                        <p className="text-white font-medium mb-4">
                          {triviaQuestions[currentTriviaIndex]?.question}
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          {triviaQuestions[currentTriviaIndex]?.options?.map((option, idx) => (
                            <button
                              key={idx}
                              onClick={() => checkTriviaAnswer(idx)}
                              className="p-3 rounded-lg bg-slate-800/50 hover:bg-purple-500/30 text-white text-left transition-colors"
                              data-testid={`trivia-option-${idx}`}
                            >
                              {option}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Word Puzzle Game */}
                    {gameTab === 'puzzle' && wordPuzzle && (
                      <div className="bg-slate-900/50 rounded-lg p-4">
                        <p className="text-slate-400 text-sm mb-2">Unscramble the word:</p>
                        <p className="text-3xl font-bold text-purple-400 tracking-widest mb-4 text-center">
                          {wordPuzzle.scrambled}
                        </p>
                        <p className="text-slate-500 text-sm mb-4">
                          Hint: {wordPuzzle.hint} ({wordPuzzle.length} letters)
                        </p>
                        <div className="flex gap-2">
                          <Input
                            value={puzzleGuess}
                            onChange={(e) => setPuzzleGuess(e.target.value.toUpperCase())}
                            placeholder="Your answer..."
                            className="bg-slate-800/50 border-slate-600 text-white uppercase"
                            onKeyDown={(e) => e.key === 'Enter' && checkWordPuzzle()}
                            data-testid="puzzle-input"
                          />
                          <Button onClick={checkWordPuzzle} className="bg-purple-500 hover:bg-purple-600">
                            Check
                          </Button>
                          <Button variant="outline" onClick={fetchWordPuzzle}>
                            Skip
                          </Button>
                        </div>
                      </div>
                    )}
                    
                    {/* Riddle Game */}
                    {gameTab === 'riddle' && riddle && (
                      <div className="bg-slate-900/50 rounded-lg p-4">
                        <p className="text-white font-medium mb-4 text-lg">
                          "{riddle.riddle}"
                        </p>
                        <div className="flex gap-2">
                          <Input
                            value={riddleGuess}
                            onChange={(e) => setRiddleGuess(e.target.value)}
                            placeholder="Your answer..."
                            className="bg-slate-800/50 border-slate-600 text-white"
                            data-testid="riddle-input"
                          />
                          <Button 
                            onClick={async () => {
                              try {
                                const res = await api.post(`/api/story-video-studio/templates/waiting-games/riddle/check?riddle_text=${encodeURIComponent(riddle.riddle)}&guess=${encodeURIComponent(riddleGuess)}`);
                                if (res.data.correct) {
                                  toast.success('Correct! 🎉');
                                  fetchRiddle();
                                } else {
                                  toast.error(`The answer was: ${res.data.answer}`);
                                }
                              } catch (err) {
                                toast.error('Failed to check');
                              }
                            }}
                            className="bg-purple-500 hover:bg-purple-600"
                          >
                            Check
                          </Button>
                          <Button variant="outline" onClick={fetchRiddle}>
                            Next
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Step 8: Final Video Player */}
        {step === 8 && project?.final_video_url && (
          <div className="space-y-6">
            {/* Urgent Download Warning */}
            <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 animate-pulse" data-testid="video-expiry-warning">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
                <div>
                  <h3 className="text-red-400 font-bold text-lg">Download Now! File expires in 30 minutes</h3>
                  <p className="text-red-200/80 text-sm">
                    Your video will be automatically deleted to save server space. Download immediately!
                  </p>
                </div>
              </div>
            </div>
            
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
                  onClick={() => {
                    const videoUrl = project.final_video_url?.startsWith('http') 
                      ? project.final_video_url 
                      : `${process.env.REACT_APP_BACKEND_URL}${project.final_video_url}`;
                    window.open(videoUrl, '_blank');
                  }}
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
                  src={project.final_video_url?.startsWith('http') ? project.final_video_url : `${process.env.REACT_APP_BACKEND_URL}${project.final_video_url}`}
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
            
            {/* NEW: Social Sharing Section */}
            <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl border border-blue-500/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Share2 className="w-5 h-5 text-blue-400" />
                Share Your Video
              </h3>
              <p className="text-slate-400 text-sm mb-4">
                Proud of your creation? Share it with the world!
              </p>
              
              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={() => shareVideo('facebook')}
                  className="bg-[#1877F2] hover:bg-[#166FE5] text-white"
                  data-testid="share-facebook"
                >
                  <Facebook className="w-4 h-4 mr-2" />
                  Facebook
                </Button>
                <Button
                  onClick={() => shareVideo('twitter')}
                  className="bg-[#1DA1F2] hover:bg-[#1A8CD8] text-white"
                  data-testid="share-twitter"
                >
                  <Twitter className="w-4 h-4 mr-2" />
                  Twitter
                </Button>
                <Button
                  onClick={() => shareVideo('whatsapp')}
                  className="bg-[#25D366] hover:bg-[#22C35E] text-white"
                  data-testid="share-whatsapp"
                >
                  <MessageCircle className="w-4 h-4 mr-2" />
                  WhatsApp
                </Button>
                <Button
                  onClick={() => shareVideo('linkedin')}
                  className="bg-[#0A66C2] hover:bg-[#095CB8] text-white"
                  data-testid="share-linkedin"
                >
                  <Linkedin className="w-4 h-4 mr-2" />
                  LinkedIn
                </Button>
                <Button
                  onClick={() => shareVideo('email')}
                  variant="outline"
                  className="border-slate-600 text-white hover:bg-slate-800"
                  data-testid="share-email"
                >
                  <Mail className="w-4 h-4 mr-2" />
                  Email
                </Button>
                <Button
                  onClick={copyShareLink}
                  variant="outline"
                  className="border-slate-600 text-white hover:bg-slate-800"
                  data-testid="copy-link"
                >
                  <Copy className="w-4 h-4 mr-2" />
                  Copy Link
                </Button>
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
