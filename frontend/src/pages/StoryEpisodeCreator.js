import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  Film, ArrowLeft, Loader2, Download, Sparkles,
  Wallet, CheckCircle, Lock, ChevronRight, FileText,
  AlertTriangle, Eye, X
} from 'lucide-react';
import api, { walletAPI } from '../utils/api';

const EPISODE_OPTIONS = [
  { count: 3, credits: 15, label: '3 Episodes', description: 'Quick mini-series' },
  { count: 5, credits: 25, label: '5 Episodes', description: 'Standard series', popular: true },
  { count: 7, credits: 35, label: '7 Episodes', description: 'Extended adventure' }
];

export default function StoryEpisodeCreator() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [userPlan, setUserPlan] = useState('free');
  
  // Wizard state
  const [step, setStep] = useState(1);
  const [storyIdea, setStoryIdea] = useState('');
  const [episodeCount, setEpisodeCount] = useState(5);
  const [addOns, setAddOns] = useState([]);
  
  // Result state
  const [result, setResult] = useState(null);
  
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
      const response = await api.get('/api/story-episode-creator/preview');
      setPreviewData(response.data);
      setShowPreview(true);
    } catch (error) {
      toast.error('Failed to load preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  const getBaseCost = () => {
    const option = EPISODE_OPTIONS.find(o => o.count === episodeCount);
    return option?.credits || 25;
  };

  const getAddOnCost = () => {
    let cost = 0;
    if (addOns.includes('export_pdf')) cost += 10;
    if (addOns.includes('commercial_license')) cost += 15;
    return cost;
  };

  const getTotalCost = () => getBaseCost() + getAddOnCost();
  const canAfford = wallet.availableCredits >= getTotalCost();

  const toggleAddOn = (addon) => {
    setAddOns(prev => 
      prev.includes(addon) 
        ? prev.filter(a => a !== addon)
        : [...prev, addon]
    );
  };

  const handleGenerate = async () => {
    if (!storyIdea.trim() || storyIdea.length < 10) {
      toast.error('Please enter a story idea (at least 10 characters)');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${getTotalCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);

    try {
      const response = await api.post('/api/story-episode-creator/generate', {
        story_idea: storyIdea.trim(),
        episode_count: episodeCount,
        add_ons: addOns
      });

      if (response.data.success) {
        setResult(response.data);
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
    
    let content = `# ${result.hero_name}'s Story Series\n\n`;
    content += `Story Idea: ${storyIdea}\n`;
    content += `Episodes: ${result.episode_count}\n\n`;
    
    result.episodes?.forEach(ep => {
      content += `## ${ep.title}\n\n`;
      content += `${ep.summary}\n\n`;
      content += `### Script Outline:\n`;
      ep.script_outline?.forEach((point, i) => {
        content += `${i + 1}. ${point}\n`;
      });
      if (ep.cliffhanger) {
        content += `\n**Cliffhanger:** ${ep.cliffhanger}\n`;
      }
      content += '\n---\n\n';
    });
    
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.hero_name}-series.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Series downloaded!');
  };

  const renderStep1 = () => (
    <div className="space-y-6" data-testid="step-1-idea">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">1</span>
          Step 1 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Enter Your Story Idea</h2>
        <p className="text-slate-400">Describe your story in 2-3 lines</p>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <textarea
          value={storyIdea}
          onChange={(e) => setStoryIdea(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white text-base min-h-[150px] resize-none focus:border-purple-500 focus:outline-none"
          placeholder="Example: A young inventor named Mia discovers a magical toolbox that brings her drawings to life. She must use her creativity to solve problems in her neighborhood while keeping the magic a secret."
          maxLength={500}
          data-testid="story-idea-input"
        />
        <p className="text-xs text-slate-500 mt-2 text-right">{storyIdea.length}/500 characters</p>
      </div>

      {/* Preview Button */}
      <button
        onClick={handleShowPreview}
        disabled={loadingPreview}
        className="w-full py-4 rounded-xl border-2 border-dashed border-purple-500/50 text-purple-300 hover:bg-purple-500/10 transition-all flex items-center justify-center gap-2"
        data-testid="preview-btn"
      >
        {loadingPreview ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Eye className="w-5 h-5" />
        )}
        <span className="font-medium">See Example Output (FREE)</span>
      </button>

      <Button
        onClick={() => setStep(2)}
        disabled={storyIdea.length < 10}
        className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 py-6 text-lg"
        data-testid="next-step-btn"
      >
        Continue to Choose Length <ChevronRight className="w-5 h-5 ml-2" />
      </Button>

      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-amber-200 font-medium">Content Policy</p>
          <p className="text-xs text-amber-300/70">Copyrighted characters (Disney, Marvel, Pokemon, etc.) and celebrity names are not allowed.</p>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6" data-testid="step-2-length">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">2</span>
          Step 2 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Series Length</h2>
        <p className="text-slate-400">Select how many episodes you want</p>
      </div>

      <div className="grid gap-4">
        {EPISODE_OPTIONS.map((option) => (
          <button
            key={option.count}
            onClick={() => setEpisodeCount(option.count)}
            className={`relative p-6 rounded-xl border-2 transition-all text-left ${
              episodeCount === option.count
                ? 'border-purple-500 bg-purple-500/10'
                : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
            }`}
            data-testid={`episode-option-${option.count}`}
          >
            {option.popular && (
              <span className="absolute top-3 right-3 bg-purple-500 text-white text-xs font-bold px-2 py-1 rounded">
                POPULAR
              </span>
            )}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white">{option.label}</h3>
                <p className="text-sm text-slate-400 mt-1">{option.description}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-purple-400">{option.credits}</p>
                <p className="text-xs text-slate-500">credits</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2 flex-wrap">
              {Array.from({ length: option.count }, (_, i) => (
                <span key={i} className="bg-slate-800 text-slate-300 text-xs px-2 py-1 rounded">
                  Episode {i + 1}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-3">
        <Button
          onClick={() => setStep(1)}
          variant="outline"
          className="flex-1 border-slate-600"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button
          onClick={() => setStep(3)}
          className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
          data-testid="next-step-btn"
        >
          Continue to Generate <ChevronRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6" data-testid="step-3-generate">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-purple-500/20 text-purple-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold">3</span>
          Step 3 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Generate Your Series</h2>
        <p className="text-slate-400">Review and create your mini series</p>
      </div>

      {/* Summary */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4">Your Story</h3>
        <p className="text-slate-300 text-sm bg-slate-800/50 rounded-lg p-3">{storyIdea}</p>
        <div className="mt-4 flex items-center gap-4">
          <span className="bg-purple-500/20 text-purple-300 px-3 py-1 rounded-full text-sm">
            {episodeCount} Episodes
          </span>
          <span className="text-slate-400 text-sm">{getBaseCost()} credits</span>
        </div>
      </div>

      {/* Add-ons */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4">Optional Add-ons</h3>
        <div className="space-y-3">
          <button
            onClick={() => toggleAddOn('export_pdf')}
            className={`w-full p-4 rounded-lg border flex items-center justify-between ${
              addOns.includes('export_pdf')
                ? 'border-green-500 bg-green-500/10'
                : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center gap-3">
              <Download className={`w-5 h-5 ${addOns.includes('export_pdf') ? 'text-green-400' : 'text-slate-400'}`} />
              <div className="text-left">
                <p className="text-white font-medium">Export PDF</p>
                <p className="text-xs text-slate-400">Download as formatted PDF</p>
              </div>
            </div>
            <span className="text-green-400 font-bold">+10 cr</span>
          </button>

          <button
            onClick={() => toggleAddOn('commercial_license')}
            className={`w-full p-4 rounded-lg border flex items-center justify-between ${
              addOns.includes('commercial_license')
                ? 'border-yellow-500 bg-yellow-500/10'
                : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center gap-3">
              <Lock className={`w-5 h-5 ${addOns.includes('commercial_license') ? 'text-yellow-400' : 'text-slate-400'}`} />
              <div className="text-left">
                <p className="text-white font-medium">Commercial License</p>
                <p className="text-xs text-slate-400">Use for commercial purposes</p>
              </div>
            </div>
            <span className="text-yellow-400 font-bold">+15 cr</span>
          </button>
        </div>
      </div>

      {/* Pricing Summary */}
      <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-slate-300">Base ({episodeCount} episodes)</span>
          <span className="text-white font-medium">{getBaseCost()} credits</span>
        </div>
        {addOns.length > 0 && (
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-300">Add-ons</span>
            <span className="text-white font-medium">+{getAddOnCost()} credits</span>
          </div>
        )}
        <div className="border-t border-purple-500/30 pt-3 mt-3">
          <div className="flex items-center justify-between">
            <span className="text-purple-300 font-semibold">Total</span>
            <span className="text-2xl font-bold text-white">{getTotalCost()} credits</span>
          </div>
        </div>

        {userPlan === 'free' && !addOns.includes('commercial_license') && (
          <p className="text-xs text-amber-400 mt-3 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Free preview includes watermark. Upgrade for watermark-free content.
          </p>
        )}
      </div>

      <div className="flex gap-3">
        <Button
          onClick={() => setStep(2)}
          variant="outline"
          className="flex-1 border-slate-600"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button
          onClick={handleGenerate}
          disabled={generating || !canAfford}
          className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 py-6"
          data-testid="generate-btn"
        >
          {generating ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              Creating Series...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Create My Series
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

  const renderResult = () => (
    <div className="space-y-6" data-testid="result-section">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 bg-green-500/20 text-green-300 px-4 py-2 rounded-full text-sm mb-4">
          <CheckCircle className="w-5 h-5" />
          Series Created!
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">{result.hero_name}'s Adventure</h2>
        <p className="text-slate-400">{result.episode_count} episodes ready</p>
      </div>

      <div className="flex gap-3 mb-6">
        <Button onClick={handleDownload} className="flex-1 bg-green-600 hover:bg-green-700">
          <Download className="w-4 h-4 mr-2" /> Download Series
        </Button>
        <Button onClick={() => { setResult(null); setStep(1); setStoryIdea(''); }} variant="outline" className="flex-1 border-slate-600">
          Create Another
        </Button>
      </div>

      {result.has_watermark && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 flex items-center gap-2 text-sm">
          <Lock className="w-4 h-4 text-amber-400" />
          <span className="text-amber-300">Preview watermarked. Upgrade to remove.</span>
        </div>
      )}

      <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
        {result.episodes?.map((ep, idx) => (
          <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-bold text-white mb-2">{ep.title}</h3>
            <p className="text-slate-300 text-sm mb-4">{ep.summary}</p>
            
            <div className="bg-slate-800/50 rounded-lg p-4 mb-4">
              <p className="text-xs text-purple-400 font-medium mb-2">SCRIPT OUTLINE</p>
              <ol className="list-decimal list-inside space-y-1">
                {ep.script_outline?.map((point, i) => (
                  <li key={i} className="text-sm text-slate-300">{point}</li>
                ))}
              </ol>
            </div>

            {ep.cliffhanger && (
              <div className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-3">
                <p className="text-xs text-pink-400 font-medium mb-1">CLIFFHANGER</p>
                <p className="text-sm text-pink-200 italic">"{ep.cliffhanger}"</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );

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
        <div className="max-w-4xl mx-auto px-4 py-4">
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
                  <h1 className="text-lg font-bold text-white">Story Episode Creator</h1>
                  <p className="text-xs text-slate-400">Turn one idea into a binge-worthy mini series</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
              <Wallet className="w-4 h-4 text-purple-400" />
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
          </>
        )}
      </main>
    </div>
  );
}
