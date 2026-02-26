import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  Wand2, ArrowLeft, Loader2, Copy, Download,
  Wallet, RefreshCw, Sparkles, Smile, Flame,
  Feather, Crown, Zap, CheckCircle
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Slider } from '../components/ui/slider';
import api, { walletAPI } from '../utils/api';

const TONE_ICONS = {
  funny: Smile,
  aggressive: Flame,
  calm: Feather,
  luxury: Crown,
  motivational: Zap
};

const TONE_COLORS = {
  funny: 'from-yellow-500 to-orange-500',
  aggressive: 'from-red-500 to-pink-500',
  calm: 'from-green-500 to-teal-500',
  luxury: 'from-purple-500 to-indigo-500',
  motivational: 'from-blue-500 to-cyan-500'
};

export default function ToneSwitcher() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [wallet, setWallet] = useState({ availableCredits: 0 });
  const [pricing, setPricing] = useState({});
  const [tones, setTones] = useState({});
  
  // Form state
  const [originalText, setOriginalText] = useState('');
  const [targetTone, setTargetTone] = useState('funny');
  const [intensity, setIntensity] = useState(50);
  const [keepLength, setKeepLength] = useState('same');
  const [variationCount, setVariationCount] = useState(5);
  
  // Result state
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [walletRes, pricingRes, tonesRes] = await Promise.all([
        walletAPI.getWallet(),
        api.get('/api/tone-switcher/pricing'),
        api.get('/api/tone-switcher/tones')
      ]);
      
      setWallet(walletRes.data);
      setPricing(pricingRes.data);
      setTones(tonesRes.data.tones || {});
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getCost = () => {
    if (variationCount <= 1) return pricing.pricing?.SINGLE_REWRITE || 1;
    if (variationCount <= 5) return pricing.pricing?.BATCH_5 || 3;
    return pricing.pricing?.BATCH_10 || 5;
  };

  const canAfford = wallet.availableCredits >= getCost();

  const handlePreview = async () => {
    if (!originalText.trim()) {
      toast.error('Please enter some text to transform');
      return;
    }

    setPreviewing(true);
    setPreview(null);

    try {
      const response = await api.post('/api/tone-switcher/preview', {
        text: originalText.slice(0, 500),
        targetTone,
        intensity,
        keepLength,
        variationCount: 1
      });

      setPreview(response.data.preview);
    } catch (error) {
      toast.error('Preview failed');
    } finally {
      setPreviewing(false);
    }
  };

  const handleGenerate = async () => {
    if (!originalText.trim()) {
      toast.error('Please enter some text to transform');
      return;
    }

    if (!canAfford) {
      toast.error(`Need ${getCost()} credits. You have ${wallet.availableCredits}.`);
      return;
    }

    setGenerating(true);
    setResult(null);

    try {
      const response = await api.post('/api/tone-switcher/rewrite', {
        text: originalText,
        targetTone,
        intensity,
        keepLength,
        variationCount
      });

      if (response.data.success) {
        setResult(response.data);
        const walletRes = await walletAPI.getWallet();
        setWallet(walletRes.data);
        toast.success(`Generated ${variationCount} variation(s)!`);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Generation failed';
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async (text, index) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (e) {
      toast.error('Failed to copy');
    }
  };

  const handleDownload = () => {
    if (!result) return;
    
    let content = `Original Text:\n${originalText}\n\n`;
    content += `Tone: ${targetTone} (Intensity: ${intensity}%)\n\n`;
    content += `Variations:\n\n`;
    
    result.variations?.forEach((v, i) => {
      content += `--- Variation ${i + 1} ---\n${v.text}\n\n`;
    });
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tone-switched-${targetTone}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Downloaded!');
  };

  const ToneIcon = TONE_ICONS[targetTone] || Wand2;

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-cyan-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="text-slate-400 hover:text-white">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-2">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${TONE_COLORS[targetTone]} flex items-center justify-center`}>
                  <Wand2 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Tone Switcher</h1>
                  <p className="text-xs text-slate-400">AI-Free emotional tone rewriter</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Wallet className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-white">{wallet.availableCredits}</span>
                <span className="text-xs text-slate-500">credits</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Input */}
          <div className="space-y-6">
            {/* Original Text */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Original Text</h3>
              <textarea
                value={originalText}
                onChange={(e) => setOriginalText(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white text-sm min-h-[200px] resize-none"
                placeholder="Paste your script, caption, or any text you want to transform..."
                maxLength={5000}
              />
              <p className="text-xs text-slate-500 mt-2">{originalText.length}/5000 characters</p>
            </div>

            {/* Tone Selection */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Choose Tone</h3>
              <div className="grid grid-cols-5 gap-2">
                {Object.entries(tones).map(([key, info]) => {
                  const Icon = TONE_ICONS[key] || Wand2;
                  return (
                    <button
                      key={key}
                      onClick={() => setTargetTone(key)}
                      className={`p-3 rounded-lg border text-center transition-all ${
                        targetTone === key
                          ? `border-cyan-500 bg-gradient-to-br ${TONE_COLORS[key]} bg-opacity-20`
                          : 'border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <Icon className={`w-5 h-5 mx-auto mb-1 ${targetTone === key ? 'text-white' : 'text-slate-400'}`} />
                      <p className={`text-xs font-medium ${targetTone === key ? 'text-white' : 'text-slate-400'}`}>
                        {info.name}
                      </p>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-3">
                {tones[targetTone]?.description}
              </p>
            </div>

            {/* Settings */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs text-slate-400">Intensity</label>
                  <span className="text-xs text-cyan-400">{intensity}%</span>
                </div>
                <Slider
                  value={[intensity]}
                  onValueChange={(v) => setIntensity(v[0])}
                  max={100}
                  step={10}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-slate-600 mt-1">
                  <span>Subtle</span>
                  <span>Medium</span>
                  <span>Bold</span>
                </div>
              </div>
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Length Preference</label>
                <Select value={keepLength} onValueChange={setKeepLength}>
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="shorter">Make Shorter</SelectItem>
                    <SelectItem value="same">Keep Same Length</SelectItem>
                    <SelectItem value="longer">Make Longer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-xs text-slate-400 mb-2 block">Variations</label>
                <div className="flex gap-2">
                  {[1, 5, 10].map(num => (
                    <button
                      key={num}
                      onClick={() => setVariationCount(num)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                        variationCount === num
                          ? 'bg-cyan-500 text-white'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      {num === 1 ? 'Single' : `${num} Pack`}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Button
                onClick={handlePreview}
                disabled={previewing || !originalText.trim()}
                variant="outline"
                className="flex-1 border-slate-600"
              >
                {previewing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <RefreshCw className="w-4 h-4 mr-1" />}
                Free Preview
              </Button>
              
              <Button
                onClick={handleGenerate}
                disabled={generating || !canAfford || !originalText.trim()}
                className={`flex-1 bg-gradient-to-r ${TONE_COLORS[targetTone]}`}
                data-testid="generate-tone-btn"
              >
                {generating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Rewriting...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Generate ({getCost()} credits)
                  </span>
                )}
              </Button>
            </div>
          </div>

          {/* Right: Results */}
          <div className="space-y-6">
            {/* Preview */}
            {preview && !result && (
              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-cyan-300 mb-3">Preview (First 500 chars)</h3>
                <p className="text-white text-sm">{preview}</p>
                <p className="text-xs text-slate-500 mt-3">
                  Like what you see? Generate full variations with credits.
                </p>
              </div>
            )}

            {/* Full Results */}
            {result && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    {result.variations?.length} Variation(s) Generated
                  </h3>
                  <Button size="sm" onClick={handleDownload} className="bg-green-600 hover:bg-green-700">
                    <Download className="w-4 h-4 mr-1" /> Download All
                  </Button>
                </div>
                
                <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                  {result.variations?.map((v, idx) => (
                    <div key={idx} className="bg-slate-800/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-slate-500">
                          Variation {idx + 1} • Intensity {v.intensity}%
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleCopy(v.text, idx)}
                          className="text-slate-400 hover:text-white"
                        >
                          {copiedIndex === idx ? (
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                      <p className="text-white text-sm whitespace-pre-wrap">{v.text}</p>
                    </div>
                  ))}
                </div>
                
                <p className="text-xs text-slate-500 text-center mt-4">
                  Generated content is template-based and should be reviewed before posting.
                </p>
              </div>
            )}

            {/* Empty State */}
            {!preview && !result && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
                <ToneIcon className="w-20 h-20 text-slate-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Transform Your Text</h3>
                <p className="text-slate-400 max-w-md mx-auto">
                  Paste your text, choose a tone, and watch it transform.
                  No AI API costs - uses smart template transformations.
                </p>
              </div>
            )}

            {/* Tone Info */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <ToneIcon className="w-4 h-4" />
                {tones[targetTone]?.name} Tone
              </h3>
              <p className="text-sm text-slate-400 mb-3">
                {tones[targetTone]?.description}
              </p>
              <div className="flex flex-wrap gap-2">
                {tones[targetTone]?.sampleEmojis?.map((emoji, i) => (
                  <span key={i} className="text-lg">{emoji}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
