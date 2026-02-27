import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { generationAPI, creditAPI } from '../utils/api';
import api from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Download, Loader2, ArrowLeft, Coins, Clock, AlertCircle, Share2, LogOut, FileText, BookOpen, Palette, Gift, CheckCircle, XCircle, Eye, EyeOff } from 'lucide-react';
import StoryProgressBar from '../components/StoryProgressBar';
import UpgradeBanner from '../components/UpgradeBanner';
import UpgradeModal from '../components/UpgradeModal';
import ShareButton from '../components/ShareButton';
import HelpGuide from '../components/HelpGuide';

export default function StoryGenerator() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [generationId, setGenerationId] = useState(null);
  const [result, setResult] = useState(null);
  const [isFreeTier, setIsFreeTier] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [pendingDownloadType, setPendingDownloadType] = useState(null);
  const [worksheetLoading, setWorksheetLoading] = useState(false);
  const [worksheetResult, setWorksheetResult] = useState(null);
  const [printableLoading, setPrintableLoading] = useState(false);
  const [pdfProgress, setPdfProgress] = useState({ step: 0, message: '' });
  const [showPersonalization, setShowPersonalization] = useState(false);
  const [personalization, setPersonalization] = useState({
    child_name: '',
    dedication: ''
  });
  const [fillBlankAnswers, setFillBlankAnswers] = useState({});
  const [fillBlankResults, setFillBlankResults] = useState({});
  const [showAnswers, setShowAnswers] = useState(false);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    ageGroup: '',
    theme: 'Adventure',
    genre: 'Fantasy',
    customGenre: '',
    moral: 'Friendship',
    characters: ['Kid', 'Dog'],
    setting: 'forest',
    scenes: 8,
    language: 'English',
    style: 'Animated 3D',
    length: '60s'
  });

  // List of inappropriate/vulgar words to block in custom genre
  const blockedWords = [
    'adult', 'sex', 'porn', 'xxx', 'nude', 'naked', 'erotic', 'violent', 'gore', 'blood',
    'kill', 'murder', 'death', 'drug', 'alcohol', 'beer', 'wine', 'cigarette', 'smoke',
    'gun', 'weapon', 'abuse', 'hate', 'racist', 'discrimination', 'vulgar', 'profanity',
    'explicit', 'mature', 'inappropriate', 'offensive', 'disturbing', 'graphic', 'brutal',
    'torture', 'horror', 'scary', 'nightmare', 'demon', 'devil', 'evil', 'cult', 'occult',
    'gambling', 'casino', 'betting', 'suicide', 'self-harm', 'bully', 'harassment'
  ];

  // Validate custom genre
  const validateCustomGenre = (genre) => {
    if (!genre || genre.trim() === '') return { valid: false, message: 'Please enter a genre' };
    
    const lowerGenre = genre.toLowerCase();
    
    // Check for blocked words
    for (const word of blockedWords) {
      if (lowerGenre.includes(word)) {
        return { valid: false, message: 'This genre contains inappropriate content. Please choose a kid-friendly genre.' };
      }
    }
    
    // Check minimum length
    if (genre.trim().length < 3) {
      return { valid: false, message: 'Genre must be at least 3 characters' };
    }
    
    // Check maximum length
    if (genre.trim().length > 50) {
      return { valid: false, message: 'Genre must be less than 50 characters' };
    }
    
    return { valid: true, message: '' };
  };

  useEffect(() => {
    fetchCredits();
  }, []);

  useEffect(() => {
    if (generationId && polling) {
      const interval = setInterval(checkGenerationStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [generationId, polling]);

  const fetchCredits = async () => {
    try {
      const response = await creditAPI.getBalance();
      setCredits(response.data.balance);
      setIsFreeTier(response.data.isFreeTier);
    } catch (error) {
      toast.error('Failed to load credits');
    }
  };

  const getCreditCost = () => {
    const costs = { 8: 6, 10: 7, 12: 8 };
    return costs[formData.scenes] || 6;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate age group is selected
    if (!formData.ageGroup) {
      toast.error('Please select an Age Group before generating');
      return;
    }

    // Validate custom genre if selected
    if (formData.genre === 'Custom') {
      const validation = validateCustomGenre(formData.customGenre);
      if (!validation.valid) {
        toast.error(validation.message);
        return;
      }
    }
    
    const cost = getCreditCost();
    if (credits < cost) {
      toast.error(`Insufficient credits! Need ${cost} credits.`);
      navigate('/app/billing');
      return;
    }

    // Reset state for new generation
    setResult(null);
    setGenerationId(null);
    setPolling(false);
    setWorksheetResult(null);  // Reset worksheet
    setShowPersonalization(false);  // Reset personalization
    setPersonalization({ child_name: '', dedication: '' });
    setLoading(true);
    
    try {
      // Use custom genre if selected, otherwise use the selected genre
      const genreToUse = formData.genre === 'Custom' ? formData.customGenre.trim() : formData.genre;
      
      // Create clean request data - map frontend fields to backend expected fields
      const requestData = {
        ageGroup: formData.ageGroup,
        genre: genreToUse,
        theme: formData.theme || 'Friendship',
        sceneCount: formData.scenes  // Backend expects sceneCount, not scenes
      };
      
      const response = await generationAPI.generateStory(requestData);
      
      // Story generation is now synchronous - get result directly
      if (response.data.status === 'COMPLETED' && response.data.result) {
        setResult(response.data.result);
        setGenerationId(response.data.generationId);
        setCredits(response.data.remainingCredits || credits - cost);
        toast.success('Story pack generated successfully!');
      } else {
        // Fallback to polling if still processing
        setGenerationId(response.data.generationId);
        setCredits(response.data.remainingCredits || credits - cost);
        setPolling(true);
        toast.success('Story generation started! This may take 30-90 seconds.');
      }
    } catch (error) {
      console.error('Story generation error:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Generation failed. Please try again.';
      toast.error(errorMessage);
      
      // If it's a template not found error, suggest trying a different combination
      if (errorMessage.includes('template') || errorMessage.includes('matching')) {
        toast.info('Try selecting a different age group or genre combination');
      }
    } finally {
      setLoading(false);
    }
  };

  const checkGenerationStatus = async () => {
    try {
      const response = await generationAPI.getGeneration(generationId);
      if (response.data.status === 'COMPLETED' || response.data.status === 'SUCCEEDED') {
        setResult(response.data.outputJson);
        setPolling(false);
        setLoading(false);
        toast.success('Story pack generated successfully!');
      } else if (response.data.status === 'FAILED') {
        setPolling(false);
        setLoading(false);
        toast.error('Generation failed');
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  };

  const handleDownloadClick = (type) => {
    if (isFreeTier) {
      setPendingDownloadType(type);
      setShowUpgradeModal(true);
    } else {
      if (type === 'json') {
        downloadJSON(false);
      } else {
        downloadPDF();
      }
    }
  };

  const handleDownloadWithWatermark = () => {
    setShowUpgradeModal(false);
    if (pendingDownloadType === 'json') {
      downloadJSON(true);
    } else {
      downloadPDF(); // PDF will have watermark added server-side for free tier
    }
    setPendingDownloadType(null);
  };

  const downloadJSON = (withWatermark = true) => {
    // Add watermark for free-tier users
    const downloadContent = (isFreeTier && withWatermark) 
      ? { 
          ...result, 
          watermark: '⚡ Made with CreatorStudio AI - Upgrade to remove watermark',
          free_tier: true 
        }
      : result;
    
    const blob = new Blob([JSON.stringify(downloadContent, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `story-pack-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    toast.success('Downloaded!');
  };

  const downloadPDF = async () => {
    try {
      const response = await generationAPI.downloadPDF(generationId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `story-pack-${generationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(isFreeTier ? 'PDF Downloaded with watermark!' : 'PDF Downloaded!');
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error('Failed to download PDF');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Upgrade Modal */}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => { setShowUpgradeModal(false); setPendingDownloadType(null); }}
        onDownloadWithWatermark={handleDownloadWithWatermark}
      />

      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <Link to="/app"><Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800"><ArrowLeft className="w-4 h-4 mr-1 sm:mr-2" /><span className="hidden sm:inline">Dashboard</span></Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" /><span className="text-lg sm:text-xl font-bold text-white">Story Generator</span></div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-2 bg-purple-500/20 border border-purple-500/30 rounded-full px-3 sm:px-4 py-2"><Coins className="w-4 h-4 text-purple-400" /><span className="font-semibold text-purple-300 text-sm sm:text-base">{credits}</span></div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="text-slate-400 hover:text-white hover:bg-slate-800" data-testid="story-logout-btn">
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
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-5 sm:mb-6">Create Kids Story Pack</h2>
            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6" data-testid="story-form">
              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <Label className="text-slate-300 font-medium text-sm mb-2 block">Age Group <span className="text-red-400">*</span></Label>
                  <Select value={formData.ageGroup} onValueChange={(value) => setFormData({...formData, ageGroup: value})}>
                    <SelectTrigger className={`bg-slate-900/60 border-slate-600 text-white focus:ring-purple-500/20 ${!formData.ageGroup ? 'border-orange-500/50' : ''}`} data-testid="story-age-select">
                      <SelectValue placeholder="Select age group" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="4-6" className="text-white focus:bg-purple-600">4-6 years (Preschool)</SelectItem>
                      <SelectItem value="6-8" className="text-white focus:bg-purple-600">6-8 years (Early Elementary)</SelectItem>
                      <SelectItem value="8-10" className="text-white focus:bg-purple-600">8-10 years (Middle Childhood)</SelectItem>
                      <SelectItem value="10-13" className="text-white focus:bg-purple-600">10-13 years (Pre-Teen)</SelectItem>
                      <SelectItem value="13-15" className="text-white focus:bg-purple-600">13-15 years (Early Teen)</SelectItem>
                      <SelectItem value="15-17" className="text-white focus:bg-purple-600">15-17 years (Late Teen)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-slate-300 font-medium text-sm mb-2 block">Genre</Label>
                  <Select value={formData.genre} onValueChange={(value) => setFormData({...formData, genre: value, customGenre: value === 'Custom' ? formData.customGenre : ''})}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-purple-500/20" data-testid="story-genre-select"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="Fantasy" className="text-white focus:bg-purple-600">Fantasy</SelectItem>
                      <SelectItem value="Adventure" className="text-white focus:bg-purple-600">Adventure</SelectItem>
                      <SelectItem value="Mystery" className="text-white focus:bg-purple-600">Mystery/Detective</SelectItem>
                      <SelectItem value="SciFi" className="text-white focus:bg-purple-600">Science Fiction</SelectItem>
                      <SelectItem value="Fairy Tale" className="text-white focus:bg-purple-600">Fairy Tale</SelectItem>
                      <SelectItem value="Mythology" className="text-white focus:bg-purple-600">Mythology</SelectItem>
                      <SelectItem value="Historical" className="text-white focus:bg-purple-600">Historical Fiction</SelectItem>
                      <SelectItem value="Comedy" className="text-white focus:bg-purple-600">Comedy/Humor</SelectItem>
                      <SelectItem value="Animal" className="text-white focus:bg-purple-600">Animal Stories</SelectItem>
                      <SelectItem value="Superhero" className="text-white focus:bg-purple-600">Superhero</SelectItem>
                      <SelectItem value="Friendship" className="text-white focus:bg-purple-600">Friendship</SelectItem>
                      <SelectItem value="Educational" className="text-white focus:bg-purple-600">Educational</SelectItem>
                      <SelectItem value="Custom" className="text-white focus:bg-purple-600">✨ Custom Genre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Custom Genre Input */}
              {formData.genre === 'Custom' && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                  <Label className="text-purple-300 font-medium text-sm mb-2 block">Enter Custom Genre <span className="text-red-400">*</span></Label>
                  <Input
                    type="text"
                    placeholder="e.g., Space Exploration, Underwater Adventure, Time Travel..."
                    value={formData.customGenre}
                    onChange={(e) => setFormData({...formData, customGenre: e.target.value})}
                    className="mt-2 bg-slate-900/60 border-slate-600 text-white placeholder:text-slate-500"
                    maxLength={50}
                    data-testid="custom-genre-input"
                  />
                  <p className="text-xs text-purple-300 mt-2">
                    💡 Suggestions: Nature & Wildlife, Space Exploration, Underwater Adventure, Time Travel, 
                    Dinosaur World, Magical Creatures, Sports & Teamwork, Music & Dance, Cooking Adventures
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Note: Only kid-friendly genres are allowed. Inappropriate content will be rejected.
                  </p>
                </div>
              )}
              <div>
                <Label className="text-slate-300 font-medium text-sm mb-2 block">Number of Scenes</Label>
                <Select value={formData.scenes.toString()} onValueChange={(value) => setFormData({...formData, scenes: parseInt(value)})}>
                  <SelectTrigger className="bg-slate-900/60 border-slate-600 text-white focus:ring-purple-500/20"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="8" className="text-white focus:bg-purple-600">8 scenes (10 credits)</SelectItem>
                    <SelectItem value="10" className="text-white focus:bg-purple-600">10 scenes (10 credits)</SelectItem>
                    <SelectItem value="12" className="text-white focus:bg-purple-600">12 scenes (10 credits)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-purple-300"><Coins className="w-4 h-4" /><span className="font-medium">Cost: {getCreditCost()} credits</span></div>
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-3 rounded-xl transition-all duration-200 shadow-lg shadow-purple-500/25" data-testid="story-generate-btn">
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />{polling ? 'Generating... (30-90s)' : 'Starting...'}</> : <><Sparkles className="w-4 h-4 mr-2" />Generate Story Pack</>}
              </Button>
            </form>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
            <div className="flex items-center justify-between mb-5 sm:mb-6"><h2 className="text-xl sm:text-2xl font-bold text-white">Story Pack</h2>
              {result && (
                <div className="flex gap-2">
                  <ShareButton type="STORY" title={result.title || 'Kids Story Pack'} preview={result.synopsis || ''} />
                  <Button variant="outline" size="sm" onClick={() => handleDownloadClick('json')} className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white" data-testid="download-story-btn">
                    <Download className="w-4 h-4 mr-1 sm:mr-2" />
                    <span className="hidden sm:inline">Download</span>
                  </Button>
                </div>
              )}
            </div>
            {loading && !result && (
              <StoryProgressBar isGenerating={loading} />
            )}
            {!loading && !result && <div className="text-center py-12 text-slate-400"><Clock className="w-12 h-12 mx-auto mb-4 text-slate-600" /><p>Your story pack will appear here</p></div>}
            {result && <div className="space-y-5 max-h-[700px] overflow-y-auto pr-2 custom-scrollbar" data-testid="story-result">
              {/* Free Tier Watermark Banner */}
              {isFreeTier && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-purple-300 font-medium text-sm">⚡ Made with CreatorStudio AI</p>
                    <p className="text-purple-400 text-xs mt-1">
                      Free tier content includes watermark. <Link to="/pricing" className="underline font-medium hover:text-purple-300">Upgrade</Link> to remove watermarks.
                    </p>
                  </div>
                </div>
              )}
              
              {/* Cover Image - AI Generated */}
              {result.coverImageUrl && (
                <div className="bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-xl p-4" data-testid="story-cover-image">
                  <h4 className="font-bold text-lg text-white mb-3 flex items-center gap-2">
                    <span className="text-xl">🎨</span> Story Cover Image
                  </h4>
                  <div className="relative rounded-xl overflow-hidden">
                    <img 
                      src={`${process.env.REACT_APP_BACKEND_URL}${result.coverImageUrl}`}
                      alt={result.title || 'Story Cover'}
                      className="w-full h-auto max-h-96 object-cover rounded-xl shadow-lg"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.innerHTML = '<div class="text-slate-400 text-center py-8">Image loading...</div>';
                      }}
                    />
                  </div>
                </div>
              )}
              
              {/* Story Title & Synopsis */}
              <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-xl p-5">
                <h3 className="text-xl sm:text-2xl font-bold text-white mb-2">{result.title}</h3>
                <p className="text-slate-300 mb-3">{result.synopsis}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="bg-purple-500/30 text-purple-200 px-2 py-1 rounded-lg">{result.genre || formData.genre}</span>
                  <span className="bg-blue-500/30 text-blue-200 px-2 py-1 rounded-lg">Ages {result.ageGroup || formData.ageGroup}</span>
                  {result.moral && <span className="bg-emerald-500/30 text-emerald-200 px-2 py-1 rounded-lg">Moral: {result.moral}</span>}
                </div>
              </div>
              
              {/* Characters */}
              {result.characters && result.characters.length > 0 && (
                <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
                  <h4 className="font-bold text-lg text-white mb-3 flex items-center gap-2">
                    <span className="text-xl">👥</span> Characters ({result.characters.length})
                  </h4>
                  <div className="grid gap-3">
                    {result.characters.map((char, idx) => (
                      <div key={idx} className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-purple-300">{char.name}</span>
                          <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{char.role}</span>
                        </div>
                        <p className="text-sm text-slate-400">{char.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Scenes */}
              {result.scenes && result.scenes.length > 0 && (
                <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4">
                  <h4 className="font-bold text-lg text-white mb-3 flex items-center gap-2">
                    <span className="text-xl">🎬</span> Scenes ({result.scenes.length})
                  </h4>
                  <div className="space-y-4">
                    {result.scenes.map((scene, idx) => (
                      <div key={idx} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="bg-purple-600 text-white text-xs font-bold px-2 py-1 rounded-lg">Scene {scene.scene_number || scene.sceneNumber || idx + 1}</span>
                          <span className="font-semibold text-slate-200">{scene.title || scene.sceneTitle}</span>
                        </div>
                        {scene.setting && <p className="text-xs text-slate-400 mb-2">📍 {scene.setting}</p>}
                        
                        {/* Scene Image - AI Generated */}
                        {scene.imageUrl && (
                          <div className="mb-3">
                            <img 
                              src={`${process.env.REACT_APP_BACKEND_URL}${scene.imageUrl}`}
                              alt={`Scene ${idx + 1}`}
                              className="w-full h-48 object-cover rounded-lg shadow-md"
                              data-testid={`scene-image-${idx}`}
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          </div>
                        )}
                        
                        {/* Visual Description */}
                        {(scene.visual_description || scene.visualDescription) && (
                          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-2 mb-2">
                            <p className="text-xs font-medium text-blue-300 mb-1">🎨 Visual Description:</p>
                            <p className="text-sm text-blue-200">{scene.visual_description || scene.visualDescription}</p>
                          </div>
                        )}
                        
                        {/* Narration */}
                        {scene.narration && (
                          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-2 mb-2">
                            <p className="text-xs font-medium text-purple-300 mb-1">📖 Narration:</p>
                            <p className="text-sm text-purple-200 italic">"{scene.narration}"</p>
                          </div>
                        )}
                        
                        {/* Dialogue */}
                        {((scene.dialogue && scene.dialogue.length > 0) || scene.characterDialogue) && (
                          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2 mb-2">
                            <p className="text-xs font-medium text-emerald-300 mb-1">💬 Dialogue:</p>
                            {scene.dialogue ? scene.dialogue.map((d, dIdx) => (
                              <p key={dIdx} className="text-sm text-emerald-200">
                                <span className="font-semibold">{d.speaker}:</span> "{d.line}"
                              </p>
                            )) : (
                              <p className="text-sm text-emerald-200">{scene.characterDialogue}</p>
                            )}
                          </div>
                        )}
                        
                        {/* Image Prompt */}
                        {scene.image_prompt && (
                          <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-2">
                            <p className="text-xs font-medium text-orange-300 mb-1">🖼️ Image Prompt:</p>
                            <p className="text-xs text-orange-200">{scene.image_prompt}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* YouTube Metadata */}
              {result.youtubeMetadata && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                  <h4 className="font-bold text-lg text-white mb-3 flex items-center gap-2">
                    <span className="text-xl">📺</span> YouTube Metadata
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-red-300">Video Title:</p>
                      <p className="text-sm font-semibold text-white">{result.youtubeMetadata.title}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-red-300">Description:</p>
                      <p className="text-sm text-slate-300 whitespace-pre-wrap">{result.youtubeMetadata.description}</p>
                    </div>
                    {result.youtubeMetadata.tags && (
                      <div>
                        <p className="text-xs font-medium text-red-300 mb-1">Tags:</p>
                        <div className="flex flex-wrap gap-1">
                          {result.youtubeMetadata.tags.map((tag, idx) => (
                            <span key={idx} className="bg-red-500/20 text-red-300 text-xs px-2 py-0.5 rounded border border-red-500/30">{tag}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Story Tools - Educational Add-ons */}
              <div className="bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-xl p-4">
                <h4 className="font-bold text-lg text-white mb-4 flex items-center gap-2">
                  <span className="text-xl">🎓</span> Educational Add-ons
                </h4>
                
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Worksheet Generator */}
                  <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-5 h-5 text-amber-400" />
                      <h5 className="font-semibold text-white">Story Worksheet</h5>
                    </div>
                    <p className="text-sm text-slate-300 mb-3">5 comprehension questions, fill-in-the-blanks, vocabulary, and coloring prompt</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-amber-300 font-medium flex items-center gap-1">
                        <Coins className="w-3 h-3" /> 3 credits
                      </span>
                      <Button 
                        size="sm" 
                        className="bg-amber-600 hover:bg-amber-700"
                        disabled={worksheetLoading || !generationId}
                        onClick={async () => {
                          if (credits < 3) {
                            toast.error('Need 3 credits for worksheet');
                            return;
                          }
                          setWorksheetLoading(true);
                          try {
                            const response = await api.post(`/api/story-tools/worksheet/${generationId}`);
                            setWorksheetResult(response.data.worksheet);
                            setCredits(response.data.remainingCredits);
                            setFillBlankAnswers({});  // Reset answers
                            setFillBlankResults({});  // Reset results
                            setShowAnswers(false);    // Hide answers
                            toast.success('Worksheet generated!');
                          } catch (error) {
                            toast.error(error.response?.data?.detail || 'Failed to generate worksheet');
                          } finally {
                            setWorksheetLoading(false);
                          }
                        }}
                        data-testid="generate-worksheet-btn"
                      >
                        {worksheetLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate'}
                      </Button>
                    </div>
                  </div>
                  
                  {/* Printable Book */}
                  <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-2 mb-2">
                      <BookOpen className="w-5 h-5 text-orange-400" />
                      <h5 className="font-semibold text-white">Printable Story Book</h5>
                    </div>
                    <p className="text-sm text-slate-300 mb-2">Beautiful PDF with cover, story pages, moral, and activity page</p>
                    
                    {/* Personalization Pack - Premium Upsell */}
                    <div className="bg-gradient-to-r from-pink-500/20 to-purple-500/20 rounded-lg p-3 mb-3 border border-pink-500/30">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <input 
                            type="checkbox" 
                            id="personalize" 
                            checked={showPersonalization}
                            onChange={(e) => setShowPersonalization(e.target.checked)}
                            className="rounded border-pink-500/50 bg-slate-800"
                            data-testid="personalization-checkbox"
                          />
                          <label htmlFor="personalize" className="text-sm font-medium text-pink-300 flex items-center gap-1 cursor-pointer">
                            <Gift className="w-4 h-4 text-pink-400" /> 
                            Personalization Pack
                          </label>
                        </div>
                        <span className="text-xs bg-pink-500/30 text-pink-300 px-2 py-0.5 rounded-full">+2 credits</span>
                      </div>
                      <p className="text-xs text-slate-400 mb-2">Make the story special with your child's name and a personal dedication!</p>
                      
                      {showPersonalization && (
                        <div className="space-y-2 pt-2 border-t border-pink-500/30">
                          <div>
                            <label className="text-xs font-medium text-slate-300">Child's Name (max 300 chars)</label>
                            <Input 
                              placeholder="e.g., Emma, Aarav, Sofia" 
                              value={personalization.child_name}
                              onChange={(e) => setPersonalization({...personalization, child_name: e.target.value.slice(0, 300)})}
                              className="text-sm mt-1 bg-slate-900/60 border-slate-600 text-white placeholder:text-slate-500"
                              maxLength={300}
                              data-testid="child-name-input"
                            />
                            <p className="text-xs text-slate-400 mt-1">{personalization.child_name?.length || 0}/300 characters</p>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-slate-300">Dedication Message (max 300 chars)</label>
                            <Input 
                              placeholder="e.g., For my little star, with love from Mommy" 
                              value={personalization.dedication}
                              onChange={(e) => setPersonalization({...personalization, dedication: e.target.value.slice(0, 300)})}
                              className="text-sm mt-1 bg-slate-900/60 border-slate-600 text-white placeholder:text-slate-500"
                              maxLength={300}
                              data-testid="dedication-input"
                            />
                            <p className="text-xs text-slate-400 mt-1">{personalization.dedication?.length || 0}/300 characters</p>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-slate-300">Birthday Message (Optional, max 300 chars)</label>
                            <Input 
                              placeholder="e.g., Happy 5th Birthday!" 
                              value={personalization.birthday_message || ''}
                              onChange={(e) => setPersonalization({...personalization, birthday_message: e.target.value.slice(0, 300)})}
                              className="text-sm mt-1 bg-slate-900/60 border-slate-600 text-white placeholder:text-slate-500"
                              maxLength={300}
                              data-testid="birthday-input"
                            />
                            <p className="text-xs text-slate-400 mt-1">{personalization.birthday_message?.length || 0}/300 characters</p>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* PDF Progress Bar - Full Width */}
                    {printableLoading && (
                      <div className="mt-4 p-3 bg-purple-500/20 rounded-xl border border-purple-500/30">
                        <div className="flex justify-between text-sm text-purple-300 mb-2">
                          <span className="font-medium">{pdfProgress.message}</span>
                          <span className="font-bold">{Math.min(pdfProgress.step * 25, 100)}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${Math.min(pdfProgress.step * 25, 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-slate-400 mt-2">
                          <span className={`px-2 py-0.5 rounded ${pdfProgress.step >= 1 ? 'bg-purple-500/30 text-purple-300 font-medium' : ''}`}>Prepare</span>
                          <span className={`px-2 py-0.5 rounded ${pdfProgress.step >= 2 ? 'bg-purple-500/30 text-purple-300 font-medium' : ''}`}>Render</span>
                          <span className={`px-2 py-0.5 rounded ${pdfProgress.step >= 3 ? 'bg-purple-500/30 text-purple-300 font-medium' : ''}`}>Generate</span>
                          <span className={`px-2 py-0.5 rounded ${pdfProgress.step >= 4 ? 'bg-purple-500/30 text-purple-300 font-medium' : ''}`}>Download</span>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-sm text-orange-400 font-semibold flex items-center gap-1">
                        <Coins className="w-4 h-4" /> {showPersonalization ? '6' : '4'} credits
                      </span>
                      <Button 
                        size="sm" 
                        className="bg-orange-500 hover:bg-orange-600"
                        disabled={printableLoading || !generationId}
                        onClick={async () => {
                          const cost = showPersonalization ? 6 : 4;
                          if (credits < cost) {
                            toast.error(`Need ${cost} credits for printable book`);
                            return;
                          }
                          setPrintableLoading(true);
                          setPdfProgress({ step: 1, message: 'Preparing your storybook...' });
                          
                          try {
                            const payload = {
                              include_activities: true,
                              personalization: showPersonalization ? personalization : null
                            };
                            
                            // Step 1: Create printable book
                            setPdfProgress({ step: 1, message: 'Creating printable book...' });
                            const response = await api.post(`/api/story-tools/printable-book/${generationId}`, payload);
                            setCredits(response.data.remainingCredits);
                            
                            // Show expiry notice
                            toast.info('⏰ Download link active for 5 minutes!', { duration: 5000 });
                            
                            // Step 2: Rendering PDF
                            setPdfProgress({ step: 2, message: 'Rendering beautiful pages...' });
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Step 3: Download the PDF
                            setPdfProgress({ step: 3, message: 'Generating PDF file...' });
                            const token = localStorage.getItem('token');
                            const pdfResponse = await fetch(`${process.env.REACT_APP_BACKEND_URL}${response.data.downloadUrl}`, {
                              method: 'GET',
                              headers: {
                                'Authorization': `Bearer ${token}`
                              }
                            });
                            
                            if (!pdfResponse.ok) {
                              if (pdfResponse.status === 410) {
                                throw new Error('Download link expired. Please generate a new PDF.');
                              }
                              throw new Error('Failed to download PDF');
                            }
                            
                            setPdfProgress({ step: 4, message: 'Downloading your storybook...' });
                            const blob = await pdfResponse.blob();
                            
                            // Create download link
                            const url = window.URL.createObjectURL(blob);
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = `storybook-${response.data.bookId}.pdf`;
                            link.style.display = 'none';
                            document.body.appendChild(link);
                            link.click();
                            
                            // Cleanup
                            setTimeout(() => {
                              document.body.removeChild(link);
                              window.URL.revokeObjectURL(url);
                            }, 100);
                            
                            setPdfProgress({ step: 5, message: 'Complete!' });
                            toast.success('PDF downloaded! Note: Download links expire after 5 minutes.');
                          } catch (error) {
                            console.error('PDF Download Error:', error);
                            toast.error(error.response?.data?.detail || error.message || 'Failed to create printable book');
                          } finally {
                            setPrintableLoading(false);
                            setPdfProgress({ step: 0, message: '' });
                          }
                        }}
                        data-testid="generate-printable-btn"
                      >
                        {printableLoading ? (
                          <span className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Processing...
                          </span>
                        ) : 'Create PDF'}
                      </Button>
                    </div>
                  </div>
                </div>
                
                {/* Worksheet Result */}
                {worksheetResult && (
                  <div className="mt-4 bg-slate-900/50 rounded-xl p-4 border border-amber-500/30">
                    <div className="flex items-center justify-between mb-4">
                      <h5 className="font-bold text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-amber-400" />
                        Interactive Worksheet: {worksheetResult.story_title}
                      </h5>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAnswers(!showAnswers)}
                        className="flex items-center gap-1 border-slate-600 text-slate-300 hover:bg-slate-700"
                      >
                        {showAnswers ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        {showAnswers ? 'Hide Answers' : 'Show Answers'}
                      </Button>
                    </div>
                    
                    <div className="space-y-6">
                      {/* Fill in the Blanks - Interactive */}
                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                        <h6 className="font-semibold text-sm mb-3 flex items-center gap-2 text-amber-300">
                          ✏️ Fill in the Blanks
                          <span className="text-xs text-slate-400">(Type your answers and check)</span>
                        </h6>
                        <div className="space-y-4">
                          {worksheetResult.fill_blanks?.map((fb, i) => {
                            const userAnswer = fillBlankAnswers[i] || '';
                            const result = fillBlankResults[i];
                            const correctAnswer = fb.answer;
                            
                            return (
                              <div key={i} className="space-y-2">
                                <div className="flex items-start gap-2">
                                  <span className="font-medium text-amber-400 mt-2">{fb.number}.</span>
                                  <div className="flex-1">
                                    <p className="text-sm text-slate-200 mb-2">
                                      {fb.sentence.split('_______')[0]}
                                      <Input
                                        className={`inline-block w-40 mx-1 text-center bg-slate-800 border-slate-600 text-white ${
                                          result === true ? 'border-emerald-500 bg-emerald-500/20' :
                                          result === false ? 'border-red-500 bg-red-500/20' : ''
                                        }`}
                                        placeholder="your answer"
                                        value={userAnswer}
                                        onChange={(e) => {
                                          setFillBlankAnswers({...fillBlankAnswers, [i]: e.target.value});
                                          setFillBlankResults({...fillBlankResults, [i]: undefined});
                                        }}
                                      />
                                      {fb.sentence.split('_______')[1]}
                                    </p>
                                    
                                    {/* Validation result */}
                                    {result === true && (
                                      <div className="flex items-center gap-1 text-emerald-400 text-sm">
                                        <CheckCircle className="w-4 h-4" />
                                        <span>Correct! Well done!</span>
                                      </div>
                                    )}
                                    {result === false && (
                                      <div className="text-sm">
                                        <div className="flex items-center gap-1 text-red-400">
                                          <XCircle className="w-4 h-4" />
                                          <span>Not quite right</span>
                                        </div>
                                        <p className="text-emerald-400 mt-1">
                                          <strong>Correct answer:</strong> {correctAnswer}
                                        </p>
                                      </div>
                                    )}
                                    
                                    {/* Show answer when toggled */}
                                    {showAnswers && result === undefined && (
                                      <p className="text-sm text-blue-400 mt-1">
                                        <strong>Answer:</strong> {correctAnswer}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Check Answers Button */}
                        <div className="mt-4 flex gap-2">
                          <Button
                            size="sm"
                            className="bg-amber-600 hover:bg-amber-700"
                            onClick={() => {
                              const newResults = {};
                              let allCorrect = true;
                              worksheetResult.fill_blanks?.forEach((fb, i) => {
                                const userAnswer = (fillBlankAnswers[i] || '').toLowerCase().trim();
                                const correctAnswer = (fb.answer || '').toLowerCase().trim();
                                
                                // Normalize both answers for comparison
                                const normalizeAnswer = (str) => str.replace(/[^a-z0-9\s]/g, '').toLowerCase().trim();
                                const normalizedUser = normalizeAnswer(userAnswer);
                                const normalizedCorrect = normalizeAnswer(correctAnswer);
                                
                                // Check for exact match or partial match
                                const isCorrect = normalizedUser.length >= 2 && (
                                  normalizedUser === normalizedCorrect ||
                                  normalizedCorrect.includes(normalizedUser) ||
                                  normalizedUser.includes(normalizedCorrect.split(' ')[0])
                                );
                                
                                newResults[i] = isCorrect;
                                if (!isCorrect) allCorrect = false;
                              });
                              setFillBlankResults(newResults);
                              
                              const correct = Object.values(newResults).filter(v => v === true).length;
                              const total = worksheetResult.fill_blanks?.length || 0;
                              
                              if (allCorrect) {
                                toast.success('🎉 Well done! All answers are correct!', { duration: 5000 });
                              } else if (correct > 0) {
                                toast.info(`You got ${correct} out of ${total} correct. Keep trying!`);
                              } else {
                                toast.error(`Try again! Check the answers shown below.`);
                              }
                            }}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Check My Answers
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setFillBlankAnswers({});
                              setFillBlankResults({});
                            }}
                          >
                            Reset
                          </Button>
                        </div>
                      </div>
                      
                      {/* Comprehension Questions */}
                      <div className="bg-blue-50 rounded-lg p-4">
                        <h6 className="font-semibold text-sm mb-3">📝 Comprehension Questions</h6>
                        <div className="space-y-3">
                          {worksheetResult.comprehension_questions?.map((q, i) => (
                            <div key={i} className="bg-white rounded p-3 border border-blue-200">
                              <p className="text-sm font-medium text-slate-800 mb-2">{q.number}. {q.question}</p>
                              {showAnswers && (
                                <p className="text-sm text-green-700 bg-green-50 p-2 rounded">
                                  <strong>Answer:</strong> {q.answer}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* Vocabulary */}
                      <div className="bg-purple-50 rounded-lg p-4">
                        <h6 className="font-semibold text-sm mb-3">📖 Vocabulary Words</h6>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {worksheetResult.vocabulary?.map((v, i) => (
                            <div key={i} className="bg-white rounded p-2 border border-purple-200 text-center">
                              <span className="font-medium text-purple-800">{v.word}</span>
                              {v.hint && <p className="text-xs text-slate-500 mt-1">{v.hint}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* Moral Reflection */}
                      <div className="bg-green-50 rounded-lg p-4">
                        <h6 className="font-semibold text-sm mb-2">💭 Moral Reflection</h6>
                        <p className="text-sm text-slate-700 mb-2">
                          <strong>Story's Moral:</strong> "{worksheetResult.moral_reflection?.moral}"
                        </p>
                        <p className="text-sm text-slate-600 italic">{worksheetResult.moral_reflection?.question}</p>
                      </div>
                      
                      {/* Coloring Prompt */}
                      <div className="bg-pink-50 rounded-lg p-4">
                        <h6 className="font-semibold text-sm mb-2">🎨 Drawing Activity</h6>
                        <p className="text-sm text-slate-700 italic">{worksheetResult.coloring_prompt}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
            </div>}
          </div>
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="story-generator" />
    </div>
  );
}