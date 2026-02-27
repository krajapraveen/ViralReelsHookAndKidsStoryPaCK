import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';
import {
  Calendar, ArrowLeft, Loader2, Download, Sparkles,
  Wallet, Target, Clock, Megaphone, Hash, FileText,
  CheckCircle, Instagram, Youtube, ChevronRight
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';

export default function ChallengeGenerator() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [niches, setNiches] = useState({});
  const [platforms, setPlatforms] = useState({});
  const [goals, setGoals] = useState({});
  
  // Form state
  const [challengeType, setChallengeType] = useState('7_day');
  const [niche, setNiche] = useState('motivation');
  const [platform, setPlatform] = useState('instagram');
  const [goal, setGoal] = useState('followers');
  const [timePerDay, setTimePerDay] = useState(10);
  
  // Result state
  const [generatedChallenge, setGeneratedChallenge] = useState(null);
  const [activeDay, setActiveDay] = useState(1);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [walletRes, pricingRes, nichesRes, platformsRes, goalsRes] = await Promise.all([
        walletAPI.getWallet(),
        api.get('/api/challenge-generator/pricing'),
        api.get('/api/challenge-generator/niches'),
        api.get('/api/challenge-generator/platforms'),
        api.get('/api/challenge-generator/goals')
      ]);
      
      setWallet(walletRes.data);
      setPricing(pricingRes.data);
      setNiches(nichesRes.data.niches || {});
      setPlatforms(platformsRes.data.platforms || {});
      setGoals(goalsRes.data.goals || {});
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getCost = () => {
    const priceKey = challengeType === '30_day' ? '30_DAY' : '7_DAY';
    return pricing.pricing?.[priceKey] || 6;
  };

  const getDays = () => challengeType === '30_day' ? 30 : 7;
  const canAfford = wallet.availableCredits >= getCost();

  const handleGenerate = async () => {
    if (!canAfford) {
      toast.error(`Need ${getCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);

    try {
      const response = await api.post('/api/challenge-generator/generate', {
        challengeType,
        niche,
        platform,
        goal,
        timePerDay
      });

      if (response.data.success) {
        setGeneratedChallenge(response.data);
        setActiveDay(1);
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success(`${getDays()}-Day Challenge created!`);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadCSV = () => {
    if (!generatedChallenge) return;
    
    let csv = 'Day,Theme,Content Type,Hook,CTA,Posting Time,Hashtags\n';
    
    generatedChallenge.dailyPlans?.forEach(day => {
      csv += `${day.day},${day.theme},"${day.contentType}","${day.hook}","${day.callToAction}",${day.postingTime},"${day.hashtags?.join(' ')}"\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${getDays()}-day-challenge.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Calendar downloaded!');
  };

  const getPlatformIcon = () => {
    switch (platform) {
      case 'instagram': return <Instagram className="w-4 h-4" />;
      case 'youtube': return <Youtube className="w-4 h-4" />;
      default: return <Megaphone className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Challenge Generator</h1>
                  <p className="text-xs text-slate-400">Create trending content challenges</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Wallet className="w-4 h-4 text-orange-400" />
                <span className="font-bold text-white">{wallet.availableCredits}</span>
                <span className="text-xs text-slate-500">credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left: Settings */}
          <div className="space-y-6">
            {/* Challenge Type */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Challenge Duration</h3>
              <div className="grid grid-cols-2 gap-3">
                {['7_day', '30_day'].map(type => (
                  <button
                    key={type}
                    onClick={() => setChallengeType(type)}
                    className={`p-4 rounded-lg border text-center transition-all ${
                      challengeType === type
                        ? 'border-orange-500 bg-orange-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <Calendar className="w-6 h-6 mx-auto mb-2 text-orange-400" />
                    <p className="text-sm font-medium text-white">
                      {type === '7_day' ? '7 Days' : '30 Days'}
                    </p>
                    <p className="text-xs text-orange-400">
                      {pricing.pricing?.[type === '7_day' ? '7_DAY' : '30_DAY']} credits
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Niche & Platform */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-4">
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Content Niche</label>
                <Select value={niche} onValueChange={setNiche}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(niches).map(n => (
                      <SelectItem key={n} value={n}>
                        {n.charAt(0).toUpperCase() + n.slice(1).replace('_', ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Platform</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(platforms).map(p => (
                      <SelectItem key={p} value={p}>
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Goal</label>
                <Select value={goal} onValueChange={setGoal}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(goals).map(g => (
                      <SelectItem key={g} value={g}>
                        {g.charAt(0).toUpperCase() + g.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Time per Day: {timePerDay} min</label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="5"
                  value={timePerDay}
                  onChange={(e) => setTimePerDay(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-slate-500">
                  <span>5 min</span>
                  <span>60 min</span>
                </div>
              </div>
            </div>

            {/* Generate Button */}
            <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-medium text-orange-300">Total Cost</p>
                  <p className="text-xs text-orange-400">{getDays()}-day challenge pack</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">{getCost()}</p>
                  <p className="text-xs text-slate-400">credits</p>
                </div>
              </div>
              
              <Button
                onClick={handleGenerate}
                disabled={generating || !canAfford}
                className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                data-testid="generate-challenge-btn"
              >
                {generating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating Challenge...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Generate {getDays()}-Day Challenge
                  </span>
                )}
              </Button>
            </div>
          </div>

          {/* Center & Right: Results */}
          <div className="lg:col-span-2 space-y-6">
            {generatedChallenge ? (
              <>
                {/* Header & Download */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-green-400" />
                        Your {getDays()}-Day Challenge
                      </h3>
                      <p className="text-sm text-slate-400">
                        {niche.replace('_', ' ')} • {platform} • {goal}
                      </p>
                    </div>
                    <Button onClick={handleDownloadCSV} className="bg-green-600 hover:bg-green-700">
                      <Download className="w-4 h-4 mr-1" /> CSV Calendar
                    </Button>
                  </div>
                  
                  {/* Strategy Info */}
                  <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
                    <p className="text-xs text-orange-400 font-medium mb-1">
                      Strategy Focus: {generatedChallenge.goalStrategy?.focus}
                    </p>
                    <p className="text-xs text-slate-400">
                      {generatedChallenge.goalStrategy?.tip}
                    </p>
                  </div>
                </div>

                {/* Day Selector */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {generatedChallenge.dailyPlans?.map((day, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveDay(day.day)}
                        className={`flex-shrink-0 w-12 h-12 rounded-lg text-sm font-medium transition-all ${
                          activeDay === day.day
                            ? 'bg-orange-500 text-white'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        {day.day}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Active Day Details */}
                {generatedChallenge.dailyPlans?.[activeDay - 1] && (
                  <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded">
                        DAY {activeDay}
                      </span>
                      <span className="text-sm text-slate-400">
                        {generatedChallenge.dailyPlans[activeDay - 1].theme}
                      </span>
                    </div>
                    
                    <div className="space-y-4">
                      {/* Content Type & Time */}
                      <div className="flex gap-4">
                        <div className="flex items-center gap-2 text-slate-400">
                          {getPlatformIcon()}
                          <span className="text-sm">{generatedChallenge.dailyPlans[activeDay - 1].contentType}</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-400">
                          <Clock className="w-4 h-4" />
                          <span className="text-sm">{generatedChallenge.dailyPlans[activeDay - 1].postingTime}</span>
                        </div>
                      </div>
                      
                      {/* Hook */}
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <p className="text-xs text-orange-400 font-medium mb-2">HOOK</p>
                        <p className="text-white">{generatedChallenge.dailyPlans[activeDay - 1].hook}</p>
                      </div>
                      
                      {/* CTA */}
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <p className="text-xs text-green-400 font-medium mb-2">CALL TO ACTION</p>
                        <p className="text-white">{generatedChallenge.dailyPlans[activeDay - 1].callToAction}</p>
                      </div>
                      
                      {/* Hashtags */}
                      <div className="bg-slate-800/50 rounded-lg p-4">
                        <p className="text-xs text-blue-400 font-medium mb-2 flex items-center gap-1">
                          <Hash className="w-3 h-3" /> HASHTAGS
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {generatedChallenge.dailyPlans[activeDay - 1].hashtags?.map((tag, i) => (
                            <span key={i} className="text-sm text-blue-400 bg-blue-500/10 px-2 py-1 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      {/* Tips */}
                      <div className="text-xs text-slate-500">
                        <p className="font-medium mb-1">Tips:</p>
                        <ul className="space-y-1">
                          {generatedChallenge.dailyPlans[activeDay - 1].tips?.map((tip, i) => (
                            <li key={i}>• {tip}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
                
                <p className="text-xs text-slate-500 text-center">
                  Generated content is template-based and should be reviewed before posting.
                </p>
              </>
            ) : (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
                <Calendar className="w-20 h-20 text-slate-700 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Your Challenge Calendar</h3>
                <p className="text-slate-400 max-w-md mx-auto">
                  Configure your niche, platform, and goal to generate a complete
                  day-by-day content challenge with hooks, CTAs, and hashtags.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
      
      {/* Help Guide */}
      <HelpGuide pageId="challenge-generator" />
    </div>
  );
}
