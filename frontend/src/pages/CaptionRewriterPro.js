import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  Wand2, ArrowLeft, Loader2, Copy, Download,
  Wallet, CheckCircle, ChevronRight, Lock,
  Smile, Sparkles, Heart, Rocket, BookOpen,
  AlertTriangle, Crown, Eye, X
} from 'lucide-react';
import api, { walletAPI } from '../utils/api';

const TONES = [
  { id: 'funny', name: 'Funny', emoji: '😂', icon: Smile, color: 'from-yellow-500 to-orange-500', description: 'Add humor and make people laugh' },
  { id: 'luxury', name: 'Luxury', emoji: '✨', icon: Crown, color: 'from-purple-500 to-indigo-500', description: 'Sophisticated and premium feel' },
  { id: 'bold', name: 'Bold', emoji: '💪', icon: Sparkles, color: 'from-red-500 to-pink-500', description: 'Confident, direct, no-nonsense' },
  { id: 'emotional', name: 'Emotional', emoji: '❤️', icon: Heart, color: 'from-pink-400 to-rose-500', description: 'Heartfelt and touching' },
  { id: 'motivational', name: 'Motivational', emoji: '🚀', icon: Rocket, color: 'from-blue-500 to-cyan-500', description: 'Inspiring and empowering' },
  { id: 'storytelling', name: 'Storytelling', emoji: '📖', icon: BookOpen, color: 'from-green-500 to-teal-500', description: 'Narrative and engaging' }
];

const PACK_OPTIONS = [
  { id: 'single_tone', label: 'Single Tone', credits: 5, variations: 3, description: '3 variations in 1 tone' },
  { id: 'three_tones', label: '3 Tones Pack', credits: 12, variations: 9, description: '3 variations × 3 tones', popular: true },
  { id: 'all_tones', label: 'All Tones Pack', credits: 20, variations: 18, description: '3 variations × 6 tones' }
];

export default function CaptionRewriterPro() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [userPlan, setUserPlan] = useState('free');
  
  // Wizard state
  const [step, setStep] = useState(1);
  const [text, setText] = useState('');
  const [tone, setTone] = useState('');
  const [packType, setPackType] = useState('single_tone');
  const [addCommercial, setAddCommercial] = useState(false);
  
  // Result state
  const [result, setResult] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  
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
      const response = await api.get('/api/caption-rewriter-pro/preview');
      setPreviewData(response.data);
      setShowPreview(true);
    } catch (error) {
      toast.error('Failed to load preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  const getBaseCost = () => {
    const option = PACK_OPTIONS.find(p => p.id === packType);
    return option?.credits || 5;
  };

  const getTotalCost = () => {
    let cost = getBaseCost();
    if (addCommercial) cost += 10;
    return cost;
  };

  const canAfford = wallet.availableCredits >= getTotalCost();

  const handleGenerate = async () => {
    if (!text.trim() || text.length < 10) {
      toast.error('Please enter text (at least 10 characters)');
      return;
    }

    if (!tone) {
      toast.error('Please select a tone');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${getTotalCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);

    try {
      const response = await api.post('/api/caption-rewriter-pro/rewrite', {
        text: text.trim(),
        tone,
        pack_type: packType,
        add_ons: addCommercial ? ['commercial_use'] : []
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

  const handleCopy = async (textToCopy, id) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedId(id);
      toast.success('Copied!');
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      toast.error('Failed to copy');
    }
  };

  const handleDownload = () => {
    if (!result) return;
    
    let content = `# Caption Rewrites\n\n`;
    content += `Original: ${result.original_text}\n\n`;
    
    Object.entries(result.results || {}).forEach(([toneKey, toneData]) => {
      content += `## ${toneData.emoji} ${toneData.tone_name}\n\n`;
      toneData.variations?.forEach((v, i) => {
        content += `### Variation ${i + 1}\n${v.text}\n\n`;
      });
    });
    
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'caption-rewrites.md';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Downloaded!');
  };

  const renderStep1 = () => (
    <div className="space-y-6" data-testid="step-1-text">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-cyan-500/20 text-cyan-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">1</span>
          Step 1 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Paste Your Text</h2>
        <p className="text-slate-400">Enter the caption or content you want to rewrite</p>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white text-base min-h-[180px] resize-none focus:border-cyan-500 focus:outline-none"
          placeholder="Example: Check out our new product! It's really good and you should buy it. We think you'll love it."
          maxLength={2000}
          data-testid="text-input"
        />
        <p className="text-xs text-slate-500 mt-2 text-right">{text.length}/2000 characters</p>
      </div>

      {/* Preview Button */}
      <button
        onClick={handleShowPreview}
        disabled={loadingPreview}
        className="w-full py-4 rounded-xl border-2 border-dashed border-cyan-500/50 text-cyan-300 hover:bg-cyan-500/10 transition-all flex items-center justify-center gap-2"
        data-testid="preview-btn"
      >
        {loadingPreview ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Eye className="w-5 h-5" />
        )}
        <span className="font-medium">See Example Rewrites (FREE)</span>
      </button>

      <Button
        onClick={() => setStep(2)}
        disabled={text.length < 10}
        className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 py-6 text-lg"
        data-testid="next-step-btn"
      >
        Continue to Choose Tone <ChevronRight className="w-5 h-5 ml-2" />
      </Button>

      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-amber-200 font-medium">Content Policy</p>
          <p className="text-xs text-amber-300/70">Copyrighted content, brand names, and celebrity references are not allowed.</p>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6" data-testid="step-2-tone">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-cyan-500/20 text-cyan-300 px-4 py-2 rounded-full text-sm mb-4">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">2</span>
          Step 2 of 3
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Choose Tone</h2>
        <p className="text-slate-400">Select a viral tone for your rewrite</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {TONES.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTone(t.id)}
              className={`p-5 rounded-xl border-2 transition-all text-left ${
                tone === t.id
                  ? 'border-cyan-500 bg-cyan-500/10'
                  : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
              }`}
              data-testid={`tone-${t.id}`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${t.color} flex items-center justify-center`}>
                  <span className="text-xl">{t.emoji}</span>
                </div>
                <h3 className="text-lg font-bold text-white">{t.name}</h3>
              </div>
              <p className="text-xs text-slate-400">{t.description}</p>
            </button>
          );
        })}
      </div>

      <div className="flex gap-3">
        <Button onClick={() => setStep(1)} variant="outline" className="flex-1 border-slate-600">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Button>
        <Button
          onClick={() => setStep(3)}
          disabled={!tone}
          className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
          data-testid="next-step-btn"
        >
          Continue <ChevronRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStep3 = () => {
    const selectedTone = TONES.find(t => t.id === tone);

    return (
      <div className="space-y-6" data-testid="step-3-generate">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-cyan-500/20 text-cyan-300 px-4 py-2 rounded-full text-sm mb-4">
            <span className="w-6 h-6 rounded-full bg-cyan-500 text-white flex items-center justify-center text-xs font-bold">3</span>
            Step 3 of 3
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Generate Rewrite</h2>
          <p className="text-slate-400">Choose pack and generate 3 variations</p>
        </div>

        {/* Summary */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">{selectedTone?.emoji}</span>
            <div>
              <h3 className="text-white font-medium">{selectedTone?.name} Tone</h3>
              <p className="text-xs text-slate-400">{selectedTone?.description}</p>
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-sm text-slate-300 line-clamp-3">{text}</p>
          </div>
        </div>

        {/* Pack Selection */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4">Choose Pack</h3>
          <div className="space-y-3">
            {PACK_OPTIONS.map((pack) => (
              <button
                key={pack.id}
                onClick={() => setPackType(pack.id)}
                className={`w-full p-4 rounded-lg border-2 flex items-center justify-between ${
                  packType === pack.id
                    ? 'border-cyan-500 bg-cyan-500/10'
                    : 'border-slate-700 hover:border-slate-600'
                }`}
                data-testid={`pack-${pack.id}`}
              >
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <p className="text-white font-medium">{pack.label}</p>
                    {pack.popular && (
                      <span className="bg-cyan-500 text-white text-xs px-2 py-0.5 rounded">BEST VALUE</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{pack.description}</p>
                </div>
                <span className="text-cyan-400 font-bold">{pack.credits} cr</span>
              </button>
            ))}
          </div>
        </div>

        {/* Commercial License */}
        <button
          onClick={() => setAddCommercial(!addCommercial)}
          className={`w-full p-4 rounded-xl border flex items-center justify-between ${
            addCommercial
              ? 'border-yellow-500 bg-yellow-500/10'
              : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'
          }`}
        >
          <div className="flex items-center gap-3">
            <Lock className={`w-5 h-5 ${addCommercial ? 'text-yellow-400' : 'text-slate-400'}`} />
            <div className="text-left">
              <p className="text-white font-medium">Commercial Use</p>
              <p className="text-xs text-slate-400">Use for commercial purposes</p>
            </div>
          </div>
          <span className="text-yellow-400 font-bold">+10 cr</span>
        </button>

        {/* Pricing */}
        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-300">Pack ({PACK_OPTIONS.find(p => p.id === packType)?.label})</span>
            <span className="text-white font-medium">{getBaseCost()} credits</span>
          </div>
          {addCommercial && (
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300">Commercial Use</span>
              <span className="text-white font-medium">+10 credits</span>
            </div>
          )}
          <div className="border-t border-cyan-500/30 pt-3 mt-3">
            <div className="flex items-center justify-between">
              <span className="text-cyan-300 font-semibold">Total</span>
              <span className="text-2xl font-bold text-white">{getTotalCost()} credits</span>
            </div>
          </div>

          {userPlan === 'free' && !addCommercial && (
            <p className="text-xs text-amber-400 mt-3 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Free preview. Add Commercial Use for unrestricted usage.
            </p>
          )}
        </div>

        <div className="flex gap-3">
          <Button onClick={() => setStep(2)} variant="outline" className="flex-1 border-slate-600">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generating || !canAfford}
            className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 py-6"
            data-testid="generate-btn"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Rewriting...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Generate Rewrites
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
          {result.total_variations} Variations Ready!
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Your Rewrites</h2>
        <p className="text-slate-400">Copy or download your new captions</p>
      </div>

      <div className="flex gap-3 mb-6">
        <Button onClick={handleDownload} className="flex-1 bg-green-600 hover:bg-green-700">
          <Download className="w-4 h-4 mr-2" /> Download All
        </Button>
        <Button onClick={() => { setResult(null); setStep(1); setText(''); setTone(''); }} variant="outline" className="flex-1 border-slate-600">
          Rewrite Another
        </Button>
      </div>

      {/* Original */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <p className="text-xs text-slate-500 mb-2">ORIGINAL</p>
        <p className="text-sm text-slate-400">{result.original_text}</p>
      </div>

      {/* Results by Tone */}
      <div className="space-y-6">
        {Object.entries(result.results || {}).map(([toneKey, toneData]) => (
          <div key={toneKey} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">{toneData.emoji}</span>
              <h3 className="text-lg font-bold text-white">{toneData.tone_name}</h3>
            </div>
            
            <div className="space-y-3">
              {toneData.variations?.map((v, i) => {
                const copyId = `${toneKey}-${i}`;
                return (
                  <div key={i} className="bg-slate-800/50 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <p className="text-xs text-slate-500 mb-1">Variation {v.variation}</p>
                        <p className="text-white text-sm">{v.text}</p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopy(v.text, copyId)}
                        className="flex-shrink-0"
                      >
                        {copiedId === copyId ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-slate-400" />
                        )}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Preview Modal */}
      {showPreview && previewData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-cyan-500/30 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-cyan-500/20 to-blue-500/20 p-4 border-b border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                  <Eye className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">FREE Preview</h3>
                  <p className="text-xs text-cyan-300">See what you'll get before you commit</p>
                </div>
              </div>
              <button onClick={() => setShowPreview(false)} className="text-slate-400 hover:text-white p-2">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3 mb-4">
                <p className="text-xs text-cyan-400 mb-1">ORIGINAL TEXT</p>
                <p className="text-white text-sm">{previewData.original_text}</p>
              </div>
              
              <div className="space-y-4">
                {Object.entries(previewData.results || {}).map(([toneKey, toneData]) => (
                  <div key={toneKey} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xl">{toneData.emoji}</span>
                      <h4 className="text-white font-bold">{toneData.tone_name}</h4>
                    </div>
                    <div className="space-y-2">
                      {toneData.variations?.slice(0, 2).map((v, i) => (
                        <div key={i} className="bg-slate-900/50 rounded p-3">
                          <p className="text-xs text-slate-500 mb-1">Variation {v.variation}</p>
                          <p className="text-sm text-slate-300">{v.text}</p>
                        </div>
                      ))}
                      <p className="text-xs text-slate-500 italic text-center">...and more variations</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-700 bg-slate-800/50">
              <p className="text-xs text-center text-slate-400 mb-3">{previewData.preview_message}</p>
              <Button 
                onClick={() => setShowPreview(false)} 
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
              >
                <Sparkles className="w-4 h-4 mr-2" /> Create Your Own Rewrites
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
                  <Wand2 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">Caption Rewriter Pro</h1>
                  <p className="text-xs text-slate-400">Rewrite your content in viral tones instantly</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
              <Wallet className="w-4 h-4 text-cyan-400" />
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
