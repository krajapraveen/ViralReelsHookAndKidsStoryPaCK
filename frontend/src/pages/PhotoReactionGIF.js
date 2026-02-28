import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Upload, Wand2, Camera, Loader2, Download, 
  Check, AlertTriangle, Shield, Sparkles, Crown, Image, Play,
  Smile, Heart, Star, Zap, Eye, PartyPopper, Hand, Flame
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import ShareCreation from '../components/ShareCreation';
import WaitingWithGames from '../components/WaitingWithGames';
import { useNotifications } from '../contexts/NotificationContext';

// ============================================
// COPYRIGHT BLOCKED KEYWORDS
// ============================================
const BLOCKED_KEYWORDS = [
  'marvel', 'dc', 'disney', 'naruto', 'pokemon', 'spiderman', 'batman',
  'avengers', 'goku', 'harry potter', 'hogwarts', 'frozen', 'elsa',
  'mickey', 'minnie', 'pixar', 'fortnite', 'minecraft', 'celebrity',
  'politician', 'real person', 'nude', 'nsfw', 'violence', 'gore'
];

const checkBlockedContent = (text) => {
  if (!text) return { blocked: false };
  const lowerText = text.toLowerCase();
  for (const keyword of BLOCKED_KEYWORDS) {
    if (lowerText.includes(keyword)) {
      return { 
        blocked: true, 
        message: 'Brand-based or copyrighted content is not allowed.'
      };
    }
  }
  return { blocked: false };
};

// ============================================
// REACTION TYPES (9 Options)
// ============================================
const REACTION_TYPES = [
  { id: 'happy', emoji: '😀', name: 'Happy', description: 'Joyful smile', color: 'from-yellow-400 to-amber-500' },
  { id: 'laughing', emoji: '😂', name: 'Laughing', description: 'LOL moment', color: 'from-yellow-500 to-orange-500' },
  { id: 'love', emoji: '😍', name: 'Love', description: 'Heart eyes', color: 'from-pink-400 to-rose-500' },
  { id: 'cool', emoji: '😎', name: 'Cool', description: 'Sunglasses vibe', color: 'from-blue-400 to-cyan-500' },
  { id: 'surprised', emoji: '😮', name: 'Surprised', description: 'Wow moment', color: 'from-purple-400 to-violet-500' },
  { id: 'sad', emoji: '😢', name: 'Sad', description: 'Emotional moment', color: 'from-blue-500 to-indigo-600' },
  { id: 'celebrate', emoji: '👏', name: 'Celebrate', description: 'Clapping', color: 'from-green-400 to-emerald-500' },
  { id: 'waving', emoji: '👋', name: 'Waving', description: 'Hello/Goodbye', color: 'from-orange-400 to-amber-500' },
  { id: 'wow', emoji: '🔥', name: 'Wow', description: 'On fire!', color: 'from-red-500 to-orange-600' },
];

// ============================================
// GIF STYLES (5 Options)
// ============================================
const GIF_STYLES = [
  { id: 'cartoon_motion', name: 'Cartoon Motion', description: 'Bouncy cartoon animation' },
  { id: 'comic_bounce', name: 'Comic Bounce', description: 'Classic comic pop effect' },
  { id: 'sticker_style', name: 'Sticker Style', description: 'Cute sticker with outline' },
  { id: 'neon_glow', name: 'Neon Glow', description: 'Glowing neon effect' },
  { id: 'minimal_clean', name: 'Minimal Clean', description: 'Simple and elegant' },
];

// ============================================
// PRICING
// ============================================
const PRICING = {
  single: {
    base: 8,
    addOns: {
      hd_quality: 3,
      transparent_bg: 3,
      text_caption: 2,
      commercial_license: 10
    }
  },
  pack: {
    base: 25,  // 6 emotions at once
    addOns: {
      hd_quality: 5,
      commercial_license: 15
    }
  }
};

export default function PhotoReactionGIF() {
  // User state
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  
  // Wizard state
  const [step, setStep] = useState(1);
  const maxSteps = 4;
  
  // Step 1: Photo
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  
  // Step 2: Reaction type
  const [mode, setMode] = useState('single'); // 'single' or 'pack'
  const [selectedReaction, setSelectedReaction] = useState(null);
  const [selectedPackReactions, setSelectedPackReactions] = useState([]);
  
  // Step 3: Style
  const [selectedStyle, setSelectedStyle] = useState('cartoon_motion');
  
  // Step 4: Add-ons & Generate
  const [addOns, setAddOns] = useState({
    hd_quality: false,
    transparent_bg: false,
    text_caption: false,
    commercial_license: false
  });
  const [captionText, setCaptionText] = useState('');
  
  // Generation state
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [pollingInterval, setPollingIntervalState] = useState(null);
  
  // Modals
  const [showRating, setShowRating] = useState(false);
  const [showUpsell, setShowUpsell] = useState(false);

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

  // Photo handlers
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

  // Calculate cost
  const calculateCost = () => {
    let total = 0;
    
    if (mode === 'single') {
      total = PRICING.single.base;
      if (addOns.hd_quality) total += PRICING.single.addOns.hd_quality;
      if (addOns.transparent_bg) total += PRICING.single.addOns.transparent_bg;
      if (addOns.text_caption) total += PRICING.single.addOns.text_caption;
      if (addOns.commercial_license) total += PRICING.single.addOns.commercial_license;
    } else {
      total = PRICING.pack.base;
      if (addOns.hd_quality) total += PRICING.pack.addOns.hd_quality;
      if (addOns.commercial_license) total += PRICING.pack.addOns.commercial_license;
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
      const res = await api.get(`/api/reaction-gif/job/${jobId}`);
      setJob(res.data);
      
      if (res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
        if (pollingInterval) clearInterval(pollingInterval);
        setPollingIntervalState(null);
        setLoading(false);
        fetchCredits();
        
        if (res.data.status === 'COMPLETED') {
          toast.success('Your reaction GIF is ready!');
          setTimeout(() => setShowRating(true), 2000);
        } else {
          toast.error('Generation failed. Please try again.');
        }
      }
    } catch (e) {
      console.error('Poll error:', e);
    }
  }, [pollingInterval]);

  // Generate GIF
  const generateGIF = async () => {
    if (!photo) {
      toast.error('Please upload a photo first');
      return;
    }
    
    if (mode === 'single' && !selectedReaction) {
      toast.error('Please select a reaction type');
      return;
    }
    
    // Validate caption
    if (addOns.text_caption && captionText) {
      const check = checkBlockedContent(captionText);
      if (check.blocked) {
        toast.error(check.message);
        return;
      }
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
      formData.append('mode', mode);
      formData.append('style', selectedStyle);
      
      if (mode === 'single') {
        formData.append('reaction', selectedReaction);
      } else {
        // Pack mode - use default 6 emotions
        formData.append('reactions', JSON.stringify(['happy', 'laughing', 'love', 'cool', 'surprised', 'wow']));
      }
      
      formData.append('hd_quality', addOns.hd_quality);
      formData.append('transparent_bg', addOns.transparent_bg);
      formData.append('caption', addOns.text_caption ? captionText : '');
      formData.append('commercial_license', addOns.commercial_license);
      
      const res = await api.post('/api/reaction-gif/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setJob({ id: res.data.jobId, status: 'QUEUED', progress: 0 });
      toast.success('Generation started!');
      
      const interval = setInterval(() => pollJobStatus(res.data.jobId), 2000);
      setPollingIntervalState(interval);
      
    } catch (e) {
      setLoading(false);
      toast.error(e.response?.data?.detail || 'Generation failed');
    }
  };

  // Download handler
  const handleDownload = async () => {
    if (!job?.id) return;
    
    // Free users see watermark
    if (userPlan === 'free' && !job.purchased) {
      setShowUpsell(true);
      return;
    }
    
    try {
      const res = await api.post(`/api/reaction-gif/download/${job.id}`);
      if (res.data.success) {
        toast.success('Download started!');
        
        res.data.downloadUrls?.forEach((url, i) => {
          const fullUrl = url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`;
          const link = document.createElement('a');
          link.href = fullUrl;
          link.download = `reaction_gif_${i + 1}.gif`;
          link.click();
        });
        
        fetchCredits();
      }
    } catch (e) {
      toast.error('Download failed');
    }
  };

  // Navigation
  const nextStep = () => {
    if (step < maxSteps) setStep(step + 1);
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  // Reset
  const resetWizard = () => {
    setStep(1);
    clearPhoto();
    setMode('single');
    setSelectedReaction(null);
    setSelectedStyle('cartoon_motion');
    setAddOns({
      hd_quality: false,
      transparent_bg: false,
      text_caption: false,
      commercial_license: false
    });
    setCaptionText('');
    setJob(null);
  };

  // Can proceed?
  const canProceed = () => {
    switch (step) {
      case 1: return photo !== null;
      case 2: return mode === 'pack' || selectedReaction !== null;
      case 3: return selectedStyle !== null;
      case 4: return true;
      default: return false;
    }
  };

  // ============================================
  // RENDER STEP 1: Upload Photo
  // ============================================
  const renderStep1 = () => (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 1 of 4</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Upload Your Photo</h3>
        <p className="text-slate-400">Use a clear front-facing image for best results</p>
      </div>
      
      <div 
        className="border-2 border-dashed border-slate-600 rounded-2xl p-12 text-center hover:border-pink-500 transition-colors cursor-pointer"
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
      
      <div className="flex justify-center mt-8">
        <Button 
          onClick={nextStep}
          disabled={!canProceed()}
          className="px-8 bg-gradient-to-r from-pink-600 to-purple-600"
          data-testid="next-step-btn"
        >
          Continue <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 2: Choose Reaction
  // ============================================
  const renderStep2 = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 2 of 4</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Choose Reaction Type</h3>
        <p className="text-slate-400">Select the emotion for your reaction GIF</p>
      </div>
      
      {/* Mode Selection */}
      <div className="flex justify-center mb-8">
        <div className="bg-slate-800/50 rounded-2xl p-2 flex gap-2">
          <button
            onClick={() => setMode('single')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              mode === 'single' 
                ? 'bg-gradient-to-r from-pink-600 to-purple-600 text-white' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Smile className="w-5 h-5" />
            Single Reaction
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">{PRICING.single.base} cr</span>
          </button>
          <button
            onClick={() => setMode('pack')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              mode === 'pack' 
                ? 'bg-gradient-to-r from-pink-600 to-purple-600 text-white' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-5 h-5" />
            Reaction Pack (6)
            <span className="text-xs bg-yellow-500 text-black px-2 py-0.5 rounded-full">BEST VALUE</span>
          </button>
        </div>
      </div>
      
      {mode === 'single' ? (
        /* Single Reaction Grid */
        <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
          {REACTION_TYPES.map((reaction) => (
            <div
              key={reaction.id}
              onClick={() => setSelectedReaction(reaction.id)}
              className={`relative p-4 rounded-2xl border-2 cursor-pointer transition-all hover:scale-105 text-center ${
                selectedReaction === reaction.id
                  ? 'border-pink-500 bg-pink-500/20 shadow-lg shadow-pink-500/20'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
              }`}
              data-testid={`reaction-${reaction.id}`}
            >
              <span className="text-5xl mb-2 block">{reaction.emoji}</span>
              <p className="font-medium text-white text-sm">{reaction.name}</p>
              <p className="text-xs text-slate-500">{reaction.description}</p>
              {selectedReaction === reaction.id && (
                <Check className="absolute top-2 right-2 w-5 h-5 text-pink-400" />
              )}
            </div>
          ))}
        </div>
      ) : (
        /* Pack Info */
        <div className="bg-gradient-to-r from-pink-600/20 to-purple-600/20 border border-pink-500/30 rounded-2xl p-8 text-center">
          <h4 className="text-xl font-bold text-white mb-4">Reaction Pack Includes:</h4>
          <div className="flex flex-wrap justify-center gap-4 mb-6">
            {['😀', '😂', '😍', '😎', '😮', '🔥'].map((emoji, i) => (
              <div key={i} className="text-5xl">{emoji}</div>
            ))}
          </div>
          <p className="text-slate-300 mb-4">Get 6 reaction GIFs at once for the price of 3!</p>
          <div className="inline-flex items-center gap-2 bg-green-500/20 text-green-400 px-4 py-2 rounded-full">
            <Star className="w-5 h-5" />
            Save 55% compared to buying separately
          </div>
        </div>
      )}
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep}
          disabled={!canProceed()}
          className="px-8 bg-gradient-to-r from-pink-600 to-purple-600"
        >
          Continue <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 3: Choose Style
  // ============================================
  const renderStep3 = () => (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
          <span className="text-pink-400 font-medium">Step 3 of 4</span>
        </div>
        <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Choose GIF Style</h3>
        <p className="text-slate-400">Select the animation style for your GIF</p>
      </div>
      
      <div className="space-y-3">
        {GIF_STYLES.map((style) => (
          <div
            key={style.id}
            onClick={() => setSelectedStyle(style.id)}
            className={`flex items-center justify-between p-5 rounded-xl border-2 cursor-pointer transition-all ${
              selectedStyle === style.id
                ? 'border-pink-500 bg-pink-500/10'
                : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
            }`}
            data-testid={`style-${style.id}`}
          >
            <div className="flex items-center gap-4">
              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                selectedStyle === style.id ? 'border-pink-500 bg-pink-500' : 'border-slate-600'
              }`}>
                {selectedStyle === style.id && <Check className="w-3 h-3 text-white" />}
              </div>
              <div>
                <h4 className="font-semibold text-white">{style.name}</h4>
                <p className="text-sm text-slate-400">{style.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button 
          onClick={nextStep}
          disabled={!canProceed()}
          className="px-8 bg-gradient-to-r from-pink-600 to-purple-600"
        >
          Continue <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // ============================================
  // RENDER STEP 4: Generate
  // ============================================
  const renderStep4 = () => {
    const reaction = REACTION_TYPES.find(r => r.id === selectedReaction);
    const style = GIF_STYLES.find(s => s.id === selectedStyle);
    
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-500/20 rounded-full mb-4">
            <span className="text-pink-400 font-medium">Step 4 of 4</span>
          </div>
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">Create My GIF</h3>
          <p className="text-slate-400">Add extras and generate your reaction GIF</p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8">
          {/* Add-ons & Summary */}
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h4 className="font-bold text-white mb-4">Summary</h4>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Type:</span>
                  <span className="text-white">{mode === 'single' ? 'Single Reaction' : 'Reaction Pack (6)'}</span>
                </div>
                {mode === 'single' && reaction && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Reaction:</span>
                    <span className="text-white">{reaction.emoji} {reaction.name}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-400">Style:</span>
                  <span className="text-white">{style?.name}</span>
                </div>
              </div>
            </div>
            
            {/* Add-ons */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
              <h4 className="font-bold text-white mb-4">Add-ons</h4>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
                  <span className="text-slate-300 text-sm">HD Quality</span>
                  <div className="flex items-center gap-2">
                    <span className="text-pink-400 text-sm">
                      +{mode === 'single' ? PRICING.single.addOns.hd_quality : PRICING.pack.addOns.hd_quality} cr
                    </span>
                    <input 
                      type="checkbox" 
                      checked={addOns.hd_quality}
                      onChange={(e) => setAddOns({...addOns, hd_quality: e.target.checked})}
                      className="w-4 h-4 accent-pink-500"
                    />
                  </div>
                </label>
                
                {mode === 'single' && (
                  <>
                    <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
                      <span className="text-slate-300 text-sm">Transparent Background</span>
                      <div className="flex items-center gap-2">
                        <span className="text-pink-400 text-sm">+{PRICING.single.addOns.transparent_bg} cr</span>
                        <input 
                          type="checkbox" 
                          checked={addOns.transparent_bg}
                          onChange={(e) => setAddOns({...addOns, transparent_bg: e.target.checked})}
                          className="w-4 h-4 accent-pink-500"
                        />
                      </div>
                    </label>
                    
                    <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
                      <span className="text-slate-300 text-sm">Text Caption</span>
                      <div className="flex items-center gap-2">
                        <span className="text-pink-400 text-sm">+{PRICING.single.addOns.text_caption} cr</span>
                        <input 
                          type="checkbox" 
                          checked={addOns.text_caption}
                          onChange={(e) => setAddOns({...addOns, text_caption: e.target.checked})}
                          className="w-4 h-4 accent-pink-500"
                        />
                      </div>
                    </label>
                    
                    {addOns.text_caption && (
                      <Input
                        placeholder="Enter caption text..."
                        value={captionText}
                        onChange={(e) => setCaptionText(e.target.value)}
                        className="bg-slate-700 border-slate-600 text-white"
                        maxLength={50}
                      />
                    )}
                  </>
                )}
                
                <label className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700">
                  <span className="text-slate-300 text-sm">Commercial License</span>
                  <div className="flex items-center gap-2">
                    <span className="text-pink-400 text-sm">
                      +{mode === 'single' ? PRICING.single.addOns.commercial_license : PRICING.pack.addOns.commercial_license} cr
                    </span>
                    <input 
                      type="checkbox" 
                      checked={addOns.commercial_license}
                      onChange={(e) => setAddOns({...addOns, commercial_license: e.target.checked})}
                      className="w-4 h-4 accent-pink-500"
                    />
                  </div>
                </label>
              </div>
            </div>
            
            {/* Cost */}
            <div className="bg-gradient-to-r from-pink-600/20 to-purple-600/20 border border-pink-500/30 rounded-xl p-6">
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-white">Total Cost:</span>
                <span className="text-3xl font-bold text-pink-400">{calculateCost()} credits</span>
              </div>
              {userPlan !== 'free' && (
                <p className="text-xs text-green-400 mt-1">
                  {userPlan === 'creator' ? '20%' : userPlan === 'pro' ? '30%' : '40%'} subscriber discount applied!
                </p>
              )}
            </div>
            
            <Button 
              onClick={generateGIF}
              disabled={loading || credits < calculateCost()}
              className="w-full py-6 text-lg bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
              data-testid="generate-btn"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Creating Your GIF...</>
              ) : (
                <><Wand2 className="w-5 h-5 mr-2" /> Create My GIF</>
              )}
            </Button>
          </div>
          
          {/* Result */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
            <h4 className="font-bold text-white mb-4">Result</h4>
            
            {job ? (
              <div className="space-y-4">
                {/* Status */}
                <div className="flex items-center justify-between">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                    job.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400 animate-pulse'
                  }`}>
                    {job.status === 'PROCESSING' ? 'CREATING...' : job.status}
                  </span>
                </div>
                
                {/* Progress - Show WaitingWithGames during processing */}
                {(job.status === 'PROCESSING' || job.status === 'QUEUED') && (
                  <WaitingWithGames 
                    progress={job.progress || 0}
                    status={job.progressMessage || (job.status === 'QUEUED' ? 'In queue - your GIF is being prepared...' : 'Creating your reaction GIF...')}
                    estimatedTime="30-60 seconds"
                    onCancel={() => toast.info('Generation in progress - please wait')}
                    currentFeature="/app/gif-maker"
                    showExploreFeatures={true}
                  />
                )}
                
                {/* Result GIF */}
                {job.status === 'COMPLETED' && job.resultUrl && (
                  <div className="space-y-4">
                    <div className="rounded-xl overflow-hidden border border-slate-600 bg-slate-700/50">
                      <img 
                        src={job.resultUrl.startsWith('http') ? job.resultUrl : `${process.env.REACT_APP_BACKEND_URL}${job.resultUrl}`}
                        alt="Reaction GIF"
                        className="w-full"
                      />
                    </div>
                    
                    {/* Free user watermark notice */}
                    {userPlan === 'free' && !job.purchased ? (
                      <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-xl p-4 text-center">
                        <p className="text-yellow-400 font-medium mb-2">Preview (Watermarked)</p>
                        <Button 
                          onClick={() => setShowUpsell(true)}
                          className="bg-yellow-500 hover:bg-yellow-600 text-black"
                        >
                          <Crown className="w-4 h-4 mr-2" /> Remove Watermark & Download
                        </Button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <Button onClick={handleDownload} className="flex-1 bg-pink-600 hover:bg-pink-700">
                          <Download className="w-4 h-4 mr-2" /> Download
                        </Button>
                        <ShareCreation 
                          contentType="reaction_gif"
                          contentId={job.id}
                          previewUrl={job.resultUrl}
                        />
                      </div>
                    )}
                  </div>
                )}
                
                {/* Pack Results */}
                {job.status === 'COMPLETED' && job.results && job.results.length > 1 && (
                  <div className="grid grid-cols-3 gap-2">
                    {job.results.map((result, i) => (
                      <div key={i} className="rounded-lg overflow-hidden border border-slate-600">
                        <img 
                          src={result.url.startsWith('http') ? result.url : `${process.env.REACT_APP_BACKEND_URL}${result.url}`}
                          alt={`Reaction ${i + 1}`}
                          className="w-full"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <Play className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                <p>Your reaction GIF will appear here</p>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex justify-between mt-8">
          <Button variant="outline" onClick={prevStep} className="text-slate-300 border-slate-600" disabled={loading}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          {job?.status === 'COMPLETED' && (
            <Button onClick={resetWizard} variant="outline" className="text-slate-300 border-slate-600">
              Create Another
            </Button>
          )}
        </div>
      </div>
    );
  };

  // ============================================
  // MAIN RENDER
  // ============================================
  const renderCurrentStep = () => {
    switch (step) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      case 4: return renderStep4();
      default: return renderStep1();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
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
                <Smile className="w-6 h-6 text-pink-400" />
                <div>
                  <h1 className="text-xl md:text-2xl font-bold text-white">Photo Reaction GIF Creator</h1>
                  <p className="text-xs text-slate-400 hidden md:block">Turn your photo into fun, shareable reaction GIFs in seconds</p>
                </div>
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Progress Indicator */}
        <div className="max-w-md mx-auto mb-8">
          <div className="flex items-center justify-between">
            {Array.from({ length: maxSteps }).map((_, i) => (
              <React.Fragment key={i}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                  i + 1 < step ? 'bg-green-500 text-white' :
                  i + 1 === step ? 'bg-pink-600 text-white scale-110' :
                  'bg-slate-700 text-slate-400'
                }`}>
                  {i + 1 < step ? <Check className="w-5 h-5" /> : i + 1}
                </div>
                {i < maxSteps - 1 && (
                  <div className={`flex-1 h-1 mx-2 rounded ${
                    i + 1 < step ? 'bg-green-500' : 'bg-slate-700'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-500">
            <span>Upload</span>
            <span>Reaction</span>
            <span>Style</span>
            <span>Create</span>
          </div>
        </div>

        {renderCurrentStep()}
        
        {/* Legal Disclaimer */}
        <div className="mt-12 bg-slate-800/30 rounded-xl p-4 border border-slate-700 max-w-4xl mx-auto">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-pink-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-slate-300 font-medium mb-1">Content Policy</p>
              <p className="text-xs text-slate-400">
                Brand-based or copyrighted content is not allowed. 
                Upload only images you own or have permission to use.
              </p>
            </div>
          </div>
        </div>
      </main>
      
      {/* Modals */}
      <RatingModal 
        isOpen={showRating}
        onClose={() => setShowRating(false)}
        featureKey="reaction_gif"
        relatedRequestId={job?.id}
      />
      
      <UpsellModal
        isOpen={showUpsell}
        onClose={() => setShowUpsell(false)}
        feature="reaction_gif"
        generationId={job?.id}
        onSuccess={() => {
          fetchCredits();
          setShowUpsell(false);
        }}
      />
    </div>
  );
}
