import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  BookOpen, ArrowLeft, Loader2, Download, Sparkles,
  Wallet, ChevronRight, Film, Users, FileText, 
  CheckCircle, AlertCircle, Plus
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';

export default function StorySeries() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [themes, setThemes] = useState([]);
  const [userStories, setUserStories] = useState([]);
  
  // Form state
  const [selectedStoryId, setSelectedStoryId] = useState('');
  const [storySummary, setStorySummary] = useState('');
  const [characterNames, setCharacterNames] = useState(['']);
  const [targetAge, setTargetAge] = useState('4-7');
  const [theme, setTheme] = useState('Adventure');
  const [episodeCount, setEpisodeCount] = useState(5);
  
  // Result state
  const [generatedSeries, setGeneratedSeries] = useState(null);
  const [seriesHistory, setSeriesHistory] = useState([]);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [walletRes, pricingRes, themesRes, storiesRes, historyRes] = await Promise.all([
        walletAPI.getWallet(),
        api.get('/api/story-series/pricing'),
        api.get('/api/story-series/themes'),
        api.get('/api/story-series/user-stories'),
        api.get('/api/story-series/history?limit=5')
      ]);
      
      setWallet(walletRes.data);
      setPricing(pricingRes.data);
      setThemes(themesRes.data.themes || []);
      setUserStories(storiesRes.data.stories || []);
      setSeriesHistory(historyRes.data.series || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getCost = () => {
    const priceKey = `${episodeCount}_EPISODES`;
    return pricing.pricing?.[priceKey] || 12;
  };

  const canAfford = wallet.availableCredits >= getCost();

  const handleAddCharacter = () => {
    if (characterNames.length < 5) {
      setCharacterNames([...characterNames, '']);
    }
  };

  const handleCharacterChange = (index, value) => {
    const updated = [...characterNames];
    updated[index] = value;
    setCharacterNames(updated);
  };

  const handleStorySelect = (storyId) => {
    setSelectedStoryId(storyId);
    const story = userStories.find(s => s.id === storyId);
    if (story) {
      setStorySummary(story.synopsis || '');
      setTheme(story.theme || 'Adventure');
      if (story.characters?.length) {
        setCharacterNames(story.characters.slice(0, 5));
      }
    }
  };

  const handleGenerate = async () => {
    if (!storySummary.trim() && !selectedStoryId) {
      toast.error('Please provide a story summary or select an existing story');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${getCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);

    try {
      const response = await api.post('/api/story-series/generate', {
        storyId: selectedStoryId || null,
        storySummary: storySummary.trim(),
        characterNames: characterNames.filter(c => c.trim()),
        targetAgeGroup: targetAge,
        theme,
        episodeCount
      });

      if (response.data.success) {
        setGeneratedSeries(response.data);
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success(`Series generated! ${response.data.episodeCount} episodes created.`);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!generatedSeries) return;
    
    // Create simple text export
    let content = `# ${generatedSeries.episodes?.[0]?.title?.split(':')[0] || 'Story'} Series\n\n`;
    content += `Theme: ${theme}\nEpisodes: ${episodeCount}\n\n`;
    
    generatedSeries.episodes?.forEach(ep => {
      content += `## ${ep.title}\n`;
      content += `Arc Stage: ${ep.arcStage}\n\n`;
      content += `Scene Beats:\n`;
      ep.sceneBeats?.forEach((beat, i) => {
        content += `${i + 1}. ${beat}\n`;
      });
      content += `\nCliffhanger: ${ep.cliffhanger}\n`;
      if (ep.nextEpisodeHook) {
        content += `Next Episode Hook: ${ep.nextEpisodeHook}\n`;
      }
      content += '\n---\n\n';
    });
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'story-series-outline.txt';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Outline downloaded!');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Film className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Story Series Mode</h1>
                  <p className="text-xs text-slate-400">Turn stories into multi-episode series</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Wallet className="w-4 h-4 text-purple-400" />
                <span className="font-bold text-white">{wallet.availableCredits}</span>
                <span className="text-xs text-slate-500">credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input Form */}
          <div className="space-y-6">
            {/* Source Story */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-purple-400" />
                Source Story
              </h3>
              
              {userStories.length > 0 && (
                <div className="mb-4">
                  <label className="text-xs text-slate-400 mb-2 block">Select Existing Story</label>
                  <Select value={selectedStoryId} onValueChange={handleStorySelect}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue placeholder="Choose a story..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">New Story</SelectItem>
                      {userStories.map(story => (
                        <SelectItem key={story.id} value={story.id}>
                          {story.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Story Summary</label>
                <textarea
                  value={storySummary}
                  onChange={(e) => setStorySummary(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm min-h-[100px]"
                  placeholder="Describe your story's main plot, characters, and setting..."
                  maxLength={1000}
                />
                <p className="text-xs text-slate-500 mt-1">{storySummary.length}/1000</p>
              </div>
            </div>

            {/* Characters */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Users className="w-4 h-4 text-pink-400" />
                Characters
              </h3>
              
              {characterNames.map((name, idx) => (
                <input
                  key={idx}
                  type="text"
                  value={name}
                  onChange={(e) => handleCharacterChange(idx, e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm mb-2"
                  placeholder={`Character ${idx + 1} name`}
                  maxLength={50}
                />
              ))}
              
              {characterNames.length < 5 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAddCharacter}
                  className="border-slate-600 text-slate-400"
                >
                  <Plus className="w-4 h-4 mr-1" /> Add Character
                </Button>
              )}
            </div>

            {/* Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Series Settings</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 mb-2 block">Theme</label>
                  <Select value={theme} onValueChange={setTheme}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {themes.map(t => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <label className="text-xs text-slate-400 mb-2 block">Age Group</label>
                  <Select value={targetAge} onValueChange={setTargetAge}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2-4">2-4 years</SelectItem>
                      <SelectItem value="4-7">4-7 years</SelectItem>
                      <SelectItem value="7-10">7-10 years</SelectItem>
                      <SelectItem value="10+">10+ years</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="col-span-2">
                  <label className="text-xs text-slate-400 mb-2 block">Episodes</label>
                  <div className="flex gap-2">
                    {[3, 5, 7].map(num => (
                      <button
                        key={num}
                        onClick={() => setEpisodeCount(num)}
                        className={`flex-1 py-3 rounded-lg text-sm font-medium transition-all ${
                          episodeCount === num
                            ? 'bg-purple-500 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        {num} Episodes
                        <span className="block text-xs opacity-70">
                          {pricing.pricing?.[`${num}_EPISODES`] || 0} credits
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Cost & Generate */}
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-medium text-purple-300">Total Cost</p>
                  <p className="text-xs text-purple-400">{episodeCount} episodes bundle</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">{getCost()}</p>
                  <p className="text-xs text-slate-400">credits</p>
                </div>
              </div>
              
              <Button
                onClick={handleGenerate}
                disabled={generating || !canAfford}
                className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                data-testid="generate-series-btn"
              >
                {generating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating Series...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Generate {episodeCount}-Episode Series
                  </span>
                )}
              </Button>
              
              {!canAfford && (
                <p className="text-xs text-red-400 text-center mt-2">
                  Insufficient credits. <Link to="/app/billing" className="underline">Buy more</Link>
                </p>
              )}
            </div>
          </div>

          {/* Right: Results */}
          <div className="space-y-6">
            {generatedSeries ? (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    Series Generated!
                  </h3>
                  <Button size="sm" onClick={handleDownloadPDF} className="bg-green-600 hover:bg-green-700">
                    <Download className="w-4 h-4 mr-1" /> Download
                  </Button>
                </div>
                
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {generatedSeries.episodes?.map((ep, idx) => (
                    <div key={idx} className="bg-slate-800/50 rounded-lg p-4">
                      <h4 className="font-semibold text-white mb-1">{ep.title}</h4>
                      <p className="text-xs text-purple-400 mb-3">Arc: {ep.arcStage}</p>
                      
                      <div className="space-y-1 mb-3">
                        {ep.sceneBeats?.slice(0, 4).map((beat, i) => (
                          <p key={i} className="text-xs text-slate-400">• {beat}</p>
                        ))}
                        {ep.sceneBeats?.length > 4 && (
                          <p className="text-xs text-slate-500">...and {ep.sceneBeats.length - 4} more beats</p>
                        )}
                      </div>
                      
                      {ep.cliffhanger && (
                        <p className="text-xs text-pink-400 italic">"{ep.cliffhanger}"</p>
                      )}
                    </div>
                  ))}
                </div>
                
                <p className="text-xs text-slate-500 text-center mt-4">
                  Generated content is template-based and should be reviewed before use.
                </p>
              </div>
            ) : (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center">
                <Film className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Your Series Will Appear Here</h3>
                <p className="text-sm text-slate-400">
                  Configure your settings and generate a multi-episode series
                </p>
              </div>
            )}

            {/* Recent History */}
            {seriesHistory.length > 0 && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-white mb-4">Recent Series</h3>
                <div className="space-y-2">
                  {seriesHistory.slice(0, 3).map(series => (
                    <div key={series.id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                      <div>
                        <p className="text-sm text-white">{series.theme} Series</p>
                        <p className="text-xs text-slate-500">{series.episodeCount} episodes</p>
                      </div>
                      <span className="text-xs text-slate-400">
                        {new Date(series.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
