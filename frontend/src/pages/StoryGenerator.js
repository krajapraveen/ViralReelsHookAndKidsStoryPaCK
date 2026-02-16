import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { generationAPI, creditAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Download, Loader2, ArrowLeft, Coins, Clock, AlertCircle, Share2, LogOut } from 'lucide-react';
import StoryProgressBar from '../components/StoryProgressBar';
import UpgradeBanner from '../components/UpgradeBanner';
import UpgradeModal from '../components/UpgradeModal';
import ShareButton from '../components/ShareButton';

export default function StoryGenerator() {
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [generationId, setGenerationId] = useState(null);
  const [result, setResult] = useState(null);
  const [isFreeTier, setIsFreeTier] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [pendingDownloadType, setPendingDownloadType] = useState(null);
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
    style: 'Pixar-like 3D',
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
    setLoading(true);
    
    try {
      // Use custom genre if selected, otherwise use the selected genre
      const genreToUse = formData.genre === 'Custom' ? formData.customGenre.trim() : formData.genre;
      
      // Create clean request data without customGenre field
      const { customGenre, ...cleanFormData } = formData;
      const requestData = { ...cleanFormData, genre: genreToUse };
      
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
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Generation failed');
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
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `story-pack-${Date.now()}.json`;
    a.click();
    toast.success('Downloaded!');
  };

  const downloadPDF = async () => {
    try {
      const response = await generationAPI.downloadPDF(generationId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `story-pack-${generationId}.pdf`;
      a.click();
      toast.success(isFreeTier ? 'PDF Downloaded with watermark!' : 'PDF Downloaded!');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Upgrade Modal */}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => { setShowUpgradeModal(false); setPendingDownloadType(null); }}
        onDownloadWithWatermark={handleDownloadWithWatermark}
      />

      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app"><Button variant="ghost" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />Dashboard</Button></Link>
            <div className="flex items-center gap-2"><Sparkles className="w-6 h-6 text-purple-500" /><span className="text-xl font-bold">Story Generator</span></div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-slate-100 rounded-full px-4 py-2"><Coins className="w-4 h-4 text-purple-500" /><span className="font-semibold">{credits} Credits</span></div>
            <Button variant="ghost" size="sm" onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} data-testid="story-logout-btn">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Upgrade Banners */}
        {credits === 0 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="exhausted" />}
        {credits > 0 && credits <= 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="low" />}
        {isFreeTier && credits > 10 && <UpgradeBanner credits={credits} isFreeTier={isFreeTier} type="watermark" />}

        <div className="grid lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-2xl font-bold mb-6">Create Kids Story Pack</h2>
            <form onSubmit={handleSubmit} className="space-y-6" data-testid="story-form">
              <div className="grid md:grid-cols-2 gap-4">
                <div><Label>Age Group <span className="text-red-500">*</span></Label>
                  <Select value={formData.ageGroup} onValueChange={(value) => setFormData({...formData, ageGroup: value})}>
                    <SelectTrigger className={!formData.ageGroup ? 'border-orange-300' : ''}>
                      <SelectValue placeholder="Select age group" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3-5">3-5 years (Preschool)</SelectItem>
                      <SelectItem value="6-8">6-8 years (Early Elementary)</SelectItem>
                      <SelectItem value="9-12">9-12 years (Middle Childhood)</SelectItem>
                      <SelectItem value="13-15">13-15 years (Early Teens)</SelectItem>
                      <SelectItem value="16-17">16-17 years (Late Teens)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Genre</Label>
                  <Select value={formData.genre} onValueChange={(value) => setFormData({...formData, genre: value, customGenre: value === 'Custom' ? formData.customGenre : ''})}>
                    <SelectTrigger data-testid="story-genre-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Fantasy">Fantasy</SelectItem>
                      <SelectItem value="Adventure">Adventure</SelectItem>
                      <SelectItem value="Mystery">Mystery/Detective</SelectItem>
                      <SelectItem value="SciFi">Science Fiction</SelectItem>
                      <SelectItem value="Fairy Tale">Fairy Tale</SelectItem>
                      <SelectItem value="Mythology">Mythology</SelectItem>
                      <SelectItem value="Historical">Historical Fiction</SelectItem>
                      <SelectItem value="Comedy">Comedy/Humor</SelectItem>
                      <SelectItem value="Animal">Animal Stories</SelectItem>
                      <SelectItem value="Superhero">Superhero</SelectItem>
                      <SelectItem value="Friendship">Friendship</SelectItem>
                      <SelectItem value="Educational">Educational</SelectItem>
                      <SelectItem value="Custom">✨ Custom Genre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Custom Genre Input */}
              {formData.genre === 'Custom' && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <Label className="text-purple-700">Enter Custom Genre <span className="text-red-500">*</span></Label>
                  <Input
                    type="text"
                    placeholder="e.g., Space Exploration, Underwater Adventure, Time Travel..."
                    value={formData.customGenre}
                    onChange={(e) => setFormData({...formData, customGenre: e.target.value})}
                    className="mt-2 bg-white"
                    maxLength={50}
                    data-testid="custom-genre-input"
                  />
                  <p className="text-xs text-purple-600 mt-2">
                    💡 Suggestions: Nature & Wildlife, Space Exploration, Underwater Adventure, Time Travel, 
                    Dinosaur World, Magical Creatures, Sports & Teamwork, Music & Dance, Cooking Adventures
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Note: Only kid-friendly genres are allowed. Inappropriate content will be rejected.
                  </p>
                </div>
              )}
              <div><Label>Number of Scenes</Label>
                <Select value={formData.scenes.toString()} onValueChange={(value) => setFormData({...formData, scenes: parseInt(value)})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="8">8 scenes (6 credits)</SelectItem>
                    <SelectItem value="10">10 scenes (7 credits)</SelectItem>
                    <SelectItem value="12">12 scenes (8 credits)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-purple-700"><Coins className="w-4 h-4" /><span className="font-medium">Cost: {getCreditCost()} credits</span></div>
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-purple-500 hover:bg-purple-600 text-white" data-testid="story-generate-btn">
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />{polling ? 'Generating... (30-90s)' : 'Starting...'}</> : <><Sparkles className="w-4 h-4 mr-2" />Generate Story Pack</>}
              </Button>
            </form>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-6"><h2 className="text-2xl font-bold">Story Pack</h2>
              {result && (
                <div className="flex gap-2">
                  <ShareButton type="STORY" title={result.title || 'Kids Story Pack'} preview={result.synopsis || ''} />
                  <Button variant="outline" size="sm" onClick={() => handleDownloadClick('pdf')} data-testid="download-story-pdf">
                    <Download className="w-4 h-4 mr-2" />
                    PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleDownloadClick('json')} data-testid="download-story-btn">
                    <Download className="w-4 h-4 mr-2" />
                    JSON
                  </Button>
                </div>
              )}
            </div>
            {loading && !result && (
              <StoryProgressBar isGenerating={loading} />
            )}
            {!loading && !result && <div className="text-center py-12 text-slate-500"><Clock className="w-12 h-12 mx-auto mb-4 text-slate-300" /><p>Your story pack will appear here</p></div>}
            {result && <div className="space-y-4 max-h-[600px] overflow-y-auto" data-testid="story-result">
              {/* Free Tier Watermark Banner */}
              {isFreeTier && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-purple-700 font-medium text-sm">⚡ Made with CreatorStudio AI</p>
                    <p className="text-purple-600 text-xs mt-1">
                      Free tier content includes watermark. <Link to="/pricing" className="underline font-medium">Upgrade</Link> to remove watermarks.
                    </p>
                  </div>
                </div>
              )}
              <div className="bg-gradient-to-r from-purple-50 to-slate-50 border border-purple-200 rounded-lg p-6"><h3 className="text-2xl font-bold text-purple-900 mb-2">{result.title}</h3><p className="text-slate-700">{result.synopsis}</p></div>
              {result.scenes && <div><h3 className="font-bold text-lg mb-3">Scenes: {result.scenes.length}</h3><p className="text-sm text-slate-600">Complete scene breakdown available in downloaded JSON</p></div>}
            </div>}
          </div>
        </div>
      </div>
    </div>
  );
}