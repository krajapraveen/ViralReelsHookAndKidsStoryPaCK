import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, ArrowRight, Upload, Wand2, Loader2, Download, 
  Check, Image, Sparkles, Coins, Crown, Lock, AlertCircle,
  MessageSquare, Palette, Grid3X3, Zap, Shield, ChevronRight,
  X, Plus, Minus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import RatingModal from '../components/RatingModal';
import UpsellModal from '../components/UpsellModal';
import ShareCreation from '../components/ShareCreation';

// =============================================================================
// CONFIGURATION - COPYRIGHT SAFE STYLES
// =============================================================================
const COMIC_STYLES = [
  { id: 'superhero', name: 'Superhero Style', description: 'Bold heroic look', icon: '🦸', premium: false },
  { id: 'manga', name: 'Manga Style', description: 'Japanese comic art', icon: '🎌', premium: false },
  { id: 'cartoon', name: 'Cartoon Style', description: 'Fun animated look', icon: '🎨', premium: false },
  { id: 'retro', name: 'Retro Comic Style', description: 'Classic vintage comics', icon: '📰', premium: false },
  { id: 'fantasy', name: 'Fantasy Style', description: 'Magical fantasy art', icon: '🧙', premium: true },
  { id: 'kids', name: 'Kids Comic Style', description: 'Cute and friendly', icon: '🧒', premium: false },
  { id: 'scifi', name: 'Sci-Fi Style', description: 'Futuristic tech look', icon: '🚀', premium: true },
  { id: 'meme', name: 'Funny Meme Style', description: 'Internet humor style', icon: '😂', premium: true },
];

const STRIP_GENRES = [
  { id: 'action', name: 'Action', icon: '💥' },
  { id: 'comedy', name: 'Comedy', icon: '😄' },
  { id: 'romance', name: 'Romance', icon: '💕' },
  { id: 'adventure', name: 'Adventure', icon: '🗺️' },
  { id: 'fantasy', name: 'Fantasy', icon: '🧙' },
  { id: 'scifi', name: 'Sci-Fi', icon: '🚀' },
  { id: 'kids', name: 'Kids Friendly', icon: '🧸' },
];

// Pricing configuration
const PRICING = {
  avatar: { base: 10, label: 'Comic Avatar' },
  strip_3: { base: 18, label: '3 Panel Strip' },
  strip_6: { base: 30, label: '6 Panel Strip' },
  addons: {
    background: { credits: 3, label: 'Comic Background' },
    speech_bubble: { credits: 2, label: 'Speech Bubble' },
    transparent: { credits: 3, label: 'Transparent PNG' },
    hd: { credits: 5, label: 'HD Export' },
    commercial: { credits: 10, label: 'Commercial License' },
  }
};

// Copyright blocked keywords
const BLOCKED_KEYWORDS = [
  'marvel', 'dc', 'disney', 'naruto', 'pokemon', 'avengers', 'spiderman', 
  'batman', 'superman', 'ironman', 'hulk', 'thor', 'captain america',
  'wonder woman', 'aquaman', 'flash', 'joker', 'thanos', 'loki',
  'mickey', 'minnie', 'goku', 'pikachu', 'anime', 'nintendo', 'sonic'
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================
export default function PhotoToComic() {
  const navigate = useNavigate();
  
  // Mode selection
  const [mode, setMode] = useState(null); // 'avatar' or 'strip'
  const [step, setStep] = useState(1);
  
  // User state
  const [credits, setCredits] = useState(0);
  const [userPlan, setUserPlan] = useState('free');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  // Form state - Avatar
  const [uploadedPhoto, setUploadedPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState(null);
  const [addons, setAddons] = useState({
    background: false,
    speech_bubble: false,
    transparent: false,
    hd: false,
    commercial: false,
  });
  
  // Form state - Strip
  const [selectedGenre, setSelectedGenre] = useState(null);
  const [dialogue, setDialogue] = useState('');
  const [panelCount, setPanelCount] = useState(3);
  
  // Job polling state
  const [currentJobId, setCurrentJobId] = useState(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobMessage, setJobMessage] = useState('');
  const [assetValidated, setAssetValidated] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Result state
  const [result, setResult] = useState(null);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);
  const [lastGenerationId, setLastGenerationId] = useState(null);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const [creditsRes, userRes] = await Promise.all([
        api.get('/api/credits/balance'),
        api.get('/api/auth/me')
      ]);
      setCredits(creditsRes.data.credits || 0);
      setUserPlan(userRes.data.user?.plan || 'free');
    } catch (error) {
      console.error('Failed to fetch user data');
    }
  };

  // =============================================================================
  // HANDLERS
  // =============================================================================
  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Photo must be under 10MB');
      return;
    }
    
    setUploadedPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const removePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setUploadedPhoto(null);
    setPhotoPreview(null);
  };

  const toggleAddon = (addonKey) => {
    setAddons(prev => ({ ...prev, [addonKey]: !prev[addonKey] }));
  };

  const checkCopyrightViolation = (text) => {
    const lowerText = text.toLowerCase();
    for (const keyword of BLOCKED_KEYWORDS) {
      if (lowerText.includes(keyword)) {
        return keyword;
      }
    }
    return null;
  };

  const calculateTotal = () => {
    let total = 0;
    
    if (mode === 'avatar') {
      total = PRICING.avatar.base;
    } else if (mode === 'strip') {
      total = panelCount === 3 ? PRICING.strip_3.base : PRICING.strip_6.base;
    }
    
    // Add addons
    Object.entries(addons).forEach(([key, enabled]) => {
      if (enabled && PRICING.addons[key]) {
        total += PRICING.addons[key].credits;
      }
    });
    
    return total;
  };

  const handleGenerate = async () => {
    if (!uploadedPhoto) {
      toast.error('Please upload a photo');
      return;
    }
    if (mode === 'avatar' && !selectedStyle) {
      toast.error('Please select a style');
      return;
    }
    if (mode === 'strip' && !selectedGenre) {
      toast.error('Please select a genre');
      return;
    }
    if (dialogue) {
      const violation = checkCopyrightViolation(dialogue);
      if (violation) {
        toast.error(`Brand-based or copyrighted characters are not allowed. Found: "${violation}"`);
        return;
      }
    }
    const totalCost = calculateTotal();
    if (credits < totalCost) {
      toast.error(`Insufficient credits. Need ${totalCost}, have ${credits}`);
      navigate('/app/billing');
      return;
    }

    setGenerating(true);
    setJobProgress(0);
    setJobMessage('Submitting...');
    setAssetValidated(false);

    try {
      const formData = new FormData();
      formData.append('photo', uploadedPhoto);
      formData.append('mode', mode);
      formData.append('style', selectedStyle || '');
      formData.append('genre', selectedGenre || '');
      formData.append('dialogue', dialogue);
      formData.append('panel_count', panelCount.toString());
      formData.append('addons', JSON.stringify(addons));

      const res = await api.post('/api/photo-to-comic/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (res.data.success && res.data.jobId) {
        setCurrentJobId(res.data.jobId);
        setLastGenerationId(res.data.jobId);
        setCredits(prev => prev - totalCost);
        setStep(mode === 'avatar' ? 4 : 6);
        toast.success('Generation started!');
        pollJobStatus(res.data.jobId);
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string' && detail.includes('copyright')) {
        toast.error(detail);
      } else {
        toast.error('Generation failed. Please try again.');
      }
      setGenerating(false);
    }
  };

  const pollJobStatus = async (jobId) => {
    const maxAttempts = 60;
    let attempt = 0;

    const poll = async () => {
      if (attempt >= maxAttempts) {
        setGenerating(false);
        toast.error('Generation timed out. Check your history for results.');
        return;
      }
      attempt++;
      try {
        const res = await api.get(`/api/photo-to-comic/job/${jobId}`);
        const job = res.data;
        setJobProgress(job.progress || 0);
        setJobMessage(job.progressMessage || 'Processing...');

        if (job.status === 'COMPLETED') {
          setGenerating(false);
          setResult(job);
          // Validate asset before enabling download
          validateAsset(jobId);
          setTimeout(() => setShowRatingModal(true), 2000);
          return;
        }
        if (job.status === 'FAILED') {
          setGenerating(false);
          toast.error(job.error || 'Generation failed.');
          return;
        }
        setTimeout(() => poll(), 2000);
      } catch {
        setTimeout(() => poll(), 3000);
      }
    };
    poll();
  };

  const validateAsset = async (jobId) => {
    try {
      const res = await api.get(`/api/photo-to-comic/validate-asset/${jobId}`);
      setAssetValidated(res.data.valid === true);
      if (!res.data.valid) {
        toast.warning('Asset validation pending. Download may not be ready yet.');
      }
    } catch {
      setAssetValidated(true); // Fallback: allow download
    }
  };

  const handleDownload = async () => {
    if (!currentJobId && !lastGenerationId) return;
    const jobId = currentJobId || lastGenerationId;
    setDownloading(true);
    try {
      const res = await api.post(`/api/photo-to-comic/download/${jobId}`);
      if (res.data.success && res.data.downloadUrls?.length) {
        for (const url of res.data.downloadUrls) {
          const a = document.createElement('a');
          a.href = url;
          a.download = `comic_${jobId.slice(0, 8)}.png`;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
        toast.success('Download started!');
      } else {
        toast.error('No downloadable assets found.');
      }
    } catch (error) {
      toast.error('Download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const resetForm = () => {
    setMode(null);
    setStep(1);
    removePhoto();
    setSelectedStyle(null);
    setSelectedGenre(null);
    setDialogue('');
    setPanelCount(3);
    setAddons({
      background: false,
      speech_bubble: false,
      transparent: false,
      hd: false,
      commercial: false,
    });
    setResult(null);
    setCurrentJobId(null);
    setJobProgress(0);
    setJobMessage('');
    setAssetValidated(false);
    setDownloading(false);
    setGenerating(false);
  };

  const isPremiumStyle = (styleId) => {
    const style = COMIC_STYLES.find(s => s.id === styleId);
    return style?.premium && userPlan === 'free';
  };

  // =============================================================================
  // RENDER HELPERS
  // =============================================================================
  const totalCredits = calculateTotal();

  // Mode Selection Screen
  const renderModeSelection = () => (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">What would you like to create?</h2>
        <p className="text-slate-400">Choose your comic creation type</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
        {/* Comic Avatar Option */}
        <button
          onClick={() => { setMode('avatar'); setStep(1); }}
          className="relative p-6 rounded-2xl border-2 border-slate-700 hover:border-purple-500 bg-slate-800/50 text-left transition-all duration-300 transform hover:scale-[1.02] group"
          data-testid="mode-avatar"
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center text-3xl shadow-lg">
              🦸
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Comic Avatar</h3>
              <p className="text-purple-400 text-sm">Single Character</p>
            </div>
          </div>
          
          <p className="text-slate-300 text-sm mb-4">
            Upload your photo and get a unique comic-style character avatar.
          </p>
          
          <div className="bg-slate-900/50 rounded-lg p-3 flex items-center justify-between">
            <span className="text-slate-400 text-sm">Starting from</span>
            <span className="font-bold text-white flex items-center gap-1">
              <Coins className="w-4 h-4 text-yellow-400" />
              10 credits
            </span>
          </div>
          
          <ChevronRight className="absolute top-1/2 right-4 -translate-y-1/2 w-6 h-6 text-slate-600 group-hover:text-purple-400 transition-colors" />
        </button>

        {/* Comic Strip Option */}
        <button
          onClick={() => { setMode('strip'); setStep(1); }}
          className="relative p-6 rounded-2xl border-2 border-slate-700 hover:border-cyan-500 bg-slate-800/50 text-left transition-all duration-300 transform hover:scale-[1.02] group"
          data-testid="mode-strip"
        >
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-xl flex items-center justify-center text-3xl shadow-lg">
              <Grid3X3 className="w-8 h-8 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Comic Strip</h3>
              <p className="text-cyan-400 text-sm">Mini Story (3-6 Panels)</p>
            </div>
          </div>
          
          <p className="text-slate-300 text-sm mb-4">
            Turn your photo into a fun comic strip with multiple panels.
          </p>
          
          <div className="bg-slate-900/50 rounded-lg p-3 flex items-center justify-between">
            <span className="text-slate-400 text-sm">Starting from</span>
            <span className="font-bold text-white flex items-center gap-1">
              <Coins className="w-4 h-4 text-yellow-400" />
              18 credits
            </span>
          </div>
          
          <ChevronRight className="absolute top-1/2 right-4 -translate-y-1/2 w-6 h-6 text-slate-600 group-hover:text-cyan-400 transition-colors" />
        </button>
      </div>
    </div>
  );

  // Avatar Step 1: Upload Photo
  const renderAvatarStep1 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-purple-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">1</span>
          Step 1 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Upload Your Photo</h2>
        <p className="text-slate-400">Use a clear front-facing photo for best results</p>
      </div>

      {!photoPreview ? (
        <label className="block border-2 border-dashed border-slate-600 rounded-2xl p-12 text-center hover:border-purple-500 transition-all cursor-pointer bg-slate-800/30">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handlePhotoUpload}
            data-testid="photo-upload"
          />
          <div className="w-20 h-20 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Upload className="w-10 h-10 text-purple-400" />
          </div>
          <p className="text-white font-medium mb-1">Click or drag to upload</p>
          <p className="text-sm text-slate-400">PNG, JPG up to 10MB</p>
        </label>
      ) : (
        <div className="relative rounded-2xl overflow-hidden bg-slate-800/50 border border-slate-700">
          <img 
            src={photoPreview} 
            alt="Preview" 
            className="w-full max-h-96 object-contain"
          />
          <button
            onClick={removePhoto}
            className="absolute top-3 right-3 w-8 h-8 bg-red-500 rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
      )}

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setMode(null)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={() => setStep(2)}
          disabled={!photoPreview}
          className="bg-gradient-to-r from-purple-600 to-pink-600 disabled:opacity-50"
          data-testid="avatar-step1-continue"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Avatar Step 2: Choose Style
  const renderAvatarStep2 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-4xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-purple-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">2</span>
          Step 2 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Comic Style</h2>
        <p className="text-slate-400">Select the artistic style for your character</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {COMIC_STYLES.map((style) => {
          const isLocked = style.premium && userPlan === 'free';
          const isSelected = selectedStyle === style.id;
          
          return (
            <button
              key={style.id}
              onClick={() => !isLocked && setSelectedStyle(style.id)}
              disabled={isLocked}
              className={`relative p-4 rounded-xl border-2 text-center transition-all duration-300 ${
                isSelected
                  ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
                  : isLocked
                  ? 'border-slate-700 bg-slate-800/30 opacity-60 cursor-not-allowed'
                  : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'
              }`}
              data-testid={`style-${style.id}`}
            >
              {isLocked && (
                <div className="absolute top-2 right-2 bg-yellow-500/20 rounded-full p-1">
                  <Lock className="w-3 h-3 text-yellow-500" />
                </div>
              )}
              <div className="text-4xl mb-2">{style.icon}</div>
              <h3 className={`font-semibold text-sm ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                {style.name}
              </h3>
              <p className="text-xs text-slate-500 mt-1">{style.description}</p>
              {isLocked && (
                <div className="mt-2 text-xs text-yellow-400 flex items-center justify-center gap-1">
                  <Crown className="w-3 h-3" />
                  PRO
                </div>
              )}
              {isSelected && (
                <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-purple-500 rounded-full p-1">
                  <Check className="w-3 h-3 text-white" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(1)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={() => setStep(3)}
          disabled={!selectedStyle}
          className="bg-gradient-to-r from-purple-600 to-pink-600 disabled:opacity-50"
          data-testid="avatar-step2-continue"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Avatar Step 3: Enhancements & Generate
  const renderAvatarStep3 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-purple-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">3</span>
          Step 3 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Optional Enhancements</h2>
        <p className="text-slate-400">Add extras to make your avatar unique</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Addons Column */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            Add-ons
          </h3>
          <div className="space-y-3">
            {Object.entries(PRICING.addons).map(([key, addon]) => (
              <button
                key={key}
                onClick={() => toggleAddon(key)}
                className={`w-full p-3 rounded-xl border-2 flex items-center justify-between transition-all ${
                  addons[key]
                    ? 'border-purple-500 bg-purple-500/20'
                    : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                }`}
                data-testid={`addon-${key}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    addons[key] ? 'bg-purple-500 border-purple-500' : 'border-slate-500'
                  }`}>
                    {addons[key] && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <span className={addons[key] ? 'text-white' : 'text-slate-300'}>{addon.label}</span>
                </div>
                <span className="text-purple-400 font-semibold">+{addon.credits}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Summary Column */}
        <div className="bg-gradient-to-b from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Coins className="w-5 h-5 text-yellow-400" />
            Order Summary
          </h3>
          
          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-slate-300">
              <span>Comic Avatar (Base)</span>
              <span>{PRICING.avatar.base} credits</span>
            </div>
            {Object.entries(addons).map(([key, enabled]) => enabled && (
              <div key={key} className="flex justify-between text-slate-400 text-sm">
                <span>+ {PRICING.addons[key].label}</span>
                <span>+{PRICING.addons[key].credits}</span>
              </div>
            ))}
          </div>
          
          <div className="border-t border-slate-700 pt-3">
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-white">Total</span>
              <span className="text-2xl font-bold text-purple-400">{totalCredits} credits</span>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-slate-900/50 rounded-xl text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Your Balance</span>
              <span className={credits >= totalCredits ? 'text-emerald-400' : 'text-red-400'}>
                {credits} credits
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(2)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={handleGenerate}
          disabled={generating || credits < totalCredits}
          className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 px-8 disabled:opacity-50"
          data-testid="generate-avatar"
        >
          {generating ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5 mr-2" />
              Generate My Comic Character
            </>
          )}
        </Button>
      </div>
    </div>
  );

  // Strip Step 1: Upload Photo (same as avatar)
  const renderStripStep1 = renderAvatarStep1;

  // Strip Step 2: Choose Genre
  const renderStripStep2 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-cyan-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">2</span>
          Step 2 of 5
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Genre</h2>
        <p className="text-slate-400">What kind of comic story?</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STRIP_GENRES.map((genre) => (
          <button
            key={genre.id}
            onClick={() => setSelectedGenre(genre.id)}
            className={`p-4 rounded-xl border-2 text-center transition-all ${
              selectedGenre === genre.id
                ? 'border-cyan-500 bg-cyan-500/20'
                : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'
            }`}
            data-testid={`genre-${genre.id}`}
          >
            <div className="text-3xl mb-2">{genre.icon}</div>
            <h3 className={`font-semibold ${selectedGenre === genre.id ? 'text-white' : 'text-slate-300'}`}>
              {genre.name}
            </h3>
          </button>
        ))}
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(1)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={() => setStep(3)}
          disabled={!selectedGenre}
          className="bg-gradient-to-r from-cyan-600 to-blue-600 disabled:opacity-50"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Strip Step 3: Dialogue (Optional)
  const renderStripStep3 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-cyan-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">3</span>
          Step 3 of 5
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Add Dialogue (Optional)</h2>
        <p className="text-slate-400">What should your character say?</p>
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <MessageSquare className="w-5 h-5 text-cyan-400 mt-1" />
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Character Dialogue
            </label>
            <textarea
              value={dialogue}
              onChange={(e) => setDialogue(e.target.value.slice(0, 200))}
              placeholder="Enter what your character says... (optional)"
              rows={3}
              className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none resize-none"
              data-testid="dialogue-input"
            />
            <p className="text-xs text-slate-500 mt-1">{dialogue.length}/200 characters</p>
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(2)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={() => setStep(4)}
          className="bg-gradient-to-r from-cyan-600 to-blue-600"
        >
          {dialogue ? 'Continue' : 'Skip'}
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Strip Step 4: Panel Count
  const renderStripStep4 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-cyan-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">4</span>
          Step 4 of 5
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Select Panel Count</h2>
        <p className="text-slate-400">How many panels in your comic strip?</p>
      </div>

      <div className="grid grid-cols-2 gap-6 max-w-md mx-auto">
        <button
          onClick={() => setPanelCount(3)}
          className={`p-6 rounded-2xl border-2 text-center transition-all ${
            panelCount === 3
              ? 'border-cyan-500 bg-cyan-500/20'
              : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'
          }`}
          data-testid="panels-3"
        >
          <div className="grid grid-cols-3 gap-1 mb-4 mx-auto w-24">
            {[1,2,3].map(i => (
              <div key={i} className="aspect-square bg-slate-600 rounded" />
            ))}
          </div>
          <h3 className="font-bold text-white text-lg">3 Panels</h3>
          <p className="text-cyan-400 font-semibold">{PRICING.strip_3.base} credits</p>
        </button>

        <button
          onClick={() => setPanelCount(6)}
          className={`p-6 rounded-2xl border-2 text-center transition-all ${
            panelCount === 6
              ? 'border-cyan-500 bg-cyan-500/20'
              : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'
          }`}
          data-testid="panels-6"
        >
          <div className="grid grid-cols-3 gap-1 mb-4 mx-auto w-24">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="aspect-square bg-slate-600 rounded" />
            ))}
          </div>
          <h3 className="font-bold text-white text-lg">6 Panels</h3>
          <p className="text-cyan-400 font-semibold">{PRICING.strip_6.base} credits</p>
        </button>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(3)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={() => setStep(5)}
          className="bg-gradient-to-r from-cyan-600 to-blue-600"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  // Strip Step 5: Add-ons & Generate
  const renderStripStep5 = () => (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 text-sm text-cyan-400 mb-2">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">5</span>
          Step 5 of 5
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Enhancements & Generate</h2>
        <p className="text-slate-400">Add extras and create your comic strip</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Addons */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4">Add-ons</h3>
          <div className="space-y-3">
            {['hd', 'commercial'].map((key) => (
              <button
                key={key}
                onClick={() => toggleAddon(key)}
                className={`w-full p-3 rounded-xl border-2 flex items-center justify-between transition-all ${
                  addons[key]
                    ? 'border-cyan-500 bg-cyan-500/20'
                    : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    addons[key] ? 'bg-cyan-500 border-cyan-500' : 'border-slate-500'
                  }`}>
                    {addons[key] && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <span className={addons[key] ? 'text-white' : 'text-slate-300'}>{PRICING.addons[key].label}</span>
                </div>
                <span className="text-cyan-400 font-semibold">+{PRICING.addons[key].credits}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Summary */}
        <div className="bg-gradient-to-b from-slate-800/50 to-slate-900/50 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Coins className="w-5 h-5 text-yellow-400" />
            Order Summary
          </h3>
          
          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-slate-300">
              <span>{panelCount} Panel Strip</span>
              <span>{panelCount === 3 ? PRICING.strip_3.base : PRICING.strip_6.base} credits</span>
            </div>
            {Object.entries(addons).map(([key, enabled]) => enabled && PRICING.addons[key] && (
              <div key={key} className="flex justify-between text-slate-400 text-sm">
                <span>+ {PRICING.addons[key].label}</span>
                <span>+{PRICING.addons[key].credits}</span>
              </div>
            ))}
          </div>
          
          <div className="border-t border-slate-700 pt-3">
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-white">Total</span>
              <span className="text-2xl font-bold text-cyan-400">{totalCredits} credits</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(4)} className="border-slate-600 text-white">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={handleGenerate}
          disabled={generating || credits < totalCredits}
          className="bg-gradient-to-r from-emerald-600 to-green-600 px-8 disabled:opacity-50"
          data-testid="generate-strip"
        >
          {generating ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5 mr-2" />
              Generate Comic Strip
            </>
          )}
        </Button>
      </div>
    </div>
  );

  // Result Screen
  const renderResult = () => {
    const imageUrl = result?.resultUrl || result?.resultUrls?.[0];
    const panels = result?.panels;
    const isCompleted = result?.status === 'COMPLETED';

    return (
      <div className="space-y-6 animate-in fade-in duration-500 max-w-3xl mx-auto text-center">
        {/* Still generating — show progress */}
        {generating && (
          <div className="space-y-4">
            <div className="w-20 h-20 bg-indigo-500/20 rounded-full flex items-center justify-center mx-auto">
              <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
            </div>
            <h2 className="text-2xl font-bold text-white">Creating Your Comic...</h2>
            <p className="text-slate-400">{jobMessage || 'Processing...'}</p>
            <div className="w-full max-w-sm mx-auto bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                style={{ width: `${jobProgress}%` }}
              />
            </div>
            <p className="text-xs text-slate-500">{jobProgress}% — Estimated ~25 seconds</p>
          </div>
        )}

        {/* Completed — show result */}
        {!generating && isCompleted && (
          <>
            <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-10 h-10 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Your Comic is Ready!</h2>
            <p className="text-slate-400">Saved as a permanent asset — download anytime</p>

            {/* Avatar result */}
            {imageUrl && !panels && (
              <div className="relative rounded-2xl overflow-hidden border border-slate-700 bg-white max-w-md mx-auto">
                <img src={imageUrl} alt="Generated Comic" className="w-full" crossOrigin="anonymous" />
                {userPlan === 'free' && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                    <span className="text-4xl font-bold text-white/30 rotate-[-30deg]">PREVIEW</span>
                  </div>
                )}
              </div>
            )}

            {/* Strip result */}
            {panels && panels.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
                {panels.map((panel, i) => (
                  <div key={i} className="rounded-xl overflow-hidden border border-slate-700 bg-white">
                    <img src={panel.imageUrl} alt={`Panel ${i + 1}`} className="w-full" crossOrigin="anonymous" />
                    {panel.dialogue && (
                      <div className="bg-slate-900 p-2 text-sm text-slate-300">{panel.dialogue}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-4 justify-center flex-wrap">
              <Button
                onClick={handleDownload}
                disabled={downloading || !assetValidated}
                className="bg-gradient-to-r from-purple-600 to-pink-600 disabled:opacity-50"
                data-testid="download-result"
              >
                {downloading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Downloading...</>
                ) : !assetValidated ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Validating...</>
                ) : (
                  <><Download className="w-4 h-4 mr-2" />Download</>
                )}
              </Button>
              <ShareCreation
                type={mode === 'avatar' ? 'COMIC_AVATAR' : 'COMIC_STRIP'}
                title="My Comic Character"
                preview="Created with Visionary Suite"
                generationId={lastGenerationId}
              />
            </div>

            {userPlan === 'free' && (
              <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl p-4 max-w-md mx-auto">
                <p className="text-purple-300 text-sm">Remove Watermark</p>
                <Button
                  onClick={() => navigate('/app/subscription')}
                  className="mt-2 bg-purple-600 hover:bg-purple-700"
                >
                  <Crown className="w-4 h-4 mr-2" />
                  Upgrade Now
                </Button>
              </div>
            )}

            <Button variant="outline" onClick={resetForm} className="border-slate-600 text-white">
              Create Another
            </Button>
          </>
        )}

        {/* Failed */}
        {!generating && !isCompleted && result?.status === 'FAILED' && (
          <div className="space-y-4">
            <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto">
              <AlertCircle className="w-10 h-10 text-red-400" />
            </div>
            <h2 className="text-2xl font-bold text-white">Generation Failed</h2>
            <p className="text-slate-400">Credits have been refunded. Please try again.</p>
            <Button variant="outline" onClick={resetForm} className="border-slate-600 text-white">
              Try Again
            </Button>
          </div>
        )}
      </div>
    );
  };

  // =============================================================================
  // MAIN RENDER
  // =============================================================================
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg text-xl">
                🎨
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Convert Photos To Comic Character</h1>
                <p className="text-xs text-slate-400 hidden sm:block">Upload your photo and turn it into a unique comic-style character</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2 bg-slate-800/50 rounded-full px-4 py-2 border border-slate-700">
            <Coins className="w-4 h-4 text-yellow-400" />
            <span className="font-bold text-white">{credits}</span>
            <span className="text-xs text-slate-400 hidden sm:inline">credits</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {!mode && renderModeSelection()}
        
        {mode === 'avatar' && step === 1 && renderAvatarStep1()}
        {mode === 'avatar' && step === 2 && renderAvatarStep2()}
        {mode === 'avatar' && step === 3 && renderAvatarStep3()}
        {mode === 'avatar' && step === 4 && renderResult()}
        
        {mode === 'strip' && step === 1 && renderStripStep1()}
        {mode === 'strip' && step === 2 && renderStripStep2()}
        {mode === 'strip' && step === 3 && renderStripStep3()}
        {mode === 'strip' && step === 4 && renderStripStep4()}
        {mode === 'strip' && step === 5 && renderStripStep5()}
        {mode === 'strip' && step === 6 && renderResult()}
      </main>

      {/* Footer Disclaimer */}
      <footer className="border-t border-slate-800/50 py-4 mt-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-start gap-2 text-xs text-slate-500">
            <Shield className="w-4 h-4 text-slate-600 flex-shrink-0 mt-0.5" />
            <p>
              <strong>Copyright Notice:</strong> We do not allow copyrighted characters or brand-based content. 
              Upload only photos you own or have permission to use. All comic styles are original creations.
            </p>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <RatingModal 
        isOpen={showRatingModal}
        onClose={() => setShowRatingModal(false)}
        featureKey="photo_to_comic"
        relatedRequestId={lastGenerationId}
        onSubmitSuccess={() => setShowRatingModal(false)}
      />
      
      <UpsellModal
        isOpen={showUpsellModal}
        onClose={() => setShowUpsellModal(false)}
        generationId={lastGenerationId}
        feature="photo_to_comic"
        onSuccess={() => fetchUserData()}
      />
    </div>
  );
}
