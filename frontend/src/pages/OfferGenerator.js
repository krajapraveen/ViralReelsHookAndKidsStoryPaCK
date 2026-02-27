import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, AlertTriangle, BookOpen, DollarSign, Download, Gift, Shield } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OfferGenerator = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [copied, setCopied] = useState(null);
  
  // Form state
  const [productName, setProductName] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [mainProblem, setMainProblem] = useState('');
  const [priceRange, setPriceRange] = useState('');
  const [tone, setTone] = useState('bold');
  
  // Results
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/offer-generator/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!productName.trim() || !targetAudience.trim() || !mainProblem.trim()) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/offer-generator/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          product_name: productName,
          target_audience: targetAudience,
          main_problem: mainProblem,
          price_range: priceRange || '97',
          tone
        })
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setResult(data);
        toast.success(`Generated in ${data.generation_time_ms}ms!`);
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (e) {
      toast.error('Failed to generate');
    } finally {
      setGenerating(false);
    }
  };

  const copyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied!');
  };

  const downloadAll = () => {
    if (!result) return;
    const bonusText = result.bonuses.map((b, i) => `Bonus ${i+1}: ${b.name} (${b.value})\n${b.description}`).join('\n\n');
    const content = `OFFER: ${result.offer_name}\n${'='.repeat(50)}\n\nHOOK:\n${result.offer_hook}\n\n\nBONUSES:\n${'='.repeat(50)}\n${bonusText}\n\n\nGUARANTEE:\n${'='.repeat(50)}\n${result.guarantee}\n\n\nPRICING ANGLE:\n${'='.repeat(50)}\n${result.pricing_angle}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${productName.replace(/\s+/g, '-')}-offer.txt`;
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-green-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-green-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <DollarSign className="w-6 h-6 text-green-400" />
                Offer Generator
              </h1>
              <p className="text-slate-400 text-sm">Create irresistible offers that convert</p>
            </div>
          </div>
          <button
            onClick={() => setShowManual(!showManual)}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg text-slate-300 hover:bg-slate-700 text-sm"
          >
            <BookOpen className="w-4 h-4" /> User Manual
          </button>
        </div>

        {/* User Manual */}
        {showManual && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-6">
            <h3 className="text-lg font-bold text-white mb-4">How to Use</h3>
            <ol className="space-y-2 text-slate-300 text-sm list-decimal list-inside">
              <li>Describe your product or service</li>
              <li>Define your target audience</li>
              <li>Identify the main problem you solve</li>
              <li>Click generate</li>
              <li>Adjust & launch your offer</li>
            </ol>
          </div>
        )}

        {/* Copyright Disclaimer */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-6 flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-200 text-sm">
            All generated content is original and generic. Do not include copyrighted or trademarked content.
          </p>
        </div>

        {/* Generator Form */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 mb-6">
          <div className="space-y-4">
            {/* Product Name */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Product/Service Name *</label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g., Instagram Growth Course, Fitness Coaching"
                maxLength={100}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                data-testid="product-input"
              />
            </div>

            {/* Target Audience */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Target Audience *</label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="e.g., Small business owners, Fitness enthusiasts"
                maxLength={100}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                data-testid="audience-input"
              />
            </div>

            {/* Main Problem */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Main Problem You Solve *</label>
              <textarea
                value={mainProblem}
                onChange={(e) => setMainProblem(e.target.value)}
                placeholder="What pain point or challenge does your offer address?"
                maxLength={200}
                rows={2}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                data-testid="problem-input"
              />
              <p className="text-xs text-slate-500 mt-1">{mainProblem.length}/200</p>
            </div>

            {/* Price & Tone */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Price Range (optional)</label>
                <input
                  type="text"
                  value={priceRange}
                  onChange={(e) => setPriceRange(e.target.value)}
                  placeholder="e.g., 97, 197, 497"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                  data-testid="price-input"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Tone</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="tone-select"
                >
                  {config?.tones?.map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={generating || !productName.trim() || !targetAudience.trim() || !mainProblem.trim()}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white font-medium py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="generate-btn"
            >
              {generating ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  Generating Offer...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Generate Offer (20 Credits)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-white">Your Irresistible Offer</h2>
              <button
                onClick={downloadAll}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm"
              >
                <Download className="w-4 h-4" /> Download All
              </button>
            </div>

            {/* Offer Name */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">Offer Name</h3>
                <button onClick={() => copyText(result.offer_name, 'name')} className="p-2 hover:bg-slate-700 rounded-lg">
                  {copied === 'name' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-2xl font-bold text-green-400">{result.offer_name}</p>
            </div>

            {/* Offer Hook */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">Offer Hook</h3>
                <button onClick={() => copyText(result.offer_hook, 'hook')} className="p-2 hover:bg-slate-700 rounded-lg">
                  {copied === 'hook' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300 text-lg">{result.offer_hook}</p>
            </div>

            {/* Bonuses */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Gift className="w-5 h-5 text-yellow-400" /> Bonus Ideas
              </h3>
              <div className="space-y-4">
                {result.bonuses?.map((bonus, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl p-4 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-white">{bonus.name}</span>
                        <span className="text-green-400 text-sm">({bonus.value})</span>
                      </div>
                      <p className="text-slate-400 text-sm">{bonus.description}</p>
                    </div>
                    <button onClick={() => copyText(`${bonus.name}: ${bonus.description}`, `bonus-${i}`)} className="p-2 hover:bg-slate-700 rounded-lg">
                      {copied === `bonus-${i}` ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Guarantee */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" /> Guarantee
                </h3>
                <button onClick={() => copyText(result.guarantee, 'guarantee')} className="p-2 hover:bg-slate-700 rounded-lg">
                  {copied === 'guarantee' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300">{result.guarantee}</p>
            </div>

            {/* Pricing Angle */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-400" /> Pricing Angle
                </h3>
                <button onClick={() => copyText(result.pricing_angle, 'pricing')} className="p-2 hover:bg-slate-700 rounded-lg">
                  {copied === 'pricing' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300 whitespace-pre-line">{result.pricing_angle}</p>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Copyright 2026 CreatorStudio AI. All rights reserved.
        </div>
      </div>
    </div>
  );
};

export default OfferGenerator;
