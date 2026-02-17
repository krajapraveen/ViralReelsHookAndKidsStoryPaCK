import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { 
  Sparkles, Zap, Target, TrendingUp, FileText, Calendar,
  Hash, MessageSquare, BarChart2, RefreshCw, Share2, Clock,
  ChevronRight, Star, Flame, Award
} from 'lucide-react';

const TOOLS = [
  { id: 'hook-analyzer', name: 'Hook Analyzer', icon: <Target className="w-5 h-5" />, cost: 2, description: 'Analyze hooks for virality factors' },
  { id: 'swipe-file', name: 'Viral Swipe File', icon: <Flame className="w-5 h-5" />, cost: 3, description: 'Access viral hook database' },
  { id: 'bio-generator', name: 'Bio Generator', icon: <FileText className="w-5 h-5" />, cost: 3, description: 'Generate optimized social bios' },
  { id: 'caption-generator', name: 'Caption Generator', icon: <MessageSquare className="w-5 h-5" />, cost: 2, description: 'Create engaging captions' },
  { id: 'viral-score', name: 'Viral Score', icon: <TrendingUp className="w-5 h-5" />, cost: 1, description: 'Calculate virality potential' },
  { id: 'headline-generator', name: 'Headline Generator', icon: <Zap className="w-5 h-5" />, cost: 2, description: 'Create attention-grabbing headlines' },
  { id: 'thread-generator', name: 'Thread Generator', icon: <Hash className="w-5 h-5" />, cost: 5, description: 'Structure viral threads' },
  { id: 'posting-schedule', name: 'Posting Schedule', icon: <Calendar className="w-5 h-5" />, cost: 2, description: 'Optimize posting times' },
  { id: 'content-repurpose', name: 'Content Repurposing', icon: <RefreshCw className="w-5 h-5" />, cost: 5, description: 'Convert to multiple formats' },
  { id: 'poll-generator', name: 'Poll Generator', icon: <BarChart2 className="w-5 h-5" />, cost: 1, description: 'Create engaging polls' },
  { id: 'story-templates', name: 'Story Templates', icon: <Share2 className="w-5 h-5" />, cost: 2, description: 'Get IG/TikTok story templates' },
  { id: 'consistency-tracker', name: 'Consistency Tracker', icon: <Clock className="w-5 h-5" />, cost: 1, description: 'Track posting consistency' },
];

export default function CreatorProTools() {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(0);
  const [activeTool, setActiveTool] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  // Form states
  const [hookInput, setHookInput] = useState('');
  const [nicheInput, setNicheInput] = useState('general');
  const [topicInput, setTopicInput] = useState('');
  const [platformInput, setPlatformInput] = useState('instagram');
  const [contentInput, setContentInput] = useState('');

  // Helper function to extract error message
  const getErrorMessage = (error, defaultMsg = 'Operation failed') => {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(d => d.msg || d).join(', ');
    return defaultMsg;
  };

  useEffect(() => {
    fetchCredits();
  }, []);

  const fetchCredits = async () => {
    try {
      const res = await api.get('/api/credits/balance');
      setCredits(res.data.credits || 0);
    } catch (error) {
      console.error('Failed to fetch credits:', error);
    }
  };

  const analyzeHook = async () => {
    if (!hookInput.trim()) {
      toast.error('Please enter a hook to analyze');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('hook', hookInput);
      formData.append('niche', nicheInput);
      
      const res = await api.post('/api/creator-pro/hook-analyzer', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Hook analyzed!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Analysis failed'));
    } finally {
      setLoading(false);
    }
  };

  const getSwipeFile = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/creator-pro/swipe-file/${nicheInput}?limit=10`);
      setResult(res.data);
      fetchCredits();
      toast.success('Swipe file loaded!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load swipe file'));
    } finally {
      setLoading(false);
    }
  };

  const generateBio = async () => {
    if (!topicInput.trim()) {
      toast.error('Please enter your profession');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('profession', topicInput);
      formData.append('platform', platformInput);
      formData.append('tone', 'professional');
      
      const res = await api.post('/api/creator-pro/bio-generator', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Bios generated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const generateCaption = async () => {
    if (!topicInput.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('topic', topicInput);
      formData.append('platform', platformInput);
      formData.append('tone', 'engaging');
      
      const res = await api.post('/api/creator-pro/caption-generator', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Captions generated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const calculateViralScore = async () => {
    if (!hookInput.trim()) {
      toast.error('Please enter a hook');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('hook', hookInput);
      formData.append('caption', contentInput);
      formData.append('hashtags', '#viral #trending');
      
      const res = await api.post('/api/creator-pro/viral-score', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Score calculated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Calculation failed'));
    } finally {
      setLoading(false);
    }
  };

  const generateHeadlines = async () => {
    if (!topicInput.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('topic', topicInput);
      formData.append('style', 'all');
      formData.append('count', '5');
      
      const res = await api.post('/api/creator-pro/headline-generator', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Headlines generated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const generateThread = async () => {
    if (!topicInput.trim()) {
      toast.error('Please enter a topic');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('topic', topicInput);
      formData.append('points', '7');
      formData.append('platform', 'twitter');
      
      const res = await api.post('/api/creator-pro/thread-generator', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Thread generated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const getPostingSchedule = async () => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('platform', platformInput);
      formData.append('content_frequency', 'daily');
      
      const res = await api.post('/api/creator-pro/posting-schedule', formData);
      setResult(res.data);
      fetchCredits();
      toast.success('Schedule generated!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const renderToolForm = () => {
    if (!activeTool) return null;

    switch (activeTool) {
      case 'hook-analyzer':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Your Hook</label>
              <Textarea
                value={hookInput}
                onChange={(e) => setHookInput(e.target.value)}
                placeholder="Enter your hook to analyze..."
                className="bg-slate-700 border-slate-600 text-white"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Niche</label>
              <select 
                value={nicheInput} 
                onChange={(e) => setNicheInput(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="general">General</option>
                <option value="fitness">Fitness</option>
                <option value="business">Business</option>
                <option value="relationships">Relationships</option>
                <option value="motivation">Motivation</option>
                <option value="lifestyle">Lifestyle</option>
              </select>
            </div>
            <Button onClick={analyzeHook} disabled={loading} className="w-full bg-purple-600 hover:bg-purple-700">
              {loading ? 'Analyzing...' : 'Analyze Hook (2 credits)'}
            </Button>
          </div>
        );

      case 'swipe-file':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Niche</label>
              <select 
                value={nicheInput} 
                onChange={(e) => setNicheInput(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="general">General</option>
                <option value="fitness">Fitness</option>
                <option value="business">Business</option>
                <option value="relationships">Relationships</option>
                <option value="motivation">Motivation</option>
                <option value="lifestyle">Lifestyle</option>
              </select>
            </div>
            <Button onClick={getSwipeFile} disabled={loading} className="w-full bg-purple-600 hover:bg-purple-700">
              {loading ? 'Loading...' : 'Get Viral Hooks (3 credits)'}
            </Button>
          </div>
        );

      case 'bio-generator':
      case 'caption-generator':
      case 'headline-generator':
      case 'thread-generator':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                {activeTool === 'bio-generator' ? 'Profession' : 'Topic'}
              </label>
              <Input
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder={activeTool === 'bio-generator' ? 'e.g., Digital Marketer' : 'e.g., Productivity tips'}
                className="bg-slate-700 border-slate-600 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Platform</label>
              <select 
                value={platformInput} 
                onChange={(e) => setPlatformInput(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="instagram">Instagram</option>
                <option value="twitter">Twitter/X</option>
                <option value="tiktok">TikTok</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </div>
            <Button 
              onClick={
                activeTool === 'bio-generator' ? generateBio :
                activeTool === 'caption-generator' ? generateCaption :
                activeTool === 'headline-generator' ? generateHeadlines :
                generateThread
              } 
              disabled={loading} 
              className="w-full bg-purple-600 hover:bg-purple-700"
            >
              {loading ? 'Generating...' : `Generate (${TOOLS.find(t => t.id === activeTool)?.cost || 2} credits)`}
            </Button>
          </div>
        );

      case 'viral-score':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Hook</label>
              <Input
                value={hookInput}
                onChange={(e) => setHookInput(e.target.value)}
                placeholder="Your hook..."
                className="bg-slate-700 border-slate-600 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Caption (optional)</label>
              <Textarea
                value={contentInput}
                onChange={(e) => setContentInput(e.target.value)}
                placeholder="Your caption..."
                className="bg-slate-700 border-slate-600 text-white"
                rows={2}
              />
            </div>
            <Button onClick={calculateViralScore} disabled={loading} className="w-full bg-purple-600 hover:bg-purple-700">
              {loading ? 'Calculating...' : 'Calculate Score (1 credit)'}
            </Button>
          </div>
        );

      case 'posting-schedule':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Platform</label>
              <select 
                value={platformInput} 
                onChange={(e) => setPlatformInput(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="twitter">Twitter/X</option>
                <option value="linkedin">LinkedIn</option>
                <option value="youtube">YouTube</option>
              </select>
            </div>
            <Button onClick={getPostingSchedule} disabled={loading} className="w-full bg-purple-600 hover:bg-purple-700">
              {loading ? 'Generating...' : 'Get Schedule (2 credits)'}
            </Button>
          </div>
        );

      default:
        return (
          <div className="text-center text-slate-400 py-8">
            <p>This tool is coming soon!</p>
          </div>
        );
    }
  };

  const renderResult = () => {
    if (!result) return null;

    return (
      <div className="mt-6 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Results</h3>
        
        {/* Hook Analysis Result */}
        {result.analysis && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold text-white">{result.analysis.totalScore}/100</span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                result.analysis.color === 'green' ? 'bg-green-500/20 text-green-400' :
                result.analysis.color === 'blue' ? 'bg-blue-500/20 text-blue-400' :
                result.analysis.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-orange-500/20 text-orange-400'
              }`}>
                {result.analysis.rating}
              </span>
            </div>
            {result.analysis.improvements && result.analysis.improvements.length > 0 && (
              <div>
                <p className="text-sm text-slate-400 mb-2">Improvements:</p>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.analysis.improvements.map((imp, i) => (
                    <li key={i}>{imp}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Swipe File Result */}
        {result.hooks && (
          <div className="space-y-3">
            {result.hooks.map((hook, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-white font-medium">{hook.hook}</p>
                <div className="flex gap-4 mt-2 text-sm text-slate-400">
                  <span>👁 {hook.views}</span>
                  <span>💬 {hook.engagement}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Bio Generator Result */}
        {result.bios && (
          <div className="space-y-3">
            {result.bios.map((bio, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-white">{bio.bio}</p>
                <p className="text-xs text-slate-400 mt-1">{bio.charCount} characters</p>
              </div>
            ))}
          </div>
        )}

        {/* Caption Generator Result */}
        {result.captions && (
          <div className="space-y-3">
            {result.captions.map((cap, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-white whitespace-pre-wrap">{cap.caption}</p>
              </div>
            ))}
          </div>
        )}

        {/* Viral Score Result */}
        {result.totalScore !== undefined && result.tier && (
          <div className="text-center">
            <p className="text-4xl font-bold text-white mb-2">{result.totalScore}</p>
            <p className="text-xl text-purple-400">{result.tier}</p>
          </div>
        )}

        {/* Headlines Result */}
        {result.headlines && (
          <div className="space-y-4">
            {Object.entries(result.headlines).map(([style, headlines]) => (
              <div key={style}>
                <p className="text-sm font-medium text-purple-400 mb-2 capitalize">{style}</p>
                {headlines.map((h, i) => (
                  <p key={i} className="text-white p-2 bg-slate-700/50 rounded mb-1">{h}</p>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Thread Result */}
        {result.thread && (
          <div className="space-y-2">
            {result.thread.tweets.map((tweet, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <p className="text-xs text-purple-400 mb-1">Tweet {tweet.number}</p>
                <p className="text-white">{tweet.template}</p>
              </div>
            ))}
          </div>
        )}

        {/* Schedule Result */}
        {result.schedule && (
          <div className="space-y-2">
            {result.schedule.map((day, i) => (
              <div key={i} className={`p-3 rounded-lg flex justify-between items-center ${
                day.isOptimalDay ? 'bg-green-500/10 border border-green-500/20' : 'bg-slate-700/50'
              }`}>
                <span className="text-white font-medium">{day.day}</span>
                <span className="text-slate-300">{day.postTime || 'No post'}</span>
                {day.isOptimalDay && <span className="text-green-400 text-xs">Best day</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Award className="w-8 h-8 text-yellow-500" />
              Creator Pro Tools
            </h1>
            <p className="text-slate-400 mt-1">15+ Advanced tools for content creators</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-400">Your Credits</p>
            <p className="text-2xl font-bold text-purple-400">{credits}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Tools List */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
              <h2 className="text-lg font-semibold mb-4">Available Tools</h2>
              <div className="space-y-2">
                {TOOLS.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => { setActiveTool(tool.id); setResult(null); }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-all ${
                      activeTool === tool.id 
                        ? 'bg-purple-600 text-white' 
                        : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {tool.icon}
                      <span className="font-medium">{tool.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 bg-slate-600/50 rounded">{tool.cost} cr</span>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Tool Interface */}
          <div className="lg:col-span-2">
            {activeTool ? (
              <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
                <div className="flex items-center gap-3 mb-6">
                  {TOOLS.find(t => t.id === activeTool)?.icon}
                  <div>
                    <h2 className="text-xl font-semibold">{TOOLS.find(t => t.id === activeTool)?.name}</h2>
                    <p className="text-sm text-slate-400">{TOOLS.find(t => t.id === activeTool)?.description}</p>
                  </div>
                </div>
                
                {renderToolForm()}
                {renderResult()}
              </div>
            ) : (
              <div className="bg-slate-800/50 rounded-xl p-12 border border-slate-700 text-center">
                <Sparkles className="w-16 h-16 text-purple-500 mx-auto mb-4" />
                <h2 className="text-2xl font-semibold mb-2">Select a Tool</h2>
                <p className="text-slate-400">Choose from 15+ professional tools to supercharge your content creation</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
