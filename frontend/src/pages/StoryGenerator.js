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
                    <SelectTrigger className={!formData.ageGroup ? 'border-orange-300' : ''} data-testid="story-age-select">
                      <SelectValue placeholder="Select age group" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="4-6">4-6 years (Preschool)</SelectItem>
                      <SelectItem value="6-8">6-8 years (Early Elementary)</SelectItem>
                      <SelectItem value="8-10">8-10 years (Middle Childhood)</SelectItem>
                      <SelectItem value="10-13">10-13 years (Pre-Teen)</SelectItem>
                      <SelectItem value="13-15">13-15 years (Early Teen)</SelectItem>
                      <SelectItem value="15-17">15-17 years (Late Teen)</SelectItem>
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
            {result && <div className="space-y-6 max-h-[700px] overflow-y-auto pr-2" data-testid="story-result">
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
              
              {/* Story Title & Synopsis */}
              <div className="bg-gradient-to-r from-purple-50 to-slate-50 border border-purple-200 rounded-lg p-6">
                <h3 className="text-2xl font-bold text-purple-900 mb-2">{result.title}</h3>
                <p className="text-slate-700 mb-3">{result.synopsis}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded">{result.genre || formData.genre}</span>
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">Ages {result.ageGroup || formData.ageGroup}</span>
                  {result.moral && <span className="bg-green-100 text-green-700 px-2 py-1 rounded">Moral: {result.moral}</span>}
                </div>
              </div>
              
              {/* Characters */}
              {result.characters && result.characters.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                    <span className="text-xl">👥</span> Characters ({result.characters.length})
                  </h4>
                  <div className="grid gap-3">
                    {result.characters.map((char, idx) => (
                      <div key={idx} className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-purple-700">{char.name}</span>
                          <span className="text-xs bg-slate-200 px-2 py-0.5 rounded">{char.role}</span>
                        </div>
                        <p className="text-sm text-slate-600">{char.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Scenes */}
              {result.scenes && result.scenes.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                    <span className="text-xl">🎬</span> Scenes ({result.scenes.length})
                  </h4>
                  <div className="space-y-4">
                    {result.scenes.map((scene, idx) => (
                      <div key={idx} className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="bg-purple-500 text-white text-xs font-bold px-2 py-1 rounded">Scene {scene.scene_number || idx + 1}</span>
                          <span className="font-semibold text-slate-800">{scene.title}</span>
                        </div>
                        {scene.setting && <p className="text-xs text-slate-500 mb-2">📍 {scene.setting}</p>}
                        
                        {/* Visual Description */}
                        {scene.visual_description && (
                          <div className="bg-blue-50 rounded p-2 mb-2">
                            <p className="text-xs font-medium text-blue-700 mb-1">🎨 Visual Description:</p>
                            <p className="text-sm text-blue-800">{scene.visual_description}</p>
                          </div>
                        )}
                        
                        {/* Narration */}
                        {scene.narration && (
                          <div className="bg-purple-50 rounded p-2 mb-2">
                            <p className="text-xs font-medium text-purple-700 mb-1">📖 Narration:</p>
                            <p className="text-sm text-purple-800 italic">"{scene.narration}"</p>
                          </div>
                        )}
                        
                        {/* Dialogue */}
                        {scene.dialogue && scene.dialogue.length > 0 && (
                          <div className="bg-green-50 rounded p-2 mb-2">
                            <p className="text-xs font-medium text-green-700 mb-1">💬 Dialogue:</p>
                            {scene.dialogue.map((d, dIdx) => (
                              <p key={dIdx} className="text-sm text-green-800">
                                <span className="font-semibold">{d.speaker}:</span> "{d.line}"
                              </p>
                            ))}
                          </div>
                        )}
                        
                        {/* Image Prompt */}
                        {scene.image_prompt && (
                          <div className="bg-orange-50 rounded p-2">
                            <p className="text-xs font-medium text-orange-700 mb-1">🖼️ Image Prompt:</p>
                            <p className="text-xs text-orange-800">{scene.image_prompt}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* YouTube Metadata */}
              {result.youtubeMetadata && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="font-bold text-lg mb-3 flex items-center gap-2">
                    <span className="text-xl">📺</span> YouTube Metadata
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-red-700">Video Title:</p>
                      <p className="text-sm font-semibold text-slate-800">{result.youtubeMetadata.title}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-red-700">Description:</p>
                      <p className="text-sm text-slate-700 whitespace-pre-wrap">{result.youtubeMetadata.description}</p>
                    </div>
                    {result.youtubeMetadata.tags && (
                      <div>
                        <p className="text-xs font-medium text-red-700 mb-1">Tags:</p>
                        <div className="flex flex-wrap gap-1">
                          {result.youtubeMetadata.tags.map((tag, idx) => (
                            <span key={idx} className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded">{tag}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Story Tools - Educational Add-ons */}
              <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-4">
                <h4 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <span className="text-xl">🎓</span> Educational Add-ons
                </h4>
                
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Worksheet Generator */}
                  <div className="bg-white rounded-lg p-4 border border-amber-200">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-5 h-5 text-amber-600" />
                      <h5 className="font-semibold">Story Worksheet</h5>
                    </div>
                    <p className="text-sm text-slate-600 mb-3">5 comprehension questions, fill-in-the-blanks, vocabulary, and coloring prompt</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-amber-700 font-medium flex items-center gap-1">
                        <Coins className="w-3 h-3" /> 3 credits
                      </span>
                      <Button 
                        size="sm" 
                        className="bg-amber-500 hover:bg-amber-600"
                        disabled={worksheetLoading || !generationId}
                        onClick={async () => {
                          if (credits < 3) {
                            toast.error('Need 3 credits for worksheet');
                            return;
                          }
                          setWorksheetLoading(true);
                          try {
                            const response = await api.post(`/api/story-tools/worksheet/generate?generation_id=${generationId}`);
                            setWorksheetResult(response.data.worksheet);
                            setCredits(response.data.remainingCredits);
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
                  <div className="bg-white rounded-lg p-4 border border-amber-200">
                    <div className="flex items-center gap-2 mb-2">
                      <BookOpen className="w-5 h-5 text-orange-600" />
                      <h5 className="font-semibold">Printable Story Book</h5>
                    </div>
                    <p className="text-sm text-slate-600 mb-2">Beautiful PDF with cover, story pages, moral, and activity page</p>
                    
                    {/* Personalization Toggle */}
                    <div className="flex items-center gap-2 mb-3">
                      <input 
                        type="checkbox" 
                        id="personalize" 
                        checked={showPersonalization}
                        onChange={(e) => setShowPersonalization(e.target.checked)}
                        className="rounded"
                      />
                      <label htmlFor="personalize" className="text-xs text-slate-600 flex items-center gap-1">
                        <Gift className="w-3 h-3 text-pink-500" /> Add personalization (+2 credits)
                      </label>
                    </div>
                    
                    {showPersonalization && (
                      <div className="space-y-2 mb-3">
                        <Input 
                          placeholder="Child's name (replaces hero)" 
                          value={personalization.child_name}
                          onChange={(e) => setPersonalization({...personalization, child_name: e.target.value})}
                          className="text-sm"
                        />
                        <Input 
                          placeholder="Dedication message (optional)" 
                          value={personalization.dedication}
                          onChange={(e) => setPersonalization({...personalization, dedication: e.target.value})}
                          className="text-sm"
                        />
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-orange-700 font-medium flex items-center gap-1">
                        <Coins className="w-3 h-3" /> {showPersonalization ? '6' : '4'} credits
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
                          try {
                            const payload = {
                              include_activities: true,
                              personalization: showPersonalization ? personalization : null
                            };
                            const response = await api.post(`/api/story-tools/printable-book/generate?generation_id=${generationId}`, payload);
                            setCredits(response.data.remainingCredits);
                            toast.success('Printable book created! Downloading...');
                            
                            // Download the PDF
                            window.open(`${process.env.REACT_APP_BACKEND_URL}${response.data.downloadUrl}`, '_blank');
                          } catch (error) {
                            toast.error(error.response?.data?.detail || 'Failed to create printable book');
                          } finally {
                            setPrintableLoading(false);
                          }
                        }}
                        data-testid="generate-printable-btn"
                      >
                        {printableLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create PDF'}
                      </Button>
                    </div>
                  </div>
                </div>
                
                {/* Worksheet Result */}
                {worksheetResult && (
                  <div className="mt-4 bg-white rounded-lg p-4 border border-amber-200">
                    <div className="flex items-center justify-between mb-4">
                      <h5 className="font-bold flex items-center gap-2">
                        <FileText className="w-5 h-5 text-amber-600" />
                        Interactive Worksheet: {worksheetResult.story_title}
                      </h5>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAnswers(!showAnswers)}
                        className="flex items-center gap-1"
                      >
                        {showAnswers ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        {showAnswers ? 'Hide Answers' : 'Show Answers'}
                      </Button>
                    </div>
                    
                    <div className="space-y-6">
                      {/* Fill in the Blanks - Interactive */}
                      <div className="bg-amber-50 rounded-lg p-4">
                        <h6 className="font-semibold text-sm mb-3 flex items-center gap-2">
                          ✏️ Fill in the Blanks
                          <span className="text-xs text-slate-500">(Type your answers and check)</span>
                        </h6>
                        <div className="space-y-4">
                          {worksheetResult.fill_blanks?.map((fb, i) => {
                            const userAnswer = fillBlankAnswers[i] || '';
                            const result = fillBlankResults[i];
                            const correctAnswer = fb.answer;
                            
                            return (
                              <div key={i} className="space-y-2">
                                <div className="flex items-start gap-2">
                                  <span className="font-medium text-amber-700 mt-2">{fb.number}.</span>
                                  <div className="flex-1">
                                    <p className="text-sm text-slate-700 mb-2">
                                      {fb.sentence.split('_______')[0]}
                                      <Input
                                        className={`inline-block w-40 mx-1 text-center ${
                                          result === true ? 'border-green-500 bg-green-50' :
                                          result === false ? 'border-red-500 bg-red-50' : ''
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
                                      <div className="flex items-center gap-1 text-green-600 text-sm">
                                        <CheckCircle className="w-4 h-4" />
                                        <span>Correct!</span>
                                      </div>
                                    )}
                                    {result === false && (
                                      <div className="text-sm">
                                        <div className="flex items-center gap-1 text-red-600">
                                          <XCircle className="w-4 h-4" />
                                          <span>Not quite right</span>
                                        </div>
                                        {showAnswers && (
                                          <p className="text-green-700 mt-1">
                                            <strong>Correct answer:</strong> {correctAnswer}
                                          </p>
                                        )}
                                      </div>
                                    )}
                                    
                                    {/* Show answer when toggled */}
                                    {showAnswers && result === undefined && (
                                      <p className="text-sm text-blue-600 mt-1">
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
                            className="bg-amber-500 hover:bg-amber-600"
                            onClick={() => {
                              const newResults = {};
                              worksheetResult.fill_blanks?.forEach((fb, i) => {
                                const userAnswer = (fillBlankAnswers[i] || '').toLowerCase().trim();
                                const correctAnswer = (fb.answer || '').toLowerCase().trim();
                                // Check if the answer contains the key words or is similar
                                newResults[i] = userAnswer.length > 0 && (
                                  correctAnswer.includes(userAnswer) || 
                                  userAnswer.includes(correctAnswer.split(' ')[0]) ||
                                  userAnswer === correctAnswer
                                );
                              });
                              setFillBlankResults(newResults);
                              
                              const correct = Object.values(newResults).filter(v => v === true).length;
                              const total = worksheetResult.fill_blanks?.length || 0;
                              toast.success(`You got ${correct} out of ${total} correct!`);
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
    </div>
  );
}