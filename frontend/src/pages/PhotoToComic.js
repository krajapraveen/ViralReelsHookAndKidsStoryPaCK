import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Upload, Wand2, Image, Camera, Sparkles, 
  Loader2, Download, Check, AlertTriangle, Shield, Info,
  User, Palette, Book, Zap, Crown, Lock
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import ShareCreation from '../components/ShareCreation';

// Copyright blocked keywords (case-insensitive, substring match)
const BLOCKED_KEYWORDS = [
  // Superhero / Comic IP
  'marvel', 'dc', 'avengers', 'spiderman', 'spider-man', 'batman', 'superman',
  'ironman', 'iron man', 'captain america', 'thor', 'hulk', 'joker', 
  'wonder woman', 'flash', 'deadpool', 'x-men', 'wolverine', 'venom',
  // Disney / Animation
  'disney', 'pixar', 'frozen', 'elsa', 'anna', 'mickey', 'minnie', 
  'donald duck', 'goofy', 'toy story', 'lightyear',
  // Anime / Manga
  'naruto', 'sasuke', 'dragon ball', 'goku', 'one piece', 'luffy', 
  'attack on titan', 'demon slayer', 'pokemon', 'pikachu', 'studio ghibli',
  // Games / Entertainment
  'fortnite', 'minecraft', 'league of legends', 'valorant', 'pubg', 
  'call of duty', 'gta', 'harry potter', 'hogwarts',
  // Brand / Logo
  'nike', 'adidas', 'coca cola', 'pepsi', 'apple logo', 'tesla logo', 
  'youtube logo', 'instagram logo', 'facebook logo'
];

// Check for blocked keywords
const checkBlockedContent = (text) => {
  if (!text) return { blocked: false };
  const lowerText = text.toLowerCase();
  for (const keyword of BLOCKED_KEYWORDS) {
    if (lowerText.includes(keyword)) {
      return { 
        blocked: true, 
        keyword,
        suggestion: `We create original comic characters only. Try using generic descriptions like "masked hero" or "animated style" instead.`
      };
    }
  }
  return { blocked: false };
};

// Safe Style Presets
const STYLE_PRESETS = {
  action: [
    { id: 'bold_superhero', name: 'Bold Superhero', description: 'Dynamic heroic poses with bold colors' },
    { id: 'dark_vigilante', name: 'Dark Vigilante', description: 'Moody, shadowy crime-fighter style' },
    { id: 'retro_action', name: 'Retro Action Comic', description: 'Classic 80s action comic aesthetic' },
    { id: 'dynamic_battle', name: 'Dynamic Battle Scene', description: 'High-energy action sequences' },
  ],
  fun: [
    { id: 'cartoon_fun', name: 'Cartoon Fun', description: 'Bright, playful cartoon style' },
    { id: 'meme_expression', name: 'Meme Expression', description: 'Exaggerated funny expressions' },
    { id: 'comic_caricature', name: 'Comic Caricature', description: 'Playful exaggerated features' },
    { id: 'exaggerated_reaction', name: 'Exaggerated Reaction', description: 'Over-the-top emotional reactions' },
  ],
  soft: [
    { id: 'romance_comic', name: 'Romance Comic', description: 'Soft, dreamy romantic style' },
    { id: 'dreamy_pastel', name: 'Dreamy Pastel', description: 'Gentle pastel color palette' },
    { id: 'soft_manga', name: 'Soft Manga Inspired', description: 'Gentle anime-inspired look' },
    { id: 'cute_chibi', name: 'Cute Chibi', description: 'Adorable mini character style' },
  ],
  fantasy: [
    { id: 'magical_fantasy', name: 'Magical Fantasy', description: 'Enchanted mystical atmosphere' },
    { id: 'medieval_adventure', name: 'Medieval Adventure', description: 'Knights and castles theme' },
    { id: 'scifi_neon', name: 'Sci-Fi Neon', description: 'Futuristic neon cyberpunk' },
    { id: 'cyberpunk_comic', name: 'Cyberpunk Comic', description: 'High-tech dystopian style' },
  ],
  kids: [
    { id: 'kids_storybook', name: 'Kids Storybook Comic', description: 'Friendly children\'s book style' },
    { id: 'friendly_animal', name: 'Friendly Animal Comic', description: 'Cute animal characters' },
    { id: 'classroom_comic', name: 'Classroom Comic', description: 'School-themed fun' },
    { id: 'adventure_kids', name: 'Adventure Kids Style', description: 'Kid-friendly adventures' },
  ],
  minimal: [
    { id: 'black_white_ink', name: 'Black & White Ink', description: 'Classic ink illustration' },
    { id: 'sketch_outline', name: 'Sketch Outline', description: 'Hand-drawn sketch look' },
    { id: 'noir_comic', name: 'Noir Comic', description: 'Film noir dramatic shadows' },
    { id: 'vintage_print', name: 'Vintage Print Style', description: 'Retro newspaper print' },
  ],
};

// Genre Presets
const GENRE_PRESETS = [
  { id: 'action', name: 'Action', icon: Zap },
  { id: 'comedy', name: 'Comedy', icon: Sparkles },
  { id: 'romance', name: 'Romance', icon: Sparkles },
  { id: 'adventure', name: 'Adventure', icon: Sparkles },
  { id: 'fantasy', name: 'Fantasy', icon: Sparkles },
  { id: 'scifi', name: 'Sci-Fi', icon: Sparkles },
  { id: 'mystery', name: 'Mystery', icon: Sparkles },
  { id: 'kids_friendly', name: 'Kids Friendly', icon: Sparkles },
  { id: 'slice_of_life', name: 'Slice of Life', icon: Sparkles },
  { id: 'motivational', name: 'Motivational', icon: Sparkles },
];

// Pricing Configuration
const PRICING = {
  comic_avatar: {
    base: 15,
    add_ons: {
      transparent_bg: 3,
      multiple_poses: 5,
      hd_export: 5,
    }
  },
  comic_strip: {
    panels: {
      3: { credits: 25, label: '3 Panels' },
      4: { credits: 32, label: '4 Panels', popular: true },
      6: { credits: 45, label: '6 Panels', bestValue: true },
    },
    add_ons: {
      auto_dialogue: 5,
      custom_speech: 3,
      hd_export: 8,
    }
  }
};

export default function PhotoToComic() {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  
  // Mode selection: 'avatar' or 'strip'
  const [mode, setMode] = useState(null);
  
  // Wizard step (1-3 for avatar, 1-5 for strip)
  const [step, setStep] = useState(1);
  
  // Photo upload
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  
  // Style & customization
  const [styleCategory, setStyleCategory] = useState('action');
  const [selectedStyle, setSelectedStyle] = useState(null);
  const [genre, setGenre] = useState('action');
  const [customDetails, setCustomDetails] = useState('');
  const [dialogue, setDialogue] = useState('');
  
  // Comic Strip specific
  const [panelCount, setPanelCount] = useState(4);
  const [storyPrompt, setStoryPrompt] = useState('');
  const [includeDialogue, setIncludeDialogue] = useState(true);
  
  // Add-ons
  const [addOns, setAddOns] = useState({
    transparent_bg: false,
    multiple_poses: false,
    hd_export: false,
    auto_dialogue: true,
    custom_speech: false,
  });
  
  // Generation state
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [pollingInterval, setPollingIntervalState] = useState(null);
  
  // Modals
  const [showRating, setShowRating] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);
  const [contentError, setContentError] = useState(null);

  useEffect(() => {
    fetchCredits();
    fetchUserPlan();
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  const fetchCredits = async () => {
    try {
      const res = await api.get('/api/credits/balance');
      setCredits(res.data.credits);
    } catch (e) {
      console.error('Failed to fetch credits');
    }
  };

  const fetchUserPlan = async () => {
    try {
      const res = await api.get('/api/user/profile');
      setUserPlan(res.data.user?.plan || 'free');
    } catch (e) {
      console.error('Failed to fetch user plan');
    }
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Image too large. Max 10MB.');
        return;
      }
      if (photoPreview) URL.revokeObjectURL(photoPreview);
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
      setJob(null);
    }
  };

  const clearPhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
    setJob(null);
  };

  // Validate text inputs for blocked content
  const validateContent = (text) => {
    const check = checkBlockedContent(text);
    if (check.blocked) {
      setContentError(check);
      return false;
    }
    setContentError(null);
    return true;
  };

  // Calculate total cost
  const calculateCost = () => {
    let total = 0;
    if (mode === 'avatar') {
      total = PRICING.comic_avatar.base;
      if (addOns.transparent_bg) total += PRICING.comic_avatar.add_ons.transparent_bg;
      if (addOns.multiple_poses) total += PRICING.comic_avatar.add_ons.multiple_poses;
      if (addOns.hd_export) total += PRICING.comic_avatar.add_ons.hd_export;
    } else if (mode === 'strip') {
      total = PRICING.comic_strip.panels[panelCount]?.credits || 25;
      if (addOns.auto_dialogue) total += PRICING.comic_strip.add_ons.auto_dialogue;
      if (addOns.custom_speech) total += PRICING.comic_strip.add_ons.custom_speech;
      if (addOns.hd_export) total += PRICING.comic_strip.add_ons.hd_export;
    }
    
    // Apply plan discount
    if (userPlan === 'creator') total = Math.floor(total * 0.8);
    else if (userPlan === 'pro') total = Math.floor(total * 0.7);
    else if (userPlan === 'studio') total = Math.floor(total * 0.6);
    
    return total;
  };

  // Poll job status
  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await api.get(`/api/photo-to-comic/job/${jobId}`);
      setJob(res.data);
      
      if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
        if (pollingInterval) clearInterval(pollingInterval);
        setPollingIntervalState(null);
        setLoading(false);
        fetchCredits();
        
        if (res.data.status === 'COMPLETED') {
          toast.success('Your comic character is ready!');
          setTimeout(() => setShowRating(true), 2000);
        } else {
          toast.error('Generation failed. Please try again.');
        }
      }
    } catch (e) {
      console.error('Poll error:', e);
    }
  }, [pollingInterval]);

  // Generate comic avatar
  const generateAvatar = async () => {
    if (!photo) {
      toast.error('Please upload a photo first');
      return;
    }
    
    if (!selectedStyle) {
      toast.error('Please select a style');
      return;
    }
    
    // Validate custom details
    if (customDetails && !validateContent(customDetails)) {
      toast.error('Please remove copyrighted references from your description');
      return;
    }
    
    const cost = calculateCost();
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      setShowUpsell(true);
      return;
    }
    
    setLoading(true);
    setJob(null);
    
    try {
      const formData = new FormData();
      formData.append('photo', photo);
      formData.append('mode', 'avatar');
      formData.append('style', selectedStyle);
      formData.append('style_category', styleCategory);
      formData.append('genre', genre);
      formData.append('custom_details', customDetails || '');
      formData.append('transparent_bg', addOns.transparent_bg);
      formData.append('multiple_poses', addOns.multiple_poses);
      formData.append('hd_export', addOns.hd_export);
      
      const res = await api.post('/api/photo-to-comic/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Generation started!');
      
      const interval = setInterval(() => pollJobStatus(res.data.jobId), 2000);
      setPollingIntervalState(interval);
      
    } catch (e) {
      setLoading(false);
      const errorMsg = e.response?.data?.detail || 'Generation failed';
      if (errorMsg.includes('Copyrighted') || errorMsg.includes('not allowed')) {
        setContentError({ blocked: true, suggestion: errorMsg });
      }
      toast.error(errorMsg);
    }
  };

  // Generate comic strip
  const generateStrip = async () => {
    if (!photo) {
      toast.error('Please upload a photo first');
      return;
    }
    
    if (!storyPrompt.trim()) {
      toast.error('Please describe your comic story');
      return;
    }
    
    // Validate story prompt
    if (!validateContent(storyPrompt)) {
      toast.error('Please remove copyrighted references from your story');
      return;
    }
    
    // Validate dialogue
    if (dialogue && !validateContent(dialogue)) {
      toast.error('Please remove copyrighted references from dialogue');
      return;
    }
    
    const cost = calculateCost();
    if (credits < cost) {
      toast.error(`Insufficient credits. Need ${cost} credits.`);
      setShowUpsell(true);
      return;
    }
    
    setLoading(true);
    setJob(null);
    
    try {
      const formData = new FormData();
      formData.append('photo', photo);
      formData.append('mode', 'strip');
      formData.append('style', selectedStyle || 'cartoon_fun');
      formData.append('style_category', styleCategory);
      formData.append('genre', genre);
      formData.append('panel_count', panelCount);
      formData.append('story_prompt', storyPrompt);
      formData.append('dialogue', dialogue || '');
      formData.append('include_dialogue', includeDialogue);
      formData.append('hd_export', addOns.hd_export);
      
      const res = await api.post('/api/photo-to-comic/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Comic strip generation started!');
      
      const interval = setInterval(() => pollJobStatus(res.data.jobId), 2000);
      setPollingIntervalState(interval);
      
    } catch (e) {
      setLoading(false);
      const errorMsg = e.response?.data?.detail || 'Generation failed';
      if (errorMsg.includes('Copyrighted') || errorMsg.includes('not allowed')) {
        setContentError({ blocked: true, suggestion: errorMsg });
      }
      toast.error(errorMsg);
    }
  };

  // Download handler
  const handleDownload = async () => {
    if (!job?.id) return;
    
    try {
      const res = await api.post(`/api/photo-to-comic/download/${job.id}`);
      if (res.data.success) {
        toast.success(res.data.alreadyPurchased ? 'Re-downloading...' : `Downloaded! ${res.data.creditsDeducted || 0} credits used`);
        
        res.data.downloadUrls?.forEach((url, i) => {
          const fullUrl = url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`;
          const link = document.createElement('a');
          link.href = fullUrl;
          link.download = `comic_${job.id.slice(0, 8)}_${i + 1}.png`;
          link.click();
        });
        
        fetchCredits();
      }
    } catch (e) {
      toast.error('Download failed');
    }
  };

  // Get max steps based on mode
  const getMaxSteps = () => mode === 'avatar' ? 3 : 5;

  // Navigate steps
  const nextStep = () => {
    if (step < getMaxSteps()) setStep(step + 1);
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  // Reset wizard
  const resetWizard = () => {
    setMode(null);
    setStep(1);
    clearPhoto();
    setSelectedStyle(null);
    setCustomDetails('');
    setDialogue('');
    setStoryPrompt('');
    setJob(null);
    setContentError(null);
    setAddOns({
      transparent_bg: false,
      multiple_poses: false,
      hd_export: false,
      auto_dialogue: true,
      custom_speech: false,
    });
  };

  // Render mode selection
  const renderModeSelection = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
          Choose Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">Creation Mode</span>
        </h2>
        <p className="text-slate-400">Transform your photos into amazing comic art</p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Comic Avatar Card */}
        <div 
          onClick={() => { setMode('avatar'); setStep(1); }}
          className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 cursor-pointer hover:border-purple-500 hover:bg-slate-800/70 transition-all group"
          data-testid="mode-avatar"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-500/20 rounded-xl">
              <User className="w-8 h-8 text-purple-400" />
            </div>
            <span className="px-3 py-1 bg-green-500/20 text-green-400 text-sm font-medium rounded-full">
              RECOMMENDED
            </span>
          </div>
          <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
            Comic Avatar
          </h3>
          <p className="text-slate-400 mb-4">
            Transform your photo into a single comic character portrait. Perfect for profile pictures and avatars.
          </p>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <span className="flex items-center gap-1">
              <Check className="w-4 h-4 text-green-400" /> 3 Steps
            </span>
            <span className="flex items-center gap-1">
              <Sparkles className="w-4 h-4 text-purple-400" /> From {PRICING.comic_avatar.base} credits
            </span>
          </div>
        </div>
        
        {/* Comic Strip Card */}
        <div 
          onClick={() => { setMode('strip'); setStep(1); }}
          className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 cursor-pointer hover:border-pink-500 hover:bg-slate-800/70 transition-all group"
          data-testid="mode-strip"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-pink-500/20 rounded-xl">
              <Book className="w-8 h-8 text-pink-400" />
            </div>
            <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 text-sm font-medium rounded-full">
              POPULAR
            </span>
          </div>
          <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-pink-300 transition-colors">
            Comic Strip
          </h3>
          <p className="text-slate-400 mb-4">
            Create a multi-panel comic story featuring you as the main character with AI-generated dialogue.
          </p>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <span className="flex items-center gap-1">
              <Check className="w-4 h-4 text-green-400" /> 5 Steps
            </span>
            <span className="flex items-center gap-1">
              <Sparkles className="w-4 h-4 text-pink-400" /> From {PRICING.comic_strip.panels[3].credits} credits
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  // Render Avatar Step 1: Upload Photo
  const renderAvatarStep1 = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 1 of 3</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Upload Your Photo</h3>
        <p className="text-slate-400">Choose a clear, front-facing photo for best results</p>
      </div>
      
      <div 
        className="border-2 border-dashed border-slate-600 rounded-2xl p-12 text-center hover:border-purple-500 transition-colors cursor-pointer"
        onClick={() => document.getElementById('photo-input').click()}
      >
        {photoPreview ? (
          <div className="space-y-4">
            <img src={photoPreview} alt="Preview" className="max-h-64 mx-auto rounded-xl shadow-lg" />
            <Button variant="outline" onClick={(e) => { e.stopPropagation(); clearPhoto(); }} className="text-slate-300">
              Change Photo
            </Button>
          </div>
        ) : (
          <>
            <Camera className="w-16 h-16 mx-auto text-slate-500 mb-4" />
            <p className="text-lg text-slate-300 mb-2">Click to upload or drag and drop</p>
            <p className="text-sm text-slate-500">PNG, JPG, WEBP up to 10MB</p>
          </>
        )}
      </div>
      <input
        id="photo-input"
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handlePhotoUpload}
        data-testid="photo-input"
      />
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={() => setMode(null)} className="text-slate-300">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep} 
          disabled={!photo}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
          data-testid="next-step-btn"
        >
          Next <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Render Avatar Step 2: Style Selection
  const renderAvatarStep2 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 2 of 3</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Choose Your Style</h3>
        <p className="text-slate-400">Select a comic style that matches your vision</p>
      </div>
      
      {/* Style Category Tabs */}
      <div className="flex flex-wrap justify-center gap-2 mb-6">
        {Object.keys(STYLE_PRESETS).map((cat) => (
          <button
            key={cat}
            onClick={() => { setStyleCategory(cat); setSelectedStyle(null); }}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              styleCategory === cat 
                ? 'bg-purple-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Style Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {STYLE_PRESETS[styleCategory]?.map((style) => (
          <div
            key={style.id}
            onClick={() => setSelectedStyle(style.id)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedStyle === style.id
                ? 'border-purple-500 bg-purple-500/20'
                : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'
            }`}
            data-testid={`style-${style.id}`}
          >
            <h4 className="font-medium text-white mb-1">{style.name}</h4>
            <p className="text-xs text-slate-400">{style.description}</p>
          </div>
        ))}
      </div>
      
      {/* Genre Selection */}
      <div className="mb-6">
        <label className="block text-sm text-slate-400 mb-2">Genre</label>
        <div className="flex flex-wrap gap-2">
          {GENRE_PRESETS.map((g) => (
            <button
              key={g.id}
              onClick={() => setGenre(g.id)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                genre === g.id
                  ? 'bg-pink-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {g.name}
            </button>
          ))}
        </div>
      </div>
      
      {/* Custom Details */}
      <div className="mb-6">
        <label className="block text-sm text-slate-400 mb-2">Custom Details (Optional)</label>
        <Textarea
          placeholder="Add specific details like clothing, accessories, background... (No copyrighted characters!)"
          value={customDetails}
          onChange={(e) => {
            setCustomDetails(e.target.value);
            validateContent(e.target.value);
          }}
          className="bg-slate-700 border-slate-600 text-white"
          data-testid="custom-details"
        />
        {contentError && (
          <div className="mt-2 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-400 text-sm font-medium">Copyrighted content detected</p>
              <p className="text-red-300/80 text-xs mt-1">{contentError.suggestion}</p>
            </div>
          </div>
        )}
      </div>
      
      <div className="flex justify-between">
        <Button variant="outline" onClick={prevStep} className="text-slate-300">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep} 
          disabled={!selectedStyle || contentError?.blocked}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Next <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Render Avatar Step 3: Generate & Result
  const renderAvatarStep3 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full mb-4">
          <span className="text-purple-400 font-medium">Step 3 of 3</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Generate Your Avatar</h3>
        <p className="text-slate-400">Review your options and generate</p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-8">
        {/* Summary & Add-ons */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <h4 className="font-bold text-white mb-4">Summary</h4>
          
          <div className="space-y-3 mb-6">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Style:</span>
              <span className="text-white">{STYLE_PRESETS[styleCategory]?.find(s => s.id === selectedStyle)?.name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Genre:</span>
              <span className="text-white">{GENRE_PRESETS.find(g => g.id === genre)?.name}</span>
            </div>
          </div>
          
          <h4 className="font-bold text-white mb-3">Add-ons</h4>
          <div className="space-y-3 mb-6">
            <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
              <span className="text-slate-300 text-sm">Transparent Background</span>
              <div className="flex items-center gap-2">
                <span className="text-purple-400 text-sm">+{PRICING.comic_avatar.add_ons.transparent_bg} cr</span>
                <input 
                  type="checkbox" 
                  checked={addOns.transparent_bg}
                  onChange={(e) => setAddOns({...addOns, transparent_bg: e.target.checked})}
                  className="w-4 h-4 accent-purple-500"
                />
              </div>
            </label>
            <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
              <span className="text-slate-300 text-sm">Multiple Poses (3 variations)</span>
              <div className="flex items-center gap-2">
                <span className="text-purple-400 text-sm">+{PRICING.comic_avatar.add_ons.multiple_poses} cr</span>
                <input 
                  type="checkbox" 
                  checked={addOns.multiple_poses}
                  onChange={(e) => setAddOns({...addOns, multiple_poses: e.target.checked})}
                  className="w-4 h-4 accent-purple-500"
                />
              </div>
            </label>
            <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
              <span className="text-slate-300 text-sm">HD Export (300 DPI)</span>
              <div className="flex items-center gap-2">
                <span className="text-purple-400 text-sm">+{PRICING.comic_avatar.add_ons.hd_export} cr</span>
                <input 
                  type="checkbox" 
                  checked={addOns.hd_export}
                  onChange={(e) => setAddOns({...addOns, hd_export: e.target.checked})}
                  className="w-4 h-4 accent-purple-500"
                />
              </div>
            </label>
          </div>
          
          {/* Cost Summary */}
          <div className="border-t border-slate-600 pt-4">
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-white">Total Cost:</span>
              <span className="text-2xl font-bold text-purple-400">{calculateCost()} credits</span>
            </div>
            {userPlan !== 'free' && (
              <p className="text-xs text-green-400 mt-1">
                {userPlan === 'creator' ? '20%' : userPlan === 'pro' ? '30%' : '40%'} subscriber discount applied!
              </p>
            )}
          </div>
          
          <Button 
            onClick={generateAvatar}
            disabled={loading || credits < calculateCost()}
            className="w-full mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            data-testid="generate-btn"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating...</>
            ) : (
              <><Wand2 className="w-4 h-4 mr-2" /> Generate Avatar ({calculateCost()} credits)</>
            )}
          </Button>
        </div>
        
        {/* Result Panel */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <h4 className="font-bold text-white mb-4">Result</h4>
          
          {job ? (
            <div className="space-y-4">
              {/* Status Badge */}
              <div className="flex items-center justify-between">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                  job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                  'bg-yellow-500/20 text-yellow-400 animate-pulse'
                }`}>
                  {job.status === 'PROCESSING' ? 'GENERATING...' : job.status}
                </span>
              </div>
              
              {/* Progress Bar */}
              {(job.status === 'PROCESSING' || job.status === 'QUEUED') && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Progress</span>
                    <span className="text-purple-400">{job.progress || 0}%</span>
                  </div>
                  <Progress value={job.progress || 0} className="h-2" />
                </div>
              )}
              
              {/* Result Image */}
              {job.resultUrl && (
                <div className="rounded-xl overflow-hidden border border-slate-600">
                  <img 
                    src={job.resultUrl.startsWith('http') ? job.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${job.resultUrl}`}
                    alt="Comic Avatar"
                    className="w-full"
                  />
                </div>
              )}
              
              {/* Download Button */}
              {job.status === 'COMPLETED' && job.resultUrl && (
                <div className="flex gap-2">
                  <Button onClick={handleDownload} className="flex-1 bg-purple-600 hover:bg-purple-700">
                    <Download className="w-4 h-4 mr-2" /> Download
                  </Button>
                  <ShareCreation 
                    contentType="comic_avatar"
                    contentId={job.id}
                    previewUrl={job.resultUrl}
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <Image className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p>Your comic avatar will appear here</p>
            </div>
          )}
        </div>
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300" disabled={loading}>
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        {job?.status === 'COMPLETED' && (
          <Button onClick={resetWizard} variant="outline" className="text-slate-300">
            Create Another
          </Button>
        )}
      </div>
    </div>
  );

  // Render Strip Steps (1-5)
  const renderStripStep1 = () => renderAvatarStep1(); // Same photo upload

  const renderStripStep2 = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 2 of 5</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Describe Your Story</h3>
        <p className="text-slate-400">What adventure will your comic character have?</p>
      </div>
      
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        <div className="mb-6">
          <label className="block text-sm text-slate-400 mb-2">Story Description *</label>
          <Textarea
            placeholder="Describe your comic story... e.g., 'A day at the beach with friends, building sandcastles and playing volleyball'"
            value={storyPrompt}
            onChange={(e) => {
              setStoryPrompt(e.target.value);
              validateContent(e.target.value);
            }}
            className="bg-slate-700 border-slate-600 text-white min-h-32"
            data-testid="story-prompt"
          />
          {contentError && (
            <div className="mt-2 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 text-sm font-medium">Copyrighted content detected</p>
                <p className="text-red-300/80 text-xs mt-1">{contentError.suggestion}</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Panel Count Selection */}
        <div className="mb-6">
          <label className="block text-sm text-slate-400 mb-2">Number of Panels</label>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(PRICING.comic_strip.panels).map(([count, info]) => (
              <button
                key={count}
                onClick={() => setPanelCount(parseInt(count))}
                className={`p-4 rounded-xl border text-center transition-all ${
                  panelCount === parseInt(count)
                    ? 'border-pink-500 bg-pink-500/20'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'
                }`}
              >
                <div className="text-2xl font-bold text-white mb-1">{count}</div>
                <div className="text-xs text-slate-400">Panels</div>
                <div className="text-sm text-pink-400 mt-2">{info.credits} cr</div>
                {info.popular && (
                  <span className="inline-block mt-2 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                    POPULAR
                  </span>
                )}
                {info.bestValue && (
                  <span className="inline-block mt-2 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                    BEST VALUE
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep} 
          disabled={!storyPrompt.trim() || contentError?.blocked}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Next <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStripStep3 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 3 of 5</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Choose Style & Genre</h3>
        <p className="text-slate-400">Customize the look of your comic strip</p>
      </div>
      
      {/* Style Category Tabs */}
      <div className="flex flex-wrap justify-center gap-2 mb-6">
        {Object.keys(STYLE_PRESETS).map((cat) => (
          <button
            key={cat}
            onClick={() => { setStyleCategory(cat); setSelectedStyle(null); }}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              styleCategory === cat 
                ? 'bg-pink-600 text-white' 
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Style Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {STYLE_PRESETS[styleCategory]?.map((style) => (
          <div
            key={style.id}
            onClick={() => setSelectedStyle(style.id)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedStyle === style.id
                ? 'border-pink-500 bg-pink-500/20'
                : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'
            }`}
          >
            <h4 className="font-medium text-white mb-1">{style.name}</h4>
            <p className="text-xs text-slate-400">{style.description}</p>
          </div>
        ))}
      </div>
      
      {/* Genre Selection */}
      <div className="mb-6">
        <label className="block text-sm text-slate-400 mb-2">Genre</label>
        <div className="flex flex-wrap gap-2">
          {GENRE_PRESETS.map((g) => (
            <button
              key={g.id}
              onClick={() => setGenre(g.id)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                genre === g.id
                  ? 'bg-pink-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {g.name}
            </button>
          ))}
        </div>
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep} 
          disabled={!selectedStyle}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Next <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStripStep4 = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 4 of 5</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Dialogue & Add-ons</h3>
        <p className="text-slate-400">Customize dialogue and extra features</p>
      </div>
      
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        {/* Dialogue Options */}
        <div className="mb-6">
          <label className="flex items-center gap-3 mb-4">
            <input 
              type="checkbox"
              checked={includeDialogue}
              onChange={(e) => setIncludeDialogue(e.target.checked)}
              className="w-5 h-5 accent-pink-500"
            />
            <span className="text-white font-medium">Include Dialogue Bubbles</span>
          </label>
          
          {includeDialogue && (
            <div className="pl-8 space-y-4">
              <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer">
                <span className="text-slate-300 text-sm">Auto-generate dialogue (AI)</span>
                <div className="flex items-center gap-2">
                  <span className="text-pink-400 text-sm">+{PRICING.comic_strip.add_ons.auto_dialogue} cr</span>
                  <input 
                    type="radio"
                    name="dialogue-type"
                    checked={addOns.auto_dialogue && !addOns.custom_speech}
                    onChange={() => setAddOns({...addOns, auto_dialogue: true, custom_speech: false})}
                    className="w-4 h-4 accent-pink-500"
                  />
                </div>
              </label>
              
              <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer">
                <span className="text-slate-300 text-sm">Write custom dialogue</span>
                <div className="flex items-center gap-2">
                  <span className="text-pink-400 text-sm">+{PRICING.comic_strip.add_ons.custom_speech} cr</span>
                  <input 
                    type="radio"
                    name="dialogue-type"
                    checked={addOns.custom_speech}
                    onChange={() => setAddOns({...addOns, auto_dialogue: false, custom_speech: true})}
                    className="w-4 h-4 accent-pink-500"
                  />
                </div>
              </label>
              
              {addOns.custom_speech && (
                <Textarea
                  placeholder="Write your dialogue... (One line per panel, use | to separate)"
                  value={dialogue}
                  onChange={(e) => {
                    setDialogue(e.target.value);
                    validateContent(e.target.value);
                  }}
                  className="bg-slate-700 border-slate-600 text-white"
                  data-testid="custom-dialogue"
                />
              )}
            </div>
          )}
        </div>
        
        {/* Other Add-ons */}
        <div className="border-t border-slate-600 pt-4">
          <h4 className="font-medium text-white mb-3">Extra Features</h4>
          <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
            <span className="text-slate-300 text-sm">HD Export (300 DPI)</span>
            <div className="flex items-center gap-2">
              <span className="text-pink-400 text-sm">+{PRICING.comic_strip.add_ons.hd_export} cr</span>
              <input 
                type="checkbox" 
                checked={addOns.hd_export}
                onChange={(e) => setAddOns({...addOns, hd_export: e.target.checked})}
                className="w-4 h-4 accent-pink-500"
              />
            </div>
          </label>
        </div>
        
        {/* Cost Summary */}
        <div className="border-t border-slate-600 pt-4 mt-4">
          <div className="flex justify-between items-center">
            <span className="text-lg font-bold text-white">Estimated Total:</span>
            <span className="text-2xl font-bold text-pink-400">{calculateCost()} credits</span>
          </div>
          {userPlan !== 'free' && (
            <p className="text-xs text-green-400 mt-1">
              Subscriber discount applied!
            </p>
          )}
        </div>
      </div>
      
      {contentError && (
        <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 text-sm font-medium">Copyrighted content detected</p>
            <p className="text-red-300/80 text-xs mt-1">{contentError.suggestion}</p>
          </div>
        </div>
      )}
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep} 
          disabled={contentError?.blocked}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Next <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStripStep5 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 5 of 5</span>
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Generate Your Comic</h3>
        <p className="text-slate-400">Review and create your comic strip</p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-8">
        {/* Summary */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <h4 className="font-bold text-white mb-4">Summary</h4>
          
          <div className="space-y-3 mb-6">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Panels:</span>
              <span className="text-white">{panelCount}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Style:</span>
              <span className="text-white">{STYLE_PRESETS[styleCategory]?.find(s => s.id === selectedStyle)?.name || 'Selected'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Genre:</span>
              <span className="text-white">{GENRE_PRESETS.find(g => g.id === genre)?.name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Dialogue:</span>
              <span className="text-white">{includeDialogue ? (addOns.auto_dialogue ? 'AI Generated' : 'Custom') : 'None'}</span>
            </div>
          </div>
          
          <div className="p-3 bg-slate-700/50 rounded-lg mb-4">
            <p className="text-slate-400 text-xs mb-1">Story:</p>
            <p className="text-white text-sm">{storyPrompt.slice(0, 100)}...</p>
          </div>
          
          {/* Cost Summary */}
          <div className="border-t border-slate-600 pt-4">
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-white">Total Cost:</span>
              <span className="text-2xl font-bold text-pink-400">{calculateCost()} credits</span>
            </div>
          </div>
          
          <Button 
            onClick={generateStrip}
            disabled={loading || credits < calculateCost()}
            className="w-full mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            data-testid="generate-strip-btn"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating...</>
            ) : (
              <><Wand2 className="w-4 h-4 mr-2" /> Generate Comic Strip ({calculateCost()} credits)</>
            )}
          </Button>
        </div>
        
        {/* Result */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 max-h-[600px] overflow-y-auto">
          <h4 className="font-bold text-white mb-4">Result</h4>
          
          {job ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                  job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                  'bg-yellow-500/20 text-yellow-400 animate-pulse'
                }`}>
                  {job.status === 'PROCESSING' ? 'GENERATING...' : job.status}
                </span>
              </div>
              
              {(job.status === 'PROCESSING' || job.status === 'QUEUED') && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Progress</span>
                    <span className="text-pink-400">{job.progress || 0}%</span>
                  </div>
                  <Progress value={job.progress || 0} className="h-2" />
                  {job.progressMessage && (
                    <p className="text-xs text-slate-500">{job.progressMessage}</p>
                  )}
                </div>
              )}
              
              {/* Panel Results */}
              {job.panels && job.panels.length > 0 && (
                <div className="space-y-4">
                  {job.panels.map((panel, i) => (
                    <div key={i} className="rounded-xl overflow-hidden border border-slate-600 bg-slate-700/50">
                      <img 
                        src={panel.imageUrl?.startsWith('http') ? panel.imageUrl : `${process.env.REACT_APP_BACKEND_URL}${panel.imageUrl}`}
                        alt={`Panel ${i + 1}`}
                        className="w-full"
                      />
                      {panel.dialogue && (
                        <div className="p-3 border-t border-slate-600">
                          <p className="text-sm text-slate-300">{panel.dialogue}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {job.status === 'COMPLETED' && job.panels && (
                <div className="flex gap-2 sticky bottom-0 bg-slate-800/90 p-2 rounded-lg">
                  <Button onClick={handleDownload} className="flex-1 bg-pink-600 hover:bg-pink-700">
                    <Download className="w-4 h-4 mr-2" /> Download All
                  </Button>
                  <ShareCreation 
                    contentType="comic_strip"
                    contentId={job.id}
                    previewUrl={job.panels[0]?.imageUrl}
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <Book className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p>Your comic strip will appear here</p>
            </div>
          )}
        </div>
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300" disabled={loading}>
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        {job?.status === 'COMPLETED' && (
          <Button onClick={resetWizard} variant="outline" className="text-slate-300">
            Create Another
          </Button>
        )}
      </div>
    </div>
  );

  // Main render logic
  const renderCurrentStep = () => {
    if (!mode) return renderModeSelection();
    
    if (mode === 'avatar') {
      switch (step) {
        case 1: return renderAvatarStep1();
        case 2: return renderAvatarStep2();
        case 3: return renderAvatarStep3();
        default: return renderAvatarStep1();
      }
    }
    
    if (mode === 'strip') {
      switch (step) {
        case 1: return renderStripStep1();
        case 2: return renderStripStep2();
        case 3: return renderStripStep3();
        case 4: return renderStripStep4();
        case 5: return renderStripStep5();
        default: return renderStripStep1();
      }
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
                <Camera className="w-6 h-6 text-purple-400" />
                <h1 className="text-xl md:text-2xl font-bold text-white">Convert Photos To Comic Character</h1>
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Progress Indicator */}
        {mode && (
          <div className="max-w-xl mx-auto mb-8">
            <div className="flex items-center justify-between">
              {Array.from({ length: getMaxSteps() }).map((_, i) => (
                <React.Fragment key={i}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    i + 1 < step ? 'bg-green-500 text-white' :
                    i + 1 === step ? 'bg-purple-600 text-white' :
                    'bg-slate-700 text-slate-400'
                  }`}>
                    {i + 1 < step ? <Check className="w-4 h-4" /> : i + 1}
                  </div>
                  {i < getMaxSteps() - 1 && (
                    <div className={`flex-1 h-1 mx-2 rounded ${
                      i + 1 < step ? 'bg-green-500' : 'bg-slate-700'
                    }`} />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {renderCurrentStep()}
        
        {/* Legal Safety Notice */}
        <div className="mt-12 bg-slate-800/30 rounded-xl p-4 border border-slate-700 max-w-4xl mx-auto">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-slate-300 font-medium mb-1">Content Policy</p>
              <p className="text-xs text-slate-400">
                Upload only images you own or have permission to use. We do not allow copyrighted characters, 
                celebrity likeness, or brand-based requests. All generated content must be original.
              </p>
            </div>
          </div>
        </div>
      </main>
      
      {/* Modals */}
      <RatingModal 
        isOpen={showRating}
        onClose={() => setShowRating(false)}
        featureKey="photo_to_comic"
        relatedRequestId={job?.id}
      />
      
      <UpsellModal
        isOpen={showUpsell}
        onClose={() => setShowUpsell(false)}
        feature="photo_to_comic"
        generationId={job?.id}
        onSuccess={() => {
          fetchCredits();
          setShowUpsell(false);
        }}
      />
    </div>
  );
}
