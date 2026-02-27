import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  Calendar, ArrowLeft, Loader2, Download, Sparkles,
  Wallet, CheckCircle, ChevronRight, Lock,
  Instagram, Youtube, Linkedin, Baby, Briefcase,
  Users, DollarSign, MessageCircle, TrendingUp,
  AlertTriangle, Clock, Hash, Eye, X
} from 'lucide-react';
import api, { walletAPI } from '../utils/api';

const PLATFORMS = [
  { id: 'instagram', name: 'Instagram', icon: Instagram, color: 'from-pink-500 to-purple-500' },
  { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'from-red-500 to-red-600' },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'from-blue-600 to-blue-700' },
  { id: 'kids_channel', name: 'Kids Channel', icon: Baby, color: 'from-green-400 to-teal-500' },
  { id: 'business', name: 'Business', icon: Briefcase, color: 'from-slate-500 to-slate-600' }
];

const DURATIONS = [
  { days: 7, credits: 10, label: '7 Days', description: 'Quick sprint' },
  { days: 14, credits: 18, label: '14 Days', description: 'Standard plan', popular: true },
  { days: 30, credits: 30, label: '30 Days', description: 'Full month' }
];

const GOALS = [
  { id: 'followers', name: 'Followers', icon: Users, description: 'Grow your audience' },
  { id: 'sales', name: 'Sales', icon: DollarSign, description: 'Convert to customers' },
  { id: 'engagement', name: 'Engagement', icon: MessageCircle, description: 'Build community' },
  { id: 'brand_growth', name: 'Brand Growth', icon: TrendingUp, description: 'Increase awareness' }
];

export default function ContentChallengePlanner() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [userPlan, setUserPlan] = useState('free');
  
  // Wizard state
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState('');
  const [duration, setDuration] = useState(14);
  const [goal, setGoal] = useState('');
  
  // Result state
  const [result, setResult] = useState(null);
  const [activeDay, setActiveDay] = useState(1);
  
  // Preview Mode state
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const walletRes = await walletAPI.getWallet();
      setWallet(walletRes.data);
      setUserPlan(walletRes.data.plan || 'free');
    } catch (error) {
      console.error('Failed to load wallet:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleShowPreview = async () => {
    setLoadingPreview(true);
    try {
      const response = await api.get('/api/content-challenge-planner/preview');
      setPreviewData(response.data);
      setShowPreview(true);
    } catch (error) {
      toast.error('Failed to load preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  const getCost = () => {
    const option = DURATIONS.find(d => d.days === duration);
    return option?.credits || 18;
  };

  const canAfford = wallet.availableCredits >= getCost();

  const handleGenerate = async () => {
    if (!platform || !goal) {
      toast.error('Please complete all steps');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${getCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);

    try {
      const response = await api.post('/api/content-challenge-planner/generate', {
        platform,
        duration,
        goal
      });

      if (response.data.success) {
        setResult(response.data);
        setActiveDay(1);
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success(response.data.message);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    
    let content = `# ${duration}-Day Content Challenge\n\n`;
    content += `Platform: ${result.platform}\n`;
    content += `Goal: ${result.goal}\n\n`;
    
    result.daily_plans?.forEach(day => {
      content += `## Day ${day.day}\n\n`;
      content += `**Hook:** ${day.hook}\n\n`;
      content += `**Content Idea:** ${day.content_idea}\n\n`;
      content += `**Caption:** ${day.caption}\n\n`;
      content += `**CTA:** ${day.cta}\n\n`;
      content += `**Hashtags:** ${day.hashtags?.join(' ')}\n\n`;
      content += `**Best Time:** ${day.posting_time}\n\n`;
      content += '---\n\n';
    });
    
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${duration}-day-content-plan.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Plan downloaded!');
  };

  const renderStep1 = () => (
    <div className="space-y-6" data-testid="step-1-platform">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-orange-500/20 text-orange-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold">1</span>
          Step 1 of 4
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Platform</h2>
        <p className="text-slate-400">Select where you'll be posting</p>
      </div>

      <div className="grid gap-3">
        {PLATFORMS.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.id}
              onClick={() => setPlatform(p.id)}
              className={`p-5 rounded-xl border-2 transition-all flex items-center gap-4 ${
                platform === p.id
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
              }`}
              data-testid={`platform-${p.id}`}
            >
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${p.color} flex items-center justify-center`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <span className="text-lg font-medium text-white">{p.name}</span>
              {platform === p.id && (
                <CheckCircle className="w-5 h-5 text-orange-400 ml-auto" />
              )}
            </button>
          );
        })}
      </div>

      {/* Preview Button */}
      <button
        onClick={handleShowPreview}
        disabled={loadingPreview}
        className="w-full py-4 rounded-xl border-2 border-dashed border-orange-500/50 text-orange-300 hover:bg-orange-500/10 transition-all flex items-center justify-center gap-2"
        data-testid="preview-btn"
      >
        {loadingPreview ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Eye className="w-5 h-5" />
        )}
        <span className="font-medium">See Example Plan (FREE)</span>
      </button>

      <Button
        onClick={() => setStep(2)}
        disabled={!platform}
        className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 py-6 text-lg"
        data-testid="next-step-btn"
      >
        Continue <ChevronRight className="w-5 h-5 ml-2" />
      </Button>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6" data-testid="step-2-duration">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-orange-500/20 text-orange-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold">2</span>
          Step 2 of 4
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Duration</h2>
        <p className="text-slate-400">How long is your content challenge?</p>
      </div>

      <div className="grid gap-4">
        {DURATIONS.map((d) => (
          <button
            key={d.days}
            onClick={() => setDuration(d.days)}
            className={`relative p-6 rounded-xl border-2 transition-all text-left ${
              duration === d.days
                ? 'border-orange-500 bg-orange-500/10'
                : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
            }`}
            data-testid={`duration-${d.days}`}
          >
            {d.popular && (
              <span className="absolute top-3 right-3 bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded">
                POPULAR
              </span>
            )}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white">{d.label}</h3>
                <p className="text-sm text-slate-400 mt-1">{d.description}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-orange-400">{d.credits}</p>
                <p className="text-xs text-slate-500">credits</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-3">
        <Button onClick={() => setStep(1)} variant="outline" className="flex-1 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button
          onClick={() => setStep(3)}
          className="flex-1 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
          data-testid="next-step-btn"
        >
          Continue <ChevronRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6" data-testid="step-3-goal">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-orange-500/20 text-orange-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold">3</span>
          Step 3 of 4
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Goal</h2>
        <p className="text-slate-400">What do you want to achieve?</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {GOALS.map((g) => {
          const Icon = g.icon;
          return (
            <button
              key={g.id}
              onClick={() => setGoal(g.id)}
              className={`p-5 rounded-xl border-2 transition-all text-center ${
                goal === g.id
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
              }`}
              data-testid={`goal-${g.id}`}
            >
              <Icon className={`w-8 h-8 mx-auto mb-3 ${goal === g.id ? 'text-orange-400' : 'text-slate-400'}`} />
              <h3 className="text-white font-medium">{g.name}</h3>
              <p className="text-xs text-slate-400 mt-1">{g.description}</p>
            </button>
          );
        })}
      </div>

      <div className="flex gap-3">
        <Button onClick={() => setStep(2)} variant="outline" className="flex-1 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button
          onClick={() => setStep(4)}
          disabled={!goal}
          className="flex-1 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
          data-testid="next-step-btn"
        >
          Continue <ChevronRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStep4 = () => {
    const selectedPlatform = PLATFORMS.find(p => p.id === platform);
    const selectedGoal = GOALS.find(g => g.id === goal);
    const PlatformIcon = selectedPlatform?.icon || Calendar;

    return (
      <div className="space-y-6" data-testid="step-4-generate">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-orange-500/20 text-orange-300 px-4 py-2 rounded-full text-sm mb-4">
            <span className="w-6 h-6 rounded-full bg-orange-500 text-white flex items-center justify-center text-xs font-bold">4</span>
            Step 4 of 4
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Generate Plan</h2>
          <p className="text-slate-400">Review and create your content plan</p>
        </div>

        {/* Summary */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Your Plan Summary</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <PlatformIcon className="w-6 h-6 mx-auto mb-2 text-orange-400" />
              <p className="text-sm text-white">{selectedPlatform?.name}</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <Calendar className="w-6 h-6 mx-auto mb-2 text-orange-400" />
              <p className="text-sm text-white">{duration} Days</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              {selectedGoal?.icon && <selectedGoal.icon className="w-6 h-6 mx-auto mb-2 text-orange-400" />}
              <p className="text-sm text-white">{selectedGoal?.name}</p>
            </div>
          </div>
        </div>

        {/* What You Get */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4">What You Get</h3>
          <div className="space-y-2">
            {[
              `${duration} days of content ideas`,
              'Hook for each day',
              'Caption templates',
              'Call-to-action suggestions',
              'Optimal posting times',
              'Relevant hashtags'
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm text-slate-300">{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pricing */}
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <span className="text-orange-300 font-semibold">Total Cost</span>
            <span className="text-2xl font-bold text-white">{getCost()} credits</span>
          </div>
          {userPlan === 'free' && (
            <p className="text-xs text-amber-400 mt-3 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Free preview includes watermark
            </p>
          )}
        </div>

        <div className="flex gap-3">
          <Button onClick={() => setStep(3)} variant="outline" className="flex-1 border-slate-600">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generating || !canAfford}
            className="flex-1 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 py-6"
            data-testid="generate-btn"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Creating Plan...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Generate Plan
              </span>
            )}
          </Button>
        </div>

        {!canAfford && (
          <p className="text-center text-red-400 text-sm">
            Insufficient credits. <Link to="/app/billing" className="underline">Buy more</Link>
          </p>
        )}
      </div>
    );
  };

  const renderResult = () => (
    <div className="space-y-6" data-testid="result-section">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 bg-green-500/20 text-green-300 px-4 py-2 rounded-full text-sm mb-4">
          <CheckCircle className="w-5 h-5" />
          Plan Ready!
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">{result.duration}-Day Content Plan</h2>
        <p className="text-slate-400">{result.platform} • {result.goal}</p>
      </div>

      <div className="flex gap-3 mb-6">
        <Button onClick={handleDownload} className="flex-1 bg-green-600 hover:bg-green-700">
          <Download className="w-4 h-4 mr-2" /> Download Plan
        </Button>
        <Button onClick={() => { setResult(null); setStep(1); setPlatform(''); setGoal(''); }} variant="outline" className="flex-1 border-slate-600">
          Create Another
        </Button>
      </div>

      {/* Day Selector */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {result.daily_plans?.map((day) => (
            <button
              key={day.day}
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

      {/* Active Day Content */}
      {result.daily_plans?.[activeDay - 1] && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-3">
            <span className="bg-orange-500 text-white text-sm font-bold px-3 py-1 rounded">
              DAY {activeDay}
            </span>
            <span className="text-slate-400 text-sm">{result.daily_plans[activeDay - 1].content_type}</span>
            <div className="ml-auto flex items-center gap-1 text-slate-400">
              <Clock className="w-4 h-4" />
              <span className="text-sm">{result.daily_plans[activeDay - 1].posting_time}</span>
            </div>
          </div>

          <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
            <p className="text-xs text-orange-400 font-medium mb-2">HOOK</p>
            <p className="text-white">{result.daily_plans[activeDay - 1].hook}</p>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-xs text-purple-400 font-medium mb-2">CONTENT IDEA</p>
            <p className="text-slate-200">{result.daily_plans[activeDay - 1].content_idea}</p>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-xs text-blue-400 font-medium mb-2">CAPTION</p>
            <p className="text-slate-200">{result.daily_plans[activeDay - 1].caption}</p>
          </div>

          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
            <p className="text-xs text-green-400 font-medium mb-2">CTA</p>
            <p className="text-green-200">{result.daily_plans[activeDay - 1].cta}</p>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-xs text-cyan-400 font-medium mb-2 flex items-center gap-1">
              <Hash className="w-3 h-3" /> HASHTAGS
            </p>
            <div className="flex flex-wrap gap-2">
              {result.daily_plans[activeDay - 1].hashtags?.map((tag, i) => (
                <span key={i} className="text-sm text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-orange-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4">
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
                  <h1 className="text-lg font-bold text-white">Content Challenge Planner</h1>
                  <p className="text-xs text-slate-400">Get a ready-to-post content plan in seconds</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
              <Wallet className="w-4 h-4 text-orange-400" />
              <span className="font-bold text-white">{wallet.availableCredits}</span>
              <span className="text-xs text-slate-500">credits</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        {result ? renderResult() : (
          <>
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            {step === 4 && renderStep4()}
          </>
        )}
      </main>
    </div>
  );
}
