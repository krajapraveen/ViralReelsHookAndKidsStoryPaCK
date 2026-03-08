import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { generationAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Copy, Download, Loader2, ArrowLeft, Coins, AlertCircle, LogOut } from 'lucide-react';

import ShareButton from '../components/ShareButton';
import ShareCreation from '../components/ShareCreation';
import UpgradeBanner from '../components/UpgradeBanner';
import UpgradeModal from '../components/UpgradeModal';
import UpsellModal from '../components/UpsellModal';
import ReelProgressBar from '../components/ReelProgressBar';
import HelpGuide from '../components/HelpGuide';
import RatingModal from '../components/RatingModal';
import WaitingWithGames from '../components/WaitingWithGames';
import analytics from '../utils/analytics';

export default function ReelGenerator() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [isFreeTier, setIsFreeTier] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);
  const [lastGenerationId, setLastGenerationId] = useState(null);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    topic: '',
    niche: 'Luxury',
    tone: 'Bold',
    duration: '30s',
    language: 'English',
    goal: 'Followers',
    audience: 'General'
  });

  // Blocked words for content filtering
  const blockedWords = [
    // Adult/Sexual content
    'sex', 'porn', 'xxx', 'nude', 'naked', 'erotic', 'adult', 'nsfw', 'explicit',
    'orgasm', 'masturbat', 'penis', 'vagina', 'boob', 'breast', 'nipple', 'genital',
    'prostitut', 'escort', 'stripper', 'onlyfans', 'fetish', 'bdsm', 'kinky',
    // Violence
    'kill', 'murder', 'blood', 'gore', 'violent', 'torture', 'abuse', 'assault',
    'rape', 'molest', 'stab', 'shoot', 'bomb', 'terrorist', 'massacre', 'genocide',
    'decapitat', 'dismember', 'mutilat', 'brutal',
    // Hate/Discrimination
    'racist', 'racism', 'nazi', 'hitler', 'hate', 'discriminat', 'slur', 'bigot',
    'homophob', 'transphob', 'sexist', 'supremac', 'extremist',
    // Drugs/Illegal
    'cocaine', 'heroin', 'meth', 'crack', 'ecstasy', 'lsd', 'overdose', 'drug deal',
    // Self-harm
    'suicide', 'self-harm', 'cutting', 'anorex', 'bulimi',
    // Disturbing
    'pedophil', 'incest', 'bestiality', 'necrophil', 'cannibal',
    // Profanity (common)
    'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'cunt', 'dick', 'cock', 'whore'
  ];

  // Validate content for inappropriate words
  const validateContent = (text) => {
    if (!text || text.trim() === '') {
      return { valid: false, message: 'Please enter a topic' };
    }
    
    const lowerText = text.toLowerCase();
    
    for (const word of blockedWords) {
      if (lowerText.includes(word)) {
        return { 
          valid: false, 
          message: 'Your topic contains inappropriate content. Please use family-friendly language.' 
        };
      }
    }
    
    return { valid: true, message: '' };
  };

  useEffect(() => {
    fetchCredits();
  }, []);

  const fetchCredits = async () => {
    try {
      const response = await creditAPI.getBalance();
      setCredits(response.data.balance);
      setIsFreeTier(response.data.isFreeTier);
    } catch (error) {
      toast.error('Failed to load credits');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate topic content
    const validation = validateContent(formData.topic);
    if (!validation.valid) {
      toast.error(validation.message);
      return;
    }
    
    if (credits < 1) {
      toast.error('Insufficient credits! Please buy more.');
      navigate('/pricing');
      return;
    }

    // Reset state for new generation
    setResult(null);
    setLoading(true);
    
    try {
      const response = await generationAPI.generateReel(formData);
      // Backend returns result, not output
      setResult(response.data.result);
      setCredits(response.data.remainingCredits || credits - 1);
      setLastGenerationId(response.data.generationId || null);
      toast.success('Reel script generated successfully!');
      
      // Track reel generation in Google Analytics
      analytics.trackGeneration('reel_generator', 10);
      
      // Show rating modal after successful generation (with delay)
      setTimeout(() => {
        setShowRatingModal(true);
      }, 2000);
      
      // Show upsell modal after rating
      setTimeout(() => {
        setShowUpsellModal(true);
      }, 4000);
    } catch (error) {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const handleDownloadClick = () => {
    if (isFreeTier) {
      setShowUpgradeModal(true);
    } else {
      downloadJSON(false);
    }
  };

  const downloadJSON = (withWatermark = true) => {
    setShowUpgradeModal(false);
    // Add watermark for free-tier users
    const downloadContent = (isFreeTier && withWatermark) 
      ? { 
          ...result, 
          watermark: '⚡ Made with Visionary Suite - Upgrade to remove watermark',
          free_tier: true 
        }
      : result;
    
    const blob = new Blob([JSON.stringify(downloadContent, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reel-script-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Upgrade Modal */}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)}
        onDownloadWithWatermark={() => downloadJSON(true)}
      />

      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
                <ArrowLeft className="w-4 h-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Dashboard</span>
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-400" />
              <span className="text-lg sm:text-xl font-bold text-white">Reel Generator</span>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 rounded-full px-3 sm:px-4 py-2">
              <Coins className="w-4 h-4 text-indigo-400" />
              <span className="font-semibold text-indigo-300 text-sm sm:text-base">{credits}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-slate-400 hover:text-white hover:bg-slate-800" data-testid="reel-logout-btn">
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline ml-2">Logout</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Upgrade Banners */}
        {credits === 0 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="exhausted" />}
        {credits > 0 && credits <= 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="low" />}
        {isFreeTier && credits > 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="watermark" />}

        <div className="grid lg:grid-cols-2 gap-6 sm:gap-8">
          {/* Input Form */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-5 sm:mb-6">Generate Reel Script</h2>
            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6" data-testid="reel-form">
              <div>
                <Label htmlFor="topic" className="text-slate-300 font-medium text-sm mb-2 block">Topic *</Label>
                <Textarea
                  id="topic"
                  value={formData.topic}
                  onChange={(e) => setFormData({...formData, topic: e.target.value})}
                  placeholder="E.g., Morning routines of successful entrepreneurs"
                  required
                  rows={3}
                  className="bg-slate-900/60 border-slate-600 text-white placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500/20 resize-none"
                  data-testid="reel-topic-input"
                  data-tour="reel-topic-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <Label htmlFor="niche" className="text-slate-300 font-medium text-sm mb-2 block">Niche</Label>
                  <Select value={formData.niche} onValueChange={(value) => setFormData({...formData, niche: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20" data-testid="reel-niche-select" data-tour="reel-niche-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="Luxury" className="text-white focus:bg-indigo-600">Luxury</SelectItem>
                      <SelectItem value="Relationships" className="text-white focus:bg-indigo-600">Relationships</SelectItem>
                      <SelectItem value="Health" className="text-white focus:bg-indigo-600">Health & Fitness</SelectItem>
                      <SelectItem value="Finance" className="text-white focus:bg-indigo-600">Finance</SelectItem>
                      <SelectItem value="Tech" className="text-white focus:bg-indigo-600">Technology</SelectItem>
                      <SelectItem value="Custom" className="text-white focus:bg-indigo-600">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="tone" className="text-slate-300 font-medium text-sm mb-2 block">Tone</Label>
                  <Select value={formData.tone} onValueChange={(value) => setFormData({...formData, tone: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="Bold" className="text-white focus:bg-indigo-600">Bold</SelectItem>
                      <SelectItem value="Calm" className="text-white focus:bg-indigo-600">Calm</SelectItem>
                      <SelectItem value="Funny" className="text-white focus:bg-indigo-600">Funny</SelectItem>
                      <SelectItem value="Emotional" className="text-white focus:bg-indigo-600">Emotional</SelectItem>
                      <SelectItem value="Authority" className="text-white focus:bg-indigo-600">Authority</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <Label htmlFor="duration" className="text-slate-300 font-medium text-sm mb-2 block">Duration</Label>
                  <Select value={formData.duration} onValueChange={(value) => setFormData({...formData, duration: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="15s" className="text-white focus:bg-indigo-600">15 seconds</SelectItem>
                      <SelectItem value="30s" className="text-white focus:bg-indigo-600">30 seconds</SelectItem>
                      <SelectItem value="60s" className="text-white focus:bg-indigo-600">60 seconds</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="language" className="text-slate-300 font-medium text-sm mb-2 block">Language</Label>
                  <Select value={formData.language} onValueChange={(value) => setFormData({...formData, language: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700 max-h-[300px]">
                      {/* Major World Languages */}
                      <SelectItem value="English" className="text-white focus:bg-indigo-600">English</SelectItem>
                      <SelectItem value="Spanish" className="text-white focus:bg-indigo-600">Spanish (Español)</SelectItem>
                      <SelectItem value="French" className="text-white focus:bg-indigo-600">French (Français)</SelectItem>
                      <SelectItem value="German" className="text-white focus:bg-indigo-600">German (Deutsch)</SelectItem>
                      <SelectItem value="Italian" className="text-white focus:bg-indigo-600">Italian (Italiano)</SelectItem>
                      <SelectItem value="Portuguese" className="text-white focus:bg-indigo-600">Portuguese (Português)</SelectItem>
                      <SelectItem value="Russian" className="text-white focus:bg-indigo-600">Russian (Русский)</SelectItem>
                      <SelectItem value="Japanese" className="text-white focus:bg-indigo-600">Japanese (日本語)</SelectItem>
                      <SelectItem value="Korean" className="text-white focus:bg-indigo-600">Korean (한국어)</SelectItem>
                      <SelectItem value="Chinese" className="text-white focus:bg-indigo-600">Chinese (中文)</SelectItem>
                      <SelectItem value="Arabic" className="text-white focus:bg-indigo-600">Arabic (العربية)</SelectItem>
                      <SelectItem value="Hindi" className="text-white focus:bg-indigo-600">Hindi (हिंदी)</SelectItem>
                      <SelectItem value="Hinglish" className="text-white focus:bg-indigo-600">Hinglish</SelectItem>
                      {/* Indian Languages */}
                      <SelectItem value="Telugu" className="text-white focus:bg-indigo-600">Telugu (తెలుగు)</SelectItem>
                      <SelectItem value="Tamil" className="text-white focus:bg-indigo-600">Tamil (தமிழ்)</SelectItem>
                      <SelectItem value="Kannada" className="text-white focus:bg-indigo-600">Kannada (ಕನ್ನಡ)</SelectItem>
                      <SelectItem value="Malayalam" className="text-white focus:bg-indigo-600">Malayalam (മലയാളം)</SelectItem>
                      <SelectItem value="Marathi" className="text-white focus:bg-indigo-600">Marathi (मराठी)</SelectItem>
                      <SelectItem value="Bengali" className="text-white focus:bg-indigo-600">Bengali (বাংলা)</SelectItem>
                      <SelectItem value="Gujarati" className="text-white focus:bg-indigo-600">Gujarati (ગુજરાતી)</SelectItem>
                      <SelectItem value="Punjabi" className="text-white focus:bg-indigo-600">Punjabi (ਪੰਜਾਬੀ)</SelectItem>
                      {/* European Languages */}
                      <SelectItem value="Dutch" className="text-white focus:bg-indigo-600">Dutch (Nederlands)</SelectItem>
                      <SelectItem value="Polish" className="text-white focus:bg-indigo-600">Polish (Polski)</SelectItem>
                      <SelectItem value="Swedish" className="text-white focus:bg-indigo-600">Swedish (Svenska)</SelectItem>
                      <SelectItem value="Norwegian" className="text-white focus:bg-indigo-600">Norwegian (Norsk)</SelectItem>
                      <SelectItem value="Danish" className="text-white focus:bg-indigo-600">Danish (Dansk)</SelectItem>
                      <SelectItem value="Finnish" className="text-white focus:bg-indigo-600">Finnish (Suomi)</SelectItem>
                      <SelectItem value="Greek" className="text-white focus:bg-indigo-600">Greek (Ελληνικά)</SelectItem>
                      <SelectItem value="Turkish" className="text-white focus:bg-indigo-600">Turkish (Türkçe)</SelectItem>
                      <SelectItem value="Czech" className="text-white focus:bg-indigo-600">Czech (Čeština)</SelectItem>
                      <SelectItem value="Hungarian" className="text-white focus:bg-indigo-600">Hungarian (Magyar)</SelectItem>
                      <SelectItem value="Romanian" className="text-white focus:bg-indigo-600">Romanian (Română)</SelectItem>
                      <SelectItem value="Ukrainian" className="text-white focus:bg-indigo-600">Ukrainian (Українська)</SelectItem>
                      {/* Asian Languages */}
                      <SelectItem value="Thai" className="text-white focus:bg-indigo-600">Thai (ไทย)</SelectItem>
                      <SelectItem value="Vietnamese" className="text-white focus:bg-indigo-600">Vietnamese (Tiếng Việt)</SelectItem>
                      <SelectItem value="Indonesian" className="text-white focus:bg-indigo-600">Indonesian (Bahasa)</SelectItem>
                      <SelectItem value="Malay" className="text-white focus:bg-indigo-600">Malay (Bahasa Melayu)</SelectItem>
                      <SelectItem value="Filipino" className="text-white focus:bg-indigo-600">Filipino (Tagalog)</SelectItem>
                      {/* Middle Eastern */}
                      <SelectItem value="Persian" className="text-white focus:bg-indigo-600">Persian (فارسی)</SelectItem>
                      <SelectItem value="Hebrew" className="text-white focus:bg-indigo-600">Hebrew (עברית)</SelectItem>
                      <SelectItem value="Urdu" className="text-white focus:bg-indigo-600">Urdu (اردو)</SelectItem>
                      {/* African */}
                      <SelectItem value="Swahili" className="text-white focus:bg-indigo-600">Swahili (Kiswahili)</SelectItem>
                      <SelectItem value="Afrikaans" className="text-white focus:bg-indigo-600">Afrikaans</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <Label htmlFor="goal" className="text-slate-300 font-medium text-sm mb-2 block">Goal</Label>
                  <Select value={formData.goal} onValueChange={(value) => setFormData({...formData, goal: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="Followers" className="text-white focus:bg-indigo-600">Gain Followers</SelectItem>
                      <SelectItem value="Leads" className="text-white focus:bg-indigo-600">Generate Leads</SelectItem>
                      <SelectItem value="Sales" className="text-white focus:bg-indigo-600">Drive Sales</SelectItem>
                      <SelectItem value="Awareness" className="text-white focus:bg-indigo-600">Brand Awareness</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="audience" className="text-slate-300 font-medium text-sm mb-2 block">Audience</Label>
                  <Select value={formData.audience} onValueChange={(value) => setFormData({...formData, audience: value})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-indigo-500/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700 max-h-[300px]">
                      {/* General */}
                      <SelectItem value="General" className="text-white focus:bg-indigo-600">General Audience</SelectItem>
                      {/* Age Groups */}
                      <SelectItem value="Gen Z (13-24)" className="text-white focus:bg-indigo-600">Gen Z (13-24)</SelectItem>
                      <SelectItem value="Millennials (25-40)" className="text-white focus:bg-indigo-600">Millennials (25-40)</SelectItem>
                      <SelectItem value="Gen X (41-56)" className="text-white focus:bg-indigo-600">Gen X (41-56)</SelectItem>
                      <SelectItem value="Baby Boomers (57-75)" className="text-white focus:bg-indigo-600">Baby Boomers (57-75)</SelectItem>
                      {/* Professional */}
                      <SelectItem value="Young Professionals" className="text-white focus:bg-indigo-600">Young Professionals</SelectItem>
                      <SelectItem value="Entrepreneurs" className="text-white focus:bg-indigo-600">Entrepreneurs</SelectItem>
                      <SelectItem value="Business Executives" className="text-white focus:bg-indigo-600">Business Executives</SelectItem>
                      <SelectItem value="Freelancers" className="text-white focus:bg-indigo-600">Freelancers</SelectItem>
                      <SelectItem value="Remote Workers" className="text-white focus:bg-indigo-600">Remote Workers</SelectItem>
                      <SelectItem value="Small Business Owners" className="text-white focus:bg-indigo-600">Small Business Owners</SelectItem>
                      {/* Students */}
                      <SelectItem value="College Students" className="text-white focus:bg-indigo-600">College Students</SelectItem>
                      <SelectItem value="High School Students" className="text-white focus:bg-indigo-600">High School Students</SelectItem>
                      <SelectItem value="Graduate Students" className="text-white focus:bg-indigo-600">Graduate Students</SelectItem>
                      {/* Lifestyle */}
                      <SelectItem value="Parents" className="text-white focus:bg-indigo-600">Parents</SelectItem>
                      <SelectItem value="New Parents" className="text-white focus:bg-indigo-600">New Parents</SelectItem>
                      <SelectItem value="Stay-at-Home Parents" className="text-white focus:bg-indigo-600">Stay-at-Home Parents</SelectItem>
                      <SelectItem value="Fitness Enthusiasts" className="text-white focus:bg-indigo-600">Fitness Enthusiasts</SelectItem>
                      <SelectItem value="Health Conscious" className="text-white focus:bg-indigo-600">Health Conscious</SelectItem>
                      <SelectItem value="Travelers" className="text-white focus:bg-indigo-600">Travelers</SelectItem>
                      <SelectItem value="Foodies" className="text-white focus:bg-indigo-600">Foodies</SelectItem>
                      <SelectItem value="Gamers" className="text-white focus:bg-indigo-600">Gamers</SelectItem>
                      {/* Interest-Based */}
                      <SelectItem value="Tech Enthusiasts" className="text-white focus:bg-indigo-600">Tech Enthusiasts</SelectItem>
                      <SelectItem value="Fashion Lovers" className="text-white focus:bg-indigo-600">Fashion Lovers</SelectItem>
                      <SelectItem value="Beauty Enthusiasts" className="text-white focus:bg-indigo-600">Beauty Enthusiasts</SelectItem>
                      <SelectItem value="Music Fans" className="text-white focus:bg-indigo-600">Music Fans</SelectItem>
                      <SelectItem value="Sports Fans" className="text-white focus:bg-indigo-600">Sports Fans</SelectItem>
                      <SelectItem value="Book Lovers" className="text-white focus:bg-indigo-600">Book Lovers</SelectItem>
                      <SelectItem value="DIY Enthusiasts" className="text-white focus:bg-indigo-600">DIY Enthusiasts</SelectItem>
                      <SelectItem value="Pet Owners" className="text-white focus:bg-indigo-600">Pet Owners</SelectItem>
                      {/* Financial */}
                      <SelectItem value="Investors" className="text-white focus:bg-indigo-600">Investors</SelectItem>
                      <SelectItem value="Crypto Enthusiasts" className="text-white focus:bg-indigo-600">Crypto Enthusiasts</SelectItem>
                      <SelectItem value="Budget Conscious" className="text-white focus:bg-indigo-600">Budget Conscious</SelectItem>
                      <SelectItem value="Luxury Consumers" className="text-white focus:bg-indigo-600">Luxury Consumers</SelectItem>
                      {/* Regional */}
                      <SelectItem value="Urban Dwellers" className="text-white focus:bg-indigo-600">Urban Dwellers</SelectItem>
                      <SelectItem value="Suburban Families" className="text-white focus:bg-indigo-600">Suburban Families</SelectItem>
                      <SelectItem value="Rural Communities" className="text-white focus:bg-indigo-600">Rural Communities</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-indigo-300">
                  <Coins className="w-4 h-4" />
                  <span className="font-medium">Cost: 10 credits per reel</span>
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/25"
                data-testid="reel-generate-btn"
                data-tour="reel-generate-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Reel Script
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Result Display */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5 sm:mb-6">
              <h2 className="text-xl sm:text-2xl font-bold text-white">Generated Script</h2>
              {result && result.hooks && (
                <div className="flex gap-2">
                  <ShareButton type="REEL" title={result.best_hook || ''} preview={result.caption_short || ''} />
                  <Button variant="outline" size="sm" onClick={() => copyToClipboard(JSON.stringify(result, null, 2))} className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" data-testid="copy-result-btn">
                    <Copy className="w-4 h-4 mr-1 sm:mr-2" />
                    <span className="hidden sm:inline">Copy</span>
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadClick} className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" data-testid="download-result-btn">
                    <Download className="w-4 h-4 mr-1 sm:mr-2" />
                    <span className="hidden sm:inline">Download</span>
                  </Button>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <ReelProgressBar isGenerating={loading} />

            {!result && !loading && (
              <div className="text-center py-12 text-slate-400">
                <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                <p>Your generated reel script will appear here</p>
              </div>
            )}
            
            {loading && !result && (
              <WaitingWithGames 
                progress={50}
                status="Generating your reel script..."
                estimatedTime="10-30 seconds"
                onCancel={() => toast.info('Generation in progress - please wait')}
                currentFeature="/app/reel"
                showExploreFeatures={true}
              />
            )}
            
            {result && result.hooks && (
              <div className="space-y-5 sm:space-y-6 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar" data-testid="reel-result">
                {/* Free Tier Watermark Banner */}
                {isFreeTier && (
                  <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-purple-300 font-medium text-sm">⚡ Made with Visionary Suite</p>
                      <p className="text-purple-400 text-xs mt-1">
                        Free tier content includes watermark. <Link to="/pricing" className="underline font-medium hover:text-purple-300">Upgrade</Link> to remove watermarks.
                      </p>
                    </div>
                  </div>
                )}

                {/* Hooks */}
                <div>
                  <h3 className="font-bold text-lg text-white mb-3">🎯 5 Hooks</h3>
                  <div className="space-y-2">
                    {result.hooks?.map((hook, idx) => (
                      <div key={idx} className="bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl flex items-start gap-2">
                        <span className="font-bold text-indigo-400 min-w-[20px]">{idx + 1}.</span>
                        <span className="text-slate-200">{hook}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Best Hook */}
                {result.best_hook && (
                  <div className="bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-xl p-4">
                    <h3 className="font-bold text-lg text-white mb-2">⭐ Best Hook</h3>
                    <p className="text-indigo-200">{result.best_hook}</p>
                  </div>
                )}

                {/* Script Scenes */}
                {result.script?.scenes && (
                  <div>
                    <h3 className="font-bold text-lg text-white mb-3">🎬 Script</h3>
                    <div className="space-y-3">
                      {result.script.scenes.map((scene, idx) => (
                        <div key={idx} className="border border-slate-700/50 bg-slate-900/30 rounded-xl p-4">
                          <div className="font-semibold text-purple-400 mb-2">{scene.time}</div>
                          <div className="space-y-2">
                            {scene.on_screen_text && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500 uppercase">On-Screen:</span>
                                <p className="text-sm text-slate-200">{scene.on_screen_text}</p>
                              </div>
                            )}
                            {scene.voiceover && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500 uppercase">Voiceover:</span>
                                <p className="text-sm text-slate-200">{scene.voiceover}</p>
                              </div>
                            )}
                            {scene.broll && scene.broll.length > 0 && (
                              <div>
                                <span className="text-xs font-semibold text-slate-500 uppercase">B-Roll:</span>
                                <p className="text-sm text-slate-400">{scene.broll.join(', ')}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* CTA */}
                {result.script?.cta && (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
                    <h3 className="font-bold text-white mb-2">📢 Call to Action</h3>
                    <p className="text-emerald-200">{result.script.cta}</p>
                  </div>
                )}

                {/* Captions */}
                <div className="space-y-3">
                  {result.caption_short && (
                    <div>
                      <h3 className="font-bold text-white mb-2">📝 Short Caption</h3>
                      <p className="text-sm bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl text-slate-200">{result.caption_short}</p>
                    </div>
                  )}
                  {result.caption_long && (
                    <div>
                      <h3 className="font-bold text-white mb-2">📄 Long Caption</h3>
                      <p className="text-sm bg-slate-900/50 border border-slate-700/50 p-3 rounded-xl text-slate-200 whitespace-pre-wrap">{result.caption_long}</p>
                    </div>
                  )}
                </div>

                {/* Hashtags */}
                {result.hashtags && (
                  <div>
                    <h3 className="font-bold text-white mb-2">#️⃣ Hashtags</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.hashtags.map((tag, idx) => (
                        <span key={idx} className="bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-full text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Posting Tips */}
                {result.posting_tips && (
                  <div>
                    <h3 className="font-bold text-white mb-2">💡 Posting Tips</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                      {result.posting_tips.map((tip, idx) => (
                        <li key={idx}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="reel-generator" />
      
      {/* Rating Modal */}
      <RatingModal 
        isOpen={showRatingModal}
        onClose={() => setShowRatingModal(false)}
        featureKey="reel_generator"
        relatedRequestId={lastGenerationId}
        onSubmitSuccess={() => setShowRatingModal(false)}
      />
      
      {/* Upsell Modal - Shows after generation */}
      <UpsellModal
        isOpen={showUpsellModal}
        onClose={() => setShowUpsellModal(false)}
        generationId={lastGenerationId}
        feature="reel"
        onSuccess={(upsellId, data) => {
          toast.success(`${upsellId} applied!`);
          fetchCredits();
        }}
      />
    </div>
  );
}