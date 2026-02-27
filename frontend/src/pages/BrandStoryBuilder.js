import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, AlertTriangle, BookOpen, Building2, Download } from 'lucide-react';
import { toast } from 'sonner';
import HelpGuide from '../components/HelpGuide';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BrandStoryBuilder = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [copied, setCopied] = useState(null);
  
  // Form state
  const [businessName, setBusinessName] = useState('');
  const [mission, setMission] = useState('');
  const [founderStory, setFounderStory] = useState('');
  const [industry, setIndustry] = useState('Technology');
  const [tone, setTone] = useState('professional');
  
  // Results
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/brand-story-builder/config`);
      if (res.ok) setConfig(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!businessName.trim() || !mission.trim() || !founderStory.trim()) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/brand-story-builder/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ business_name: businessName, mission, founder_story: founderStory, industry, tone })
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
    const content = `BRAND STORY\n${'='.repeat(50)}\n\n${result.brand_story}\n\n\nELEVATOR PITCH\n${'='.repeat(50)}\n\n${result.elevator_pitch}\n\n\nABOUT SECTION\n${'='.repeat(50)}\n\n${result.about_section}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${businessName.replace(/\s+/g, '-')}-brand-story.txt`;
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/app" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Building2 className="w-6 h-6 text-blue-400" />
                Brand Story Builder
              </h1>
              <p className="text-slate-400 text-sm">Create your complete brand narrative</p>
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
              <li>Enter your business details</li>
              <li>Select your industry and tone</li>
              <li>Click generate</li>
              <li>Copy & use on your website</li>
            </ol>
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <h4 className="text-red-400 font-medium mb-2">What Not To Do</h4>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>Do not copy competitor brand stories</li>
                <li>Do not use trademark slogans</li>
              </ul>
            </div>
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
            {/* Business Name */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Business Name *</label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="Your business or brand name"
                maxLength={100}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="business-name-input"
              />
            </div>

            {/* Mission */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Mission Statement * (10-300 chars)</label>
              <textarea
                value={mission}
                onChange={(e) => setMission(e.target.value)}
                placeholder="What is your mission? What do you aim to achieve?"
                maxLength={300}
                rows={2}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="mission-input"
              />
              <p className="text-xs text-slate-500 mt-1">{mission.length}/300</p>
            </div>

            {/* Founder Story */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Founder Story * (20-500 chars)</label>
              <textarea
                value={founderStory}
                onChange={(e) => setFounderStory(e.target.value)}
                placeholder="Share the journey - what inspired you to start this business?"
                maxLength={500}
                rows={4}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid="founder-story-input"
              />
              <p className="text-xs text-slate-500 mt-1">{founderStory.length}/500</p>
            </div>

            {/* Industry & Tone */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Industry</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white"
                  data-testid="industry-select"
                >
                  {config?.industries?.map(i => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
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
              disabled={generating || !businessName.trim() || mission.length < 10 || founderStory.length < 20}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-medium py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="generate-btn"
            >
              {generating ? (
                <>
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                  Building Story...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Build Brand Story (18 Credits)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold text-white">Your Brand Story</h2>
              <button
                onClick={downloadAll}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm"
              >
                <Download className="w-4 h-4" /> Download All
              </button>
            </div>

            {/* Brand Story */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">Brand Story</h3>
                <button
                  onClick={() => copyText(result.brand_story, 'story')}
                  className="p-2 hover:bg-slate-700 rounded-lg"
                >
                  {copied === 'story' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300 whitespace-pre-line">{result.brand_story}</p>
            </div>

            {/* Elevator Pitch */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">Elevator Pitch</h3>
                <button
                  onClick={() => copyText(result.elevator_pitch, 'pitch')}
                  className="p-2 hover:bg-slate-700 rounded-lg"
                >
                  {copied === 'pitch' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300">{result.elevator_pitch}</p>
            </div>

            {/* About Section */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-bold text-white">Website About Section</h3>
                <button
                  onClick={() => copyText(result.about_section, 'about')}
                  className="p-2 hover:bg-slate-700 rounded-lg"
                >
                  {copied === 'about' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
              </div>
              <p className="text-slate-300 whitespace-pre-line">{result.about_section}</p>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-xs">
          Copyright 2026 CreatorStudio AI. All rights reserved.
        </div>
      </div>
      
      {/* Help Guide */}
      <HelpGuide pageId="brand-story-builder" />
    </div>
  );
};

export default BrandStoryBuilder;
